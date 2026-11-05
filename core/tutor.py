# core/tutor.py
# Builds the six tutoring steps for one topic.
# The code decides the order. The model only writes the content of steps 2 to 4,
# using the notes from that topic's pages.
# A number check stops invented numbers in the worked example.
# Run from the UNI-GPT folder to test:
#   python -m core.tutor COS331 Deadlock

import re
import sys
import chromadb
from core.llm_client import ask_model
from core.rag_pipeline import DB_FOLDER, COLLECTION_NAME
from core.checkpoint import save_check_question
from core.checkpoint import save_check_question
from core.course_plan import load_topic_pages, next_topic
from core.progress import save_progress

MAX_NOTES = 8   # how many note chunks to give the model (keeps the prompt short)

# The six steps, in the order the student sees them
STEP_TITLES = [
    "Topic",
    "Key ideas",
    "Worked example",
    "Check question",
    "Feedback",
    "Next step",
]

# The rules we give the model for every tutor step
TUTOR_RULES = """You are a study tutor. Use only the course notes provided.
Start directly with the content. Do not write an introduction.
You may explain ideas in your own simpler words.
Do not add facts, names, methods, or examples that are not in the notes.
Only attach a method or scheme to a topic if the notes place it there.
Use the exact names from the notes when listing named items.
Never write page numbers. The app shows them separately.
Finish every sentence.
Keep the answer short and clear."""

# What the model must do for each step it writes
STEP_TASKS = {
    "Key ideas": "List the 3 to 5 most important ideas of this topic. Use short bullet points.",
    "Worked example": "Give one concrete example or scenario from the notes that shows how this topic works. "
                      "If the notes do not contain one, reply with exactly: The notes do not give a worked example for this topic.",
    "Check question": "Write one question that tests whether the student understood the key ideas. "
                      "Write only the question, nothing else.",
}

# Shown instead of an example that uses numbers the notes do not contain
NO_EXAMPLE_TEXT = "The notes do not give a worked example for this topic."


# Step 1: open the notes database
def open_notes():
    client = chromadb.PersistentClient(path=DB_FOLDER)
    return client.get_collection(COLLECTION_NAME)


# Step 2: get the note chunks that come from this topic's pages (no search, just the pages)
# limit=None means get every chunk from those pages
def get_topic_notes(collection, course, pages, limit=MAX_NOTES):
    if not pages:
        return []
    results = collection.get(
        where={"$and": [{"course": course}, {"page": {"$in": pages}}]},
        include=["documents", "metadatas"],
    )
    notes = []
    for text, info in zip(results["documents"], results["metadatas"]):
        notes.append({"text": text, "page": info["page"]})
    notes.sort(key=lambda n: n["page"])     # keep the notes in page order
    if limit is None:
        return notes
    return notes[:limit]


# Step 3: put the topic, the notes and the task into messages for the model
def build_messages(task, topic_name, notes):
    notes_text = ""
    for note in notes:
        notes_text = notes_text + "[Page " + str(note["page"]) + "]\n" + note["text"] + "\n\n"
    user_message = "Topic: " + topic_name + "\n\nCourse notes:\n" + notes_text + "Task: " + task
    return [
        {"role": "system", "content": TUTOR_RULES},
        {"role": "user", "content": user_message},
    ]


# Step 4: ask the model to write one step, using only this topic's notes
def write_with_model(collection, course, topic_name, task):
    pages = load_topic_pages(course, topic_name)
    notes = get_topic_notes(collection, course, pages)
    if not notes:
        return "The notes for this topic could not be found. Check topics.json and the cleaned pages."
    return ask_model(build_messages(task, topic_name, notes))


# Step 5: the number check. Returns True only if every number in the answer is in the notes.
def numbers_are_in_notes(answer, all_notes):
    notes_text = " ".join(n["text"] for n in all_notes)
    notes_numbers = set(re.findall(r"\d+", notes_text))     # every number in the notes
    answer_numbers = set(re.findall(r"\d+", answer))        # every number in the answer
    return answer_numbers.issubset(notes_numbers)


# Step 6: the six steps for one topic, in order. Returns a list of (title, text) pairs.
def tutor_steps(collection, course, topic_name):
    steps = []

    # Step 1: the topic and its pages (no model needed)
    pages = load_topic_pages(course, topic_name)
    page_text = ", ".join(str(p) for p in pages) if pages else "none found"
    steps.append((STEP_TITLES[0], "Topic: " + topic_name + "\nPages: " + page_text))

    # Steps 2 to 4: the model writes the content
    all_notes = get_topic_notes(collection, course, pages, limit=None)
    for title in ["Key ideas", "Worked example", "Check question"]:
        text = write_with_model(collection, course, topic_name, STEP_TASKS[title])

        # The worked example must not use numbers that are not in the notes
        if title == "Worked example" and all_notes and not numbers_are_in_notes(text, all_notes):
            text = NO_EXAMPLE_TEXT

        steps.append((title, text))

    # Save the check question so checkpoints can use it
    for title, text in steps:
           if title == "Check question":
               save_check_question(course, topic_name, text)

    # Steps 5 and 6 are added by give_feedback and next_step below
    return steps


# Step 7: the model checks the student's answer against the notes
def give_feedback(collection, course, topic_name, check_question, student_answer):
    task = ("The student was asked: " + check_question + "\n"
            "The student answered: " + student_answer + "\n"
            "Say whether the answer is correct, using only the notes. "
            "Explain briefly what is right or what is missing.")
    return write_with_model(collection, course, topic_name, task)


# Step 8: the next topic, and save the progress for this topic
def next_step(course, topic_name):
    save_progress(course, topic_name)           # remember this topic is finished
    after = next_topic(course, topic_name, only_checked=True)
    if after is None:
        return "No more checked topics. Topics not yet checked by the course owner are not shown."
    return "Next topic: " + after


# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m core.tutor <COURSE> <TOPIC NAME>")
        print("Example: python -m core.tutor COS331 Deadlock")
        sys.exit(1)

    course = sys.argv[1]
    topic = sys.argv[2]
    collection = open_notes()

    for title, text in tutor_steps(collection, course, topic):
        print("== " + title + " ==")
        print(text)
        print()
    print("== Next step ==")
    print(next_step(course, topic))