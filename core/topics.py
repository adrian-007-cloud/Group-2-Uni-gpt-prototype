# core/topics.py
# Builds a topic list for a course automatically: key phrases, then groups, then topic names.
# Run from the UNI-GPT folder:
#   python -m core.topics COS335
import json
import os
import sys
from collections import Counter

os.environ["HF_HUB_OFFLINE"] = "1"   # use only the saved model, no internet

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from core.cleaner import clean_course

EMBED_MODEL = "all-MiniLM-L6-v2"
DATA_FOLDER = "data"
MIN_WORDS = 2          # a phrase needs at least 2 words
MIN_PAGES = 2          # a topic must appear on at least 2 pages
GENERAL_SHARE = 0.5    # a phrase on more than half of all pages is too general
SIMILAR_ENOUGH = 0.75  # phrases this close in meaning are grouped into one topic


# Step 1: get key phrases from each page, and record which pages each phrase came from
def extract_phrases(kw_model, pages):
    phrase_pages = {}
    for item in pages:
        if len(item["text"].split()) < 30:
            continue                                   # too little text on this page
        keywords = kw_model.extract_keywords(
            item["text"], keyphrase_ngram_range=(1, 3), stop_words="english", top_n=5
        )
        for phrase, score in keywords:
            phrase = phrase.strip().lower()
            if len(phrase.split()) < MIN_WORDS:
                continue                               # drop single words
            if any(ch.isdigit() for ch in phrase):
                continue                               # drop phrases with numbers
            phrase_pages.setdefault(phrase, set()).add(item["page"])
    return phrase_pages


# Step 2: drop phrases that appear on too many pages (general words, not topics)
def drop_general_phrases(phrase_pages, total_pages):
    limit = GENERAL_SHARE * total_pages
    return {p: pages for p, pages in phrase_pages.items() if len(pages) <= limit}


# Step 3: group phrases whose meanings are close together
def group_phrases(embed_model, phrases):
    vectors = embed_model.encode(phrases, normalize_embeddings=True)
    groups = []                                        # each group is a list of phrase indexes
    for i in range(len(phrases)):
        placed = False
        for group in groups:
            # compare with the first phrase in the group
            if float(vectors[i] @ vectors[group[0]]) >= SIMILAR_ENOUGH:
                group.append(i)
                placed = True
                break
        if not placed:
            groups.append([i])
    return groups


# Step 4: turn each group into a topic, named after its most common phrase
def build_topics(embed_model, phrase_pages):
    phrases = list(phrase_pages.keys())
    if not phrases:
        return []
    topics = []
    for group in group_phrases(embed_model, phrases):
        names = [phrases[i] for i in group]
        name = max(names, key=lambda p: len(phrase_pages[p]))
        pages = sorted(set().union(*[phrase_pages[p] for p in names]))
        if len(pages) < MIN_PAGES:
            continue                                   # too few pages to count as a topic
        topics.append({
            "name": name.title(),
            "pages": pages,
            "phrases": sorted(names),
            "checked": False,                          # the course owner sets this to true after checking
        })
    topics.sort(key=lambda t: t["pages"][0])
    return topics


def build_topic_file(course):
    # Step 5: clean the pages, then build the topics
    pages = clean_course(course)
    if not pages:
        return

    print("Loading the models...")
    embed_model = SentenceTransformer(EMBED_MODEL)
    kw_model = KeyBERT(model=embed_model)

    phrase_pages = extract_phrases(kw_model, pages)
    phrase_pages = drop_general_phrases(phrase_pages, len(pages))
    topics = build_topics(embed_model, phrase_pages)

    # Step 6: save the topic file and print it for checking
    out_path = os.path.join(DATA_FOLDER, course, "topics.json")
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump({"course": course, "topics": topics}, out, indent=2)

    print("Topics found:", len(topics))
    for topic in topics:
        print("  -", topic["name"], "| pages", topic["pages"])
    print("Saved to", out_path)


if __name__ == "__main__":
    build_topic_file(sys.argv[1])