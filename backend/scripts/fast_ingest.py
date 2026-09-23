import os
import sys
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

PDF_PATH = os.path.join(BASE_DIR, "documents", "raw", "Shariaa-Standards-ENG.pdf")
DOC_NAME = "Shariaa-Standards-ENG.pdf"
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CHUNK_WORD_SIZE = 400
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 64


def main():
    print("=" * 60)
    print("Step 1: Extracting text from PDF (Offline)...")
    print("=" * 60)
    t0 = time.time()
    reader = pypdf.PdfReader(PDF_PATH)
    pages = [p.extract_text() or "" for p in reader.pages]
    words = ("\n".join(pages)).split()
    print(f"Extracted {len(words):,} words across {len(reader.pages)} pages in {time.time()-t0:.1f}s")

    step = max(CHUNK_WORD_SIZE - CHUNK_OVERLAP_WORDS, 1)
    chunks = []
    for start in range(0, len(words), step):
        cw = words[start : start + CHUNK_WORD_SIZE]
        chunks.append(" ".join(cw))
        if start + CHUNK_WORD_SIZE >= len(words):
            break
    print(f"Created {len(chunks)} text chunks.")

    print("\n" + "=" * 60)
    print("Step 2: Generating Vector Embeddings (Offline, no DB connection yet)...")
    print("=" * 60)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    t1 = time.time()
    embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        emb = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        embeddings.extend(emb.tolist())
        print(f"• Generated embeddings {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}...")
    print(f"Completed all {len(embeddings)} embeddings in {time.time()-t1:.1f}s.")

    print("\n" + "=" * 60)
    print("Step 3: Opening Fresh DB Connection & Committing to Neon Postgres...")
    print("=" * 60)
    db_url = os.environ.get("Neon_db") or os.environ.get("NEON_DATABASE_URL")
    conn = psycopg2.connect(db_url)
    register_vector(conn)
    cur = conn.cursor()

    cur.execute("DELETE FROM document_chunks WHERE document_name = %s;", (DOC_NAME,))
    conn.commit()
    print(f"Cleared old rows for {DOC_NAME}.")

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
        print(f"• Saved {min(i + db_batch, len(chunks))}/{len(chunks)} chunks...")

    cur.execute("SELECT document_name, count(*) FROM document_chunks GROUP BY document_name;")
    status = cur.fetchall()
    print("\nFinal Database Chunks Count:")
    for doc, count in status:
        print(f"   • {doc}: {count} chunks")

    cur.close()
    conn.close()
    print("\nSUCCESS! All chunks are permanently committed to Neon DB.")


if __name__ == "__main__":
    main()
