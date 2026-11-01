# This file builds the notes database, one course at a time.
# Run these from the UNI-GPT folder:
#   python -m core.embed_store                     (add every course not stored yet)
#   python -m core.embed_store COS335              (process only COS335)
#   python -m core.embed_store COS335 --rebuild    (replace COS335 with fresh chunks)
import os
import sys
import glob
import chromadb
from sentence_transformers import SentenceTransformer
from core.chunker import chunk_pdf

DATA_FOLDER = "data"        # each course has its own folder here, named with its code
DB_FOLDER = "chroma_db"     # where the database is saved
COLLECTION = "notes"        # the name of the collection inside the database
EMBED_MODEL = "all-MiniLM-L6-v2"


# Step 1: open the database. It is created if it doesn't exist yet.
def open_collection():
    client = chromadb.PersistentClient(path=DB_FOLDER)
    return client.get_or_create_collection(COLLECTION)


# Step 2: list the course folders. The folder name is the course code.
def find_course_folders(only_course=None):
    courses = []
    for name in sorted(os.listdir(DATA_FOLDER)):
        if os.path.isdir(os.path.join(DATA_FOLDER, name)):
            if only_course is None or name == only_course:
                courses.append(name)
    return courses


# Step 3: process one course. Read its PDFs, embed the chunks, save them with the course tag.
def index_course(model, collection, course, rebuild):
    # Check whether this course is already in the database
    existing = collection.get(where={"course": course}, limit=1)
    if existing["ids"] and not rebuild:
        print(course, "is already stored. Use --rebuild to replace it.")
        return
    if existing["ids"]:
        # Remove only this course's old chunks. Other courses are not touched.
        collection.delete(where={"course": course})
        print("Removed the old chunks for", course)

    # Read every PDF in the course folder, one chunk at a time
    texts = []
    ids = []
    metadatas = []
    counter = 0
    pdf_files = sorted(glob.glob(os.path.join(DATA_FOLDER, course, "*.pdf")))
    for pdf_path in pdf_files:
        file_name = os.path.basename(pdf_path)
        for chunk_text, page in chunk_pdf(pdf_path):
            texts.append(chunk_text)
            ids.append(course + "-chunk-" + str(counter))   # unique id for each course
            metadatas.append({"course": course, "source": file_name, "page": page})
            counter = counter + 1

    if not texts:
        print("No text was found for", course, "- check its PDF files.")
        return

    # Turn the text into numbers and save everything
    print("Embedding", len(texts), "chunks for", course, "...")
    vectors = model.encode(texts, normalize_embeddings=True).tolist()
    collection.add(ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas)
    print("Stored", len(texts), "chunks for", course)


# Step 4: read the command-line options and run everything
if __name__ == "__main__":
    args = sys.argv[1:]
    rebuild = "--rebuild" in args
    names = [a for a in args if a != "--rebuild"]
    only_course = names[0] if names else None

    print("Loading the embedding model...")
    model = SentenceTransformer(EMBED_MODEL)
    collection = open_collection()

    courses = find_course_folders(only_course)
    if not courses:
        print("No course folder found. Make one inside data/, for example data/COS335/")

    for course in courses:
        index_course(model, collection, course, rebuild)

    # Show which courses are now stored
    stored = collection.get(include=["metadatas"])["metadatas"]
    print("Courses in the database:", sorted(set(m["course"] for m in stored)))