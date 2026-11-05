# Print how close the best match is for each question.
# Lower numbers mean a closer match.
# Run from the UNI-GPT folder, for example: python eval/test_distance.py COS335
import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
from sentence_transformers import SentenceTransformer

course = sys.argv[1]
questions = [
    "what is concurrency",
    "what is alpha beta pruning",
    "what is the capital of France",
    "what is weak AI",
    "what is Weak AI",
    "what weak Ai",
    "explain weak AI",
    "what is narrow AI",
]

model = SentenceTransformer("all-MiniLM-L6-v2")
collection = chromadb.PersistentClient(path="chroma_db").get_collection("notes")

for question in questions:
    vector = model.encode([question], normalize_embeddings=True).tolist()
    result = collection.query(query_embeddings=vector, n_results=1, where={"course": course})
    distance = result["distances"][0][0]
    print(round(distance, 3), "-", question)