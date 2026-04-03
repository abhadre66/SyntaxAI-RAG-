"""
Evaluation harness for SyntaxAI RAG pipeline.

Measures:
  1. Keyword hit rate  — does the answer contain expected keywords?
  2. Source precision   — did retrieval return docs from preferred sources?
  3. Query routing      — did classify_query_type get the right intent?
  4. Empty results      — how often does retrieval return nothing?

Usage:
    python eval/run_eval.py                # run full eval
    python eval/run_eval.py --dry-run      # check routing only (no API calls)
"""

import json
import os
import sys
import time
import argparse

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline import ask_question, classify_query_type


def load_questions(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "eval_questions.json")
    with open(path) as f:
        return json.load(f)


def evaluate_routing(questions):
    """Check if classify_query_type matches expected query types."""
    correct = 0
    total = len(questions)

    print("\n=== Query Routing Evaluation ===\n")
    for q in questions:
        predicted = classify_query_type(q["question"])
        expected = q["query_type"]
        match = predicted == expected
        if match:
            correct += 1
        else:
            print(f"  MISS  id={q['id']}: expected={expected}, got={predicted}")
            print(f"        \"{q['question']}\"")

    accuracy = correct / total * 100
    print(f"\nRouting accuracy: {correct}/{total} ({accuracy:.1f}%)")
    return accuracy


def evaluate_full(questions):
    """Run questions through full pipeline and measure quality."""
    results = {
        "total": len(questions),
        "keyword_hits": 0,
        "keyword_total": 0,
        "source_hits": 0,
        "source_total": 0,
        "empty_retrievals": 0,
        "errors": 0,
        "total_time": 0.0,
    }

    details = []

    print("\n=== Full Pipeline Evaluation ===\n")

    for i, q in enumerate(questions):
        qid = q["id"]
        question = q["question"]
        expected_keywords = q["expected_keywords"]
        preferred_sources = q["preferred_sources"]

        print(f"  [{i+1}/{len(questions)}] Q{qid}: {question[:60]}...", end=" ", flush=True)

        start = time.time()
        try:
            result = ask_question(question)
        except Exception as e:
            print(f"ERROR: {e}")
            results["errors"] += 1
            continue
        elapsed = time.time() - start
        results["total_time"] += elapsed

        answer = result["answer"].lower()
        sources = [doc.metadata.get("source", "") for doc in result.get("sources", [])]

        # Keyword hit rate
        keywords_found = sum(1 for kw in expected_keywords if kw.lower() in answer)
        keyword_score = keywords_found / len(expected_keywords) if expected_keywords else 0
        results["keyword_hits"] += keywords_found
        results["keyword_total"] += len(expected_keywords)

        # Source precision
        source_match = any(s in preferred_sources for s in sources)
        if source_match:
            results["source_hits"] += 1
        results["source_total"] += 1

        # Empty retrieval
        if not sources:
            results["empty_retrievals"] += 1

        status = "OK" if keyword_score >= 0.5 and source_match else "WEAK"
        print(f"{status} ({elapsed:.1f}s, kw={keyword_score:.0%}, src={'HIT' if source_match else 'MISS'})")

        details.append({
            "id": qid,
            "question": question,
            "keyword_score": keyword_score,
            "source_match": source_match,
            "sources_returned": sources,
            "time": round(elapsed, 2),
        })

    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    kw_rate = results["keyword_hits"] / results["keyword_total"] * 100 if results["keyword_total"] else 0
    src_rate = results["source_hits"] / results["source_total"] * 100 if results["source_total"] else 0
    avg_time = results["total_time"] / results["total"] if results["total"] else 0

    print(f"  Questions evaluated : {results['total']}")
    print(f"  Keyword hit rate    : {results['keyword_hits']}/{results['keyword_total']} ({kw_rate:.1f}%)")
    print(f"  Source precision    : {results['source_hits']}/{results['source_total']} ({src_rate:.1f}%)")
    print(f"  Empty retrievals   : {results['empty_retrievals']}")
    print(f"  Errors             : {results['errors']}")
    print(f"  Avg response time  : {avg_time:.2f}s")
    print(f"  Total time         : {results['total_time']:.1f}s")
    print("=" * 60)

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(output_path, "w") as f:
        json.dump({"summary": results, "details": details}, f, indent=2)
    print(f"\nDetailed results saved to {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="SyntaxAI RAG Evaluation Harness")
    parser.add_argument("--dry-run", action="store_true", help="Only test query routing (no API calls)")
    parser.add_argument("--questions", type=str, help="Path to custom questions JSON file")
    parser.add_argument("--limit", type=int, help="Only evaluate first N questions")
    args = parser.parse_args()

    questions = load_questions(args.questions)
    if args.limit:
        questions = questions[:args.limit]

    print(f"Loaded {len(questions)} evaluation questions")

    routing_accuracy = evaluate_routing(questions)

    if not args.dry_run:
        results = evaluate_full(questions)
    else:
        print("\n(Dry run — skipping full pipeline evaluation)")


if __name__ == "__main__":
    main()
