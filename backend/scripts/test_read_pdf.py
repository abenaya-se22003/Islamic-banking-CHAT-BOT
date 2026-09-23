"""
Step 3: Document Preparation — PDF Reading Test Script
======================================================
This script tests that we can successfully read and extract text from PDF files.
It's the first building block of our RAG (Retrieval-Augmented Generation) pipeline:

    PDF files → Extract text → Chunk text → Generate embeddings → Store in pgvector

For now, we're just doing the first part: extracting raw text from a PDF.

Library used:
    pdfplumber — a Python library that extracts text, tables, and metadata from PDFs.
    It works better than PyPDF2 for complex layouts (tables, columns, etc.).
"""

import os
import sys
import pdfplumber

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def read_pdf(path: str) -> str:
    """
    Opens a PDF file and extracts all text from every page.

    Args:
        path (str): The file path to the PDF document.

    Returns:
        str: The full extracted text from all pages, joined by newlines.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist at the given path.
        Exception: If the PDF can't be read (corrupted, encrypted, etc.).
    """
    # Check if the file exists before trying to open it
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF file not found: {path}")

    # Open the PDF and extract text from each page
    all_text = []

    with pdfplumber.open(path) as pdf:
        print(f"📄 Opened PDF: {os.path.basename(path)}")
        print(f"📑 Total pages: {len(pdf.pages)}")
        print("-" * 50)

        for i, page in enumerate(pdf.pages):
            # extract_text() returns the text content of a single page
            page_text = page.extract_text()

            if page_text:
                all_text.append(page_text)
            else:
                # Some pages might be images or empty
                print(f"⚠️  Page {i + 1}: No extractable text (might be an image or blank)")

    # Join all page texts with newlines
    return "\n".join(all_text)


if __name__ == "__main__":
    import glob

    # ---------------------------------------------------------------------------
    # Auto-discover all PDF files in backend/documents/raw/
    # ---------------------------------------------------------------------------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)  # Go up from scripts/ to backend/
    raw_docs_dir = os.path.join(backend_dir, "documents", "raw")
    pdf_files = sorted(glob.glob(os.path.join(raw_docs_dir, "*.pdf")))

    print("=" * 50)
    print("🔍 Islamic Banking Chatbot — PDF Reading Test")
    print("=" * 50)
    print(f"\n📂 Scanning folder: {raw_docs_dir}")
    print(f"📄 PDFs found: {len(pdf_files)}\n")

    if not pdf_files:
        print("❌ No PDF files found!")
        print("\n💡 To fix this:")
        print(f"   1. Place PDF files in: {raw_docs_dir}")
        print("   2. Re-run this script")
        sys.exit(1)

    # Test each PDF
    all_passed = True
    for pdf_path in pdf_files:
        pdf_name = os.path.basename(pdf_path)
        print("-" * 50)
        print(f"📄 Testing: {pdf_name}")

        try:
            # Extract all text from the PDF
            extracted_text = read_pdf(pdf_path)

            if not extracted_text.strip():
                print("   ⚠️  No text could be extracted (might be scanned/image-based).")
                all_passed = False
            else:
                # Print the first 300 characters as a preview
                print(f"\n   📝 First 300 characters:")
                print("   " + "-" * 46)
                for line in extracted_text[:300].split("\n"):
                    print(f"   {line}")
                print("   " + "-" * 46)

                # Print stats
                total_chars = len(extracted_text)
                total_words = len(extracted_text.split())
                print(f"   📊 Characters: {total_chars:,}  |  Words: {total_words:,}")
                print(f"   ✅ Passed!")

        except FileNotFoundError as e:
            print(f"   ❌ File not found: {e}")
            all_passed = False

        except Exception as e:
            print(f"   ❌ Error reading PDF: {e}")
            print(f"      Error type: {type(e).__name__}")
            all_passed = False

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print(f"✅ All {len(pdf_files)} PDF(s) read successfully! Ready for the next step.")
    else:
        print("⚠️  Some PDFs had issues. Check the output above.")
    print("=" * 50)
