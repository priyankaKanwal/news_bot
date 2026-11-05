# Learning Plan: AI News Chatbot (FastAPI + RAG + React)

Written for: you (JS/TS/React/Node dev learning Python + RAG). Goal is understanding, not speed.

## 1. Stack choices (and why)

| Part | Choice | Why |
|---|---|---|
| Backend | Python 3.11+ + FastAPI | Like Express, but typed (Pydantic ≈ Zod/TS interfaces) and auto-generates API docs at `/docs` |
| RSS | `feedparser` | Standard, handles messy feeds |
| Cleaning | `beautifulsoup4`, `python-dateutil` | HTML stripping, date parsing |
| Embeddings | Gemini embeddings (free tier) | No local GPU; one API key also covers the LLM |
| LLM | Gemini (`google-genai` SDK) | Free tier, supports streaming |
| Vector DB | Qdrant (Cloud free tier, or Docker) | Strong metadata filtering, needed for the 30-day window |
| Scheduler | APScheduler | Runs inside the FastAPI process; far simpler than Celery |
| App DB | SQLite (via SQLAlchemy) | Ingestion logs, chat history. Upgrade to Postgres later if you want |
| RAG | **Custom RAG, no LangChain** | You'll see every step (chunk, embed, search, prompt). Add LangChain later only to compare |
| Frontend | React + Vite + TypeScript | You know it. Streaming via `fetch` + `ReadableStream` (SSE) |
| Testing | `pytest` | |

## 2. Python for a JS dev (do this in the first 2–3 days)

| JS/TS | Python |
|---|---|
| `npm` / `package.json` | `pip` + `venv` / `requirements.txt` (or `uv`) |
| `async/await` | `async def` / `await` (same idea, `asyncio` event loop) |
| TS interfaces / Zod | Pydantic models + type hints |
| Express routes/middleware | FastAPI routes / dependencies / middleware |
| `.env` + dotenv | `.env` + `pydantic-settings` |
| Jest | pytest |

Practice: write 3 small scripts (read a JSON file, call a public API with `httpx`, parse with a Pydantic model). Then build a 3-endpoint FastAPI toy app.

## 3. Core concepts to understand (read/watch as you reach each week)

- **Embedding**: text → vector where similar meaning = nearby vectors.
- **Cosine similarity / semantic search**: how "nearest" is measured.
- **Chunking**: why long articles are split, and chunk size/overlap trade-offs.
- **Vector DB payload + filter**: metadata stored next to the vector, filtered *during* search.
- **RAG**: retrieve → build prompt with context → generate → cite. Hallucination control via prompt rules ("answer only from context, otherwise say you don't know").
- **Idempotency**: running ingestion twice must not create duplicates (deterministic IDs).

## 4. Target structure

```
news_bot/
  backend/
    app/
      main.py            # FastAPI app, startup, scheduler
      config.py          # settings from env
      api/               # routes: chat.py, health.py, admin.py
      ingestion/         # feeds.py, cleaning.py, dedup.py, pipeline.py
      rag/               # embeddings.py, vectorstore.py, retriever.py, prompt.py, llm.py
      jobs/              # scheduler.py, cleanup.py
      db/                # models, session (SQLite)
    feeds.yaml           # RSS sources (add/remove via config)
    tests/
  frontend/              # React + Vite + TS
  docs/
```

Keep ingestion and chatbot decoupled (PRD requirement): they share only the vector store module.

## 5. Week-by-week plan

Each week: **Learn → Build → Checkpoint (explain it out loud) → Commit**.

### Week 0 (2–3 days): Setup + Python/FastAPI basics
- Install Python, create venv, set up git (`.gitignore` with `.env`, `venv`).
- Get Gemini API key + Qdrant Cloud cluster.
- Build the toy FastAPI app; open `/docs`.
- **Checkpoint**: explain what Pydantic validation does for you in a request.

### Week 1: Ingestion pipeline (no AI yet)
1. `feeds.yaml` with ~6–8 feeds across categories (BBC, Reuters-style, The Hindu, Economic Times, TechCrunch, etc. Check each is a working public RSS and respect terms).
2. `feedparser` fetch → normalize into an `Article` Pydantic model (title, summary, url, publisher, published_at, category, author, image, guid).
3. Cleaning: strip HTML, whitespace/entities, normalize dates to UTC, handle missing dates (fallback to ingestion time, flagged), drop too-short articles.
4. Dedup: normalized URL + GUID → hash; then content similarity (start with title normalization / simple fuzzy match; embeddings-based later).
5. Failure handling: per-feed try/except + retries (`tenacity`), logging.
6. Write pytest tests for cleaning, dates, dedup, a dead feed.
- **Deliverable**: `python -m app.ingestion.pipeline` prints a clean deduped dataset.
- **Checkpoint**: why is a deterministic `article_id` (hash of URL) important?

### Week 2: Embeddings + Qdrant + scheduling
1. Call Gemini embeddings on a few strings; compute cosine similarity by hand with numpy to *feel* it.
2. Decide chunking (title + summary/content, ~500 tokens, small overlap). Each chunk payload: `article_id, title, content, publisher, published_at (as timestamp number), category, article_url, ingested_at, chunk_index`.
3. Create Qdrant collection, add payload index on `published_at`, upsert with deterministic point IDs.
4. Ingestion: skip articles whose `article_id` already exists (avoid paying for embeddings twice); batch embedding calls; retry on failure.
5. Ingestion run log table (feeds ok/failed, new, skipped, errors).
6. APScheduler: daily ingestion job (+ manual `/admin/ingest` endpoint for testing).
- **Deliverable**: run twice → second run stores 0 new articles.
- **Checkpoint**: why store `published_at` as a numeric timestamp for range filters?

### Week 3: RAG chatbot
1. Retriever: embed query → Qdrant search with `published_at >= now-30d` filter → top-k (try k=6–8), optional score threshold.
2. Prompt: system rules (use only context, cite sources as [1], [2], say "I don't have enough information" when context is weak), context blocks with publisher + date + URL.
3. `/chat` endpoint returning answer + sources JSON; then streaming (SSE) version.
4. "No relevant news" path: score threshold + prompt instruction. Test with off-topic questions.
5. Improvements to try one at a time: query rewriting for follow-ups (chat history), category filter, MMR/diversity across publishers.
6. Mini eval: 15 questions (from the PRD list) + expected behavior; record results by hand.
- **Checkpoint**: show a case where retrieval fails and explain why (bad chunk, threshold, vocabulary mismatch).

### Week 4: Cleanup, frontend, hardening, deploy
1. Cleanup job: delete by filter `published_at < now-30d` (Qdrant deletes all chunks since each chunk carries the date); log count deleted. Test by inserting a fake 31-day-old article.
2. React UI: chat view, streaming render, sources as clickable cards (publisher, date), suggested questions, new chat, history (localStorage first), loading/error states, mobile layout.
3. Security: keys only in backend env, input length validation, rate limiting (`slowapi`), CORS limited to your frontend.
4. Deploy: backend on Render/Railway (note: free tiers sleep, so scheduler needs an external cron ping or a separate cron job), frontend on Vercel/Netlify.
5. README, architecture diagram, API docs (FastAPI gives these free), testing report covering the 10 mandatory cases.

## 6. Mandatory test cases → where you verify them

| PRD case | How |
|---|---|
| Multiple feeds fetched | ingestion run log |
| No duplicates | run ingestion twice; count unchanged |
| Auto ingestion | scheduler log entry |
| Embeddings stored | Qdrant dashboard point count + payload |
| Answers + sources | chat tests |
| Not older than 30 days | insert old fake article; confirm never retrieved |
| Expired deleted | run cleanup; confirm count drops |
| Dead feed handled | add bad URL to `feeds.yaml`; others still ingest |
| Unavailable info | ask about something not in news |

## 7. Optional extras (after core works)
Daily digest, publisher comparison, trending topics, Hindi support. Pick one only.

## 8. How to work with me (Claude) so you actually learn
- Per task: ask me to **explain first, then you write it, then I review** rather than generating it.
- Say "quiz me" at each checkpoint.
- Stuck? Share the error and what you tried.
- Commit after every checkpoint with a meaningful message.
