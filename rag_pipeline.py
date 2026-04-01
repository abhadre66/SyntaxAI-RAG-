from dotenv import load_dotenv
import os

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv()

# --- Embeddings & Vector Store ---
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_db = FAISS.load_local(
    "vector_store",
    embeddings,
    allow_dangerous_deserialization=True
)

TOP_K = 3

# --- LLM ---
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

# --- Prompt (fixed: includes both context and question) ---
prompt_template = """
You are a Python expert assistant.

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

Answer:
"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)


def ask_question(question):
    # Step 1: Retrieve top-k from FAISS
    docs = vector_db.similarity_search(question, k=TOP_K)

    if not docs:
        return {
            "answer": "I couldn't find relevant information to answer that question.",
            "sources": []
        }

    # Step 2: Build context from retrieved docs
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    # Step 3: Generate answer
    formatted_prompt = PROMPT.format(context=context, question=question)
    response = llm.invoke(formatted_prompt)

    # Step 4: Deduplicate sources
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