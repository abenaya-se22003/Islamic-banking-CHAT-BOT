import os
import sys
import pickle
import time
import pypdf
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

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_backend_dir, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)

CACHE_FILE = os.path.join(_backend_dir, "documents", "processed", "sharia_standards_cache.pkl")
PDF_PATH = os.path.join(_backend_dir, "documents", "raw", "Shariaa-Standards-ENG.pdf")
DOC_NAME = "Shariaa-Standards-ENG.pdf"
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CHUNK_WORD_SIZE = 400
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 64


def main():
    print("=" * 60)
    print("⚡ Fast Embedding & Neon DB Sync for Shariaa-Standards-ENG.pdf")
    print("=" * 60)

    # 1. Check Cache
    if os.path.exists(CACHE_FILE):
        print(f"📦 Found cached embeddings at: {CACHE_FILE}")
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            chunks = data["chunks"]
            embeddings = data["embeddings"]
            print(f"✅ Loaded {len(chunks)} chunks and embeddings from cache.")
    else:
        print("📄 Extracting text from PDF...")
        t0 = time.time()
        reader = pypdf.PdfReader(PDF_PATH)
        pages_text = []
        for p in reader.pages:
            t = p.extract_text()
            if t:
                pages_text.append(t)
        full_text = "\n".join(pages_text)
        print(f"✅ Extracted {len(full_text.split()):,} words across {len(reader.pages)} pages in {time.time()-t0:.1f}s")

        # Chunking
        words = full_text.split()
        step = max(CHUNK_WORD_SIZE - CHUNK_OVERLAP_WORDS, 1)
        chunks = []
        for start in range(0, len(words), step):
            cw = words[start : start + CHUNK_WORD_SIZE]
            chunks.append(" ".join(cw))
            if start + CHUNK_WORD_SIZE >= len(words):
                break
        print(f"🧩 Created {len(chunks)} chunks.")

        # Embedding
        print(f"🤖 Generating embeddings with {EMBEDDING_MODEL_NAME}...")
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        embeddings = []
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            emb = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
            embeddings.extend(emb.tolist())
            print(f"   • Encoded {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks...")

        # Save Cache
        with open(CACHE_FILE, "wb") as f:
            pickle.dump({"chunks": chunks, "embeddings": embeddings}, f)
        print(f"💾 Saved cache to {CACHE_FILE}.")

    # 2. Database Insert
    db_url = os.environ.get("Neon_db") or os.environ.get("NEON_DATABASE_URL")
    print("🔗 Connecting to Neon Postgres...")
    conn = psycopg2.connect(db_url)
    register_vector(conn)
    cur = conn.cursor()

    # Clear old entries for this doc
    cur.execute("DELETE FROM document_chunks WHERE document_name = %s;", (DOC_NAME,))
    conn.commit()
    print(f"🗑️ Cleared previous chunks for {DOC_NAME}.")

    print("💾 Inserting chunks with execute_values...")
    insert_sql = """
        INSERT INTO document_chunks (document_name, module, chunk_text, chunk_index, embedding)
        VALUES %s
    """
    db_batch = 100
    for i in range(0, len(chunks), db_batch):
        c_slice = chunks[i : i + db_batch]
        e_slice = embeddings[i : i + db_batch]
        records = [(DOC_NAME, None, c_slice[j], i + j, e_slice[j]) for j in range(len(c_slice))]
        execute_values(cur, insert_sql, records, template="(%s, %s, %s, %s, %s)")
        conn.commit()

    # Final Verification
    cur.execute("SELECT document_name, count(*) FROM document_chunks GROUP BY document_name;")
    summary = cur.fetchall()
    print("\n📊 Database Status After Commit:")
    for doc, cnt in summary:
        print(f"   • {doc}: {cnt} chunks")

    cur.close()
    conn.close()
    print("\n🎉 ALL CHUNKS COMMITTED SUCCESSFULLY TO NEON DATABASE!")


if __name__ == "__main__":
    main()
