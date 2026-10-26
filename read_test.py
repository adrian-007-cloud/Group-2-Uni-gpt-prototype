from pypdf import PdfReader

FILE = "data\COS 335 Lecture Note 1.pdf"

reader = PdfReader(FILE)
print("Total pages:", len(reader.pages))

for number, page in enumerate(reader.pages, start= 1):
    print(f"--- Page {number} ---")
    print(page.extract_text())