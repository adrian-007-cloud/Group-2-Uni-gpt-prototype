# Test: what phrases does KeyBERT suggest for each page of a course PDF?
# Run from the UNI-GPT folder with the venv active, for example:
#   python eval/test_keybert.py "data/COS335/COS 335 Lecture Note 1.pdf" 20
import os
import sys

# Use only the embedding model saved on this computer, with no internet.
# This must be set before the other imports.
os.environ["HF_HUB_OFFLINE"] = "1"

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

pdf_path = sys.argv[1]
pages_to_check = int(sys.argv[2]) if len(sys.argv) > 2 else 20

# Step 1: load the embedding model that is already on this computer
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
kw_model = KeyBERT(model=embed_model)

# Step 2: open the PDF
reader = PdfReader(pdf_path)

# Step 3: for each page, print the phrases KeyBERT suggests
for number, page in enumerate(reader.pages, start=1):
    if number > pages_to_check:
        break
    text = page.extract_text() or ""
    if len(text.split()) < 30:
        print("Page", number, ": too little text, skipped")
        continue
    keywords = kw_model.extract_keywords(
        text, keyphrase_ngram_range=(1, 3), stop_words="english", top_n=5
    )
    phrases = [phrase for phrase, score in keywords]
    print("Page", number, ":", phrases)