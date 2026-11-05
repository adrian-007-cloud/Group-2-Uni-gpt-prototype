# core/checkpoint.py
# Checkpoint questions: a mid-course set and an end-of-course set.
# The questions are the check questions already written for each topic.
# They are saved in data/<course>/check_questions.json.
# Run from the UNI-GPT folder:
#   python -m core.checkpoint COS331              (show what is ready)
#   python -m core.checkpoint COS331 --generate   (write the check question for every checked topic)

import json
import os
import sys
from core.course_plan import load_topics


# Step 1: the file that holds the check question for each topic
def questions_path(course):
    return os.path.join("data", course, "check_questions.json")


# Step 2: read the saved questions (a dictionary: topic name -> question)
def load_check_questions(course):
    path = questions_path(course)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Step 3: save the check question for one topic
def save_check_question(course, topic_name, question):
    data = load_check_questions(course)
    data[topic_name] = question
    with open(questions_path(course), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# Step 4: the checked topic names in order
def checked_topic_names(course):
    return [t["name"] for t in load_topics(course, only_checked=True)]


# Step 5: which topics a checkpoint covers
# "middle" = the first half of the topics, "end" = all of them
def checkpoint_topics(course, kind):
    names = checked_topic_names(course)
    half = (len(names) + 1) // 2          # for 17 topics, the middle is topic 9
    if kind == "middle":
        return names[:half]
    if kind == "end":
        return names
    return []


# Step 6: the questions for a checkpoint (only topics that already have a question)
def checkpoint_questions(course, kind):
    saved = load_check_questions(course)
    result = []
    for name in checkpoint_topics(course, kind):
        if name in saved:
            result.append({"topic": name, "question": saved[name]})
    return result


# Step 7: after a student finishes a topic, is a checkpoint due? Returns "middle", "end" or None
def checkpoint_due(course, finished_topic):
    names = checked_topic_names(course)
    if finished_topic not in names:
        return None
    position = names.index(finished_topic)
    half = (len(names) + 1) // 2
    if position == half - 1:
        return "middle"
    if position == len(names) - 1:
        return "end"
    return None


# Step 8: write the check question for every checked topic (uses the model, takes a while)
def generate_all(course):
    # imported here so the two files do not import each other at the top
    from core.tutor import open_notes, write_with_model, STEP_TASKS
    collection = open_notes()
    for name in checked_topic_names(course):
        print("Writing question for:", name)
        text = write_with_model(collection, course, name, STEP_TASKS["Check question"])
        save_check_question(course, name, text)
    print("Done. Saved to", questions_path(course))


# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m core.checkpoint <COURSE> [--generate]")
        sys.exit(1)

    course = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--generate":
        generate_all(course)
    else:
        print("Middle checkpoint topics:", checkpoint_topics(course, "middle"))
        print("End checkpoint topics:", len(checkpoint_topics(course, "end")), "topics")
        print("Questions ready:", len(load_check_questions(course)))
        print("Middle checkpoint ready:", checkpoint_questions(course, "middle"))