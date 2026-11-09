# Measures the search step (retrieval) and the relevance cutoff on a test set you write.
# It does not change the app. Run it from the project folder:
#   python evaluate.py
#
# test_questions.json is a list like this:
#   {"course": "COS331", "question": "What is a PCB?", "should_answer": true, "expected_pages": [5]}
# should_answer false means the notes do NOT cover the question (for example, "what is the weather?").
# expected_pages are the pages that really answer it. Check them against the PDF.
#
# Outputs:
#   evaluation_results.csv  one row per question
#   evaluation_summary.txt  the numbers for the k sweep and the cutoff sweep

import csv
import json
import math
import os
import time

os.environ["HF_HUB_OFFLINE"] = "1"

import sys
PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_FOLDER)   # lets Python find the core folder
os.chdir(PROJECT_FOLDER)             # so data\ and chroma_db are found

import core.rag_pipeline as rag
from core.llm_client import ask_model

# Run "python eval\\evaluate.py" for COS331, or "python eval\\evaluate.py eval_COS335.json" for COS335.
TEST_FILE = os.path.join("eval", sys.argv[1]) if len(sys.argv) > 1 else os.path.join("eval", "test_questions.json")
RESULTS_FILE = "evaluation_results.csv"
SUMMARY_FILE = "evaluation_summary.txt"

DEPTH = 10                          # look at the top 10 chunks to rank them
KS = [1, 3, 5, 8, 10]               # k values to compare
CUTOFFS = [1.0, 1.1, 1.2, 1.3, 1.35, 1.4, 1.5, 1.6]   # cutoff values to compare


# ---------- Ranking measures ----------
# Each chunk is relevant if its page is one of the expected pages.

def is_relevant(page, expected):
    return page in expected


def precision_at_k(pages, expected, k):
    # Of the top k chunks, what share are relevant?
    top = pages[:k]
    return sum(1 for p in top if is_relevant(p, expected)) / k


def hit_at_k(pages, expected, k):
    # Is at least one relevant chunk in the top k? (1 = yes, 0 = no)
    return 1 if any(is_relevant(p, expected) for p in pages[:k]) else 0


def first_relevant_rank(pages, expected):
    # Position of the first relevant chunk, counting from 1. None if there is none.
    for rank, p in enumerate(pages, start=1):
        if is_relevant(p, expected):
            return rank
    return None


def reciprocal_rank(pages, expected):
    # 1 divided by the first relevant rank. This is what MRR averages.
    rank = first_relevant_rank(pages, expected)
    return 1 / rank if rank else 0.0


def ndcg_at_k(pages, expected, k):
    # Rewards relevant chunks that appear higher. 1.0 means the best possible order.
    gains = [1 if is_relevant(p, expected) else 0 for p in pages[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    # The best possible order puts all relevant chunks (within the depth) first
    all_gains = sorted([1 if is_relevant(p, expected) else 0 for p in pages], reverse=True)
    ideal = sum(g / math.log2(i + 2) for i, g in enumerate(all_gains[:k]))
    return dcg / ideal if ideal > 0 else 0.0


def average(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


# ---------- Main run ----------

def main():
    if not os.path.exists(TEST_FILE):
        print("Missing", TEST_FILE)
        return
    with open(TEST_FILE, encoding="utf-8") as f:
        tests = json.load(f)
    if not tests:
        print(TEST_FILE, "is empty. Add your questions first.")
        return

    model, collection = rag.load_search()
    normal_k = rag.NUMBER_OF_RESULTS          # the k the app really uses (5)
    rows = []

    for item in tests:
        question = item["question"]
        course = item["course"]
        expected = item.get("expected_pages", [])
        should_answer = item.get("should_answer", True)

        # Step A: look at the top 10 chunks, to rank them
        rag.NUMBER_OF_RESULTS = DEPTH
        found = rag.find_notes(model, collection, question, course)
        pages = [n["page"] for n in found]
        top1_distance = round(found[0]["distance"], 3) if found else None

        # Step B: the real app setting, then the real refusal decision and answer
        rag.NUMBER_OF_RESULTS = normal_k
        start = time.time()
        messages, notes = rag.prepare_question(model, collection, question, course)
        refused = messages is None
        answer = "" if refused else ask_model(messages)
        seconds = round(time.time() - start, 2)

        row = {
            "course": course,
            "question": question,
            "should_answer": should_answer,
            "expected_pages": " ".join(str(p) for p in expected),
            "top10_pages": " ".join(str(p) for p in pages),
            "top1_distance": top1_distance,
            "refused": refused,
            "refusal_correct": refused != should_answer,
            "first_relevant_rank": first_relevant_rank(pages, expected) if expected else "",
            "hit_at_3": hit_at_k(pages, expected, 3) if expected else "",
            "hit_at_5": hit_at_k(pages, expected, 5) if expected else "",
            "precision_at_5": round(precision_at_k(pages, expected, 5), 3) if expected else "",
            "reciprocal_rank": round(reciprocal_rank(pages, expected), 3) if expected else "",
            "ndcg_at_5": round(ndcg_at_k(pages, expected, 5), 3) if expected else "",
            "seconds": seconds,
            "answer": answer.replace("\n", " "),
            "correct_by_hand": "",
        }
        rows.append(row)
        print("done:", question[:60])

    rag.NUMBER_OF_RESULTS = normal_k

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # ----- Summary -----
    course_rows = [r for r in rows if r["should_answer"] and r["expected_pages"]]
    unrelated = [r for r in rows if not r["should_answer"]]
    lines = []
    lines.append("Questions: %d (course: %d, unrelated: %d)" % (len(rows), len([r for r in rows if r["should_answer"]]), len(unrelated)))
    lines.append("")
    lines.append("Ranking, over the course questions with expected pages:")
    lines.append("  MRR (mean reciprocal rank): %.3f" % average([r["reciprocal_rank"] for r in course_rows]))
    lines.append("  nDCG@5: %.3f" % average([r["ndcg_at_5"] for r in course_rows]))
    lines.append("")
    lines.append("k sweep (does the right page appear in the top k?):")
    for k in KS:
        hits = []
        precs = []
        for r in course_rows:
            pages = [int(p) for p in r["top10_pages"].split()]
            expected = [int(p) for p in r["expected_pages"].split()]
            hits.append(hit_at_k(pages, expected, k))
            precs.append(precision_at_k(pages, expected, k))
        lines.append("  k=%-2d  recall (hit rate): %.2f   precision: %.2f" % (k, average(hits), average(precs)))
    lines.append("")
    lines.append("Cutoff sweep (answer when the closest chunk distance is at most the cutoff):")
    lines.append("  cutoff  answered course  answered unrelated  recall of answering  precision of answering")
    course_all = [r for r in rows if r["should_answer"]]
    for c in CUTOFFS:
        ans_course = sum(1 for r in course_all if r["top1_distance"] is not None and r["top1_distance"] <= c)
        ans_unrel = sum(1 for r in unrelated if r["top1_distance"] is not None and r["top1_distance"] <= c)
        recall_ans = ans_course / len(course_all) if course_all else 0
        prec_ans = ans_course / (ans_course + ans_unrel) if (ans_course + ans_unrel) else 0
        lines.append("  %-6s  %-15d  %-18d  %-19.2f  %.2f" % (c, ans_course, ans_unrel, recall_ans, prec_ans))
    lines.append("")
    lines.append("Answers (answered questions only):")
    answered = [r for r in rows if not r["refused"]]
    lines.append("  average answer time: %.2f seconds" % average([r["seconds"] for r in answered]))
    lines.append("  refusal correct: %d of %d" % (sum(1 for r in rows if r["refusal_correct"]), len(rows)))
    lines.append("")
    lines.append("Next: read each answer in the CSV and mark correct_by_hand (yes or no).")

    text = "\n".join(lines)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print()
    print(text)
    print()
    print("Saved:", RESULTS_FILE, "and", SUMMARY_FILE)


if __name__ == "__main__":
    main()