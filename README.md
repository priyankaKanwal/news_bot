# AI News Intelligence

An AI-powered news chatbot that collects recent articles from configured RSS feeds, indexes them for semantic search, and answers questions with links to the source articles. Chat conversations are saved so they can be reopened or deleted from the frontend.

The current implementation uses **Google Gemini** (via `langchain-google-genai`) for answer generation, **Jina AI** (`jina-embeddings-v3`) for embeddings, a local **Hugging Face cross-encoder** for reranking, **Qdrant** for article chunks, and **PostgreSQL** for chat history.

## What it does

- Fetches and parses the RSS feeds listed in [`feeds.yaml`](feeds.yaml).
- Cleans article text and canonicalizes URLs; skips invalid articles, missing dates, and articles outside the last 30 days.
- Deduplicates by article ID, canonical URL, publisher-scoped feed GUID, and normalized content.
- Splits articles into overlapping text chunks and stores them with metadata in Qdrant.
- Retrieves relevant recent news, optionally reranks it, and asks Gemini to answer using only the retrieved articles.
- Provides a recency-based roundup for broad questions such as “What are the latest headlines?”
- Stores conversations and messages in PostgreSQL and displays them in the React chat interface.
- Returns source titles, publishers, publication dates, links, and relevance scores with answers.

The assistant is designed to say when the available articles do not contain enough information. It is not a general-purpose or real-time news service: answers depend on the feeds that have been ingested.

## Architecture

```text
RSS feeds
   │
   ▼
Ingestion: fetch → clean/normalize → date filter → deduplicate → chunk/embed
   │                                                                  │
   └──────────────────────────────► Qdrant ◄─────────────────────────┘
                                        │
React frontend ── HTTP ──► FastAPI chat API
                                        │
                              retrieve and rerank
                                        │
                                 Google Gemini
                                        │
                           answer and article sources

FastAPI and ingestion ──► PostgreSQL (articles and chat history)
```

Ingestion can be run manually or by a separate daily scheduler process. The scheduler
does not run inside the FastAPI application.

## Project layout

```text
.
├── backend/       # FastAPI app, chat API, SQLAlchemy models and services
├── docs/          # Product requirements, project plan, and build guide
├── frontend/      # React + Vite + Tailwind chat interface
├── ingestion/     # RSS loading, cleaning, filtering, deduplication, storage
├── rag/           # Qdrant, retrieval, reranking, and answer generation
├── docker-compose.yml
├── feeds.yaml
└── requirements.txt
```

## Requirements

- Python 3.11
- Node.js and npm (the frontend uses Vite)
- Docker Desktop with Docker Compose
- A Google Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))
- A Jina AI API key ([jina.ai](https://jina.ai/embeddings))
- Enough memory and disk space for the local reranker model

The first chat request may download the Hugging Face reranker model. Embedding and answer generation call hosted APIs, so ingestion and chat need internet access and use your Jina and Gemini quotas.

## Setup

Commands below use PowerShell on Windows. Run each long-lived service in its own terminal.

### 1. Create the backend environment

From the repository root:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents environment activation, either allow local activation scripts for your user or invoke the environment directly, for example:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure environment variables

Copy [`.env.example`](.env.example) to `.env` in the repository root and fill in the API keys. The following values work with the development defaults in `docker-compose.yml`:

```dotenv
POSTGRES_DB=news_bot
POSTGRES_USER=news_bot
POSTGRES_PASSWORD=news_bot_dev
DATABASE_URL=postgresql+psycopg://news_bot:news_bot_dev@localhost:5434/news_bot

QDRANT_URL=http://localhost:6333

GOOGLE_API_KEY=your-gemini-api-key
LLM_MODEL=gemini-2.5-flash
JINA_API_KEY=your-jina-api-key

INGESTION_SCHEDULE_HOUR=2
INGESTION_SCHEDULE_MINUTE=0
INGESTION_TIMEZONE=UTC
```

These PostgreSQL credentials are for local development only. Use strong credentials and appropriately secured services outside a local environment. Keep real credentials out of source control; `.env` is ignored by Git.

The ingestion scheduler defaults to 02:00 UTC each day. Set the hour, minute, and
timezone above to change its daily run time. Use a valid timezone name such as
`Asia/Kolkata`.

Optional RAG settings:

| Variable | Default | Description |
|---|---:|---|
| `RETRIEVE_TOP_K` | `10` | Maximum candidate chunks to retrieve |
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini model used for answers |
| `SCORE_THRESHOLD` | `0.60` | Minimum vector relevance score, `(cosine + 1) / 2` |
| `RERANK_TOP_N` | `3` | Number of chunks kept after reranking |
| `USE_RERANKER` | `1` | Set to `0` to disable the cross-encoder reranker |
| `NEAR_DUPLICATE_THRESHOLD` | `0.88` | Cosine similarity at which two articles count as the same story |

Set `QDRANT_URL` to an empty value to use Qdrant's local on-disk mode (`qdrant_db`) instead of the Docker service.

### 3. Start Qdrant and PostgreSQL

```powershell
docker compose up -d
docker compose ps
```

- Qdrant API and dashboard: <http://localhost:6333/dashboard>
- PostgreSQL is exposed on `localhost:5434`.

The databases use named Docker volumes and persist across container restarts. **`docker compose down -v` deletes the stored Qdrant and PostgreSQL data.**

### 4. Ingest news articles

From the repository root, with the Python environment active:

```powershell
python -m ingestion.ingestion_service
```

The command reports fetched, kept, and skipped articles per feed, failed feeds, duplicates, expired articles/chunks deleted, articles saved to PostgreSQL, and new articles/chunks indexed in Qdrant. A failed feed is reported and does not prevent the other configured feeds from being processed.

To add or remove sources, edit `feeds.yaml`. Check each publisher's terms before adding a feed. The manual command runs once; start the scheduler separately for automatic daily ingestion:

```powershell
.\venv\Scripts\python.exe -m ingestion.scheduler
```

Keep that process running in its own terminal or managed service. It runs ingestion
at the next configured time (not immediately on startup), retries transient feed
request failures using the existing fetcher, and continues processing other feeds
when one feed fails. Run only one scheduler instance to avoid overlapping scheduled
runs. Stop it with `Ctrl+C`.

### 5. Start the API

In another terminal, from the repository root:

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

The API is available at <http://localhost:8000>. Interactive API documentation is at <http://localhost:8000/docs>. On startup, the app creates the conversation tables in PostgreSQL if they do not already exist.

### 6. Start the frontend

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (normally <http://localhost:5173>). The frontend defaults to the API at `http://localhost:8000`. To use another API URL, set `VITE_API_URL` in the frontend environment before starting Vite.

The welcome screen includes the six most recently published, ingested articles from `GET /api/articles/recent`; each story links to its publisher.

## Run the project

After completing the one-time setup above, start the app in separate terminals. Run commands from the repository root unless a step says otherwise.

1. **Start the databases** (Terminal 1):

   ```powershell
   docker compose up -d
   ```

2. **Start scheduled ingestion** (Terminal 2):

   ```powershell
   .\venv\Scripts\python.exe -m ingestion.scheduler
   ```

   The scheduler stays running and ingests daily at the configured time. To run an
   immediate one-off ingestion instead, use
   `.\venv\Scripts\python.exe -m ingestion.ingestion_service` in another terminal.

3. **Start the backend API** (Terminal 3):

   ```powershell
   .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
   ```

4. **Start the frontend** (Terminal 4):

   ```powershell
   cd frontend
   npm run dev
   ```

   On the first run, install the frontend dependencies before starting Vite with `npm ci`.

5. Open <http://localhost:5173> and ask a question. The API docs are at <http://localhost:8000/docs>, and the Qdrant dashboard is at <http://localhost:6333/dashboard>.

To stop the app, press `Ctrl+C` in the frontend, backend, and scheduler terminals. Stop the databases with `docker compose down` from the repository root. This keeps their data; do not add `-v` unless you intend to delete it.

## API

All endpoints are prefixed with `/api`.

### `GET /api/health`

Checks that the API process is responding.

### `POST /api/ingestion/run`

Runs one ingestion pass for every feed in `feeds.yaml` and returns the ingestion
report. The request has no body. This endpoint waits until ingestion finishes;
use the command-line ingestion process or scheduler for longer-running jobs.

Try it from <http://localhost:8000/docs>. This development API has no
authentication, so keep the endpoint local and do not expose it publicly.

Ingestion saves article details in PostgreSQL and searchable chunks in Qdrant.
When run against existing Qdrant data, it saves articles available in the
configured feeds without indexing those same articles again.

### `POST /api/chat`

Ask a question. Omit `conversation_id` or send it as `null` to create a conversation; pass the ID returned by a previous response to continue one.

Request:

```json
{
  "question": "What are the latest technology headlines?",
  "conversation_id": null
}
```

`question` must contain 3–500 characters.

Response:

```json
{
  "conversation_id": "00000000-0000-0000-0000-000000000000",
  "answer": "A concise answer grounded in the retrieved articles.",
  "sources": [
    {
      "title": "Example article",
      "publisher": "Example publisher",
      "published_at": "2026-01-01T10:00:00+00:00",
      "url": "https://example.com/news/article",
      "score": 0.82
    }
  ]
}
```

The UUID and article values above are illustrative. If answer generation fails, the API returns `502`; when a conversation was created, the response includes its ID in the `X-Conversation-ID` header.

### `GET /api/conversations`

Lists conversations, most recently updated first. Each item includes its ID, title, and creation/update timestamps.

### `GET /api/conversations/{conversation_id}`

Returns a conversation and its saved messages, including sources. Returns `404` if the conversation does not exist.

### `DELETE /api/conversations/{conversation_id}`

Deletes a conversation and its messages. Returns `204` on success or `404` if it does not exist.

The API currently allows browser requests from `http://localhost:5173`. Update the CORS configuration in `backend/main.py` if your frontend runs from another origin.

## Useful commands

Run these from the repository root unless noted:

```powershell
# Start or stop the local databases
docker compose up -d
docker compose down

# Run ingestion
python -m ingestion.ingestion_service

# Run daily ingestion scheduler (keeps running until Ctrl+C)
python -m ingestion.scheduler

# Run the backend
python -m uvicorn backend.main:app --reload

# Frontend checks (from frontend/)
npm run lint
npm run build
```

## Troubleshooting

- **API cannot connect to PostgreSQL:** confirm `docker compose ps` shows PostgreSQL as healthy, and that `DATABASE_URL` uses port `5434`.
- **API or ingestion cannot connect to Qdrant:** confirm the Qdrant container is running and `QDRANT_URL` is `http://localhost:6333`.
- **Gemini error (`GOOGLE_API_KEY is not set`, 401/403, or model not found):** check `GOOGLE_API_KEY` in `.env` and that `LLM_MODEL` is a model your key can use.
- **Jina error (`JINA_API_KEY is not set`, 401, or 429):** check `JINA_API_KEY`; 429 means the rate limit or token quota was hit (requests are retried with backoff).
- **No articles are stored:** inspect the ingestion report. Entries with missing/invalid publication dates and entries older than 30 days are skipped. Verify that feed URLs in `feeds.yaml` are reachable and return RSS/Atom content.
- **No sources or “not enough information” answer:** rerun ingestion and check that recent articles have been stored; retrieval also applies a relevance threshold.
- **Embedding dimension error:** the existing Qdrant collection was created with a different vector size/model (for example, 384-dim vectors from the earlier `bge-small` model; Jina produces 1024-dim). Back up anything needed before deleting and recreating the collection, then rerun ingestion.
- **Frontend cannot reach the API:** ensure the API is running on port `8000`; if using a different address, set `VITE_API_URL` and allow that frontend origin in the backend CORS settings.

## Current scope and planned work

The repository's [`docs/Plan.md`](docs/Plan.md) and [`docs/PRD.md`](docs/PRD.md) describe the broader project goals. The README documents the current code: ingestion runs manually or through a standalone daily scheduler, chat answers are not streamed, and there is no authentication or per-user conversation isolation. Do not expose this development API publicly without adding appropriate access controls, operational safeguards, and production configuration.
