# SyntaxAI-RAG — Project Review

## Project Summary

A Python documentation Q&A chatbot using LangChain RetrievalQA with FAISS vector store (all-MiniLM-L6-v2 embeddings), GPT-4o-mini, and a Next.js chat frontend. Data scraped from 7 sources (~1700 docs). Essentially a tutorial-grade RAG demo, not a production system.

## Strengths

- **Multi-source ingestion** with metadata/URL preservation enables proper citation
- **Sensible defaults**: 400-char chunks with 25% overlap, temperature=0, source deduplication
- **Clean frontend**: markdown rendering, code copy, collapsible sources, keyboard shortcuts
- **Dual UI**: FastAPI + Next.js for production path, Streamlit for quick prototyping

## Weaknesses

- **No reranking or relevance filtering** — naive top-3 retrieval returns chunks regardless of quality; StackOverflow answers weighted equally to official docs
- **No conversation memory** — each query is stateless, breaking multi-turn interactions
- **Prompt template is broken** — uses `{context}` where `{question}` should be; the user's question may not reach the LLM correctly
- **API key committed to repo** (.env with `sk-proj-*` checked in) — active security vulnerability
- **Zero tests, zero CI/CD, zero Docker** — no way to verify correctness or deploy reliably
- **No input sanitization or rate limiting** on the API; CORS is allow-all
- **No Python type hints**; backend has no error handling (bare pipeline, no try/except)
- **Hardcoded backend URL** (`127.0.0.1:8000`) in frontend — breaks any non-local deployment
- **No evaluation framework** — no way to measure retrieval precision or answer quality

## Improvements (Prioritized)

1. **Fix the prompt template** — add `{question}` variable; currently the chain may silently misroute the query
2. **Remove API key from repo** — rotate the key immediately, add `.env` to `.gitignore`
3. **Add a cross-encoder reranker** (e.g., `ms-marco-MiniLM-L-6-v2`) after retrieval to filter low-relevance chunks
4. **Implement source prioritization** — boost official Python docs, demote StackOverflow
5. **Add conversation memory** via `ConversationBufferMemory` or `ConversationalRetrievalChain`
6. **Build an eval harness** — 50+ question/answer pairs, measure retrieval recall and answer accuracy
7. **Containerize** with Docker Compose (frontend + backend + volume for vector store)
8. **Add error handling** in `rag_pipeline.py` and input validation beyond Pydantic schema
