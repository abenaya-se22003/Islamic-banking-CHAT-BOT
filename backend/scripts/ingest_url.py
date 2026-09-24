"""
URL Knowledge Ingestion Script for Neon pgvector
=================================================
Fetches documentation or web pages from URLs (e.g., Mambu Shariah Deposit Principles),
extracts clean text, generates vector embeddings with BAAI/bge-large,
and permanently saves chunks into the Neon Postgres document_chunks table.
"""

import os
import sys
import time
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.url_tool import fetch_url_content

EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
CHUNK_WORD_SIZE = 350
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 64


def ingest_url(url: str, document_name: str = None, module: str = "Shariah Principles"):
    """
    Scrapes, chunks, embeds, and stores a URL's content into Neon pgvector.
    """
    if not document_name:
        document_name = url.split("://")[-1].replace("/", " > ")

    print("=" * 65)
    print(f"🌐 Step 1: Fetching and parsing web page from: {url}")
    print("=" * 65)
    t0 = time.time()
    
    # Use our URL tool to extract clean content
    result = fetch_url_content(url, max_chars=100000)
    if result.get("status") not in ("success", "warning") or not result.get("content"):
        print(f"❌ Failed to extract content: {result.get('error')}")
        return False

    raw_text = result["content"]
    words = raw_text.split()
    print(f"✅ Extracted {len(words):,} words in {time.time()-t0:.2f}s.")

    if len(words) < 20:
        print("⚠️ Extracted content is too short. Aborting ingestion.")
        return False

    # Chunking
    step = max(CHUNK_WORD_SIZE - CHUNK_OVERLAP_WORDS, 1)
    chunks = []
    for start in range(0, len(words), step):
        cw = words[start : start + CHUNK_WORD_SIZE]
        chunks.append(" ".join(cw))
        if start + CHUNK_WORD_SIZE >= len(words):
            break
    print(f"📄 Created {len(chunks)} text chunks (approx {CHUNK_WORD_SIZE} words/chunk).")

    # Embedding
    print("\n" + "=" * 65)
    print(f"🧠 Step 2: Generating Vector Embeddings ({EMBEDDING_MODEL_NAME})...")
    print("=" * 65)
    t1 = time.time()
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        # BGE recommendation: query vs document prefix
        emb = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        embeddings.extend(emb.tolist())
        print(f"• Generated embeddings for chunks {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}...")

    print(f"✅ Generated {len(embeddings)} embeddings in {time.time()-t1:.2f}s.")

    # Neon DB Storage
    print("\n" + "=" * 65)
    print("💾 Step 3: Saving Chunks to Neon Postgres...")
    print("=" * 65)
    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    if not db_url:
        print("❌ Database URL not found in environment.")
        return False

    conn = psycopg2.connect(db_url)
    register_vector(conn)
    cur = conn.cursor()

    # Clear previous chunks for this document name to prevent duplicates
    cur.execute("DELETE FROM document_chunks WHERE document_name = %s;", (document_name,))
    conn.commit()
    print(f"🗑️ Cleaned any existing chunks for '{document_name}'.")

    insert_sql = """
        INSERT INTO document_chunks (document_name, module, chunk_text, chunk_index, embedding)
        VALUES %s
    """
    db_batch = 100
    for i in range(0, len(chunks), db_batch):
        c_slice = chunks[i : i + db_batch]
        e_slice = embeddings[i : i + db_batch]
        records = [(document_name, module, c_slice[j], i + j, e_slice[j]) for j in range(len(c_slice))]
        execute_values(cur, insert_sql, records, template="(%s, %s, %s, %s, %s)")
        conn.commit()

    print(f"🎉 Successfully inserted {len(chunks)} chunks for '{document_name}' into Neon DB!")

    # Summary
    cur.execute("SELECT document_name, count(*) FROM document_chunks GROUP BY document_name;")
    rows = cur.fetchall()
    print("\n📊 Current Database Contents:")
    for doc, count in rows:
        print(f"   • {doc}: {count} chunks")

    cur.close()
    conn.close()
    return True


if __name__ == "__main__":
    # Ingest MAMBU Shariah Deposit Principles by default or accept command line URL
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://docs.mambu.com/docs/shariah-deposit-principles-and-process"
    doc_label = sys.argv[2] if len(sys.argv) > 2 else "MAMBU - Shariah Deposit Principles and Process"
    
    print(f"Starting URL Ingestion for: {target_url} ({doc_label})")
    ingest_url(target_url, document_name=doc_label)
