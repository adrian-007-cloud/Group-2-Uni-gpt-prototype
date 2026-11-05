# core/progress.py
# Saves and loads how far a student has got in a course.
# The progress file is data/<course>/progress.json.
# No student names are stored here, only topic names.
# Run from the UNI-GPT folder to test:
#   python -m core.progress COS331
 
import json
import os
import sys
 
 
# Step 1: the file that holds the progress for a course
def progress_path(course):
    return os.path.join("data", course, "progress.json")
 
 
# Step 2: read the progress (the name of the last topic the student finished)
def load_progress(course):
    path = progress_path(course)
    if not os.path.exists(path):           # no progress saved yet
        return {"last_finished": None}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
 
 
# Step 3: save the name of the topic the student has just finished
def save_progress(course, topic_name):
    data = {"last_finished": topic_name}
    with open(progress_path(course), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
 
 
# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m core.progress <COURSE>")
        sys.exit(1)
 
    course = sys.argv[1]
    print("Before:", load_progress(course))
    save_progress(course, "Deadlock")
    print("After saving Deadlock:", load_progress(course))