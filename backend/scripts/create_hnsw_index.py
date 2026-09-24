"""
HNSW Index Migration for pgvector
==================================
Creates an HNSW index on the document_chunks table for faster cosine similarity searches.

HNSW (Hierarchical Navigable Small World) advantages over IVFFlat:
- ~2-5x faster query time
- Better recall accuracy (99%+ vs 95%)
- No need for periodic re-indexing after data changes
- Slightly more memory usage (acceptable trade-off for speed)

Usage:
    python create_hnsw_index.py

Safe to run multiple times — uses IF NOT EXISTS.
"""

import os
import sys
import time

# Add parent directory to path for .env loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(BASE_DIR, ".env"))


def get_connection():
    db_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("Neon_db") or os.environ.get("NEON_DB")
    if not db_url:
        print("❌ No database URL found. Set NEON_DATABASE_URL or Neon_db in backend/.env")
        sys.exit(1)
    return psycopg2.connect(db_url)


def create_hnsw_index():
    conn = get_connection()
    cursor = conn.cursor()

    print("🔍 Checking current indexes on document_chunks...")

    # List existing indexes
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'document_chunks';
    """)
    existing = cursor.fetchall()

    if existing:
        print(f"\n📋 Found {len(existing)} existing index(es):")
        for name, defn in existing:
            print(f"   • {name}")
            if 'ivfflat' in defn.lower():
                print(f"     ⚠️  This is an IVFFlat index (slower than HNSW)")
            elif 'hnsw' in defn.lower():
                print(f"     ✅ Already using HNSW!")
    else:
        print("   No indexes found on document_chunks.")

    # Check if HNSW index already exists
    cursor.execute("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'document_chunks'
        AND indexdef ILIKE '%hnsw%';
    """)
    if cursor.fetchone():
        print("\n✅ HNSW index already exists. No changes needed.")
        cursor.close()
        conn.close()
        return

    # Drop old IVFFlat index if it exists (to avoid conflicts)
    cursor.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'document_chunks'
        AND indexdef ILIKE '%ivfflat%';
    """)
    old_indexes = cursor.fetchall()
    for (old_name,) in old_indexes:
        print(f"\n🗑️  Dropping old IVFFlat index: {old_name}...")
        cursor.execute(f"DROP INDEX IF EXISTS {old_name};")
        conn.commit()
        print(f"   ✅ Dropped {old_name}")

    # Create HNSW index
    print("\n🚀 Creating HNSW index on document_chunks.embedding...")
    print("   (This may take a moment depending on the number of chunks...)")

    start = time.time()
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200);
    """)
    conn.commit()
    elapsed = time.time() - start

    print(f"   ✅ HNSW index created in {elapsed:.1f}s")

    # Set the search parameter for optimal performance
    cursor.execute("SET hnsw.ef_search = 100;")
    conn.commit()
    print("   ✅ hnsw.ef_search set to 100 (balance between speed and accuracy)")

    # Verify
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'document_chunks'
        AND indexdef ILIKE '%hnsw%';
    """)
    result = cursor.fetchone()
    if result:
        print(f"\n🎉 Success! HNSW index is active: {result[0]}")
    else:
        print("\n⚠️  Warning: Index creation may have failed. Check Neon dashboard.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  HNSW Index Migration for Islamic Banking Chatbot")
    print("=" * 60)
    create_hnsw_index()
    print("\n" + "=" * 60)
    print("  Migration complete! Vector searches will now be faster.")
    print("=" * 60)
