# Compare pypdf and pdfplumber on one page of a PDF.
# Run from the UNI-GPT folder:
#   python eval/test_reader.py "data/COS331/COS 331 Operating SystemII Concurrencypdf.pdf" 4
import sys
from pypdf import PdfReader
import pdfplumber

pdf_path = sys.argv[1]
page_number = int(sys.argv[2])

# Read the page with pypdf (what we use now)
reader = PdfReader(pdf_path)
print("=== pypdf ===")
print(reader.pages[page_number - 1].extract_text())

# Read the same page with pdfplumber
print("\n=== pdfplumber ===")
with pdfplumber.open(pdf_path) as pdf:
    print(pdf.pages[page_number - 1].extract_text())