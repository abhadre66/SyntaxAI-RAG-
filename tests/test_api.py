"""Integration tests for the FastAPI /chat endpoint."""

from unittest.mock import patch
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from main import app

client = TestClient(app)


# ── Input validation ─────────────────────────────────────────────────

def test_empty_question():
    res = client.post("/chat", json={"question": ""})
    assert res.status_code == 200
    assert "valid question" in res.json()["answer"].lower()


def test_whitespace_only_question():
    res = client.post("/chat", json={"question": "   "})
    assert res.status_code == 200
    assert "valid question" in res.json()["answer"].lower()


def test_question_too_long():
    res = client.post("/chat", json={"question": "a" * 1001})
    assert res.status_code == 200
    assert "valid question" in res.json()["answer"].lower()


def test_missing_question_field():
    res = client.post("/chat", json={})
    assert res.status_code == 422  # Pydantic validation error


# ── Chat history ─────────────────────────────────────────────────────

@patch("main.ask_question")
def test_messages_passed_to_pipeline(mock_ask):
    mock_ask.return_value = {"answer": "test", "sources": []}

    messages = [
        {"role": "user", "content": "explain decorators"},
        {"role": "assistant", "content": "Decorators wrap functions."},
    ]
    client.post("/chat", json={"question": "what about with args?", "messages": messages})

    call_args = mock_ask.call_args
    assert call_args[1]["chat_history"] == messages


@patch("main.ask_question")
def test_empty_messages_default(mock_ask):
    mock_ask.return_value = {"answer": "test", "sources": []}

    client.post("/chat", json={"question": "hello"})

    call_args = mock_ask.call_args
    assert call_args[1]["chat_history"] == []


# ── Response format ──────────────────────────────────────────────────

@patch("main.ask_question")
def test_response_has_answer_and_sources(mock_ask):
    doc = Document(
        page_content="Decorators are...",
        metadata={"source": "Python Docs", "url": "https://docs.python.org/decorators"}
    )
    mock_ask.return_value = {
        "answer": "A decorator wraps a function.",
        "source_documents": [doc],
        "sources": [doc],
    }

    res = client.post("/chat", json={"question": "what is a decorator"})
    data = res.json()

    assert "answer" in data
    assert "sources" in data


@patch("main.ask_question")
def test_pipeline_exception_returns_error(mock_ask):
    mock_ask.side_effect = Exception("unexpected crash")

    res = client.post("/chat", json={"question": "anything"})
    data = res.json()

    assert res.status_code == 200
    assert "sorry" in data["answer"].lower()
    assert data["sources"] == []


# ── Health check ─────────────────────────────────────────────────────

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
