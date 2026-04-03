"""Unit tests for rag_pipeline helper functions."""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


# ── classify_query_type ──────────────────────────────────────────────

from rag_pipeline import classify_query_type


@pytest.mark.parametrize("query, expected", [
    # Error queries
    ("I'm getting a TypeError when calling my function", "error"),
    ("fix this traceback", "error"),
    ("my code is broken", "error"),
    ("IndexError exception in list", "error"),
    ("this doesn't work", "error"),
    ("how to debug a segfault", "error"),
    # Concept queries
    ("what is a decorator in Python", "concept"),
    ("explain list comprehensions", "concept"),
    ("difference between list and tuple", "concept"),
    ("what are generators", "concept"),
    ("why does Python use GIL", "concept"),
    # How-to queries
    ("how to read a CSV file in Python", "howto"),
    ("how can I sort a dictionary", "howto"),
    ("tutorial on async await", "howto"),
    ("implement a binary search", "howto"),
    ("how do I install packages with pip", "howto"),
    # General queries (no pattern match)
    ("Python", "general"),
    ("decorators", "general"),
    ("tell me about pandas", "general"),
])
def test_classify_query_type(query, expected):
    assert classify_query_type(query) == expected


# ── rerank_by_source ─────────────────────────────────────────────────

from rag_pipeline import rerank_by_source, FINAL_K


def _make_doc(source, content="test content"):
    return Document(page_content=content, metadata={"source": source})


def test_rerank_returns_final_k_docs():
    docs_with_scores = [
        (_make_doc("StackOverflow"), 0.80),
        (_make_doc("RealPython"), 0.80),
        (_make_doc("Python Docs"), 0.80),
        (_make_doc("GeeksforGeeks"), 0.80),
        (_make_doc("PEPs"), 0.80),
        (_make_doc("Python StdLib"), 0.80),
    ]
    result = rerank_by_source(docs_with_scores, "general")
    assert len(result) == FINAL_K


def test_rerank_prefers_authoritative_sources_on_tie():
    """When relevance scores are equal, higher-authority sources should rank first."""
    docs_with_scores = [
        (_make_doc("StackOverflow"), 0.80),
        (_make_doc("Python Docs"), 0.80),
        (_make_doc("RealPython"), 0.80),
        (_make_doc("GeeksforGeeks"), 0.80),
    ]
    result = rerank_by_source(docs_with_scores, "general")
    sources = [doc.metadata["source"] for doc in result]
    assert sources[0] == "Python Docs"
    assert "StackOverflow" not in sources  # lowest priority, should be cut


def test_rerank_error_query_boosts_stackoverflow():
    """Error queries should boost StackOverflow when scores are close."""
    docs_with_scores = [
        (_make_doc("Python Docs"), 0.80),
        (_make_doc("StackOverflow"), 0.79),
        (_make_doc("RealPython"), 0.79),
        (_make_doc("GeeksforGeeks"), 0.78),
    ]
    result = rerank_by_source(docs_with_scores, "error")
    sources = [doc.metadata["source"] for doc in result]
    # StackOverflow gets +3 bonus for error queries, so it should be in top 3
    assert "StackOverflow" in sources


def test_rerank_concept_query_boosts_official_docs():
    docs_with_scores = [
        (_make_doc("StackOverflow"), 0.82),
        (_make_doc("Python Docs"), 0.80),
        (_make_doc("RealPython"), 0.80),
        (_make_doc("PEPs"), 0.79),
    ]
    result = rerank_by_source(docs_with_scores, "concept")
    sources = [doc.metadata["source"] for doc in result]
    # Python Docs gets +3 concept bonus, PEPs gets +2
    assert "Python Docs" in sources
    assert "PEPs" in sources


def test_rerank_relevance_overrides_priority():
    """A much more relevant low-priority doc should still rank above a less relevant high-priority doc."""
    docs_with_scores = [
        (_make_doc("StackOverflow"), 0.95),  # very relevant
        (_make_doc("Python Docs"), 0.60),     # not very relevant
        (_make_doc("RealPython"), 0.55),
        (_make_doc("GeeksforGeeks"), 0.50),
    ]
    result = rerank_by_source(docs_with_scores, "general")
    sources = [doc.metadata["source"] for doc in result]
    assert sources[0] == "StackOverflow"  # relevance wins


def test_rerank_handles_unknown_source():
    docs_with_scores = [
        (_make_doc("Unknown"), 0.80),
        (_make_doc("Python Docs"), 0.80),
        (_make_doc("RealPython"), 0.80),
    ]
    result = rerank_by_source(docs_with_scores, "general")
    assert len(result) == FINAL_K


# ── condense_question ────────────────────────────────────────────────

from rag_pipeline import condense_question


def test_condense_returns_original_when_no_history():
    result = condense_question("what is a decorator", None)
    assert result == "what is a decorator"

    result = condense_question("what is a decorator", [])
    assert result == "what is a decorator"


@patch("rag_pipeline.llm")
def test_condense_calls_llm_with_history(mock_llm):
    mock_response = MagicMock()
    mock_response.content = "What are Python decorators with arguments?"
    mock_llm.invoke.return_value = mock_response

    history = [
        {"role": "user", "content": "explain decorators"},
        {"role": "assistant", "content": "Decorators are functions that wrap other functions..."},
    ]
    result = condense_question("what about with arguments?", history)

    assert result == "What are Python decorators with arguments?"
    mock_llm.invoke.assert_called_once()


@patch("rag_pipeline.llm")
def test_condense_falls_back_on_llm_error(mock_llm):
    mock_llm.invoke.side_effect = Exception("API timeout")

    history = [{"role": "user", "content": "hello"}]
    result = condense_question("what about that?", history)

    assert result == "what about that?"  # falls back to original


# ── ask_question ─────────────────────────────────────────────────────

from rag_pipeline import ask_question, FALLBACK_ANSWER


@patch("rag_pipeline.vector_db")
@patch("rag_pipeline.llm")
def test_ask_question_chat_route(mock_llm, mock_vector_db):
    """Chat messages should not hit vector store."""
    router_resp = MagicMock()
    router_resp.content = "chat"
    chat_resp = MagicMock()
    chat_resp.content = "Hey! I'm SyntaxAI, happy to help with Python."
    mock_llm.invoke.side_effect = [router_resp, chat_resp]

    result = ask_question("hello there")

    assert "SyntaxAI" in result["answer"] or "happy" in result["answer"].lower() or len(result["answer"]) > 0
    assert result["sources"] == []
    mock_vector_db.similarity_search_with_relevance_scores.assert_not_called()


@patch("rag_pipeline.vector_db")
@patch("rag_pipeline.llm")
def test_ask_question_rag_route(mock_llm, mock_vector_db):
    """Question messages should go through full RAG pipeline."""
    router_resp = MagicMock()
    router_resp.content = "question"
    answer_resp = MagicMock()
    answer_resp.content = "A decorator wraps a function."
    mock_llm.invoke.side_effect = [router_resp, answer_resp]

    doc = _make_doc("Python Docs", "Decorators are a way to modify functions.")
    mock_vector_db.similarity_search_with_relevance_scores.return_value = [
        (doc, 0.85),
    ]

    result = ask_question("what is a decorator")

    assert "decorator" in result["answer"].lower()
    assert len(result["sources"]) == 1
    mock_vector_db.similarity_search_with_relevance_scores.assert_called_once()


@patch("rag_pipeline.vector_db")
@patch("rag_pipeline.llm")
def test_ask_question_empty_retrieval(mock_llm, mock_vector_db):
    router_resp = MagicMock()
    router_resp.content = "question"
    mock_llm.invoke.return_value = router_resp

    mock_vector_db.similarity_search_with_relevance_scores.return_value = []

    result = ask_question("some obscure question")

    assert "couldn't find" in result["answer"].lower()


@patch("rag_pipeline.vector_db")
@patch("rag_pipeline.llm")
def test_ask_question_unexpected_route_defaults_to_rag(mock_llm, mock_vector_db):
    """If router returns garbage, default to RAG pipeline."""
    router_resp = MagicMock()
    router_resp.content = "maybe"
    answer_resp = MagicMock()
    answer_resp.content = "Here is the answer."
    mock_llm.invoke.side_effect = [router_resp, answer_resp]

    doc = _make_doc("RealPython", "Some content")
    mock_vector_db.similarity_search_with_relevance_scores.return_value = [(doc, 0.80)]

    result = ask_question("tell me about asyncio")
    assert result["answer"] == "Here is the answer."


@patch("rag_pipeline.llm")
def test_ask_question_total_failure_returns_fallback(mock_llm):
    mock_llm.invoke.side_effect = Exception("OpenAI is down")

    result = ask_question("anything")

    assert result["answer"] == FALLBACK_ANSWER
    assert result["sources"] == []


@patch("rag_pipeline.vector_db")
@patch("rag_pipeline.llm")
def test_ask_question_pinecone_failure(mock_llm, mock_vector_db):
    router_resp = MagicMock()
    router_resp.content = "question"
    mock_llm.invoke.return_value = router_resp

    mock_vector_db.similarity_search_with_relevance_scores.side_effect = Exception("Pinecone timeout")

    result = ask_question("what is a list")

    assert "trouble searching" in result["answer"].lower()
    assert result["sources"] == []
