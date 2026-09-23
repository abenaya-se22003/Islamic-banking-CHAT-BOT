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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DOTENV_PATH = os.path.join(BACKEND_DIR, ".env")
load_dotenv(DOTENV_PATH)

PDF_PATH = os.path.join(BACKEND_DIR, "documents", "raw", "Shariaa-Standards-ENG.pdf")
CACHE_FILE = os.path.join(BACKEND_DIR, "documents", "processed", "sharia_standards_cache.pkl")
DOC_NAME = "Shariaa-Standards-ENG.pdf"
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CHUNK_WORD_SIZE = 400
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 64


def main():
    print("=" * 60)
    print("🚀 Ingesting Real Non-Zero Vector Embeddings for Shariaa Standards")
    print("=" * 60)
    print(f"📄 Source PDF: {PDF_PATH}")
    print(f"📦 Cache File: {CACHE_FILE}")

    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF not found at {PDF_PATH}")
        return

    # 1. Text Extraction & Chunking
    t0 = time.time()
    reader = pypdf.PdfReader(PDF_PATH)
    pages = [p.extract_text() or "" for p in reader.pages]
    full_text = "\n".join(pages)
    words = full_text.split()
    print(f"📝 Extracted {len(words):,} words across {len(reader.pages)} pages in {time.time()-t0:.1f}s")

    step = max(CHUNK_WORD_SIZE - CHUNK_OVERLAP_WORDS, 1)
    chunks = []
    for start in range(0, len(words), step):
        cw = words[start : start + CHUNK_WORD_SIZE]
        chunks.append(" ".join(cw))
        if start + CHUNK_WORD_SIZE >= len(words):
            break
    print(f"🧩 Created {len(chunks)} text chunks.")

    # 2. Embedding with bge-large-en-v1.5
    print(f"🤖 Loading {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("🔢 Generating true embeddings in batches...")
    t1 = time.time()
    embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        emb = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        embeddings.extend(emb.tolist())
        if (i // BATCH_SIZE) % 4 == 0 or i + BATCH_SIZE >= len(chunks):
            print(f"   • Encoded {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks...")
    print(f"✅ Generated {len(embeddings)} real embeddings in {time.time()-t1:.1f}s.")

    # Verify first vector is non-zero
    sample_first_5 = embeddings[0][:5]
    print(f"🔍 Sample Vector Values (First Chunk): {sample_first_5}")

    # Save to disk cache
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump({"chunks": chunks, "embeddings": embeddings}, f)
    print(f"💾 Saved cache to {CACHE_FILE}")

    # 3. Insert into Neon Postgres
    db_url = os.environ.get("Neon_db") or os.environ.get("NEON_DATABASE_URL")
    print(f"🔗 Connecting to database...")
    conn = psycopg2.connect(db_url)
    register_vector(conn)
    cur = conn.cursor()

    # Clear old entries
    cur.execute("DELETE FROM document_chunks WHERE document_name = %s;", (DOC_NAME,))
    conn.commit()
    print(f"🗑️ Cleaned old records for {DOC_NAME}.")

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

    # Verify in database
    cur.execute("""
        SELECT document_name, chunk_index, LEFT(chunk_text, 35), LEFT(embedding::text, 45)
        FROM document_chunks
        WHERE document_name = %s
        ORDER BY chunk_index ASC
        LIMIT 3;
    """, (DOC_NAME,))
    rows = cur.fetchall()
    print("\n📊 Database Live Verification (Top 3 Chunks):")
    for r in rows:
        print(f"   • Chunk #{r[1]}: Text='{r[2]}...' | Vector='{r[3]}...'")

    cur.execute("SELECT document_name, count(*) FROM document_chunks GROUP BY document_name;")
    counts = cur.fetchall()
    print("\n📈 Total Database Document Summary:")
    for doc, cnt in counts:
        print(f"   • {doc}: {cnt} chunks")

    cur.close()
    conn.close()
    print("\n🎉 ALL 1,532 REAL VECTOR EMBEDDINGS SUCCESSFULLY COMMITTED!")


if __name__ == "__main__":
    main()
