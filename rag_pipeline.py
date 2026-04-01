from dotenv import load_dotenv
import os

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

TOP_K = 3

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


def ask_question(question):
    # Step 1: Route — is this chat or a real question?
    route = llm.invoke(router_prompt.format(message=question)).content.strip().lower()

    # Step 2: If casual chat, respond without RAG
    if route == "chat":
        response = llm.invoke(chat_prompt.format(message=question))
        return {
            "answer": response.content,
            "sources": []
        }

    # Step 3: Retrieve top-k from Pinecone
    docs = vector_db.similarity_search(question, k=TOP_K)

    if not docs:
        return {
            "answer": "I couldn't find relevant information to answer that question.",
            "sources": []
        }

    # Step 4: Build context from retrieved docs
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    # Step 5: Generate answer
    formatted_prompt = rag_prompt.format(context=context, question=question)
    response = llm.invoke(formatted_prompt)

    # Step 6: Deduplicate sources
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
