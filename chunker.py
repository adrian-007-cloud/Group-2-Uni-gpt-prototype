import re
from pypdf import PdfReader

MAX_WORDS = 200


def split_sentences(text):
    # Split at . ! ? or line breaks, and drop empty pieces
    pieces = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in pieces if p.strip()]


def chunk_text(text, max_words=MAX_WORDS):
    chunks = []
    current = []
    count = 0

    for sentence in split_sentences(text):
        words = len(sentence.split())
        if current and count + words > max_words:
            chunks.append(" ".join(current))
            current = []
            count = 0
        current.append(sentence)
        count += words

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_pdf(path):
    # Returns a list of (chunk_text, page_number) for the whole PDF
    reader = PdfReader(path)
    results = []
    for number, page in enumerate(reader.pages, start=1):
        for chunk in chunk_text(page.extract_text() or ""):
            results.append((chunk, number))
    return results


if __name__ == "__main__":
    FILE = "data\COS 335 Lecture Note 1.pdf"
    all_chunks = chunk_pdf(FILE)
    print("Total chunks:", len(all_chunks))
    for text, page in all_chunks[:3]:
        print(f"--- Page {page} ---")
        print(text)
        print()

    total_words = sum(len(text.split()) for text, _ in all_chunks)
    print("Average words per chunk:", total_words // len(all_chunks))
    print("Pages with text:", len({page for _, page in all_chunks}))