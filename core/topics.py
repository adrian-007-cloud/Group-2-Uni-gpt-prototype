# core/topics.py
# Builds a topic list for a prebuilt course from an outline file.
# The outline file is data/<course>/outline.txt — one topic name per line.
# Run from the UNI-GPT folder:
#   python -m core.topics COS331

import json
import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"   # use only the saved model, no internet

from sentence_transformers import SentenceTransformer
from core.cleaner import clean_course

EMBED_MODEL  = "all-MiniLM-L6-v2"
DATA_FOLDER  = "data"
TOP_PAGES      = 4      # keep at most this many pages per topic
MIN_SIMILARITY = 0.25   # a page must score at least this to count


def load_outline(course):
    """
    Read data/<course>/outline.txt and return a list of topic names.
    Each non-empty line in the file is one topic name.
    """
    outline_path = os.path.join(DATA_FOLDER, course, "outline.txt")

    # If the outline file does not exist, tell the user what to do
    if not os.path.exists(outline_path):
        print(f"No outline file found at {outline_path}")
        print("Create that file with one topic name per line, then run this script again.")
        return []

    topics = []
    with open(outline_path, encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:                          # skip blank lines
                topics.append(name)

    print(f"Loaded {len(topics)} topics from outline.")
    return topics


def find_pages_for_topic(embed_model, pages, topic_name):
    # Step A: turn the topic name into a list of numbers
    topic_vector = embed_model.encode([topic_name], normalize_embeddings=True)[0]

    # Step B: score every page for similarity to the topic
    scored = []                                  # will hold (score, page number) pairs
    for item in pages:
        if len(item["text"].split()) < 30:       # skip pages with almost no text
            continue
        page_vector = embed_model.encode([item["text"]], normalize_embeddings=True)[0]
        similarity = float(topic_vector @ page_vector)   # higher = more similar
        scored.append((similarity, item["page"]))

    # Step C: sort from most similar to least similar
    scored.sort(reverse=True)

    # Step D: keep only the best few pages that are similar enough
    best = [page for score, page in scored[:TOP_PAGES] if score >= MIN_SIMILARITY]
    return sorted(best)


def build_topic_file(course):
    """
    Main function: load the outline, clean the pages, find pages per topic,
    and write data/<course>/topics.json.
    """
    # Step 1: load the topic names from the outline file
    topic_names = load_outline(course)
    if not topic_names:
        return

    # Step 2: clean the course pages (same cleaning step as before)
    print("Cleaning the course pages...")
    pages = clean_course(course)
    if not pages:
        print("No pages found. Check that the PDFs are in data/<course>/.")
        return

    # Step 3: load the embedding model
    print("Loading the embedding model...")
    embed_model = SentenceTransformer(EMBED_MODEL)

    # Step 4: for each topic in the outline, find the matching pages
    print("Matching topics to pages...")
    topics = []
    for name in topic_names:
        matched = find_pages_for_topic(embed_model, pages, name)
        topics.append({
            "name"   : name,
            "pages"  : matched,
            "checked": False,   # set this to true after you review it
        })
        status = f"pages {matched}" if matched else "no pages found"
        print(f"  - {name}: {status}")

    # Step 5: save the topics file
    out_path = os.path.join(DATA_FOLDER, course, "topics.json")
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump({"course": course, "topics": topics}, out, indent=2)

    print(f"\nSaved {len(topics)} topics to {out_path}")
    print("Open topics.json and check the page numbers look right.")
    print("Set 'checked': true for each topic once you are happy with it.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m core.topics <COURSE>")
        print("Example: python -m core.topics COS331")
        sys.exit(1)

    build_topic_file(sys.argv[1])