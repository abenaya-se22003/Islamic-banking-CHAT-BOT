import os
import sys
import glob
import time
import traceback

import pypdf
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Force UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_backend_dir, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)

EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CHUNK_WORD_SIZE = 400
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 64


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pypdf for speed."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages_text = []
    reader = pypdf.PdfReader(pdf_path)
    for page in reader.pages:
        t = page.extract_text()
        if t:
            pages_text.append(t)
    return "\n".join(pages_text)


def chunk_text(text: str, chunk_size: int = CHUNK_WORD_SIZE, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Splits text into chunks of ~chunk_size words with overlap."""
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def get_db_connection():
    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    if not db_url:
        print("❌ Database URL environment variable is not set.")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                document_name TEXT NOT NULL,
                module TEXT,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                embedding vector(1024),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()
    register_vector(conn)
    return conn


def main():
    start_time = time.time()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    raw_docs_dir = os.path.join(backend_dir, "documents", "raw")

    pdf_files = sorted(glob.glob(os.path.join(raw_docs_dir, "*.pdf")))
    print("=" * 60)
    print("📚 Islamic Banking Vector Ingestion Pipeline")
    print("=" * 60)
    print(f"📂 PDFs found ({len(pdf_files)}): {[os.path.basename(f) for f in pdf_files]}")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT document_name, count(*) FROM document_chunks GROUP BY document_name;")
    existing = {r[0]: r[1] for r in cur.fetchall()}
    print(f"📊 Currently in database: {existing}\n")

    print(f"🤖 Loading embedding model: {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("✅ Model loaded.\n")

    for pdf_path in pdf_files:
        doc_name = os.path.basename(pdf_path)
        print("-" * 60)
        print(f"📄 Ingesting: {doc_name}")

        if doc_name in existing and existing[doc_name] > 0 and doc_name != "Shariaa-Standards-ENG.pdf":
            print(f"   ⏩ Already embedded ({existing[doc_name]} chunks) — skipping.")
            continue

        # Delete any existing chunks for this file
        cur.execute("DELETE FROM document_chunks WHERE document_name = %s;", (doc_name,))
        conn.commit()

        t0 = time.time()
        text = extract_text_from_pdf(pdf_path)
        words = len(text.split())
        print(f"   📝 Extracted {words:,} words in {time.time() - t0:.2f}s")

        chunks = chunk_text(text)
        print(f"   🧩 Generated {len(chunks)} chunks")

        if not chunks:
            continue

        print(f"   🔢 Generating embeddings in batches of {BATCH_SIZE}...")
        t1 = time.time()
        embeddings = []
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            emb_batch = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
            embeddings.extend(emb_batch.tolist())
            if (i // BATCH_SIZE) % 4 == 0 or i + BATCH_SIZE >= len(chunks):
                print(f"      • Encoded {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks...")

        print(f"   ✅ Embeddings generated in {time.time() - t1:.2f}s")

        # Insert chunks in batches using execute_values
        print(f"   💾 Inserting chunks into Neon Postgres...")
        insert_query = """
            INSERT INTO document_chunks (document_name, module, chunk_text, chunk_index, embedding)
            VALUES %s
        """

        db_batch_size = 100
        for i in range(0, len(chunks), db_batch_size):
            chunk_slice = chunks[i : i + db_batch_size]
            emb_slice = embeddings[i : i + db_batch_size]
            records = [
                (doc_name, None, chunk_slice[j], i + j, emb_slice[j])
                for j in range(len(chunk_slice))
            ]
            execute_values(cur, insert_query, records, template="(%s, %s, %s, %s, %s)")
            conn.commit()
            print(f"      • Stored {min(i + db_batch_size, len(chunks))}/{len(chunks)} chunks...")

        # Verify
        cur.execute("SELECT count(*) FROM document_chunks WHERE document_name = %s;", (doc_name,))
        verified_count = cur.fetchone()[0]
        print(f"   🎉 VERIFIED: {verified_count} chunks successfully committed in database for {doc_name}!")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print(f"🏁 Vector Ingestion Complete in {time.time() - start_time:.1f}s!")
    print("=" * 60)


if __name__ == "__main__":
    main()
