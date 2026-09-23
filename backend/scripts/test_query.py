"""
Step 6 Preview: RAG Retrieval Test Script
==========================================
Tests semantic similarity search against Neon Postgres (pgvector)
and formats the retrieved chunks with the Islamic Banking Assistant system prompt.

Usage:
    python scripts/test_query.py "What is Murabaha and how does it work at LOLC?"
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_system_prompt(bank_name: str = "LOLC Al-Falaah") -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(os.path.dirname(script_dir), "prompts", "system_prompt.txt")
    
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
            return content.replace("[Bank Name]", bank_name)
    return f"You are the Islamic Banking Assistant for {bank_name}."


def search_similar_chunks(query: str, top_k: int = 4):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    load_dotenv(os.path.join(backend_dir, ".env"))

    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    if not db_url:
        print("❌ Database URL not found in .env (expected NEON_DATABASE_URL or Neon_db).")
        sys.exit(1)

    print(f"🤖 Embedding query: \"{query}\"")
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    # For bge models, query representation benefits from the prefix at retrieval time
    query_emb = model.encode(f"Represent this sentence: {query}", normalize_embeddings=True).tolist()

    conn = psycopg2.connect(db_url)
    register_vector(conn)

    sql = """
        SELECT document_name, chunk_index, chunk_text,
               1 - (embedding <=> %s::vector) AS similarity
        FROM document_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(sql, (query_emb, query_emb, top_k))
        rows = cur.fetchall()

    conn.close()
    return rows


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "What are the Shariah principles of Islamic banking?"

    print("=" * 60)
    print("🔍 Islamic Banking Chatbot — Vector Search & Prompt Test")
    print("=" * 60)
    print(f"Query: {query}\n")

    try:
        results = search_similar_chunks(query, top_k=3)
        if not results:
            print("⚠️ No matching chunks found. Did you run scripts/embed_and_store.py first?")
            return

        print(f"📚 Retrieved Top {len(results)} Chunks:\n")
        context_parts = []
        for rank, (doc, idx, text, sim) in enumerate(results, 1):
            print(f"[{rank}] Document: {doc} (Chunk #{idx}) | Similarity: {sim:.4f}")
            print(f"    {text[:200]}...\n")
            context_parts.append(f"--- Excerpt from {doc} (Section {idx}) ---\n{text}")

        # Assemble full prompt
        system_prompt = load_system_prompt()
        user_message = (
            f"Here are the document excerpts:\n\n"
            + "\n\n".join(context_parts)
            + f"\n\nQuestion: {query}\n\nPlease answer based strictly on the excerpts above."
        )

        print("-" * 60)
        print("📋 Formatted Prompt Preview (First 500 chars of System Prompt):")
        print(system_prompt[:500] + "...\n")
        print("✅ Retrieval pipeline verified successfully!")

    except Exception as e:
        print(f"❌ Error during retrieval: {e}")


if __name__ == "__main__":
    main()
