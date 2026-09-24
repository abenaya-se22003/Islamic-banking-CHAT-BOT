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

import asyncio
import json
import os
import sys
import hashlib
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# Force UTF-8 on Windows console to prevent UnicodeEncodeError with emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, status
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg2 import register_vector
import psycopg2
from psycopg2 import pool
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# Optional Redis cache — falls back to LRU if Redis is not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from tools.report_tool import generate_report, REPORTS_DIR
from tools.url_tool import fetch_url_content

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Embedding model name — configurable via .env (default: bge-large for accuracy)
# Set EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 in .env for faster (slightly less accurate) embeddings
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
SYSTEM_PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "system_prompt.txt")


# Redis config (optional — set REDIS_URL in .env to enable)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
EMBEDDING_CACHE_TTL = int(os.environ.get("EMBEDDING_CACHE_TTL", "3600"))  # 1 hour default

# Global state for loaded model & cached system prompt
ml_models = {}

# Connection pool & cached clients (initialized in lifespan)
db_pool = None
gemini_client_cache = None
redis_client = None

# ---------------------------------------------------------------------------
# Gemini Agent Tools / Function Calling Schema
# ---------------------------------------------------------------------------
AGENT_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="generate_report",
            description=(
                "Generates a downloadable Word report (.docx). Use ONLY when the user "
                "explicitly asks for a report, downloadable summary, or document export."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "topic": {
                        "type": "STRING",
                        "description": "The title or topic of the report (e.g., 'Murabaha Home Financing Report')."
                    },
                    "content_summary": {
                        "type": "STRING",
                        "description": (
                            "Comprehensive Shariah summary, product details, eligibility, "
                            "and rules based strictly on verified document excerpts."
                        )
                    }
                },
                "required": ["topic", "content_summary"]
            }
        ),
        types.FunctionDeclaration(
            name="fetch_url_content",
            description=(
                "Fetches, reads, and extracts clean readable text content from any web page, "
                "documentation link, or online URL. Use this whenever the user provides a web link, "
                "asks to read/summarize an online resource, or when online Shariah documentation needs inspection."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "url": {
                        "type": "STRING",
                        "description": "The complete HTTP or HTTPS URL to fetch and read."
                    }
                },
                "required": ["url"]
            }
        )
    ]
)


def handle_agent_tool_call(call_name: str, call_args: dict):
    """
    Executes agent tool functions locally.
    Returns: (tool_result_dict, report_url_or_none, fetched_url_or_none)
    """
    if call_name == "generate_report":
        topic = call_args.get("topic", "Islamic Banking Report")
        content_summary = call_args.get("content_summary", "")
        res = generate_report(topic=topic, content_summary=content_summary)
        rep_url = res.get("download_url") if res.get("status") == "success" else None
        return res, rep_url, None
    elif call_name == "fetch_url_content":
        url = call_args.get("url", "")
        res = fetch_url_content(url=url)
        fetched_src = url if res.get("status") in ("success", "warning") else None
        return res, None, fetched_src
    return {"status": "error", "error": f"Unknown tool: {call_name}"}, None, None



# ---------------------------------------------------------------------------
# Lifespan context manager: preloads embedding model and system prompt once
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, gemini_client_cache, redis_client

    print(f"🤖 Initializing embedding model: {EMBEDDING_MODEL_NAME}...")
    try:
        # Load embedding model into memory on server startup
        ml_models["embedding_model"] = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("✅ Embedding model loaded successfully.")
    except Exception as exc:
        print(f"❌ Failed to load embedding model: {exc}")
        ml_models["embedding_model"] = None

    # Initialize DB connection pool (min 2, max 10 connections)
    try:
        db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
        if db_url:
            db_pool = pool.ThreadedConnectionPool(2, 10, db_url)
            print("✅ Database connection pool initialized (2-10 connections).")
        else:
            print("⚠️ No database URL found. Pool not initialized.")
    except Exception as exc:
        print(f"❌ Failed to initialize DB pool: {exc}")
        db_pool = None

    # Pre-initialize Gemini client once
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            gemini_client_cache = genai.Client(api_key=api_key)
            print("✅ Gemini client initialized.")
    except Exception as exc:
        print(f"⚠️ Failed to pre-initialize Gemini client: {exc}")

    # Initialize Redis cache (optional — graceful fallback to LRU)
    if REDIS_AVAILABLE:
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.ping()
            print("✅ Redis cache connected.")
        except Exception as exc:
            print(f"⚠️ Redis not available ({exc}). Using in-memory LRU cache instead.")
            redis_client = None
    else:
        print("ℹ️ Redis package not installed. Using in-memory LRU cache. (pip install redis to enable)")

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
    if db_pool:
        db_pool.closeall()
        print("✅ Database connection pool closed.")
    if redis_client:
        try:
            redis_client.close()
        except Exception:
            pass


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
    Gets a connection from the pool, or creates a direct connection as fallback.
    """
    global db_pool
    if db_pool:
        try:
            conn = db_pool.getconn()
            register_vector(conn)
            return conn
        except Exception as exc:
            print(f"⚠️ Pool connection failed, falling back to direct: {exc}")

    # Fallback: direct connection
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


def return_db_connection(conn):
    """Returns a connection back to the pool."""
    global db_pool
    if db_pool:
        try:
            db_pool.putconn(conn)
            return
        except Exception:
            pass
    # If not pooled, just close it
    try:
        conn.close()
    except Exception:
        pass


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
        return_db_connection(conn)


# ---------------------------------------------------------------------------
# Embedding cache: Redis first, LRU fallback
# ---------------------------------------------------------------------------
@lru_cache(maxsize=256)
def _lru_cached_embedding(question_hash: str, question: str):
    """In-memory LRU fallback cache."""
    model: SentenceTransformer = ml_models.get("embedding_model")
    if model is None:
        return None
    query_text = f"Represent this sentence: {question}"
    return model.encode(query_text, normalize_embeddings=True).tolist()


def get_cached_embedding(question_hash: str, question: str):
    """
    Tries Redis cache first (if available), then falls back to LRU cache.
    This ensures the system works with or without Redis installed.
    """
    # Try Redis first
    if redis_client:
        try:
            cache_key = f"emb:{question_hash}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # Redis read failed, fall through

    # Compute embedding (via LRU cache)
    embedding = _lru_cached_embedding(question_hash, question)

    # Store in Redis for cross-process sharing
    if redis_client and embedding:
        try:
            cache_key = f"emb:{question_hash}"
            redis_client.setex(cache_key, EMBEDDING_CACHE_TTL, json.dumps(embedding))
        except Exception:
            pass  # Redis write failed, that's okay

    return embedding


def get_gemini_client() -> genai.Client:
    """
    Returns cached Gemini client or creates one if needed.
    """
    global gemini_client_cache
    if gemini_client_cache:
        return gemini_client_cache

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API key not configured. Set GEMINI_API_KEY in backend/.env."
        )
    gemini_client_cache = genai.Client(api_key=api_key)
    return gemini_client_cache


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
        "llm_model": GEMINI_MODEL_NAME,
        "tools_enabled": ["generate_report", "fetch_url_content"],
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Search + Answer with Agent Tool Calling Endpoint:
    1. Embeds question using BAAI/bge-large-en-v1.5
    2. Performs pgvector cosine similarity search (<=>) on Neon Postgres
    3. Formats prompt with system guidelines + retrieved excerpts + question
    4. Calls Gemini API with tools (generate_report, fetch_url_content)
    5. If Gemini triggers tool_use:
       - Runs tool locally (generates docx or fetches live URL)
       - Feeds tool_result back to Gemini for final response
    6. Returns answer, sources, and report_url (or null)
    """
    user_question = request.question.strip()
    if not user_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # 1. Generate query embedding (with caching for repeated questions)
    if ml_models.get("embedding_model") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not ready. Please check server logs."
        )

    sources = []
    context_blocks = []

    try:
        question_hash = hashlib.md5(user_question.encode()).hexdigest()
        query_embedding = get_cached_embedding(question_hash, user_question)
        if query_embedding:
            # 2. Retrieve top 5 most similar chunks from pgvector
            chunks = retrieve_top_chunks(query_embedding, top_k=5)
            for doc_name, chunk_idx, chunk_text, _sim in chunks:
                context_blocks.append(
                    f"--- Document: {doc_name} (Chunk #{chunk_idx}) ---\n{chunk_text.strip()}"
                )
                if doc_name not in sources:
                    sources.append(doc_name)
    except Exception as exc:
        print(f"⚠️ Vector search warning: {exc}")

    context_str = "\n\n".join(context_blocks) if context_blocks else "(No specific internal database chunks found for this query.)"

    # 3. Read system prompt
    system_prompt = ml_models.get(
        "system_prompt",
        "You are the Islamic Banking Assistant. Answer strictly based on verified documents or tools."
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
        f"- Answer accurately and clearly.\n"
        f"- If the user asks about an online web URL or provided link, call the fetch_url_content tool.\n"
        f"- If the user explicitly asks for a downloadable report, call the generate_report tool."
    )

    # 5. Call Gemini API with automatic model fallback for quota limits
    client = get_gemini_client()
    models_to_try = [GEMINI_MODEL_NAME, "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    seen = set()
    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

    last_error = None
    response = None
    used_model = GEMINI_MODEL_NAME

    for candidate_model in models_to_try:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[AGENT_TOOLS],
                temperature=0.3,
            )
            response = client.models.generate_content(
                model=candidate_model,
                contents=user_prompt_content,
                config=config,
            )
            used_model = candidate_model
            break
        except Exception as exc:
            last_error = exc
            print(f"⚠️ Model {candidate_model} returned error: {exc}. Trying fallback model...")
            continue

    if response is None:
        if last_error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini API rate limit or error reached on models: {str(last_error)}"
            )
        raise HTTPException(status_code=500, detail="Failed to get response from Gemini.")

    try:
        # 6. Check for function calls in Gemini's response
        report_url = None
        answer_text = ""

        if response.function_calls:
            for call in response.function_calls:
                tool_result, rep_url, fetched_url = handle_agent_tool_call(call.name, call.args or {})
                if rep_url:
                    report_url = rep_url
                if fetched_url and fetched_url not in sources:
                    sources.append(f"Web: {fetched_url}")

                if call.name == "fetch_url_content":
                    extracted_body = tool_result.get("content", "")
                    synthesis_prompt = (
                        f"WEB CONTENT RETRIEVED FROM {fetched_url}:\n"
                        f"=========================================\n"
                        f"{extracted_body}\n\n"
                        f"=========================================\n"
                        f"USER QUESTION: {user_question}\n\n"
                        f"Instructions:\n"
                        f"- Provide a comprehensive, detailed, and structured text explanation answering the user's question based on the web content.\n"
                        f"- Clearly list all stages, rules, and technical details.\n"
                        f"- Cite the web source URL."
                    )
                    for syn_model in models_to_try:
                        try:
                            syn_resp = client.models.generate_content(
                                model=syn_model,
                                contents=synthesis_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_prompt,
                                    temperature=0.3,
                                ),
                            )
                            if syn_resp.text:
                                answer_text = syn_resp.text
                                break
                        except Exception:
                            continue

                elif call.name == "generate_report":
                    answer_text = f"Your report on **{call.args.get('topic', 'Islamic Banking')}** has been generated successfully and is available for download."
                break
        else:
            answer_text = response.text or ""

        if not answer_text.strip():
            if report_url:
                answer_text = "Your report has been generated successfully. You can download it using the link provided."
            else:
                answer_text = "I don't have enough information in our documents to answer this. Please contact a bank representative or Shariah advisor."

        return ChatResponse(
            answer=answer_text.strip(),
            sources=sources,
            report_url=report_url
        )

    except errors.APIError as exc:
        print(f"❌ Gemini API Error ({exc.code}): {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API returned error ({exc.code}): {exc.message}"
        )
    except Exception as exc:
        print(f"❌ Unexpected error in /chat: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(exc)}"
        )



# ---------------------------------------------------------------------------
# Streaming SSE Endpoint: /chat/stream
# ---------------------------------------------------------------------------
# Sends response tokens as Server-Sent Events for real-time display.
# Frontend receives text chunk-by-chunk instead of waiting for full response.
# Falls back gracefully — if streaming fails, sends complete response as one event.
# ---------------------------------------------------------------------------
@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """
    Streaming version of /chat using Server-Sent Events (SSE).
    Streams Gemini response tokens in real-time for instant user feedback.
    Supports Agent function calling (fetch_url_content, generate_report).
    
    SSE Event format:
    - event: token   → partial text chunk
    - event: sources → JSON array of source document names
    - event: report  → report download URL (if generated)
    - event: done    → signals stream completion
    - event: error   → error message
    """
    user_question = request.question.strip()
    if not user_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # 1. Generate query embedding
    if ml_models.get("embedding_model") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not ready."
        )

    sources = []
    context_blocks = []

    try:
        question_hash = hashlib.md5(user_question.encode()).hexdigest()
        query_embedding = get_cached_embedding(question_hash, user_question)
        if query_embedding:
            chunks = retrieve_top_chunks(query_embedding, top_k=5)
            for doc_name, chunk_idx, chunk_text, _sim in chunks:
                context_blocks.append(
                    f"--- Document: {doc_name} (Chunk #{chunk_idx}) ---\n{chunk_text.strip()}"
                )
                if doc_name not in sources:
                    sources.append(doc_name)
    except Exception as exc:
        print(f"⚠️ Vector search warning in stream: {exc}")

    context_str = "\n\n".join(context_blocks) if context_blocks else "(No specific internal database chunks found for this query.)"
    system_prompt = ml_models.get("system_prompt", "You are the Islamic Banking Assistant.")

    user_prompt_content = (
        f"DOCUMENT EXCERPTS:\n"
        f"==================\n"
        f"{context_str}\n\n"
        f"==================\n"
        f"USER REQUEST:\n"
        f"{user_question}\n\n"
        f"Instructions:\n"
        f"- Answer accurately and clearly.\n"
        f"- If the user asks about an online web URL or provided link, call the fetch_url_content tool.\n"
        f"- If the user explicitly asks for a downloadable report, call the generate_report tool."
    )

    async def event_stream():
        """Generator that yields SSE events with streamed Gemini response."""
        client = get_gemini_client()
        models_to_try = [GEMINI_MODEL_NAME, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        report_url = None
        streamed_any = False
        last_error = None

        for candidate_model in models_to_try:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[AGENT_TOOLS],
                    temperature=0.3,
                )

                # Use streaming generation
                stream_response = client.models.generate_content_stream(
                    model=candidate_model,
                    contents=user_prompt_content,
                    config=config,
                )

                for chunk in stream_response:
                    # Check for function calls (URL fetching or Report generation)
                    if chunk.function_calls:
                        for call in chunk.function_calls:
                            tool_result, rep_url, fetched_url = handle_agent_tool_call(call.name, call.args or {})
                            if rep_url:
                                report_url = rep_url
                                yield f"event: report\ndata: {json.dumps({'url': report_url})}\n\n"
                            if fetched_url and fetched_url not in sources:
                                sources.append(f"Web: {fetched_url}")

                            # If URL was fetched, synthesize and stream full text answer from the extracted content
                            if call.name == "fetch_url_content":
                                extracted_body = tool_result.get("content", "")
                                synthesis_prompt = (
                                    f"WEB CONTENT RETRIEVED FROM {fetched_url}:\n"
                                    f"=========================================\n"
                                    f"{extracted_body}\n\n"
                                    f"=========================================\n"
                                    f"USER QUESTION: {user_question}\n\n"
                                    f"Instructions:\n"
                                    f"- Provide a comprehensive, detailed, and structured text explanation answering the user's question based on the web content.\n"
                                    f"- Clearly list all stages, rules, and technical details.\n"
                                    f"- Cite the web source URL."
                                )
                                for syn_model in models_to_try:
                                    try:
                                        syn_stream = client.models.generate_content_stream(
                                            model=syn_model,
                                            contents=synthesis_prompt,
                                            config=types.GenerateContentConfig(
                                                system_instruction=system_prompt,
                                                temperature=0.3,
                                            ),
                                        )
                                        for syn_chunk in syn_stream:
                                            if syn_chunk.text:
                                                yield f"event: token\ndata: {json.dumps({'text': syn_chunk.text})}\n\n"
                                                streamed_any = True
                                                await asyncio.sleep(0)
                                        break
                                    except Exception as syn_exc:
                                        print(f"⚠️ Synthesis stream failed on {syn_model}: {syn_exc}")
                                        continue

                            elif call.name == "generate_report":
                                report_msg = f"Your report on **{call.args.get('topic', 'Islamic Banking')}** has been generated successfully and is ready for download."
                                yield f"event: token\ndata: {json.dumps({'text': report_msg})}\n\n"
                                streamed_any = True
                        break

                    # Stream text tokens directly
                    if chunk.text:
                        yield f"event: token\ndata: {json.dumps({'text': chunk.text})}\n\n"
                        streamed_any = True
                        await asyncio.sleep(0)  # Yield control for responsiveness

                if streamed_any:
                    break  # Success, stop trying models

            except Exception as exc:
                last_error = exc
                print(f"⚠️ Stream: Model {candidate_model} failed: {exc}")
                continue

        if not streamed_any:
            if last_error:
                yield f"event: error\ndata: {json.dumps({'error': str(last_error)})}\n\n"
            else:
                yield f"event: token\ndata: {json.dumps({'text': 'No response generated.'})}\n\n"

        # Send sources and completion signal
        yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
        yield f"event: done\ndata: {json.dumps({'report_url': report_url})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

