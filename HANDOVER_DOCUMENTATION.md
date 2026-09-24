# 🏛️ Technical Handover Document: LOLC Al-Falaah Islamic Banking Chatbot

**Project Name:** LOLC Al-Falaah Islamic Banking Chatbot & Agentic Assistant  
**Repository:** `Islamic-banking-CHAT-BOT`  
**Date:** September 2026  
**Document Purpose:** Complete knowledge transfer and engineering handover for the incoming AI and Software Engineering team.

---

## 📑 Table of Contents
1. [Executive Summary & System Description](#1-executive-summary--system-description)
2. [Architecture & Technical Specifications](#2-architecture--technical-specifications)
3. [Environment Configuration & Variables (.env)](#3-environment-configuration--variables-env)
4. [Step-by-Step Setup Guide on Another PC](#4-step-by-step-setup-guide-on-another-pc)
5. [Upgrading to Paid / Enterprise Cloud API Keys](#5-upgrading-to-paid--enterprise-cloud-api-keys)
6. [Core Scripts & Maintenance Tasks](#6-core-scripts--maintenance-tasks)
7. [Future Roadmap & Recommended Integrations](#7-future-roadmap--recommended-integrations)
8. [Troubleshooting & FAQs](#8-troubleshooting--faqs)

---

## 1. Executive Summary & System Description

The **LOLC Al-Falaah Islamic Banking Chatbot** is a production-grade conversational AI assistant designed to provide accurate, strictly Shariah-compliant financial information to customers, branch officers, and internal staff.

### Core Capabilities:
- **Strict Shariah Grounding:** Answers are anchored strictly against verified document excerpts (e.g., AAOIFI Shariah Standards, CASA Product Terms, and Core Banking Documentation).
- **Agent Function Calling:**
  - `generate_report`: Generates downloadable Microsoft Word (`.docx`) Shariah reports on demand.
  - `fetch_url_content`: Autonomously visits web links, extracts clean article and table content, and synthesizes answers with source citations.
- **Ultra-Fast Real-Time Streaming:** Uses Server-Sent Events (SSE) via `/chat/stream` to stream response tokens instantly with dynamic blinking cursor animations on the React frontend.
- **HNSW Vector Acceleration:** Neon PostgreSQL with `pgvector` accelerated with an HNSW index for sub-10ms vector similarity searches.
- **Dual-Tier Caching:** Redis caching for query embeddings with in-memory LRU fallback.

---

## 2. Architecture & Technical Specifications

```
┌─────────────────────────────────────────────────────────────┐
│                 React Frontend (Port 3000)                  │
│       Modern Dark/Gold Theme • SSE Streaming • Citations    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / SSE Stream
┌──────────────────────────────▼──────────────────────────────┐
│                 FastAPI Backend (Port 8000)                 │
│                                                             │
│  ┌───────────────────────┐       ┌──────────────────────┐  │
│  │ Embedding Model Cache │       │  Neon PostgreSQL DB  │  │
│  │ BAAI/bge-large-en     │       │  pgvector + HNSW     │  │
│  │ (Redis / LRU)         │       │  Threaded Pool (2-10)│  │
│  └───────────────────────┘       └──────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Gemini Agent Engine                  │  │
│  │  - Model: gemini-3.5-flash-lite / gemini-3.5-flash    │  │
│  │  - Fallback: Multi-model auto retry                   │  │
│  │  - Tools: generate_report, fetch_url_content          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack:
- **Backend Framework:** FastAPI, Uvicorn (ASGI)
- **LLM Engine:** Google GenAI Python SDK (`google-genai`)
- **Embedding Model:** `sentence-transformers` (`BAAI/bge-large-en-v1.5` / configurable to `bge-small`)
- **Database:** Neon PostgreSQL with `pgvector` & HNSW indexing
- **Web Extraction:** `trafilatura`, `beautifulsoup4`, `httpx`
- **Report Generation:** `python-docx`
- **Frontend:** React 18, Styled-Components, Lucide Icons, EventSource streaming

---

## 3. Environment Configuration & Variables (`.env`)

> [!NOTE]
> The active `.env` file containing database connections and API keys will be **provided externally and securely** by the outgoing engineer. Place that file directly into the `backend/` directory (`backend/.env`).

Below is the detailed reference of all variables configured inside the `.env` file:

```bash
# ==============================================================================
# LOLC Al-Falaah Backend Environment Configuration
# ==============================================================================

# 1. Google Gemini API Key (Can be Free tier or Paid Google Cloud Vertex / AI Studio)
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE

# 2. Neon PostgreSQL Database Connection (Must support pgvector)
NEON_DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
# Note: Neon_db is also supported as an alias for backwards compatibility:
Neon_db=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require

# 3. Primary LLM Model Selection (Default: gemini-3.5-flash-lite)
GEMINI_MODEL=gemini-3.5-flash-lite

# 4. Embedding Model Name (Default: BAAI/bge-large-en-v1.5)
# Set to BAAI/bge-small-en-v1.5 for faster, lightweight RAM environments
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# 5. Redis Cache URL (Optional - Falls back to LRU in-memory cache if not present)
REDIS_URL=redis://localhost:6379/0
EMBEDDING_CACHE_TTL=3600
```

### Explanation of Environment Variables:
| Variable | Required? | Purpose & Technical Behavior |
| :--- | :---: | :--- |
| `GEMINI_API_KEY` | **Yes** | Authenticates with Google GenAI API for model completions and function calling. |
| `NEON_DATABASE_URL` / `Neon_db` | **Yes** | Connection string for Neon PostgreSQL database storing vectorized document chunks. |
| `GEMINI_MODEL` | No | Overrides default model (e.g. `gemini-3.5-flash`, `gemini-2.5-pro`, `gemini-3.5-flash-lite`). |
| `EMBEDDING_MODEL` | No | Overrides embedding model name. |
| `REDIS_URL` | No | Redis connection URI. If absent or unreachable, the system automatically uses in-memory LRU caching without error. |

---

## 4. Step-by-Step Setup Guide on Another PC

Follow these exact steps to run the complete system on a new PC or server.

### Prerequisites:
1. **Python 3.10 to 3.14** installed (`python --version`)
2. **Node.js 18+ and npm** installed (`node --version`)
3. **Git** installed

---

### Step 1: Clone or Copy the Repository
```bash
git clone <repository-url>
cd Islamic-banking-CHAT-BOT
```

### Step 2: Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate a Python virtual environment (Recommended)
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Place your .env file
# Copy the .env file provided externally by the engineer into this folder:
# backend/.env

# 5. Verify database and HNSW index
python scripts/create_hnsw_index.py


# 6. Start the FastAPI backend server
uvicorn main:app --reload --port 8000
```
Backend health check is accessible at: `http://localhost:8000/`

---

### Step 3: Frontend Setup
Open a **new terminal**:
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start the React development server
npm start
```
The web chat application will launch at: `http://localhost:3000/`

---

## 5. Upgrading to Paid / Enterprise Cloud API Keys

When the AI team acquires an **Enterprise / Paid Tier Google Cloud Gemini API Key**:

1. **How to Apply the Key:**
   Simply update `GEMINI_API_KEY` in `backend/.env`:
   ```env
   GEMINI_API_KEY=AIzaSy...PAID_ENTERPRISE_KEY...
   ```
2. **Set High-Performance Model:**
   For enterprise throughput and reasoning, set in `backend/.env`:
   ```env
   GEMINI_MODEL=gemini-3.5-flash
   # or for deep reasoning:
   # GEMINI_MODEL=gemini-2.5-pro
   ```
3. **Multi-Model Fallback Resilience:**
   `backend/main.py` already includes automatic multi-model fallback:
   ```python
   models_to_try = [GEMINI_MODEL_NAME, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
   ```
   If a model encounters demand spikes or quota exhaustion, it seamlessly attempts the next candidate without crashing the user session.

---

## 6. Core Scripts & Maintenance Tasks

| Script Path | Purpose & How to Run |
| :--- | :--- |
| `backend/scripts/create_hnsw_index.py` | Upgrades `pgvector` ivfflat index to HNSW for 2-5x faster vector searches.<br>`python scripts/create_hnsw_index.py` |
| `backend/scripts/ingest_url.py` | Scrapes any public documentation URL, chunks, embeds, and permanently saves to Neon DB.<br>`python scripts/ingest_url.py "https://example.com/doc" "Document Title"` |
| `backend/scripts/ingest_mambu.py` | Ingests MAMBU Shariah Deposit Principles documentation into pgvector.<br>`python scripts/ingest_mambu.py` |
| `backend/scripts/fast_ingest.py` | High-speed batch ingestion of AAOIFI Shariah standards PDF into database.<br>`python scripts/fast_ingest.py` |

---

## 7. Future Roadmap & Recommended Integrations

For the incoming AI Engineering team, the system is architected around **Agent Function Calling**, making it easy to plug in external services:

```mermaid
flowchart LR
    Agent["FastAPI Agent Hub"]
    Agent --> Gmail["Gmail API<br/>Auto Quotations & Customer Inquiries"]
    Agent --> GDrive["Google Drive API<br/>Auto Ingestion of Shariah Circulars"]
    Agent --> Playwright["Playwright Crawler<br/>Core Banking & Central Bank Scraper"]
    Agent --> Canva["Canva / Pillow API<br/>Shariah Marketing Banners & Visuals"]
```

### 1. 📧 Gmail Integration
- **Use Case:** Automatically email generated Word reports (`.docx`) or send personalized Murabaha/Ijarah quotations directly to customer inquiries.
- **Implementation:** Create `backend/tools/email_tool.py` using `google-api-python-client` with Gmail API v1. Register tool `send_customer_email(to_email, subject, body, attachment_path)` in `AGENT_TOOLS`.

### 2. 📂 Google Drive Integration
- **Use Case:** Synchronize internal bank folders. Whenever the Shariah Supervisory Committee drops a new PDF circular or policy update into a designated Google Drive folder, a webhook triggers `fast_ingest.py` to auto-vectorize and update pgvector.
- **Implementation:** Google Drive API v3 change notifications (Webhooks) -> FastAPI `/admin/sync-drive` endpoint.

### 3. 🎭 Playwright Browser Automation
- **Use Case:** For websites that require JavaScript rendering, single-page apps (SPAs), login credentials, or CAPTCHA-free Central Bank exchange rate extraction.
- **Implementation:** Install `playwright` (`pip install playwright && playwright install chromium`). Replace `httpx` in `url_tool.py` with headless Playwright page navigation.

### 4. 🎨 Canva / Image Generation Integration
- **Use Case:** Generate branded Islamic Banking social media posts, Shariah profit-rate infographics, or marketing visuals.
- **Implementation:** Integrate Canva Connect API or local image templating (Pillow/SVG renderer) as an agent tool `generate_infographic(topic, stats)`.

---

## 8. Troubleshooting & FAQs

### Q1: The backend fails with `ModuleNotFoundError: No module named 'psycopg2'`
**Fix:** Run `pip install psycopg2-binary`. On Windows, ensure you are inside the activated virtual environment.

### Q2: Gemini returns `429 RESOURCE_EXHAUSTED` or `503 UNAVAILABLE`
**Fix:** 
1. The backend automatically attempts fallback models (`gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-2.5-flash`).
2. Upgrade to a paid billing project in Google Cloud / AI Studio to remove the 20-request/day free-tier ceiling.

### Q3: How do I change the bank name from LOLC Al-Falaah to another institution?
**Fix:** Edit `backend/prompts/system_prompt.txt` and replace `[Bank Name]` or references to LOLC Al-Falaah.

---
**Handover Completed Successfully.**  
*For questions regarding this repository, refer to the code structure and inline documentation.*
