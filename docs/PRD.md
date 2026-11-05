# Project Requirement Document
# AI-Powered News Intelligence Chatbot
**Project Category:** Generative AI | RAG | Data Engineering | Full-Stack Development  
**Project Type:** Individual or Team Project  
**Target Users:** Interns / GenAI Developers

---

## 1. Project Overview

Develop an AI-powered News Chatbot that automatically collects news articles from multiple reputed RSS news feeds, processes and stores them in a Vector Database, and allows users to interact with the latest news through a conversational AI interface.

The chatbot should answer user queries based on news published within the last 30 days.

The system must automatically fetch new articles, remove duplicate news, generate embeddings, store the processed information in a vector database, and delete expired news articles that are older than 30 days.

The objective is to build a continuously updated News Intelligence System using Retrieval-Augmented Generation (RAG).

## 2. Project Objectives

The application should achieve the following:

1. Automatically extract news articles from multiple RSS feeds.
2. Fetch and process news on a daily basis without manual intervention.
3. Store news articles and their vector embeddings in a Vector Database.
4. Implement a RAG-based chatbot that answers questions using stored news.
5. Restrict chatbot responses to news published within the last 30 days.
6. Automatically delete news articles older than 30 days.
7. Provide relevant source links and publication dates with chatbot responses.
8. Build a clean, responsive frontend for interacting with the chatbot.
9. Ensure that the system handles duplicate articles, ingestion failures, and missing information.

## 3. Functional Requirements

### Module 1: News Extraction (RSS Feed Integration)

Build an automated news extraction pipeline using RSS feeds from reputed news publishers.

**Requirements:**
- Integrate multiple RSS news sources.
- Fetch the latest news articles automatically.
- Extract the following information wherever available:
  - Article Title
  - Article Description / Summary
  - Full Article Content (when legally and technically accessible)
  - News Publisher
  - Publication Date
  - Article URL
  - Category / Topic
  - Author (if available)
  - Image URL (if available)
- Support multiple news categories such as:
  - Business & Finance
  - Technology
  - Politics
  - World News
  - Sports
  - Economy
  - Science & Technology
- Allow RSS feeds to be added or removed through configuration.

**Important:** Do not assume that every RSS feed provides full article content. Implement appropriate handling for feeds that provide only headlines and descriptions. Respect publisher terms, robots policies, and access restrictions.

### Module 2: Data Processing and Cleaning

Before storing news in the database, implement a data processing pipeline.

**Requirements:**
- Remove HTML tags and unnecessary formatting.
- Clean special characters and irrelevant text.
- Handle missing publication dates.
- Normalize publication dates into a consistent timezone format.
- Remove duplicate articles using article URLs, GUIDs, and content similarity.
- Generate clean text suitable for embedding generation.
- Validate that each article contains sufficient information.

**Expected Output:** A structured and clean news dataset ready for embedding generation.

### Module 3: Embedding Generation and Vector Database

Convert processed news articles into vector embeddings and store them in a Vector Database.

**Requirements:**
- Select a suitable embedding model.
- Generate embeddings for news content.
- Store embeddings in a Vector Database.
- Maintain article metadata alongside embeddings.

Suggested Vector Databases:
- Qdrant
- Pinecone
- ChromaDB
- Weaviate

Suggested Embedding Models:
- Google Gemini Embedding Models
- Jina Embeddings
- Sentence Transformers

**Metadata to store:**

| Field | Description |
|---|---|
| article_id | Unique article identifier |
| title | News headline |
| content | Processed news content |
| publisher | News source |
| published_at | Original publication date |
| category | News category |
| article_url | Original news URL |
| ingested_at | Date of ingestion |

**Important:** The vector database must support metadata filtering so that only news published within the last 30 days is retrieved.

### Module 4: Automated Daily News Ingestion

Develop an automated process that fetches and stores new articles every day.

**Requirements:**
- Implement a scheduled ingestion pipeline.
- Fetch new articles from all configured RSS feeds.
- Check whether an article already exists.
- Process only new articles.
- Generate embeddings for new articles.
- Store the embeddings and metadata in the Vector Database.
- Maintain ingestion logs and error reports.
- Implement retry mechanisms for failed RSS feeds or embedding requests.

**Expected Behaviour:**

The system should run automatically every day without requiring manual execution.

Suggested tools:
- Cron Jobs
- APScheduler
- Celery
- Background Workers

### Module 5: Automatic Data Expiration and Cleanup

This is one of the most important requirements of the project.

The Vector Database must maintain a rolling 30-day news window.

**Requirements:**
- Run a scheduled cleanup job at least once every day.
- Identify articles whose publication date is older than 30 days.
- Delete their corresponding vector embeddings and metadata from the Vector Database.
- Ensure that no expired article remains available for chatbot retrieval.
- Maintain cleanup logs.

**Example:**

If today's date is 2 November:

- News published on 2 October or later should be retained.
- News published before 2 October should be deleted.

Use the article's original publication date rather than its ingestion date.

**Important:** The cleanup process should delete the complete article record and all associated chunks, not just the parent metadata.

### Module 6: RAG-Based News Chatbot

Develop a conversational AI chatbot using Retrieval-Augmented Generation.

The chatbot should retrieve relevant information from the Vector Database and generate answers using an LLM.

**Requirements:**

1. Accept natural-language questions from users.
2. Convert the question into an embedding.
3. Perform semantic similarity search in the Vector Database.
4. Apply a 30-day publication-date filter during retrieval.
5. Retrieve the most relevant news articles or content chunks.
6. Pass the retrieved context to the LLM.
7. Generate a clear, relevant, and context-based answer.
8. Include article sources, publishers, dates, and clickable links.
9. Handle questions where relevant news is unavailable.

**Example User Queries:**

- What are the latest developments in the Indian stock market?
- What is happening in the AI industry?
- Summarize the major economic developments this week.
- What are the latest developments in the US-China trade relationship?
- What happened in the Indian economy over the last 30 days?
- Compare the recent news about Reliance Industries and Tata Motors.
- What are the major global geopolitical developments?
- Give me a summary of the latest RBI announcements.

**Important:** The chatbot must not generate fabricated news or present unsupported information as facts.

If relevant information is not available in the Vector Database, the chatbot should clearly communicate that it does not have sufficient information.

### Module 7: Chatbot Frontend

Develop a modern, responsive user interface.

**Suggested Features:**
- Chat interface similar to ChatGPT.
- New Chat functionality.
- Chat history.
- Suggested questions.
- Streaming responses.
- Clickable news sources.
- Publication dates and publisher information.
- Loading indicators.
- Error handling.
- Responsive desktop and mobile layouts.

**Optional Enhancements:**
- News category filters.
- Publisher filters.
- Date-based filters.
- Trending news section.
- Daily news summaries.
- Latest news dashboard.

---

## 4. Suggested Technology Stack

Interns can suggest alternatives, but the following stack is recommended.

| Component | Suggested Technology |
|---|---|
| Frontend | React.js / Next.js |
| Backend | Python FastAPI |
| LLM | Google Gemini / OpenAI |
| Embeddings | Jina / Gemini Embeddings |
| Vector Database | Qdrant |
| RSS Extraction | Feedparser |
| Data Processing | Python |
| RAG Framework | LangChain / Custom RAG |
| Scheduler | APScheduler / Celery |
| Database | PostgreSQL / MongoDB |
| Deployment | Render / AWS / Railway |
| Version Control | Git & GitHub |

Interns should understand why each technology is being used instead of blindly following the suggested stack.

## 5. High-Level System Architecture

The expected application workflow should look like this:

RSS News Feeds  
↓  
Automated News Extraction  
↓  
Data Cleaning & Preprocessing  
↓  
Duplicate Detection  
↓  
Embedding Generation  
↓  
Vector Database (Qdrant)  
↓  
30-Day Data Retention & Cleanup

**Chatbot Workflow:**

User Query  
↓  
Frontend Chat Interface  
↓  
Backend API  
↓  
Query Embedding Generation  
↓  
Vector Database Semantic Search  
↓  
30-Day Date Filter + Relevant Context Retrieval  
↓  
LLM (Gemini / OpenAI)  
↓  
Context-Based Answer with News Sources  
↓  
User

## 6. Non-Functional Requirements

The application should also satisfy the following requirements:

**Performance**
- Chatbot should provide responses within a reasonable time.
- Avoid unnecessary embedding generation for duplicate articles.
- Optimize vector retrieval.

**Reliability**
- The ingestion pipeline should recover from temporary failures.
- One failed RSS feed should not stop the entire ingestion process.
- Failed jobs should be logged and retried where appropriate.

**Scalability**
- Architecture should support adding more RSS feeds.
- The system should be modular and easy to extend.
- Avoid tightly coupling the ingestion pipeline with chatbot functionality.

**Data Accuracy**
- Responses must be grounded in retrieved news.
- All factual claims should have supporting sources.
- The system must distinguish between publication dates and ingestion dates.

**Security**
- Store API keys and credentials in environment variables.
- Never expose API keys on the frontend.
- Validate user inputs.
- Implement appropriate API rate limiting.

## 7. Development Phases & Timeline

Suggested project duration: 3–4 weeks.

| Phase | Tasks | Expected Deliverable |
|---|---|---|
| Week 1 | RSS integration, extraction, cleaning and deduplication | Working news ingestion pipeline |
| Week 2 | Embeddings, Vector DB integration and scheduled ingestion | Automated vector storage |
| Week 3 | RAG implementation, LLM integration and source citations | Functional news chatbot |
| Week 4 | Cleanup automation, frontend, testing and deployment | Complete deployed application |

Interns should maintain a GitHub repository throughout development and commit code regularly.

## 8. Testing & Evaluation Criteria

The completed project will be evaluated on the following parameters:

| Evaluation Parameter | Weightage |
|---|---:|
| RSS Integration & News Extraction | 10% |
| Data Cleaning & Deduplication | 10% |
| Embedding & Vector DB Implementation | 15% |
| Automated Ingestion Pipeline | 10% |
| RAG Architecture & Retrieval Accuracy | 20% |
| 30-Day Data Retention & Cleanup | 10% |
| Frontend & User Experience | 10% |
| Code Quality, Documentation & Deployment | 10% |
| Understanding of Architecture | 5% |
| **Total** | **100%** |

### Mandatory Test Cases

Interns must demonstrate the following:

1. The system can successfully fetch news from multiple RSS feeds.
2. Duplicate articles are not stored multiple times.
3. New articles are automatically ingested.
4. Embeddings are generated and stored correctly.
5. The chatbot can answer questions based on stored news.
6. The chatbot provides relevant source links.
7. The chatbot does not retrieve articles older than 30 days.
8. Expired articles and their embeddings are deleted automatically.
9. The system handles unavailable RSS feeds gracefully.
10. The chatbot responds appropriately when information is unavailable.

## 9. Final Deliverables

At the end of the project, interns must submit:

1. **Complete Source Code:** Frontend and backend repositories.
2. **GitHub Repository:** Properly structured code with meaningful commits.
3. **Working Application:** A deployed and accessible application.
4. **Architecture Diagram:** Complete system architecture and workflow.
5. **Technical Documentation:** Explanation of technologies, APIs, database schema, and implementation.
6. **README File:** Installation instructions, environment variables, and execution steps.
7. **API Documentation:** Backend endpoints and their functionality.
8. **Testing Report:** Test cases, results, and known limitations.
9. **Project Demonstration:** Live walkthrough explaining the complete application.

## 10. Advanced Features (Optional)

Interns who complete the core requirements can explore additional GenAI capabilities.

- **AI Daily News Digest:** Generate a daily summary of the most important news.
- **News Comparison:** Compare how multiple publishers report the same event.
- **Trending Topics Detection:** Identify frequently discussed topics across news sources.
- **Sentiment Analysis:** Analyze the sentiment of news articles.
- **News Categorization:** Automatically classify articles into relevant categories.
- **Entity Extraction:** Identify companies, people, countries, organizations, and other important entities.
- **Follow-up Questions:** Allow users to ask contextual follow-up questions.
- **Multilingual Support:** Allow users to ask questions in Hindi or English.
- **News Impact Analysis:** Explain the potential implications of important business and economic developments.

---

## 11. Important Instructions for Interns

This project is intended to test your understanding of Generative AI and end-to-end application development.

You are expected to:

- Understand the problem statement before starting development.
- Research and select appropriate tools and technologies.
- Understand how embeddings, vector databases, semantic search, and RAG work.
- Write modular, maintainable, and reusable code.
- Avoid relying entirely on AI-generated code without understanding it.
- Test every module independently before integration.
- Maintain proper technical documentation.
- Be prepared to explain every component of your implementation.

**The final objective is not just to build a chatbot. It is to build a reliable, automated, continuously updated News Intelligence System powered by Generative AI.**