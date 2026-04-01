# Modification Log

All upgrades applied to the SyntaxAI RAG pipeline, in order of execution.

---

## Upgrade 1: Cross-Encoder Reranker

**File changed:** `rag_pipeline.py`

### What is a Reranker?

- A bi-encoder (FAISS) embeds query and documents **separately** — fast but shallow similarity matching
- A cross-encoder takes the query-document **pair together** as input — slower but far more accurate relevance scoring
- Reranking = over-fetch with bi-encoder → re-score with cross-encoder → keep only the best

### What We Changed

- Added `cross-encoder/ms-marco-MiniLM-L-6-v2` as a reranking step
- FAISS now fetches **top-10** candidates (was top-3)
- Cross-encoder re-scores all 10, keeps **top-3 above score threshold (0.1)**
- Chunks below threshold are dropped entirely — LLM never sees irrelevant context
- Replaced LangChain `RetrievalQA` chain with direct `similarity_search → rerank → llm.invoke()` pipeline for full control

### Prompt Template Fix

- **Bug:** original prompt only had `{context}`, no `{question}` — user's question wasn't explicitly passed to the LLM
- **Fix:** prompt now has both `{context}` and `{question}` as separate variables

### Impact

- Retrieval precision significantly improved — low-relevance chunks filtered out
- Graceful fallback when no relevant content found (instead of hallucinating)
- Direct pipeline gives full control over retrieval logic

---

## Upgrade 2: Chunk Size Optimization

**File changed:** `ingest.py`

### What is Chunking?

- Raw documents are too large to embed or retrieve as-is — they must be split into smaller pieces called **chunks**
- Each chunk gets converted into a vector embedding and stored in the vector database (FAISS)
- At query time: user question embedded → compared against chunk embeddings → most similar chunks retrieved → fed to LLM as context
- **Chunk quality = retrieval quality = answer quality** — if chunks are garbage, everything downstream breaks

### Why Chunk Size Matters

- **Too small** (e.g., 400 chars): sentence fragments with no context — reranker can't score relevance on incomplete thoughts
- **Too large** (e.g., 5000 chars): multiple unrelated topics in one chunk — embeddings become diluted, retrieval loses precision
- **Sweet spot** (800–1200 chars): complete paragraph or concept — embeddings are semantically meaningful, reranker can judge relevance

### Why Chunk Overlap Matters

- Overlap ensures information at chunk boundaries isn't lost
- Without overlap: a key sentence split across two chunks may never be retrievable
- ~20% overlap is standard — preserves boundary context without excessive duplication

### What We Changed

| Setting | Before | After |
|---|---|---|
| `chunk_size` | 400 | 1000 |
| `chunk_overlap` | 100 | 200 |
| `separators` | default | `["\n\n", "\n", ". ", " "]` |

- Explicit separators split at paragraph breaks first, then newlines, then sentences — respects document structure

### Impact

- Chunks contain complete thoughts/paragraphs → reranker scores become meaningful
- Fewer but higher-quality chunks → less noise in retrieval
- LLM context window used more effectively → better answers

---

## Upgrade 3: Data Cleaning — StackOverflow Purge

**Action:** Deleted low-quality files from `data/stackoverflow/`

### What We Did

- **Step 1:** Removed all files under 500 chars → 11 files deleted
- **Step 2:** Removed all files under 1000 chars → 31 more files deleted
- **Result:** 88 → 46 files remaining

### Why

- Files under 1000 chars are typically incomplete answers, single code snippets, or one-liners
- These produce chunks with no meaningful context — pollute retrieval results
- Reranker wastes scoring capacity on junk candidates

---

## Upgrade 4: W3Schools Removal

**Action:** Deleted entire `data/w3schools/` directory (250 files)

**File changed:** `ingest.py` — removed W3Schools from `data_folders` and source mapping

### Why

- Surface-level beginner content — redundant with official Python docs
- Boilerplate-heavy (nav menus, "Try it Yourself »", "Sign in to track progress")
- 250 files of shallow content competing with authoritative sources in retrieval
- After cleaning: official docs and RealPython cover the same topics with far more depth

---

## Upgrade 5: PEP Trimming

**Action:** Kept only 11 high-value PEPs, removed 139 obscure ones

### PEPs Kept

- PEP 8 (style guide), PEP 484 (type hints), PEP 498 (f-strings), PEP 557 (dataclasses), PEP 572 (walrus operator), PEP 634/635/636 (match statement), and other commonly-queried PEPs

### Why

- Most PEPs are historical proposals, rejected ideas, or internal process documents
- Users query about ~20-30 PEPs in practice — the rest is noise
- 150 → 11 files: massive noise reduction with minimal information loss

---

## Upgrade 6: Data Expansion — Python Docs & RealPython Scraper

**File changed:** `Scrape_python_docs.py` (complete rewrite)

### Bugs Fixed in Original Scraper

- **URL resolution:** `urljoin()` instead of string concat — `library/stdtypes.html` now resolves correctly
- **Filename collisions:** full path used as filename (`library_stdtypes.txt` not `stdtypes.txt`)
- **Text cleaning:** strips nav artifacts, blank lines, copyright notices, extra whitespace
- **Content filter:** skips pages under 500 chars

### RealPython Scraper Added

- 58 curated article URLs covering:
  - Core Python (data types, loops, functions, strings)
  - OOP (classes, inheritance, metaclasses, descriptors)
  - Advanced (decorators, generators, async/await, GIL, type checking)
  - Error handling & debugging (exceptions, logging, pdb)
  - File I/O (read/write, CSV, JSON, pathlib)
  - Testing (pytest, unittest)
  - Modules & packaging (imports, venvs, pip)
  - Common libraries (requests, itertools, collections, regex)
- Cleans sidebar, promos, newsletter, and related article blocks
- 1s delay between requests (respectful rate limiting)

---

## Final State: Before vs After

| Metric | Before | After |
|---|---|---|
| Total files | 858 | 775 |
| Total chunks | ~31,700 (400 char) | 23,636 (1000 char) |
| Avg chunk quality | Sentence fragments | Complete paragraphs |
| Sources | 7 (incl. junk) | 5 (cleaned & balanced) |
| Retrieval | Naive top-3 FAISS | Top-10 FAISS → cross-encoder rerank → top-3 |
| Prompt | Missing `{question}` | Proper `{context}` + `{question}` |
| Low-relevance handling | Always returns 3 chunks | Filters by score threshold |

### Source Breakdown (After)

| Source | Files | Status |
|---|---|---|
| python_stdlib | 268 | Unchanged |
| python_docs | 17 + new scraped | Expanded |
| realpython | 6 + 58 new | Expanded |
| geeksforgeeks | 79 | Unchanged |
| stackoverflow | 46 | Cleaned (was 88) |
| peps | 11 | Trimmed (was 150) |
| w3schools | 0 | Removed (was 250) |
