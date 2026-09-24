"""
Ingest MAMBU Shariah Deposit Principles into Neon pgvector
"""

import os
import sys
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

FILE_PATH = os.path.join(BASE_DIR, "documents", "raw", "MAMBU_Shariah_Deposit_Principles_and_Process.txt")
DOC_NAME = "MAMBU - Shariah Deposit Principles and Process (docs.mambu.com)"
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")


def main():
    print(f"📄 Reading {FILE_PATH}...")
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # Split into sections/paragraphs for precise retrieval
    sections = [s.strip() for s in text.split("## ") if s.strip()]
    chunks = []
    for s in sections:
        chunks.append("## " + s)

    print(f"Created {len(chunks)} contextual chunks for MAMBU documentation.")

    print(f"🧠 Generating embeddings with {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True).tolist()
    print(f"Generated {len(embeddings)} embeddings.")

    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    conn = psycopg2.connect(db_url)
    register_vector(conn)
    cur = conn.cursor()

    cur.execute("DELETE FROM document_chunks WHERE document_name = %s;", (DOC_NAME,))
    conn.commit()
    print(f"Cleaned old entries for '{DOC_NAME}'.")

    insert_sql = """
        INSERT INTO document_chunks (document_name, module, chunk_text, chunk_index, embedding)
        VALUES %s
    """
    records = [(DOC_NAME, "MAMBU Core Banking", chunks[i], i, embeddings[i]) for i in range(len(chunks))]
    execute_values(cur, insert_sql, records, template="(%s, %s, %s, %s, %s)")
    conn.commit()
    print(f"✅ Successfully ingested {len(records)} chunks for '{DOC_NAME}' into Neon DB!")

    cur.execute("SELECT document_name, count(*) FROM document_chunks GROUP BY document_name;")
    rows = cur.fetchall()
    print("\n📊 Database Chunks Summary:")
    for doc, count in rows:
        print(f"   • {doc}: {count} chunks")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
