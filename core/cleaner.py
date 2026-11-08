# core/cleaner.py
# Cleans the text of each page before it is chunked.
# Run from the UNI-GPT folder, for example:
#   python -m core.cleaner COS335
import os
import re
import sys
from collections import Counter
import pdfplumber


PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")
MIN_REPEAT_LENGTH = 8     # a repeated line must be at least this many characters
REPEAT_SHARE = 0.5        # ...and must appear on more than half of the pages
WEAK_PAGE_WORDS = 30      # pages with fewer words than this are flagged

# Characters that PDFs often use in place of normal ones
SPECIAL_CHARACTERS = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "‘": "'", "’": "'", "“": '"', "”": '"', "\u00a0": " ",
}


# Rule 1: replace the special characters
def fix_characters(text):
    for wrong, right in SPECIAL_CHARACTERS.items():
        text = text.replace(wrong, right)
    return text


# Rule 2: join a word split by a hyphen at the end of a line ("con-" + "currency")
def join_broken_words(text):
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


# Rule 3: remove lines that contain only a number (page numbers)
def remove_bare_numbers(lines):
    return [line for line in lines if not re.fullmatch(r"\d+", line)]


# Rule 4a: find lines that repeat on more than half of the pages
def find_repeated_lines(all_pages_lines):
    counts = Counter()
    for lines in all_pages_lines:
        for line in set(lines):             # count each line once per page
            if len(line) >= MIN_REPEAT_LENGTH:
                counts[line] += 1
    limit = REPEAT_SHARE * len(all_pages_lines)
    return {line for line, count in counts.items() if count > limit}


# Rule 5: collapse extra spaces and extra blank lines
def tidy_lines(lines):
    tidy = []
    for line in lines:
        line = " ".join(line.split())
        if line == "" and (not tidy or tidy[-1] == ""):
            continue                        # skip a blank line if the last one was blank
        tidy.append(line)
    return tidy


def clean_course(course):
    folder = os.path.join(DATA_FOLDER, course)
    cleaned_folder = os.path.join(folder, "cleaned")
    os.makedirs(cleaned_folder, exist_ok=True)

     # Step 1: read every page of every PDF in the course folder, using pdfplumber
    pages = []
    for file_name in sorted(os.listdir(folder)):
        if not file_name.lower().endswith(".pdf"):
            continue
        with pdfplumber.open(os.path.join(folder, file_name)) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                pages.append({"file": file_name, "page": number, "raw": page.extract_text() or ""})
    if not pages:
        print("No PDF files found in", folder)
        return []

    # Step 2: fix characters, join broken words, split into lines, remove page numbers
    for item in pages:
        text = fix_characters(item["raw"])
        text = join_broken_words(text)
        lines = [line.strip() for line in text.split("\n")]
        item["lines"] = remove_bare_numbers(lines)

    # Step 3: find the repeated headers and footers across the whole course
    repeated = find_repeated_lines([item["lines"] for item in pages])

    # Step 4: remove the repeated lines, tidy the spacing, save each page, and keep it for the caller
    cleaned_pages = []
    weak_pages = []
    for item in pages:
        kept = [line for line in item["lines"] if line not in repeated]
        kept = tidy_lines(kept)
        text = "\n".join(kept)
        words = len(text.split())
        if words < WEAK_PAGE_WORDS:
            weak_pages.append((item["file"], item["page"], words))

        file_stem = os.path.splitext(item["file"])[0]
        out_name = file_stem + "-page-" + str(item["page"]).zfill(3) + ".txt"
        with open(os.path.join(cleaned_folder, out_name), "w", encoding="utf-8") as out:
            out.write(text)

        if words > 0:
            cleaned_pages.append({"file": item["file"], "page": item["page"], "text": text})

    # Step 5: report what happened, so you can check it by hand
    print("Pages cleaned:", len(pages))
    print("Repeated lines removed (check this list):")
    for line in sorted(repeated):
        print("  -", line)
    print("Weak pages (very little text, may be scanned):")
    for file_name, page_number, words in weak_pages:
        print("  -", file_name, "page", page_number, "with", words, "words")
    print("Cleaned pages saved in:", cleaned_folder)

    return cleaned_pages

if __name__ == "__main__":
    clean_course(sys.argv[1])