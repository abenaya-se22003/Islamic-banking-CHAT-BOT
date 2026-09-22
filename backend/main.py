"""
Steps 7, 8 & 9: Search + Answer FastAPI Endpoint with Tool Calling
===================================================================
Islamic Banking Chatbot API with Claude Agent Function Calling & Report Generation

Features:
- Document retrieval using Neon Postgres + pgvector (BAAI/bge-large-en-v1.5)
- Anthropic Claude API (claude-sonnet-4-6) with Tool Use / Function Calling
- generate_report tool creates downloadable Word (.docx) documents
- Static file serving at /reports for generated reports
- Full CORS support for React frontend (localhost:3000, 5173)
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg2 import register_vector
import psycopg2
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from tools.report_tool import generate_report, REPORTS_DIR

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Embedding model name (matches embed_and_store.py)
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CLAUDE_MODEL_NAME = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
SYSTEM_PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "system_prompt.txt")

# Global state for loaded model & cached system prompt
ml_models = {}

# ---------------------------------------------------------------------------
# Claude Tools / Function Calling Schema
# ---------------------------------------------------------------------------
REPORT_TOOLS = [
    {
        "name": "generate_report",
        "description": (
            "Generates a downloadable Word report (.docx). Use ONLY when the user "
            "explicitly asks for a report, downloadable summary, or document export."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The title or topic of the report (e.g., 'Murabaha Home Financing Report')."
                },
                "content_summary": {
                    "type": "string",
                    "description": (
                        "Comprehensive Shariah summary, product details, eligibility, "
                        "and rules based strictly on verified document excerpts."
                    )
                }
            },
            "required": ["topic", "content_summary"]
        }
    }
]


# ---------------------------------------------------------------------------
# Lifespan context manager: preloads embedding model and system prompt once
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🤖 Initializing embedding model: {EMBEDDING_MODEL_NAME}...")
    try:
        # Load embedding model into memory on server startup
        ml_models["embedding_model"] = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("✅ Embedding model loaded successfully.")
    except Exception as exc:
        print(f"❌ Failed to load embedding model: {exc}")
        ml_models["embedding_model"] = None

    # Load system prompt template
    if os.path.exists(SYSTEM_PROMPT_FILE):
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt_text = f.read()
            # Replace placeholder bank name if present
            prompt_text = prompt_text.replace("[Bank Name]", "LOLC Al-Falaah")
            ml_models["system_prompt"] = prompt_text
            print("✅ System prompt loaded.")
    else:
        ml_models["system_prompt"] = (
            "You are the Islamic Banking Assistant for LOLC Al-Falaah. "
            "Answer questions strictly based on the provided document excerpts."
        )
        print(f"⚠️ System prompt file not found at {SYSTEM_PROMPT_FILE}. Using fallback.")

    yield
    # Cleanup on shutdown
    ml_models.clear()


# ---------------------------------------------------------------------------
# FastAPI Application setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Islamic Banking Chatbot API",
    description="RAG-powered conversational assistant with agent report generation",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"  # Allows all origins for development and API consumers
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static Files: Serve generated Word reports at /reports/<filename>
# ---------------------------------------------------------------------------
os.makedirs(REPORTS_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="The user's question or report request about Islamic banking",
        example="Can you generate a report on Murabaha home financing?"
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Shariah-compliant assistant response")
    sources: List[str] = Field(
        default_factory=list,
        description="List of document names used to generate the answer"
    )
    report_url: Optional[str] = Field(
        None,
        description="Download URL for the generated Word report, or null if no report was generated"
    )


# ---------------------------------------------------------------------------
# Database & Client Helpers
# ---------------------------------------------------------------------------
def get_db_connection():
    """
    Connects to Neon Postgres using NEON_DATABASE_URL or Neon_db.
    """
    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection string not configured. Set NEON_DATABASE_URL in backend/.env."
        )

    try:
        conn = psycopg2.connect(db_url)
        register_vector(conn)
        return conn
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to database: {str(exc)}"
        )


def retrieve_top_chunks(query_embedding: list[float], top_k: int = 5):
    """
    Queries document_chunks using pgvector cosine distance (<=> operator).
    Returns list of tuples: (document_name, chunk_index, chunk_text, similarity)
    """
    conn = get_db_connection()
    try:
        sql = """
            SELECT document_name, chunk_index, chunk_text,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        with conn.cursor() as cur:
            cur.execute(sql, (query_embedding, query_embedding, top_k))
            rows = cur.fetchall()
        return rows
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search query failed: {str(exc)}"
        )
    finally:
        conn.close()


def get_claude_client() -> anthropic.Anthropic:
    """
    Instantiates Anthropic client using ANTHROPIC_API_KEY or CLAUDE_API env vars.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anthropic API key not configured. Set ANTHROPIC_API_KEY in backend/.env."
        )
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def health_check():
    """
    Health check endpoint to verify backend status.
    """
    return {
        "status": "online",
        "service": "Islamic Banking Chatbot API",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "llm_model": CLAUDE_MODEL_NAME,
        "tools_enabled": ["generate_report"],
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """
    Search + Answer with Agent Tool Calling Endpoint:
    1. Embeds question using BAAI/bge-large-en-v1.5
    2. Performs pgvector cosine similarity search (<=>) on Neon Postgres
    3. Formats prompt with system guidelines + retrieved excerpts + question
    4. Calls Claude API with tool definitions (generate_report)
    5. If Claude triggers tool_use:
       - Runs generate_report() locally
       - Feeds tool_result back to Claude for final response
       - Captures download_url for the response
    6. Returns answer, sources, and report_url (or null)
    """
    user_question = request.question.strip()
    if not user_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # 1. Generate query embedding
    model: Optional[SentenceTransformer] = ml_models.get("embedding_model")
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not ready. Please check server logs."
        )

    try:
        # BGE recommendation: prefix query with "Represent this sentence: " for retrieval
        query_text = f"Represent this sentence: {user_question}"
        query_embedding = model.encode(query_text, normalize_embeddings=True).tolist()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(exc)}"
        )

    # 2. Retrieve top 5 most similar chunks from pgvector
    chunks = retrieve_top_chunks(query_embedding, top_k=5)

    if not chunks:
        return ChatResponse(
            answer="I don't have enough information in our documents to answer this. Please contact a bank representative or Shariah advisor.",
            sources=[],
            report_url=None
        )

    # Format retrieved chunks and collect unique sources
    context_blocks = []
    sources = []
    for doc_name, chunk_idx, chunk_text, _sim in chunks:
        context_blocks.append(
            f"--- Document: {doc_name} (Chunk #{chunk_idx}) ---\n{chunk_text.strip()}"
        )
        if doc_name not in sources:
            sources.append(doc_name)

    context_str = "\n\n".join(context_blocks)

    # 3. Read system prompt
    system_prompt = ml_models.get(
        "system_prompt",
        "You are the Islamic Banking Assistant. Answer strictly based on the provided documents."
    )

    # 4. Build user message combining document excerpts and the user's question
    user_prompt_content = (
        f"DOCUMENT EXCERPTS:\n"
        f"==================\n"
        f"{context_str}\n\n"
        f"==================\n"
        f"USER REQUEST:\n"
        f"{user_question}\n\n"
        f"Instructions:\n"
        f"- Answer accurately and strictly based on the excerpts provided.\n"
        f"- If the user explicitly asks for a report, call the generate_report tool."
    )

    # 5. Call Claude API with tool definition
    client = get_claude_client()
    try:
        messages = [
            {"role": "user", "content": user_prompt_content}
        ]

        response = client.messages.create(
            model=CLAUDE_MODEL_NAME,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=REPORT_TOOLS,
        )

        # 6. Check for tool_use blocks in Claude's response
        report_url = None
        tool_use_block = None

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_report":
                tool_use_block = block
                break

        # Handle tool execution
        if tool_use_block:
            tool_input = tool_use_block.input or {}
            topic = tool_input.get("topic", "Islamic Banking Report")
            content_summary = tool_input.get("content_summary", "")

            # Execute Python function locally
            tool_result = generate_report(topic=topic, content_summary=content_summary)

            if tool_result.get("status") == "success":
                report_url = tool_result.get("download_url")

            # Send tool result back to Claude to formulate final response
            follow_up_messages = [
                {"role": "user", "content": user_prompt_content},
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": json.dumps(tool_result),
                        }
                    ],
                },
            ]

            follow_up_response = client.messages.create(
                model=CLAUDE_MODEL_NAME,
                max_tokens=1024,
                system=system_prompt,
                messages=follow_up_messages,
                tools=REPORT_TOOLS,
            )

            # Extract final text from follow-up response
            answer_text = "".join(
                block.text for block in follow_up_response.content if hasattr(block, "text")
            )

        else:
            # Standard response without tool execution
            answer_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )

        if not answer_text.strip():
            if report_url:
                answer_text = f"Your report has been generated successfully. You can download it using the link provided."
            else:
                answer_text = "I don't have enough information in our documents to answer this. Please contact a bank representative or Shariah advisor."

        return ChatResponse(
            answer=answer_text.strip(),
            sources=sources,
            report_url=report_url
        )

    except anthropic.APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to connect to Claude API: {str(exc)}"
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Claude API rate limit reached. Please try again in a moment."
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API returned error ({exc.status_code}): {exc.message}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(exc)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
