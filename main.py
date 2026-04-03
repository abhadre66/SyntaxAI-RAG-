import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import ask_question
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    try:
        chat_history = [{"role": m.role, "content": m.content} for m in query.messages]
        result = ask_question(question, chat_history=chat_history)
    except Exception as e:
        logger.error("Unhandled error in /chat: %s", e)
        return {
            "answer": "Sorry, something went wrong. Please try again.",
            "sources": []
        }

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

    answer = result["answer"]

    for i, s in enumerate(sources):
        answer += f" [{i+1}]"

    return {
        "answer": answer,
        "sources": sources
    }

@app.get("/health")
def health():
    return {"status": "ok"}
