# core/course_plan.py
# Helpers for a course's topic list. Reads data/<course>/topics.json.
# Progress is saved in core/progress.py, not here.
# Run from the UNI-GPT folder to test:
#   python -m core.course_plan COS331
 
import json
import os
import sys
 
 
# Step 1: the file that holds the topics for a course
def topics_path(course):
    return os.path.join("data", course, "topics.json")
 
 
# Step 2: read all topics for a course, in the order they appear in the file
# If only_checked is True, return only the topics the course owner has checked
def load_topics(course, only_checked=False):
    path = topics_path(course)
    if not os.path.exists(path):          # no topics file yet
        return []
 
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
 
    topics = data["topics"]
    if only_checked:
        topics = [t for t in topics if t["checked"]]   # keep only checked topics
    return topics
 
 
# Step 3: get the page numbers for one topic (returns an empty list if not found)
def load_topic_pages(course, topic_name):
    for topic in load_topics(course):      # look through every topic
        if topic["name"] == topic_name:
            return topic["pages"]
    return []
 
 
# Step 4: get the names of the topics, in order
def topic_names(course, only_checked=False):
    return [t["name"] for t in load_topics(course, only_checked)]
 
 
# Step 5: find the topic that comes after the given one (None if it is the last)
def next_topic(course, topic_name, only_checked=False):
    names = topic_names(course, only_checked)
    if topic_name not in names:
        return None
    position = names.index(topic_name)      # where this topic sits in the list
    if position + 1 < len(names):
        return names[position + 1]
    return None
 
 
# Test it on its own. Run from the UNI-GPT folder.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m core.course_plan <COURSE>")
        sys.exit(1)
 
    course = sys.argv[1]
    print("Topics in order:")
    for name in topic_names(course):
        print("  -", name, "| pages", load_topic_pages(course, name))
 
    print("Topics the owner has checked:", len(topic_names(course, only_checked=True)))