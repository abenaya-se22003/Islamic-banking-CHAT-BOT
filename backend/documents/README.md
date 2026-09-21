# 📁 Documents Folder

This folder holds all source documents for the Islamic Banking Chatbot's knowledge base.

## Folder Structure

```
documents/
├── raw/            ← Original PDF/Word files go here
├── processed/      ← Cleaned & chunked text for embeddings (auto-generated)
└── README.md       ← You are here
```

## How to Use

### `raw/` — Original Documents

Place your **original PDF and Word files** here. These are the source-of-truth documents
that the chatbot will learn from.

**Naming convention:**

```
[module]_[type]_[version].pdf
```

| Part       | Description                          | Examples                          |
|------------|--------------------------------------|-----------------------------------|
| `module`   | Banking product or topic area        | `casa`, `murabaha`, `takaful`     |
| `type`     | Document type                        | `product-terms`, `faq`, `policy`  |
| `version`  | Version number                       | `v1`, `v2`, `v3`                  |

**Examples:**
- `casa_product-terms_v1.pdf` — CASA account product terms, version 1
- `murabaha_faq_v1.pdf` — Murabaha financing FAQ
- `takaful_policy-document_v2.pdf` — Takaful insurance policy, version 2
- `general_shariah-principles_v1.pdf` — General Shariah compliance principles

### `processed/` — Processed Text (Auto-generated)

This folder will be populated automatically by our processing scripts.
It will contain:
- Cleaned text extracted from PDFs
- Chunked text segments ready for embedding
- Metadata files (source document, page numbers, etc.)

> ⚠️ **Do not manually edit files in `processed/`.** They are regenerated from `raw/` documents.
