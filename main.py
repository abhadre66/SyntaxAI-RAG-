import os
from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import ask_question
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

class Message(BaseModel):
    role: str
    content: str

class Query(BaseModel):
    question: str
    messages: list[Message] = []

@app.post("/chat")
def chat(query: Query):
    question = query.question.strip()
    if not question or len(question) > 1000:
        return {"answer": "Please provide a valid question (1-1000 characters).", "sources": []}

    chat_history = [{"role": m.role, "content": m.content} for m in query.messages]
    result = ask_question(question, chat_history=chat_history)

    docs = result.get("source_documents", [])

    sources = []
    seen = set()

    for doc in docs:
        source = doc.metadata.get("source", "")
        url = doc.metadata.get("url", "")

        if source not in seen:
            seen.add(source)
            sources.append({
                "source": source,
                "url": url
            })

    # 🔥 Add citation numbers into answer
    answer = result["answer"]

    for i, s in enumerate(sources):
        answer += f" [{i+1}]"

    return {
        "answer": answer,
        "sources": sources
    }