# This file runs the RAG steps: find the notes, build the prompt, get the answer.
import json
import os
import chromadb
from sentence_transformers import SentenceTransformer
from core.llm_client import ask_model

DB_FOLDER = "chroma_db"
COLLECTION_NAME = "notes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
NUMBER_OF_RESULTS = 3
RELEVANCE_CUTOFF = 1.35   # if even the closest note is farther than this, the notes don't cover the question
FALLBACK = "I cannot find this in the course notes."

# The rules we give the model every time
INSTRUCTIONS = """You are a study assistant. You answer a student's question using only the course notes provided.

How to answer:
1. Find the parts of the notes that relate to the question.
2. If they answer the question, explain it clearly in your own words. Use 3 to 6 sentences unless the question asks for more.
3. If the notes include examples, steps, or definitions for the topic, include them. Use only what the notes say.
4. If the question uses a different name for an idea in the notes, answer using the notes' own name for it, and say that the two names mean the same thing.
5. If the notes cover part of the question, answer that part and say which part the notes do not cover.
6. If the notes do not cover the question at all, reply with only this sentence: I cannot find this in the course notes.

Rules:
- Never add facts from outside the notes.
- Never write page numbers. The app shows them separately.
- Do not repeat the question or the notes in your answer.
- Never answer and then add the fallback sentence. Use one or the other."""


# Step 1: read data/<course>/topics.json and return the pages for one topic
def load_topic_pages(course, topic_name):
    path = os.path.join("data", course, "topics.json")
    if not os.path.exists(path):
        return []                                  # no topics file yet
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for topic in data["topics"]:                   # look through every topic
        if topic["name"] == topic_name:
            return topic["pages"]                  # the list of page numbers
    return []                                      # topic name not found


# Step 2: load the embedding model and open the notes database
def load_search():
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = chromadb.PersistentClient(path=DB_FOLDER).get_collection(COLLECTION_NAME)
    return model, collection


# List the course codes that are stored in the database
def list_courses(collection):
    stored = collection.get(include=["metadatas"])["metadatas"]
    return sorted(set(m["course"] for m in stored))


# Step 3: find the most relevant note chunks for the question
# If pages is given, only search chunks from those pages
def find_notes(model, collection, question, course, pages=None):
    question_numbers = model.encode([question], normalize_embeddings=True).tolist()

    # Build the filter: always the course, and also the pages when a topic is chosen
    if pages:
        where = {"$and": [{"course": course}, {"page": {"$in": pages}}]}
    else:
        where = {"course": course}

    results = collection.query(
        query_embeddings=question_numbers,
        n_results=NUMBER_OF_RESULTS,
        where=where,
    )
    found = []
    for text, info, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        found.append({"text": text, "page": info["page"], "distance": distance})
    return found


# Put the notes and the question into one message
def build_prompt(question, notes):
    notes_text = ""
    for note in notes:
        notes_text = notes_text + "[Page " + str(note["page"]) + "]\n" + note["text"] + "\n\n"
    return "Course notes:\n" + notes_text + "Student question: " + question


# Step 4: get the messages for the model, or None if the notes don't cover the question
def prepare_question(model, collection, question, course, pages=None):
    question = question.strip()
    notes = find_notes(model, collection, question, course, pages)

    # Notes come back closest first. If even the closest is too far, the notes don't cover this question.
    if not notes or notes[0]["distance"] > RELEVANCE_CUTOFF:
        return None, []

    prompt = build_prompt(question, notes)
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    return messages, notes


# The whole process: find notes, build the prompt, ask the model
def answer_question(model, collection, question, course, pages=None):
    messages, notes = prepare_question(model, collection, question, course, pages)
    if messages is None:
        return FALLBACK, notes
    answer = ask_model(messages)
    return answer, notes


# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    model, collection = load_search()
    answer, notes = answer_question(model, collection, "what are the types of agents", "COS331")
    print(answer)
    page_numbers = []
    for note in notes:
        if note["page"] not in page_numbers:
            page_numbers.append(note["page"])
    print("Sources: pages", ", ".join(str(p) for p in page_numbers))