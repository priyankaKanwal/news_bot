# AI News Intelligence

An AI-powered news chatbot that collects recent articles from configured RSS feeds, indexes them for semantic search, and answers questions with links to the source articles. Chat conversations are saved so they can be reopened or deleted from the frontend.

The current implementation uses **local Ollama** for answer generation, **Hugging Face sentence-transformer models** for embeddings and reranking, **Qdrant** for article chunks, and **PostgreSQL** for chat history.

## What it does

- Fetches and parses the RSS feeds listed in [`feeds.yaml`](feeds.yaml).
- Cleans article text and canonicalizes URLs; skips invalid articles, missing dates, and articles outside the last 30 days.
- Deduplicates by article ID, canonical URL, publisher-scoped feed GUID, and normalized content.
- Splits articles into overlapping text chunks and stores them with metadata in Qdrant.
- Retrieves relevant recent news, optionally reranks it, and asks a local LLM to answer using only the retrieved articles.
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
                                 local Ollama
                                        │
                           answer and article sources

FastAPI ──► PostgreSQL (conversations and messages)
```

Ingestion is run manually with the command below. A daily scheduler is not currently wired into the application.

## Project layout

```text
.
├── backend/       # FastAPI app, chat API, SQLAlchemy models and services
├── docs/          # Product requirements, project plan, and build guide
├── frontend/      # React + Vite chat interface
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
- [Ollama](https://ollama.com/) installed and running locally
- Enough memory and disk space for the local embedding and reranker models

The first ingestion or chat request may download the configured Hugging Face models. Ollama must have the configured LLM model available locally.

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

Create a `.env` file in the repository root. The following values work with the development defaults in `docker-compose.yml`:

```dotenv
POSTGRES_DB=news_bot
POSTGRES_USER=news_bot
POSTGRES_PASSWORD=news_bot_dev
DATABASE_URL=postgresql+psycopg://news_bot:news_bot_dev@localhost:5434/news_bot

QDRANT_URL=http://localhost:6333
OLLAMA_URL=http://localhost:11434
LLM_MODEL=llama3.2
```

These PostgreSQL credentials are for local development only. Use strong credentials and appropriately secured services outside a local environment. Keep real credentials out of source control; `.env` is ignored by Git.

Optional RAG settings:

| Variable | Default | Description |
|---|---:|---|
| `RETRIEVE_TOP_K` | `10` | Maximum candidate chunks to retrieve |
| `SCORE_THRESHOLD` | `0.70` | Minimum vector relevance score |
| `RERANK_TOP_N` | `3` | Number of chunks kept after reranking |
| `USE_RERANKER` | `1` | Set to `0` to disable the cross-encoder reranker |

Set `QDRANT_URL` to an empty value to use Qdrant's local on-disk mode (`qdrant_db`) instead of the Docker service.

### 3. Start Qdrant and PostgreSQL

```powershell
docker compose up -d
docker compose ps
```

- Qdrant API and dashboard: <http://localhost:6333/dashboard>
- PostgreSQL is exposed on `localhost:5434`.

The databases use named Docker volumes and persist across container restarts. **`docker compose down -v` deletes the stored Qdrant and PostgreSQL data.**

### 4. Prepare Ollama

Start Ollama if it is not already running, then download the configured model:

```powershell
ollama pull llama3.2
```

If you change `LLM_MODEL`, pull that model instead and update the `.env` value.

### 5. Ingest news articles

From the repository root, with the Python environment active:

```powershell
python -m ingestion.ingestion_service
```

The command reports fetched, kept, and skipped articles per feed, failed feeds, duplicates, expired chunks deleted, and newly stored articles/chunks. A failed feed is reported and does not prevent the other configured feeds from being processed.

To add or remove sources, edit `feeds.yaml`. Check each publisher's terms before adding a feed. The ingestion process runs only when invoked; configure an external scheduler if you need automatic daily ingestion.

### 6. Start the API

In another terminal, from the repository root:

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

The API is available at <http://localhost:8000>. Interactive API documentation is at <http://localhost:8000/docs>. On startup, the app creates the conversation tables in PostgreSQL if they do not already exist.

### 7. Start the frontend

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (normally <http://localhost:5173>). The frontend defaults to the API at `http://localhost:8000`. To use another API URL, set `VITE_API_URL` in the frontend environment before starting Vite.

## Run the project

After completing the one-time setup above, start the app in separate terminals. Run commands from the repository root unless a step says otherwise.

1. **Start the databases** (Terminal 1):

   ```powershell
   docker compose up -d
   ```

2. **Start Ollama** (Terminal 2): open the Ollama desktop app, or run `ollama serve` if it is not already running. Make sure the configured model has been downloaded (for example, run `ollama pull llama3.2` once).

3. **Fetch and index the latest feed articles** (Terminal 3):

   ```powershell
   .\venv\Scripts\python.exe -m ingestion.ingestion_service
   ```

   Wait for ingestion to finish. Run this again whenever you want to refresh the news; it is not scheduled automatically.

4. **Start the backend API** (Terminal 4):

   ```powershell
   .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
   ```

5. **Start the frontend** (Terminal 5):

   ```powershell
   cd frontend
   npm run dev
   ```

   On the first run, install the frontend dependencies before starting Vite with `npm ci`.

6. Open <http://localhost:5173> and ask a question. The API docs are at <http://localhost:8000/docs>, and the Qdrant dashboard is at <http://localhost:6333/dashboard>.

To stop the app, press `Ctrl+C` in the frontend, backend, and any terminal running Ollama. Stop the databases with `docker compose down` from the repository root. This keeps their data; do not add `-v` unless you intend to delete it.

## API

All endpoints are prefixed with `/api`.

### `GET /api/health`

Checks that the API process is responding.

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

# Run the backend
python -m uvicorn backend.main:app --reload

# Frontend checks (from frontend/)
npm run lint
npm run build
```

## Troubleshooting

- **API cannot connect to PostgreSQL:** confirm `docker compose ps` shows PostgreSQL as healthy, and that `DATABASE_URL` uses port `5434`.
- **API or ingestion cannot connect to Qdrant:** confirm the Qdrant container is running and `QDRANT_URL` is `http://localhost:6333`.
- **Ollama connection or model error:** start Ollama, verify the `OLLAMA_URL`, and run `ollama pull <model-name>` for the configured model.
- **No articles are stored:** inspect the ingestion report. Entries with missing/invalid publication dates and entries older than 30 days are skipped. Verify that feed URLs in `feeds.yaml` are reachable and return RSS/Atom content.
- **No sources or “not enough information” answer:** rerun ingestion and check that recent articles have been stored; retrieval also applies a relevance threshold.
- **Embedding dimension error:** the existing Qdrant collection was created with a different vector size/model. Back up anything needed before deleting and recreating the collection, then rerun ingestion.
- **Frontend cannot reach the API:** ensure the API is running on port `8000`; if using a different address, set `VITE_API_URL` and allow that frontend origin in the backend CORS settings.

## Current scope and planned work

The repository's [`docs/Plan.md`](docs/Plan.md) and [`docs/PRD.md`](docs/PRD.md) describe the broader project goals. The README documents the current code: ingestion is manual, chat answers are not streamed, and there is no authentication or per-user conversation isolation. Do not expose this development API publicly without adding appropriate access controls, operational safeguards, and production configuration.
