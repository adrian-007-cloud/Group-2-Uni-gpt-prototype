import re
# This file runs the RAG steps: find the notes, build the prompt, get the answer.
import os
import chromadb
from sentence_transformers import SentenceTransformer

# The project folder is one level above core/, where this file lives
PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FOLDER = os.path.join(PROJECT_FOLDER, "chroma_db")
COLLECTION_NAME = "notes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
NUMBER_OF_RESULTS = 5     # how many note chunks the model sees for each question
RELEVANCE_CUTOFF = 1.2   # if even the closest note is farther than this, the notes don't cover the question
PER_PART = 3            # how many notes to keep for each part of a multi-part question
HISTORY_EXCHANGES = 2     # how many earlier messages to send back to the model (2 = the last exchange)
HISTORY_CHARS = 600       # earlier answers are cut to this many characters to keep the prompt short

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


# Step 1: load the embedding model and open the notes database
def load_search():
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = chromadb.PersistentClient(path=DB_FOLDER).get_collection(COLLECTION_NAME)
    return model, collection


# List the course codes that are stored in the database
def list_courses(collection):
    stored = collection.get(include=["metadatas"])["metadatas"]
    return sorted(set(m["course"] for m in stored))


# Step 2: find the most relevant note chunks for the question
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


# Step 3: put the notes and the question into one message
def build_prompt(question, notes):
    notes_text = ""
    for note in notes:
        notes_text = notes_text + "[Page " + str(note["page"]) + "]\n" + note["text"] + "\n\n"
    return "Course notes:\n" + notes_text + "Student question: " + question


# Splits a multi-part question into its parts, for example
# "What is a race condition, what is deadlock and what is thrashing?" becomes three questions.
def split_parts(question):
    if not re.match(r"\s*what\b", question, re.IGNORECASE):
        return [question]
    pieces = [p.strip(" ?.") for p in re.split(r",\s*and\s+|,\s*|\s+and\s+", question)]
    pieces = [p for p in pieces if len(p.split()) >= 3]
    return pieces if len(pieces) >= 2 else [question]


# Step 4: find the last question the student asked, from the earlier messages
def is_follow_up(question):
    words = re.findall(r"[a-z']+", question.lower())
    refers_back = {"it", "its", "this", "that", "these", "those", "they", "them", "more", "example", "again"}
    return len(words) <= 6 and any(w in refers_back for w in words)


def last_question_in(history):
    for message in reversed(history):
        if message["role"] == "user":
            return message["content"]
    return ""


# Step 5: get the messages for the model, or None if the notes don't cover the question.
# history is the earlier chat as a list of {"role": ..., "content": ...}, oldest first.
# A follow-up is searched together with the question before it, so the right notes are found.
def prepare_question(model, collection, question, course, pages=None, history=None):
    question = question.strip()
    history = history or []

    # Search with only the current question, so an earlier topic does not pull the search off course.
    # Only a short follow-up that refers back ("it", "this", "example") uses the question before it.
    search_text = question
    last = last_question_in(history)
    if last and is_follow_up(question):
        search_text = last + " " + question

    # A multi-part question ("what is X, what is Y and what is Z") is searched one part at a time,
    # so each topic gets its own chunks and one topic does not crowd out the others.
    if last and is_follow_up(question):
        parts = [search_text]
    else:
        parts = split_parts(question)

    notes = []
    for part in parts:
        found = find_notes(model, collection, part, course, pages)
        # Notes come back closest first. A part whose closest note is too far is not covered.
        if not found or found[0]["distance"] > RELEVANCE_CUTOFF:
            continue
        keep = found if len(parts) == 1 else found[:PER_PART]
        for note in keep:
            if note not in notes:
                notes.append(note)

    if not notes:
        return None, []
    notes.sort(key=lambda n: n["distance"])

    # The earlier messages go between the rules and the new question, shortened to fit the model's memory
    earlier = [{"role": m["role"], "content": m["content"][:HISTORY_CHARS]}
               for m in history[-(HISTORY_EXCHANGES * 2):]]

    messages = [{"role": "system", "content": INSTRUCTIONS}]
    messages = messages + earlier
    messages.append({"role": "user", "content": build_prompt(question, notes)})
    return messages, notes