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
    # ---------------------------------------------------------------------------
    # Path to our test PDF
    # We use os.path to build the path relative to this script's location,
    # so it works no matter where you run the script from.
    # ---------------------------------------------------------------------------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)  # Go up from scripts/ to backend/
    pdf_path = os.path.join(backend_dir, "documents", "raw", "dummy_islamic_banking.pdf")

    print("=" * 50)
    print("🔍 Islamic Banking Chatbot — PDF Reading Test")
    print("=" * 50)
    print(f"\n📂 Looking for PDF at:\n   {pdf_path}\n")

    try:
        # Extract all text from the PDF
        extracted_text = read_pdf(pdf_path)

        if not extracted_text.strip():
            print("⚠️  The PDF was opened but no text could be extracted.")
            print("   This might mean the PDF contains only images/scanned pages.")
            print("   You may need OCR (e.g., pytesseract) for such files.")
        else:
            # Print the first 500 characters as a preview
            print("\n📝 First 500 characters of extracted text:")
            print("-" * 50)
            print(extracted_text[:500])
            print("-" * 50)

            # Print stats
            total_chars = len(extracted_text)
            total_words = len(extracted_text.split())
            print(f"\n📊 Stats:")
            print(f"   Total characters: {total_chars:,}")
            print(f"   Total words:      {total_words:,}")
            print(f"\n✅ PDF reading test passed! Ready for the next step.")

    except FileNotFoundError as e:
        # Clear message if the PDF doesn't exist yet
        print(f"❌ File not found: {e}")
        print("\n💡 To fix this:")
        print("   1. Place a PDF file in: backend/documents/raw/")
        print("   2. Name it: dummy_islamic_banking.pdf")
        print("   3. Re-run this script")
        sys.exit(1)

    except Exception as e:
        # Catch any other errors (corrupted PDF, permission issues, etc.)
        print(f"❌ Error reading PDF: {e}")
        print(f"   Error type: {type(e).__name__}")
        sys.exit(1)
