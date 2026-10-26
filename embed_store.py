import chromadb
from sentence_transformers import SentenceTransformer
from chunker import chunk_pdf

FILE = "data/COS 335 Lecture Note 1.pdf"
DB_FOLDER = "chroma_db"
COLLECTION = "notes"
EMBED_MODEL = "all-MiniLM-L6-v2"
TEST_QUESTION = "what are types of AI"


def build_index():
    print("Loading embedding model...")
    model = SentenceTransformer(EMBED_MODEL)

    client = chromadb.PersistentClient(path=DB_FOLDER)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    chunks = chunk_pdf(FILE)
    texts = [text for text, _ in chunks]
    ids = [f"chunk-{i}" for i in range(len(chunks))]
    metadatas = [{"source": FILE, "page": page} for _, page in chunks]

    print("Embedding", len(texts), "chunks...")
    vectors = model.encode(texts, normalize_embeddings=True).tolist()

    collection.add(ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas)
    print("Stored", collection.count(), "chunks.")
    return model, collection


def test_search(model, collection, question):
    vector = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=vector, n_results=3)
    print("\nTop 3 results for:", question)
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"--- Page {meta['page']} ---")
        print(doc[:300])
        print()


if __name__ == "__main__":
    model, collection = build_index()
    test_search(model, collection, TEST_QUESTION)