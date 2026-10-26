import csv
import chromadb
from sentence_transformers import SentenceTransformer

DB_FOLDER = "chroma_db"
COLLECTION = "notes"
EMBED_MODEL = "all-MiniLM-L6-v2"
EVAL_FILE = "eval/eval.csv"
TOP_K = 3

model = SentenceTransformer(EMBED_MODEL)
collection = chromadb.PersistentClient(path=DB_FOLDER).get_collection(COLLECTION)

with open(EVAL_FILE, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

hits = 0
reciprocal = 0.0
for row in rows:
    question = row["question"]
    correct = int(row["page"])
    vector = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=vector, n_results=TOP_K)
    pages = [m["page"] for m in results["metadatas"][0]]

    if correct in pages:
        hits += 1
        reciprocal += 1 / (pages.index(correct) + 1)
        status = "HIT "
    else:
        status = "MISS"
    print(f"{status} page {correct:>3}  top pages {pages}  {question[:45]}")

print(f"\nRecall@{TOP_K}: {hits}/{len(rows)} = {hits / len(rows):.0%}")
print(f"MRR: {reciprocal / len(rows):.2f}")