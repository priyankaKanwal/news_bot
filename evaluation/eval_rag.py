"""Measure how well the RAG pipeline answers, instead of guessing.

Stage A - retrieval (fast, no LLM). For many gate / ordering / top-N
settings, how often does the context sent to the LLM contain an
article that answers the question, and how often does an
unanswerable question still reach the LLM?

    python -m evaluation.eval_rag

Stage B - end to end (slow, calls the LLM) with the CURRENT settings.
Settings can be overridden per run with environment variables:

    SCORE_THRESHOLD=0.70 RERANK_TOP_N=5 python -m evaluation.eval_rag --e2e

Questions live in evaluation/questions.json (a snapshot of the news).
"""

import argparse
import contextlib
import io
import json
import time
from pathlib import Path

from sentence_transformers import CrossEncoder

from rag.config import (
    RERANKER_MODEL,
    RERANK_TOP_N,
    RETRIEVE_TOP_K,
    SCORE_THRESHOLD,
)
from rag.vector_store import build_recency_filter, create_vector_store

QUESTIONS = Path(__file__).parent / "questions.json"

GATES = [0.0, 0.70, 0.75, 0.78, 0.80, 0.82]
TOP_NS = [3, 5, 8]
POOL = 15  # chunks fetched from Qdrant for the grid analysis


def load_questions():
    return json.loads(QUESTIONS.read_text(encoding="utf-8"))


def stored_titles(client):
    titles, offset = [], None

    while True:
        points, offset = client.scroll(
            "news_articles", limit=256, offset=offset, with_payload=True
        )
        titles += [p.payload["metadata"]["title"].lower() for p in points]
        if offset is None:
            return titles


def matches(title, expect):
    title = title.lower()
    return any(e in title for e in expect)


def stage_a(store, client, data):
    titles = stored_titles(client)

    answerable, skipped = [], []
    for item in data["answerable"]:
        if any(matches(t, item["expect"]) for t in titles):
            answerable.append(item)
        else:
            skipped.append(item["q"])

    print(f"Answerable questions : {len(answerable)} "
          f"({len(skipped)} skipped - expected article not stored)")
    print(f"Unanswerable questions: {len(data['unanswerable'])}")

    reranker = CrossEncoder(RERANKER_MODEL)

    def candidates(q):
        results = store.similarity_search_with_relevance_scores(
            q, k=POOL, filter=build_recency_filter()
        )
        ce = reranker.predict([(q, d.page_content) for d, _ in results])
        return [
            {"vec": v, "ce": float(c), "title": d.metadata["title"]}
            for (d, v), c in zip(results, ce)
        ]

    ans = [(item, candidates(item["q"])) for item in answerable]
    una = [(q, candidates(q)) for q in data["unanswerable"]]

    best_ans = sorted(max(c["vec"] for c in cs) for _, cs in ans)
    best_una = sorted(max(c["vec"] for c in cs) for _, cs in una)
    print(f"\nBest vector score - answerable   : min {best_ans[0]:.3f}  "
          f"median {best_ans[len(best_ans) // 2]:.3f}  max {best_ans[-1]:.3f}")
    print(f"Best vector score - unanswerable : min {best_una[0]:.3f}  "
          f"median {best_una[len(best_una) // 2]:.3f}  max {best_una[-1]:.3f}")

    def context(cs, gate, order, n):
        kept = [c for c in cs if c["vec"] >= gate]
        key = "ce" if order == "cross-encoder" else "vec"
        return sorted(kept, key=lambda c: -c[key])[:n]

    print("\nhit  = answerable questions whose context contains an answering article")
    print("leak = unanswerable questions that still reach the LLM (it must refuse)\n")
    print(f"{'gate':>5} {'order':>13} {'top-N':>5} {'hit':>7} {'leak':>7}")

    for gate in GATES:
        for order in ("vector", "cross-encoder"):
            for n in TOP_NS:
                hits = sum(
                    1 for item, cs in ans
                    if any(matches(c["title"], item["expect"])
                           for c in context(cs, gate, order, n))
                )
                leaks = sum(1 for _, cs in una if context(cs, gate, order, n))
                print(f"{gate:>5.2f} {order:>13} {n:>5} "
                      f"{hits / len(ans):>6.0%} {leaks / len(una):>7.0%}")
        print()

    # Which questions does the CURRENT setting miss?
    print(f"Misses with current settings (gate {SCORE_THRESHOLD}, "
          f"cross-encoder, top {RERANK_TOP_N}):")
    for item, cs in ans:
        ctx = context(cs, SCORE_THRESHOLD, "cross-encoder", RERANK_TOP_N)
        if not any(matches(c["title"], item["expect"]) for c in ctx):
            best = max(c["vec"] for c in cs)
            print(f"  - {item['q']}  (best vec {best:.3f}, "
                  f"{'gated out' if not ctx else 'wrong chunks'})")


def stage_b(store, data):
    from rag.answer_generator import NOT_ENOUGH_INFO, generate_answer

    print(f"Current settings: gate={SCORE_THRESHOLD} top_k={RETRIEVE_TOP_K} "
          f"top_n={RERANK_TOP_N}\n")

    def ask(q):
        buf = io.StringIO()
        start = time.time()
        with contextlib.redirect_stdout(buf):
            answer, results = generate_answer(q, vector_store=store)
        return answer, results, time.time() - start

    answered = correct = 0
    for item in data["answerable"]:
        answer, _, secs = ask(item["q"])
        ok_answered = answer.strip().rstrip(".") != NOT_ENOUGH_INFO.rstrip(".")
        ok_correct = ok_answered and any(
            k in answer.lower() for k in item["keywords"]
        )
        answered += ok_answered
        correct += ok_correct
        flag = "OK " if ok_correct else ("?? " if ok_answered else "-- ")
        print(f"{flag}[{secs:4.1f}s] {item['q']}")

    refused = 0
    for q in data["unanswerable"]:
        answer, _, secs = ask(q)
        ok = answer.strip().rstrip(".") == NOT_ENOUGH_INFO.rstrip(".")
        refused += ok
        print(f"{'OK ' if ok else 'BAD'}[{secs:4.1f}s] (should refuse) {q}")
        if not ok:
            print(f"      -> {answer[:150]!r}")

    n_a, n_u = len(data["answerable"]), len(data["unanswerable"])
    print("\n" + "=" * 60)
    print(f"Answerable : answered {answered}/{n_a}, "
          f"answer contains expected keyword {correct}/{n_a}")
    print(f"Unanswerable: correctly refused {refused}/{n_u}")
    print("(OK = answered with a keyword, ?? = answered without it, "
          "-- = refused)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--e2e", action="store_true",
                        help="run stage B (calls the LLM; slow)")
    args = parser.parse_args()

    data = load_questions()
    store, client = create_vector_store()

    try:
        if args.e2e:
            stage_b(store, data)
        else:
            stage_a(store, client, data)
    finally:
        client.close()


if __name__ == "__main__":
    main()
