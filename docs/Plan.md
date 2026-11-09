# Project Plan: AI-Powered News Intelligence Chatbot

A chatbot that answers questions about the last 30 days of news. A daily job collects articles from trusted RSS feeds and deletes anything older than 30 days. Every answer links to its source articles, and the bot says it doesn't have enough information instead of guessing.

See [PRD.md](PRD.md) for the full requirements and [build-guide.html](build-guide.html) for diagrams and an animated walkthrough.

## Approach

Build a small working version first, then add one or two ideas per version. Every version runs end to end, so there is always something to test and demo. Commit after each version.

The system is two programs that share a database:

- **Ingestion** (PRD Modules 1-5): fetch, clean, deduplicate, embed, store, expire.
- **Chat app** (PRD Modules 6-7): embed the question, search, ask the LLM, show an answer with sources.

## Stack

| Need | Choice |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Frontend | React (Vite, TypeScript) |
| LLM and embeddings | Gemini |
| Vector database | Qdrant (Docker locally) |
| RSS parsing | feedparser |
| Scheduler | APScheduler |
| Relational database | PostgreSQL (SQLite is fine early on) |
| Tests | pytest |

Keep API keys in a `.env` file on the backend. Never put them in the frontend.

## Versions

| Version | What you build | PRD modules | Timing |
|---|---|---|---|
| v0 | RAG in one Python file: 3 hard-coded news items, similarity scoring, a grounded prompt to the LLM | 6 (concept) | Week 1 |
| v1 | Replace the hard-coded list with 2-3 real RSS feeds; strip HTML | 1, part of 2 | Week 1 |
| v2 | Split into `ingest.py` and `ask.py`; store vectors and metadata in Qdrant | 3 | Week 1 |
| v3 | FastAPI `POST /api/chat` and a simple React chat page with source links | 6, 7 basics | Week 2 |
| v4 | 30-day filter on every search, "not enough information" reply, dedup by URL, UTC dates | 2, 6 | Week 2 |
| v5 | Daily scheduled ingestion with retries, cleanup job, Postgres logs, chunking, more feeds, dedup by GUID and content hash | 4, 5 | Week 3 |
| v6 | Streaming, chat history, suggested questions, rate limiting, input validation, near-duplicate detection, deployment, documentation | 7 and the rest | Week 4 |

## Checklist per version

### v0: RAG in one file
- [ ] Install Python, create a virtual environment, get a Gemini API key
- [ ] Run the script and read the printed similarity scores
- [ ] Experiment: ask a different topic and watch the scores reorder
- [ ] Experiment: ask an unrelated question and confirm the answer is "I don't have that information"
- [ ] Experiment: remove the "use ONLY these sources" rule and see the model invent facts
- [ ] Experiment: rephrase the question with different words and see it still match

### v1: Real news, still in memory
- [ ] Choose 2-3 feeds and check each publisher's terms
- [ ] Parse them with feedparser (title, summary, link, publisher, date)
- [ ] Clean HTML from summaries
- [ ] Ask the PRD example questions in a loop

### v2: Qdrant
- [ ] Run Qdrant in Docker and create a collection
- [ ] Split the script into `ingest.py` and `ask.py`
- [ ] Store `published_at` as a UTC Unix timestamp in the payload
- [ ] Replace the manual similarity loop with a Qdrant search
- [ ] Inspect the stored points in the Qdrant dashboard

### v3: Chat app
- [ ] Wrap `ask.py` in FastAPI, returning `{answer, sources}`
- [ ] Build the React page: input, message list, source links
- [ ] Keep the API key on the backend only

### v4: Trustworthy answers
- [ ] Add the 30-day filter on `published_at` to every search
- [ ] Return "not enough information" when the best score is below a threshold
- [ ] Skip articles whose URL is already stored
- [ ] Decide and document what happens when a date is missing

### v5: Runs by itself
- [ ] Move ingestion into an APScheduler daily job with retries and per-feed error handling
- [ ] Add the cleanup job (delete expired points, all chunks included)
- [ ] Add Postgres tables for articles, ingestion runs and cleanup runs
- [ ] Chunk long articles; fetch full text only where robots.txt allows
- [ ] Move the feed list to `feeds.yaml`
- [ ] Deduplicate by GUID and content hash

### v6: Full PRD
- [ ] Stream answers (Server-Sent Events)
- [ ] New chat, chat history, suggested questions, loading and error states, mobile layout
- [ ] Rate limiting and input validation
- [ ] Near-duplicate detection by similarity
- [ ] Deploy backend, Qdrant, Postgres and frontend
- [ ] Write README, API docs, architecture diagram and testing report
- [ ] Rehearse the demo against all 10 mandatory tests

## Key decisions to make early

1. **The 30-day cutoff rule.** The PRD example (today 2 Nov keeps 2 Oct) is a calendar month back, which is 31 days. Exactly 30 days would drop 2 Oct. Pick one rule and put it in a single function that both the search filter and the cleanup job call.
2. **Missing publication dates.** Options are to use the feed's updated time, or skip the article. Document the choice.
3. **One embedding model.** Vectors from different models can't be compared. Switching later means recreating the collection and re-ingesting.
4. **Similarity threshold** for "not enough information". Tune it by testing on real questions.

## Mandatory tests (from the PRD)

| # | Test | How to show it |
|---|---|---|
| 1 | Fetch from multiple feeds | Run log with per-feed counts |
| 2 | No duplicates stored | Run ingestion twice; point count is unchanged |
| 3 | New articles ingested automatically | Scheduler log from an unattended run |
| 4 | Embeddings stored correctly | Qdrant dashboard shows a point with its payload |
| 5 | Answers from stored news | Ask a PRD example question |
| 6 | Relevant source links | Click a source link |
| 7 | Nothing older than 30 days is retrieved | Insert a 40-day-old point; it never appears |
| 8 | Expired articles and embeddings deleted | Run cleanup; the inserted point is gone |
| 9 | Unavailable feeds handled | Add a broken URL; the run still completes |
| 10 | Sensible reply when information is missing | Ask about something not in the news |

## Suggested repo layout

```
news_bot/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── feeds.yaml
│   │   ├── ingestion/    # fetcher, cleaner, dedup, pipeline
│   │   ├── vector/       # embedder, chunker, store
│   │   ├── rag/          # retriever, prompt, chat
│   │   ├── jobs/         # scheduler, cleanup, retention
│   │   └── db/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
├── docs/
├── docker-compose.yml
└── README.md
```

## Common mistakes to avoid

- Relying on the cleanup job alone for the 30-day rule. Filter at search time too.
- Storing dates as strings or local time. Use UTC Unix seconds.
- Using the ingestion date where the PRD requires the publication date.
- Deleting an article but leaving its chunks. Delete by filter on `published_at`.
- Embedding before checking for duplicates. Do the cheap URL checks first.
- Putting the API key in the React app.
- Using code you can't explain. Write each module yourself and test it alone.

## Evaluation weights

| Area | Weight |
|---|---:|
| RAG architecture and retrieval accuracy | 20% |
| Embedding and vector DB | 15% |
| RSS integration and extraction | 10% |
| Cleaning and deduplication | 10% |
| Automated ingestion | 10% |
| 30-day retention and cleanup | 10% |
| Frontend and UX | 10% |
| Code quality, docs, deployment | 10% |
| Understanding of architecture | 5% |
