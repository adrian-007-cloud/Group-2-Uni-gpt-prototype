# This file runs the RAG steps: find the notes, build the prompt, get the answer.
import chromadb
from sentence_transformers import SentenceTransformer
from core.llm_client import ask_model

DB_FOLDER = "chroma_db"
COLLECTION_NAME = "notes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
NUMBER_OF_RESULTS = 3

# The rules we give the model every time
INSTRUCTIONS = """You are a study assistant. You answer a student's question using only the course notes provided below.

How to answer:
1. Find the parts of the notes that relate to the question.
2. If they answer the question, explain it clearly in your own words. Use 3 to 6 sentences unless the question asks for more.
3. If the notes include examples, steps, or definitions for the topic, include them. Use only what the notes say.
4. If the notes cover part of the question, answer that part and say which part the notes do not cover.
5. If the notes do not cover the question at all, reply with only this sentence: I cannot find this in the course notes.

Never add facts from outside the notes. Never write page numbers; the app shows them separately.
Do not both answer and use the fallback sentence in the same reply.

Question format: the student's question is given at the end of the message."""

# Load the embedding model and open the notes database
def load_search():
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = chromadb.PersistentClient(path=DB_FOLDER).get_collection(COLLECTION_NAME)
    return model, collection


# List the course codes that are stored in the database
def list_courses(collection):
    stored = collection.get(include=["metadatas"])["metadatas"]
    return sorted(set(m["course"] for m in stored))

# Find the most relevant note chunks for the question
def find_notes(model, collection, question, course):
    question_numbers = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(
        query_embeddings=question_numbers,
        n_results=NUMBER_OF_RESULTS,
        where={"course": course},   # only search this course's notes
    )
    found = []
    for text, info in zip(results["documents"][0], results["metadatas"][0]):
        found.append({"text": text, "page": info["page"]})
    return found


# Put the notes and the question into one message
def build_prompt(question, notes):
    notes_text = ""
    for note in notes:
        notes_text = notes_text + "[Page " + str(note["page"]) + "]\n" + note["text"] + "\n\n"
    return "Course notes:\n" + notes_text + "Student question: " + question


# The whole process: find notes, build the prompt, ask the model
def answer_question(model, collection, question, course):
    messages, notes = prepare_question(model, collection, question, course)
    answer = ask_model(messages)
    return answer, notes

def prepare_question(model, collection, question, course):
    question = question.strip()
    notes = find_notes(model, collection, question, course)
    prompt = build_prompt(question, notes)
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    return messages, notes


# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    model, collection = load_search()
    answer, notes = answer_question(model, collection, "what are the types of agents")
    print(answer)
    page_numbers = []
    for note in notes:
        if note["page"] not in page_numbers:
            page_numbers.append(note["page"])
    print("Sources: pages", ", ".join(str(p) for p in page_numbers))