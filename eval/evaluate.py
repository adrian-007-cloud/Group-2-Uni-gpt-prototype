# This file measures the chatbot on a test set that you write.
# It does not change the app. Run it from the project folder:
#   python evaluate.py
#
# The test set is test_questions.json, a list of questions like this:
#   {"course": "COS331", "question": "What is a PCB?", "should_answer": true, "expected_pages": [5]}
# "should_answer": false means the notes do NOT cover the question (for example, "what is the weather?").
# "expected_pages" is the list of pages the answer should come from. Check these against the PDF.
#
# The results are written to evaluation_results.csv. The last column, correct_by_hand,
# is empty: read each answer and type yes or no there yourself.

import csv
import json
import os
import time

os.environ["HF_HUB_OFFLINE"] = "1"

from core.rag_pipeline import load_search, prepare_question, find_notes
from core.llm_client import ask_model

TEST_FILE = "test_questions.json"
RESULTS_FILE = "evaluation_results.csv"


def main():
    if not os.path.exists(TEST_FILE):
        print("Missing", TEST_FILE)
        return
    with open(TEST_FILE, encoding="utf-8") as f:
        tests = json.load(f)
    if not tests:
        print(TEST_FILE, "is empty. Add your questions first.")
        return

    model, collection = load_search()
    rows = []

    for item in tests:
        question = item["question"]
        course = item["course"]
        expected = item.get("expected_pages", [])
        should_answer = item.get("should_answer", True)

        # Which pages the search finds, before the relevance cutoff
        retrieved = find_notes(model, collection, question, course)
        retrieved_pages = sorted({n["page"] for n in retrieved})

        # The full chatbot: cutoff, prompt, and the model's answer, timed
        start = time.time()
        messages, notes = prepare_question(model, collection, question, course)
        refused = messages is None
        answer = "" if refused else ask_model(messages)
        seconds = round(time.time() - start, 2)

        refusal_correct = refused != should_answer
        page_hit = any(p in retrieved_pages for p in expected) if expected else ""

        rows.append({
            "course": course,
            "question": question,
            "should_answer": should_answer,
            "refused": refused,
            "refusal_correct": refusal_correct,
            "expected_pages": " ".join(str(p) for p in expected),
            "retrieved_pages": " ".join(str(p) for p in retrieved_pages),
            "page_hit": page_hit,
            "seconds": seconds,
            "answer": answer.replace("\n", " "),
            "correct_by_hand": "",
        })
        print("done:", question[:60])

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    refusal_rows = [r for r in rows]
    page_rows = [r for r in rows if r["page_hit"] != ""]
    answered = [r for r in rows if not r["refused"]]

    print()
    print("Questions:", len(rows))
    print("Refusal correct:", sum(r["refusal_correct"] for r in refusal_rows), "of", len(refusal_rows))
    if page_rows:
        print("Expected page found in top results:", sum(r["page_hit"] for r in page_rows), "of", len(page_rows))
    if answered:
        print("Average answer time (answered only):", round(sum(r["seconds"] for r in answered) / len(answered), 2), "seconds")
    print("Results saved to", RESULTS_FILE)
    print("Now read the answers and fill in correct_by_hand.")


if __name__ == "__main__":
    main()