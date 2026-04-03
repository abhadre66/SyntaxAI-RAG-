from dotenv import load_dotenv
import os
import re

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import PromptTemplate

load_dotenv()

# --- Embeddings & Vector Store ---
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_db = PineconeVectorStore(
    index_name="syntax",
    embedding=embeddings
)

RETRIEVAL_K = 6   # Fetch more candidates for re-ranking
FINAL_K = 3       # Return top 3 after re-ranking

# --- Source Authority Weights (higher = more authoritative) ---
SOURCE_PRIORITY = {
    "Python Docs": 5,
    "Python StdLib": 5,
    "PEPs": 4,
    "RealPython": 3,
    "GeeksforGeeks": 2,
    "StackOverflow": 1,
}

# --- Query Intent Detection ---
ERROR_PATTERNS = re.compile(
    r"(error|exception|traceback|bug|fix|crash|fail|issue|broken|doesn't work|not working|debug)",
    re.IGNORECASE
)
CONCEPT_PATTERNS = re.compile(
    r"(what is|what are|explain|concept|difference between|vs |meaning of|define|overview|why does)",
    re.IGNORECASE
)
HOWTO_PATTERNS = re.compile(
    r"(how to|how do|how can|tutorial|example|implement|create|build|make|write|setup|install|step)",
    re.IGNORECASE
)

# Query type -> per-source bonus
QUERY_SOURCE_BONUS = {
    "error":   {"StackOverflow": 3, "RealPython": 1},
    "concept": {"Python Docs": 3, "Python StdLib": 3, "PEPs": 2},
    "howto":   {"RealPython": 3, "Python Docs": 1, "GeeksforGeeks": 1},
}


def classify_query_type(question):
    """Classify query intent for source routing."""
    if ERROR_PATTERNS.search(question):
        return "error"
    if CONCEPT_PATTERNS.search(question):
        return "concept"
    if HOWTO_PATTERNS.search(question):
        return "howto"
    return "general"


def rerank_by_source(docs_with_scores, query_type):
    """Re-rank retrieved docs using source authority + query-type routing."""
    query_bonus = QUERY_SOURCE_BONUS.get(query_type, {})

    ranked = []
    for doc, score in docs_with_scores:
        source = doc.metadata.get("source", "Unknown")
        priority = SOURCE_PRIORITY.get(source, 0)
        bonus = query_bonus.get(source, 0)
        # score is relevance (higher = better). Add small boost so
        # source preference breaks ties but doesn't override relevance.
        final_score = score + (priority + bonus) * 0.01
        ranked.append((doc, final_score))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:FINAL_K]]


# --- LLM ---
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

# --- Router: Classify if the message needs RAG or is just conversation ---
router_prompt = PromptTemplate(
    template="""Classify this user message as either "chat" or "question".

- "chat" = greetings, casual talk, thank you, goodbye, or anything that does NOT need Python documentation to answer.
- "question" = anything that needs Python knowledge, code help, debugging, or technical explanation.

Respond with ONLY one word: chat or question

User message: {message}""",
    input_variables=["message"]
)

# --- Condense follow-up questions into standalone questions ---
condense_prompt = PromptTemplate(
    template="""Given the conversation history and a follow-up question, rephrase the follow-up into a standalone question that captures the full context. If the follow-up is already self-contained, return it as-is.

Chat History:
{chat_history}

Follow-up Question: {question}

Standalone Question:""",
    input_variables=["chat_history", "question"]
)

# --- Chat prompt (no RAG context needed) ---
chat_prompt = PromptTemplate(
    template="""You are SyntaxAI, a friendly Python expert assistant.

Respond naturally to the user's message. Be conversational, warm, and helpful. If they greet you, greet them back and let them know you can help with Python questions. Keep it brief.

User: {message}

Response:""",
    input_variables=["message"]
)

# --- RAG prompt (with context from docs) ---
rag_prompt = PromptTemplate(
    template="""You are SyntaxAI, a Python expert assistant.

Answer the question clearly and neatly using this format:

- Use short paragraphs
- Use bullet points when helpful
- Use headings when needed
- Use code blocks for examples (```python)
- Keep answers clean and readable

Context:
{context}

Question:
{question}

Answer:""",
    input_variables=["context", "question"]
)


def condense_question(question, chat_history):
    """Reformulate a follow-up question using recent chat history."""
    if not chat_history:
        return question

    history_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_history[-6:]  # last 3 exchanges max
    )

    response = llm.invoke(condense_prompt.format(
        chat_history=history_text,
        question=question
    ))
    return response.content.strip()


def ask_question(question, chat_history=None):
    # Step 1: Route — is this chat or a real question?
    route = llm.invoke(router_prompt.format(message=question)).content.strip().lower()

    # Step 2: If casual chat, respond without RAG
    if route == "chat":
        response = llm.invoke(chat_prompt.format(message=question))
        return {
            "answer": response.content,
            "sources": []
        }

    # Step 3: Condense follow-up into standalone question
    standalone_question = condense_question(question, chat_history)

    # Step 4: Classify query type for source routing
    query_type = classify_query_type(standalone_question)

    # Step 5: Retrieve top-K from Pinecone (with relevance scores)
    docs_with_scores = vector_db.similarity_search_with_relevance_scores(
        standalone_question, k=RETRIEVAL_K
    )

    if not docs_with_scores:
        return {
            "answer": "I couldn't find relevant information to answer that question.",
            "sources": []
        }

    # Step 6: Re-rank by source authority + query routing
    docs = rerank_by_source(docs_with_scores, query_type)

    # Step 7: Build context from re-ranked docs
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    # Step 8: Generate answer
    formatted_prompt = rag_prompt.format(context=context, question=standalone_question)
    response = llm.invoke(formatted_prompt)

    # Step 9: Deduplicate sources
    seen = set()
    unique_sources = []
    for doc in docs:
        content = doc.page_content[:200]
        if content not in seen:
            seen.add(content)
            unique_sources.append(doc)

    return {
        "answer": response.content,
        "sources": unique_sources
    }
