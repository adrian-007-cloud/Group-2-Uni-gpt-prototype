# Checks how well the notes were split into chunks. It does not need the model or the database.
# Run it from the project folder, once per course:
#   python evaluate_chunking.py COS331
#
# It reads the cleaned pages in data/<course>/cleaned/ and cuts them the same way the app does.
# It writes chunking_report.txt.

import glob
import os
import re
import statistics
import sys

PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_FOLDER)   # lets Python find the core folder
os.chdir(PROJECT_FOLDER)             # so data\ is found

from core.chunker import chunk_text

SIZES_TO_COMPARE = [100, 200, 400]    # chunk sizes (in words) to compare
CHUNK_LIMIT = 200                     # the size the app uses


def page_number(path):
    # The cleaner saves files named like "lecture-page-007.txt", so the page is in the name
    match = re.search(r"-page-(\d+)\.txt$", os.path.basename(path))
    return int(match.group(1)) if match else None


def ends_cleanly(text):
    # A chunk "ends cleanly" if it stops at . ! ? or a quote after one.
    # Headings and list items often have no full stop, so this is only a guide.
    return text.rstrip().endswith((".", "!", "?", '"', "'"))


def main():
    course = sys.argv[1] if len(sys.argv) > 1 else "COS331"
    folder = os.path.join("data", course, "cleaned")
    files = sorted(glob.glob(os.path.join(folder, "*.txt")))
    if not files:
        print("No cleaned pages found in", folder, "- run the cleaner first.")
        return

    pages = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            pages.append({"page": page_number(path), "text": f.read()})

    empty_pages = [p["page"] for p in pages if not p["text"].strip()]
    weak_pages = [p["page"] for p in pages if 0 < len(p["text"].split()) < 30]

    # Cut every page the way the app does
    chunks = []
    for p in pages:
        for piece in chunk_text(p["text"], CHUNK_LIMIT):
            chunks.append({"page": p["page"], "text": piece})

    lengths = [len(c["text"].split()) for c in chunks]
    too_long = [c for c in chunks if len(c["text"].split()) > CHUNK_LIMIT]
    not_clean = [c for c in chunks if not ends_cleanly(c["text"])]
    seen = {}
    duplicates = 0
    for c in chunks:
        if c["text"] in seen:
            duplicates += 1
        seen[c["text"]] = True

    lines = []
    lines.append("Course: %s" % course)
    lines.append("")
    lines.append("Pages")
    lines.append("  pages read: %d" % len(pages))
    lines.append("  empty pages: %d %s" % (len(empty_pages), empty_pages[:20]))
    lines.append("  weak pages (under 30 words, may be scanned): %d %s" % (len(weak_pages), weak_pages[:20]))
    lines.append("  pages that gave at least one chunk: %d of %d" % (len({c["page"] for c in chunks}), len(pages)))
    lines.append("")
    lines.append("Chunks at size %d words (the app's setting)" % CHUNK_LIMIT)
    lines.append("  total chunks: %d" % len(chunks))
    if lengths:
        lines.append("  words per chunk: average %.0f, shortest %d, longest %d" % (statistics.mean(lengths), min(lengths), max(lengths)))
    lines.append("  chunks over %d words (only happens with one very long sentence): %d" % (CHUNK_LIMIT, len(too_long)))
    lines.append("  chunks that do not end with . ! ? (check a few; often headings): %d (%.0f%%)" % (
        len(not_clean), 100 * len(not_clean) / max(len(chunks), 1)))
    lines.append("  repeated chunks (same text twice): %d" % duplicates)
    lines.append("  chunks crossing a page boundary: 0 by design (each page is cut on its own)")
    lines.append("")
    lines.append("Comparing chunk sizes (what if the size were different?)")
    lines.append("  size  chunks  average words")
    for size in SIZES_TO_COMPARE:
        counted = []
        for p in pages:
            counted.extend(len(t.split()) for t in chunk_text(p["text"], size))
        if counted:
            lines.append("  %-5d %-7d %.0f" % (size, len(counted), statistics.mean(counted)))
    lines.append("")
    lines.append("This shows the size of chunks, not how well they find answers.")
    lines.append("To judge the size, change CHUNK_LIMIT in chunker.py, rebuild the database, and run evaluate.py again.")

    text = "\n".join(lines)
    with open("chunking_report.txt", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print()
    print("Saved: chunking_report.txt")


if __name__ == "__main__":
    main()