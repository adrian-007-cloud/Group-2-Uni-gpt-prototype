# core/lessons.py
# Saves the tutor content (key ideas, worked example, check question) for each checked topic,
# so the model is not asked again every time a student opens a topic.
# The course owner checks data/<course>/lessons.json once. Rebuild it only when the notes change.
# Run from the UNI-GPT folder:
#   python -m core.lessons COS331 --build     (writes lessons.json, uses the model, takes a while)
#   python -m core.lessons COS331             (shows which topics are saved)

import json
import os
import sys
from core.course_plan import load_topics, load_topic_pages
from core.tutor import open_notes, write_with_model, get_topic_notes, STEP_TASKS, numbers_are_in_notes, NO_EXAMPLE_TEXT

# The steps that are saved (feedback and next step are not saved, since they depend on the student)
SAVED_STEPS = ["Key ideas", "Worked example", "Check question"]


# Step 1: the file that holds the saved lessons for a course
def lessons_path(course):
    return os.path.join("data", course, "lessons.json")


# Step 2: read the saved lessons (a dictionary: topic name -> steps)
def load_lessons(course):
    path = lessons_path(course)
    if not os.path.exists(path):          # nothing saved yet
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Step 3: save the whole dictionary to the file (called after every topic, so nothing is lost)
def save_lessons(course, saved):
    with open(lessons_path(course), "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)


# Step 4: get the saved steps for one topic (None if not saved yet)
def get_lesson(course, topic_name):
    return load_lessons(course).get(topic_name)


# Step 5: write the steps for every checked topic and save them
def build_lessons(course):
    collection = open_notes()
    saved = load_lessons(course)          # keep any lessons already built

    for topic in load_topics(course, only_checked=True):
        name = topic["name"]
        pages = load_topic_pages(course, name)

        # Skip topics with no pages, so no error message gets saved as a lesson
        if not pages:
            print("Skipped (no pages):", name)
            continue

        print("Writing lesson for:", name)
        try:
            all_notes = get_topic_notes(collection, course, pages, limit=None)

            steps = {}
            for title in SAVED_STEPS:
                text = write_with_model(collection, course, name, STEP_TASKS[title])

                # The worked example must not use numbers that are not in the notes
                if title == "Worked example" and all_notes and not numbers_are_in_notes(text, all_notes):
                    text = NO_EXAMPLE_TEXT

                steps[title] = text

            saved[name] = steps
            save_lessons(course, saved)      # save now, so a crash later does not lose this topic

        except Exception as error:
            # One failed topic should not stop the rest. Usually this means Ollama is not running.
            print("  FAILED:", name, "-", error)
            print("  Check that Ollama is running, then run the build again. Finished topics are kept.")
            continue

    print("Done. Saved", len(saved), "lessons to", lessons_path(course))
    print("Open the file and check each topic before students use it.")


# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m core.lessons <COURSE> [--build]")
        sys.exit(1)

    course = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--build":
        build_lessons(course)
    else:
        saved = load_lessons(course)
        print("Saved lessons:", len(saved))
        for name in saved:
            print("  -", name)