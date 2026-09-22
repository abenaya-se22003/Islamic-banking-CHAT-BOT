"""
Step 5: Chunking + Embedding — Embed & Store Script
====================================================
This script completes the core RAG ingestion pipeline:

    PDF files → Extract text → Chunk text → Generate embeddings → Store in pgvector

Pipeline steps:
    1. Read all PDFs from  backend/documents/raw/
    2. Extract text using pdfplumber  (reuses logic from test_read_pdf.py)
    3. Split text into ~400-word chunks with 50-word overlap
    4. Generate embeddings using BAAI/bge-large-en-v1.5  (sentence-transformers)
    5. Insert (document_name, module, chunk_text, chunk_index, embedding) into
       the Neon Postgres  document_chunks  table via pgvector

Requirements:
    pip install pdfplumber sentence-transformers psycopg2-binary pgvector python-dotenv

Environment variables (set in backend/.env):
    NEON_DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
"""

import os
import sys
import glob
import time
import traceback

import pdfplumber
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"  # 1024-dim, open-source
CHUNK_WORD_SIZE = 400       # target words per chunk
CHUNK_OVERLAP_WORDS = 50    # overlapping words between consecutive chunks


# ---------------------------------------------------------------------------
# 1.  PDF text extraction  (mirrors test_read_pdf.py logic)
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Opens a PDF and returns the full extracted text (all pages concatenated).

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        The full text content of the PDF.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages_text: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    return "\n".join(pages_text)


# ---------------------------------------------------------------------------
# 2.  Text chunking  (~400 words per chunk, 50-word overlap)
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = CHUNK_WORD_SIZE,
               overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """
    Splits *text* into chunks of approximately *chunk_size* words,
    with *overlap* words shared between consecutive chunks.

    Strategy:
        - Tokenise by whitespace into a word list.
        - Slide a window of *chunk_size* words with a step of
          (chunk_size − overlap) words.
        - Each chunk is rejoined into a single string.

    Args:
        text:       The full document text.
        chunk_size: Target number of words per chunk.
        overlap:    Number of words that overlap between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)  # ensure we always advance
    chunks: list[str] = []

    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))

        # If this chunk already reaches the end of the document, stop.
        if start + chunk_size >= len(words):
            break

    return chunks


# ---------------------------------------------------------------------------
# 3.  Embedding generation  (BAAI/bge-large-en-v1.5)
# ---------------------------------------------------------------------------
def load_embedding_model() -> SentenceTransformer:
    """
    Downloads (on first run) and loads the embedding model.
    The bge-large-en-v1.5 model recommends prepending the query prefix
    "Represent this sentence: " for retrieval tasks, but for *storage*
    we embed the raw passage text — the prefix is only needed at query time.

    Returns:
        A SentenceTransformer model instance.
    """
    print(f"🤖 Loading embedding model: {EMBEDDING_MODEL_NAME}")
    print("   (First run will download ~1.2 GB — subsequent runs use cache)")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("✅ Embedding model loaded.\n")
    return model


def generate_embeddings(model: SentenceTransformer,
                        texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a list of text strings.

    Args:
        model: A loaded SentenceTransformer model.
        texts: The text strings to embed.

    Returns:
        A list of embedding vectors (each a list of floats).
    """
    # encode() returns a numpy array of shape (n_texts, dim)
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


# ---------------------------------------------------------------------------
# 4.  Database operations  (Neon Postgres + pgvector)
# ---------------------------------------------------------------------------
def get_db_connection():
    """
    Creates a psycopg2 connection to the Neon Postgres database using
    NEON_DATABASE_URL or Neon_db environment variable and registers pgvector.
    Also ensures the pgvector extension and document_chunks table exist.

    Returns:
        A psycopg2 connection object with pgvector types registered.
    """
    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    if not db_url:
        print("❌ Database URL environment variable is not set.")
        print("   Please set NEON_DATABASE_URL or Neon_db in backend/.env:")
        print('   Neon_db="postgresql://user:pass@host/db?sslmode=require"')
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    
    # Ensure pgvector extension and table exist
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                document_name TEXT NOT NULL,
                module TEXT,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                embedding vector({1024}),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()

    register_vector(conn)
    return conn


def insert_chunks(conn, document_name: str, chunks: list[str],
                  embeddings: list[list[float]]) -> int:
    """
    Inserts all chunks (with embeddings) for a single document into the
    document_chunks table.

    Args:
        conn:           A psycopg2 connection.
        document_name:  The source PDF filename (e.g. "murabaha_faq_v1.pdf").
        chunks:         The chunk text strings.
        embeddings:     The embedding vectors (same length as chunks).

    Returns:
        The number of rows inserted.
    """
    insert_sql = """
        INSERT INTO document_chunks
            (document_name, module, chunk_text, chunk_index, embedding)
        VALUES
            (%s, %s, %s, %s, %s)
    """

    inserted = 0
    with conn.cursor() as cur:
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            cur.execute(insert_sql, (
                document_name,
                None,           # module — to be set later
                chunk_text,
                idx,            # chunk_index (0-based)
                embedding,      # pgvector handles list[float] via register_vector
            ))
            inserted += 1
    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# 5.  Main pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    start_time = time.time()

    # --- Resolve paths -------------------------------------------------------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)          # backend/
    raw_docs_dir = os.path.join(backend_dir, "documents", "raw")

    # --- Load .env -----------------------------------------------------------
    dotenv_path = os.path.join(backend_dir, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f"📦 Loaded environment from {dotenv_path}")

    # --- Discover PDFs -------------------------------------------------------
    pdf_pattern = os.path.join(raw_docs_dir, "*.pdf")
    pdf_files = sorted(glob.glob(pdf_pattern))

    if not pdf_files:
        print(f"⚠️  No PDF files found in: {raw_docs_dir}")
        print("   Place your PDF documents there and re-run this script.")
        sys.exit(0)

    print("=" * 60)
    print("📚 Islamic Banking Chatbot — Embed & Store Pipeline")
    print("=" * 60)
    print(f"\n📂 Source folder : {raw_docs_dir}")
    print(f"📄 PDFs found    : {len(pdf_files)}")
    print(f"🧩 Chunk size    : ~{CHUNK_WORD_SIZE} words, {CHUNK_OVERLAP_WORDS}-word overlap")
    print(f"🤖 Model         : {EMBEDDING_MODEL_NAME}\n")

    # --- Load embedding model (once) -----------------------------------------
    model = load_embedding_model()

    # --- Connect to Neon Postgres --------------------------------------------
    print("🔗 Connecting to Neon Postgres …")
    conn = get_db_connection()
    print("✅ Database connection established.\n")

    # --- Process each PDF ----------------------------------------------------
    total_chunks_inserted = 0
    total_pdfs_processed = 0
    failed_pdfs: list[str] = []

    for pdf_path in pdf_files:
        doc_name = os.path.basename(pdf_path)
        print("-" * 60)
        print(f"📄 Processing: {doc_name}")

        try:
            # 1. Extract text
            text = extract_text_from_pdf(pdf_path)
            word_count = len(text.split())

            if not text.strip():
                print(f"   ⚠️  No text extracted — skipping.")
                continue

            print(f"   📝 Extracted {word_count:,} words")

            # 2. Chunk
            chunks = chunk_text(text)
            print(f"   🧩 Split into {len(chunks)} chunks")

            if not chunks:
                print(f"   ⚠️  No chunks produced — skipping.")
                continue

            # 3. Generate embeddings (batch for efficiency)
            print(f"   🔢 Generating embeddings …")
            embeddings = generate_embeddings(model, chunks)
            print(f"   ✅ Generated {len(embeddings)} embeddings "
                  f"(dim={len(embeddings[0])})")

            # 4. Store in database
            inserted = insert_chunks(conn, doc_name, chunks, embeddings)
            total_chunks_inserted += inserted
            total_pdfs_processed += 1

            # 5. Progress per chunk
            for i in range(len(chunks)):
                print(f"   📌 Processed chunk {i + 1}/{len(chunks)} "
                      f"from {doc_name}")

            print(f"   ✅ Stored {inserted} chunks in database.")

        except Exception as exc:
            # Log the error but keep processing the remaining PDFs
            print(f"   ❌ ERROR processing {doc_name}: {exc}")
            traceback.print_exc()
            failed_pdfs.append(doc_name)
            # Rollback any partial transaction for this document
            conn.rollback()

    # --- Summary -------------------------------------------------------------
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 Pipeline Summary")
    print("=" * 60)
    print(f"   PDFs processed : {total_pdfs_processed}/{len(pdf_files)}")
    print(f"   Total chunks   : {total_chunks_inserted}")
    print(f"   Time elapsed   : {elapsed:.1f}s")

    if failed_pdfs:
        print(f"\n   ⚠️  Failed PDFs ({len(failed_pdfs)}):")
        for name in failed_pdfs:
            print(f"      - {name}")

    print(f"\n✅ Done!")

    # --- Cleanup -------------------------------------------------------------
    conn.close()


if __name__ == "__main__":
    main()
