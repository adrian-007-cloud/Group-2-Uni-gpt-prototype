# This file runs the RAG steps: find the notes, build the prompt, get the answer.
import chromadb
from sentence_transformers import SentenceTransformer
from core.llm_client import ask_model

DB_FOLDER = "chroma_db"
COLLECTION_NAME = "notes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
NUMBER_OF_RESULTS = 3

# The rules we give the model every time
INSTRUCTIONS = """You are a study assistant for one university course.
Answer the student's question using ONLY the course notes you are given.
If the notes do not contain the answer, say: "I cannot find this in the course notes."
At the end, list the pages you used, like this: Sources: page 13, page 19.
Keep the answer clear and simple."""


# Load the embedding model and open the notes database
def load_search():
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = chromadb.PersistentClient(path=DB_FOLDER).get_collection(COLLECTION_NAME)
    return model, collection


# Find the most relevant note chunks for the question
def find_notes(model, collection, question):
    question_numbers = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=question_numbers, n_results=NUMBER_OF_RESULTS)

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
def answer_question(model, collection, question):
    question = question.strip()    #remove spaces at the start and end
    notes = find_notes(model, collection, question)
    prompt = build_prompt(question, notes)

    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    answer = ask_model(messages)
    return answer, notes


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