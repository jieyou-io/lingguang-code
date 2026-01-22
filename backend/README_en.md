# Ling Guang Backend (FastAPI)

<b>English</b> | <a href="README.md">中文</a>

Ling Guang backend service for interacting with local AI CLIs (Claude, Codex, Gemini), providing unified sessions and streaming APIs.

## Requirements
- Python 3.11+

## Quick Start (Local)
1) Create env file:
   - Copy `.env.example` to `.env` and edit values.

2) Install dependencies:
   - `pip install -r requirements.txt`

3) Start the API:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Health Check
- `GET /health`

## Notes
- API payloads use camelCase.
- SSE keepalive is controlled by `SSE_KEEPALIVE_SECONDS` (default 15).
- Session timeout is `SESSION_TIMEOUT_SECONDS` (default 1800).
- Max concurrent sessions: `MAX_CONCURRENT_SESSIONS` (default 10).
