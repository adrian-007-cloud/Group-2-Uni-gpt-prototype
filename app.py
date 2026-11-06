import json
import os
import random
import re
os.environ["HF_HUB_OFFLINE"] = "1"   # use only the saved models, no internet

import streamlit as st
from core.rag_pipeline import load_search, list_courses, prepare_question
from core.llm_client import ask_model_stream

st.set_page_config(page_title="Uni-GPT", page_icon="📚", layout="centered")

# Step 1: a light, flat look. Colours change automatically in dark mode.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Colours. Dark mode changes these automatically. */
:root {
  --ink:#0f172a; --muted:#64748b; --accent:#6366f1; --accent2:#a855f7;
  --line:#e2e8f0; --bg:#f8fafc; --card:#ffffff; --soft:rgba(99,102,241,0.08);
  --shadow:0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -12px rgba(15,23,42,0.12);
}
@media (prefers-color-scheme: dark) {
  :root {
    --ink:#f1f5f9; --muted:#94a3b8; --accent:#818cf8; --accent2:#c084fc;
    --line:#1e293b; --bg:#0a0c12; --card:#111521; --soft:rgba(129,140,248,0.12);
    --shadow:0 1px 2px rgba(0,0,0,0.4), 0 10px 30px -14px rgba(0,0,0,0.7);
  }
}

/* Background with a soft glow at the top */
html, body, [class*="css"] { font-family:'Inter', system-ui, sans-serif; -webkit-font-smoothing:antialiased; }
.stApp {
  background:
    radial-gradient(900px 500px at 15% -10%, rgba(99,102,241,0.14), transparent 60%),
    radial-gradient(700px 400px at 100% 0%, rgba(168,85,247,0.10), transparent 55%),
    var(--bg);
}
#MainMenu, footer, header { visibility:hidden; }
[data-testid="stDecoration"] { display:none; }
.block-container { max-width:740px; padding-top:2.5rem; padding-bottom:7rem; }
.block-container > div { animation: fadeUp .5s ease both; }
@keyframes fadeUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }

/* Text */
h1, h2, h3, h4 { color:var(--ink); letter-spacing:-0.02em; }
h4 { font-weight:650; margin-top:1.4rem; }
.kicker {
  display:inline-block; color:var(--accent); font-size:0.72rem; font-weight:700;
  letter-spacing:0.09em; text-transform:uppercase; padding:5px 11px; border-radius:999px;
  background:var(--soft); margin-bottom:0.4rem;
}
.big-title {
  font-size:2.25rem; font-weight:800; line-height:1.15; letter-spacing:-0.03em; margin:0.2rem 0 0.9rem;
  background:linear-gradient(120deg, var(--ink) 25%, var(--accent) 75%, var(--accent2));
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.course-name { font-size:1.2rem; font-weight:650; color:var(--ink); margin:0; letter-spacing:-0.01em; }
.muted { color:var(--muted); font-size:0.92rem; line-height:1.6; }
.objective { color:var(--ink); line-height:1.75; }

/* Buttons: primary is a gradient with a soft glow, secondary is a clean pill */
.stButton > button {
  border-radius:999px; font-weight:600; padding:0.5rem 1.1rem; border:1px solid var(--line);
  background:var(--card); color:var(--ink); box-shadow:var(--shadow);
  transition: transform .15s ease, box-shadow .2s ease, border-color .2s ease;
}
.stButton > button:hover { transform:translateY(-1px); border-color:var(--accent); color:var(--accent); }
.stButton > button:disabled { opacity:0.4; transform:none; }
.stButton > button[kind="primary"] {
  background:linear-gradient(135deg, var(--accent), var(--accent2)); border:none; color:#fff;
  box-shadow:0 10px 24px -10px var(--accent);
}
.stButton > button[kind="primary"]:hover { color:#fff; box-shadow:0 14px 28px -10px var(--accent); }

/* Progress bar: one thin track with a gradient fill */
.track { height:6px; border-radius:999px; background:var(--line); overflow:hidden; margin:0.6rem 0 0.8rem; }
.fill { height:100%; border-radius:999px; background:linear-gradient(90deg, var(--accent), var(--accent2)); transition:width .4s ease; }

/* Quiz options */
[data-testid="stRadio"] label {
  padding:9px 14px; border-radius:12px; transition: background .15s ease;
}
[data-testid="stRadio"] label:hover { background:var(--soft); }

/* Example as a highlighted quote */
blockquote {
  border-left:3px solid var(--accent); background:var(--soft); padding:14px 18px;
  border-radius:0 14px 14px 0; margin:0.5rem 0; color:var(--ink);
}

/* Dividers that fade at the ends */
hr {
  margin:2rem 0 !important; border:none !important; height:1px;
  background:linear-gradient(90deg, transparent, var(--line), transparent) !important;
}

/* Chat messages as soft cards, and a floating input */
[data-testid="stChatMessage"] {
  background:var(--card); border:1px solid var(--line); border-radius:18px;
  padding:14px 18px; margin-bottom:12px; box-shadow:var(--shadow);
}
[data-testid="stChatInput"] {
  border-radius:999px !important; border:1px solid var(--line) !important;
  box-shadow:0 18px 40px -18px rgba(15,23,42,0.35) !important; background:var(--card) !important;
}
[data-testid="stChatInput"]:focus-within { border-color:var(--accent) !important; }
[data-testid="stBottom"] > div { background:transparent !important; }
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------

# Step 2: read a course's study file (topics and quiz). Returns None if it is missing.
def load_study(course):
    path = os.path.join("data", course, "study.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Step 3: make the list of slides: overview, topics, a middle quiz, then an end quiz
def build_slides(topics):
    total = len(topics)
    middle_after = (total + 1) // 2
    slides = [{"type": "overview"}]
    for number, topic in enumerate(topics, start=1):
        slides.append({"type": "topic", "topic": topic, "number": number, "total": total})
        if number == middle_after and number < total:
            slides.append({"type": "quiz", "kind": "middle",
                           "covered": [t["name"] for t in topics[:number]]})
    slides.append({"type": "quiz", "kind": "end", "covered": [t["name"] for t in topics]})
    return slides


# Step 4: callbacks for the buttons
def open_course(name):
    st.session_state["course"] = name
    st.session_state["slide"] = 0
    st.session_state["chat"] = []


def move(step):
    st.session_state["slide"] = st.session_state.get("slide", 0) + step


def go_home():
    st.session_state["course"] = None


# Step 5: ask the notes a question and stream the answer
def ask(course, question, model, collection, history):
    # history is the earlier chat. rag_pipeline.py uses it to search and to build the prompt.
    messages, notes = prepare_question(model, collection, question, course, history=history)
    if messages is None:
        # The notes don't cover this, so show the fallback message. It was not shown before.
        st.markdown("I cannot find this in the course notes.")
        return "I cannot find this in the course notes.", []
    pages = sorted({n["page"] for n in notes})
    text = ""
    placeholder = st.empty()
    for piece in ask_model_stream(messages):
        text += piece
        placeholder.markdown(text)
    return text, pages


# Step 5b: the "explain this topic" button puts a question in the chat for us
def ask_about(name):
    st.session_state["pending_question"] = "Explain " + name + " simply, using only the notes."


# Step 5c: the "try again" button starts a new set of quiz questions
def try_again(base):
    st.session_state[base + "_attempt"] = st.session_state.get(base + "_attempt", 0) + 1


# Step 5d: spot "my name is ..." (or "call me ...") so the app can greet the student.
# This is handled here, not by the notes, so it does not depend on the notes at all.
NAME_PATTERN = re.compile(r"\b(?:my name is|call me|i'm called)\s+([A-Za-z][A-Za-z'-]{1,30})", re.IGNORECASE)


def find_name(text):
    match = NAME_PATTERN.search(text)
    return match.group(1).capitalize() if match else None


# Step 6: load the search model once, so the page stays fast
@st.cache_resource
def get_search():
    return load_search()


model, collection = get_search()
courses = list_courses(collection)
st.session_state.setdefault("course", None)


# ---------- Home page ----------
if st.session_state["course"] is None:
    st.markdown('<div class="kicker">Uni-GPT</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-title">Learn your course from your own notes</div>', unsafe_allow_html=True)
    st.markdown('<p class="muted">Pick a course, go through it one slide at a time, take the quizzes, '
                'and ask questions. Answers come only from your notes, with the page numbers.</p>',
                unsafe_allow_html=True)
    st.write("")

    for name in courses:
        study = load_study(name)
        left, right = st.columns([4, 1], vertical_alignment="center")
        with left:
            st.markdown('<p class="course-name">%s</p>' % name, unsafe_allow_html=True)
            if study:
                st.markdown('<p class="muted">%d topics</p>' % len(study["topics"]), unsafe_allow_html=True)
            else:
                st.markdown('<p class="muted">Study plan coming soon</p>', unsafe_allow_html=True)
        with right:
            st.button("Open", key="open_" + name, on_click=open_course, args=(name,),
                      disabled=study is None, type="primary", use_container_width=True)
        st.divider()


# ---------- Course page ----------
else:
    course = st.session_state["course"]
    study = load_study(course)

    top_left, top_right = st.columns([3, 1], vertical_alignment="center")
    with top_left:
        st.markdown('<p class="course-name">%s</p>' % course, unsafe_allow_html=True)
    with top_right:
        st.button("All courses", on_click=go_home, use_container_width=True)

    if study is None:
        st.info("There is no study plan for this course yet.")
        st.stop()

    slides = build_slides(study["topics"])
    index = min(max(st.session_state.get("slide", 0), 0), len(slides) - 1)
    slide = slides[index]

    # One progress bar, drawn with HTML so only one line appears
    percent_done = index / max(len(slides) - 1, 1) * 100
    st.markdown('<div class="track"><div class="fill" style="width:%d%%"></div></div>' % percent_done,
                unsafe_allow_html=True)
    st.markdown('<p class="muted">Slide %d of %d</p>' % (index + 1, len(slides)), unsafe_allow_html=True)

    # ----- The slide itself -----
    if slide["type"] == "overview":
        st.markdown('<div class="kicker">Course overview</div>', unsafe_allow_html=True)
        st.markdown('<div class="big-title">%s</div>' % course, unsafe_allow_html=True)
        st.write("This course has %d topics, in the order of the lecture notes. "
                 "There is a quiz halfway through and one at the end." % len(study["topics"]))
        # Step A: count the topics the student has ticked as read (this browser session only)
        total_topics = len(study["topics"])
        read_count = sum(1 for n in range(1, total_topics + 1)
                         if st.session_state.get("read_%s_%d" % (course, n)))
        st.markdown('<p class="muted">%d of %d topics read</p>' % (read_count, total_topics),
                    unsafe_allow_html=True)

        st.markdown("#### Outline")
        for n, topic in enumerate(study["topics"], start=1):
            pages = topic["pages"]
            where = ("pages %d to %d" % (min(pages), max(pages))) if pages else "not in the notes"
            st.markdown("**%d. %s**  \n<span class='muted'>%s</span>" % (n, topic["name"], where),
                        unsafe_allow_html=True)
            # Step B: a tick box the student clicks once they have read the topic
            st.checkbox("I have read this topic", key="read_%s_%d" % (course, n))
            for objective in topic["objectives"]:
                st.markdown('<div class="objective">&nbsp;&nbsp;&nbsp;&nbsp;• %s</div>' % objective,
                            unsafe_allow_html=True)

    elif slide["type"] == "topic":
        t = slide["topic"]
        st.markdown('<div class="kicker">Topic %d of %d</div>' % (slide["number"], slide["total"]),
                    unsafe_allow_html=True)
        st.markdown('<div class="big-title">%s</div>' % t["name"], unsafe_allow_html=True)
        if t["pages"]:
            st.markdown('<p class="muted">From the notes, pages %s</p>'
                        % ", ".join(str(p) for p in t["pages"]), unsafe_allow_html=True)
        st.write(t["summary"])

        st.markdown("#### By the end of this topic you should be able to")
        for objective in t["objectives"]:
            st.markdown("- " + objective)

        st.markdown("#### Key ideas")
        for idea in t["key_ideas"]:
            st.markdown("- " + idea)

        st.markdown("#### Example")
        st.markdown("> " + t["example"])
        st.write("")
        st.button("Explain this topic with the chatbot", on_click=ask_about, args=(t["name"],))

    else:
        title = "Middle quiz" if slide["kind"] == "middle" else "End of course quiz"
        st.markdown('<div class="kicker">Quiz</div>', unsafe_allow_html=True)
        st.markdown('<div class="big-title">%s</div>' % title, unsafe_allow_html=True)

        # Step 7: draw the questions once per quiz and keep them while the student answers
        base = "quiz_%s_%s_%d" % (course, slide["kind"], index)
        attempt = st.session_state.get(base + "_attempt", 0)
        key = base + "_" + str(attempt)
        if key not in st.session_state:
            pool = [q for q in study["quiz"] if q["topic"] in slide["covered"]]
            size = 10 if slide["kind"] == "middle" else 20
            st.session_state[key] = random.sample(pool, min(size, len(pool)))
        items = st.session_state[key]

        if not items:
            st.info("The quiz questions for this course are not ready yet.")

        # Step 8: show each question, check the answer straight away
        results = {}
        for pos, q in enumerate(items):
            st.markdown("**%d. %s**" % (pos + 1, q["question"]))
            chosen = st.radio("Choose one answer", q["options"], index=None,
                              key="%s_%d" % (key, pos), label_visibility="collapsed")
            if chosen is not None:
                is_right = q["options"].index(chosen) == q["answer"]
                results[pos] = is_right
                if is_right:
                    st.markdown(":green[Correct]")
                else:
                    st.markdown(":red[Not quite.] The correct answer is: **" + q["options"][q["answer"]] + "**")
            st.write("")

        # Step 9: the score
        if items:
            right_count = sum(1 for v in results.values() if v)
            if len(results) == len(items):
                st.subheader("Final score: %d out of %d" % (right_count, len(items)))
                percent = right_count / len(items) * 100
                if percent >= 80:
                    st.write("Well done. You know this part well.")
                elif percent >= 50:
                    st.write("Good effort. Review the topics you missed.")
                else:
                    st.write("Review the topics again, then try once more.")
            else:
                st.markdown("**Score so far:** %d right out of %d answered" % (right_count, len(results)))

        st.write("")
        st.button("Try again with new questions", on_click=try_again, args=(base,))

    # ----- Navigation -----
    st.write("")
    back, _, forward = st.columns([1, 2, 1])
    with back:
        st.button("← Back", on_click=move, args=(-1,), disabled=index == 0, use_container_width=True)
    with forward:
        st.button("Next →", on_click=move, args=(1,), type="primary",
                  disabled=index == len(slides) - 1, use_container_width=True)

    # ----- Chat: below the slide, always available -----
    st.divider()
    st.markdown('<div class="kicker">Ask your notes</div>', unsafe_allow_html=True)
    st.session_state.setdefault("chat", [])
    for m in st.session_state["chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["text"])
            if m["pages"]:
                st.caption("From pages " + ", ".join(str(p) for p in m["pages"]))

    question = st.chat_input("Ask a question about %s" % course) or st.session_state.pop("pending_question", None)
    if question:
        # the chat before this question, in the form rag_pipeline.py expects
        history = [{"role": m["role"], "content": m["text"]} for m in st.session_state["chat"]]
        st.session_state["chat"].append({"role": "user", "text": question, "pages": []})
        with st.chat_message("user"):
            st.write(question)
        name = find_name(question)
        with st.chat_message("assistant"):
            if name:
                st.session_state["student_name"] = name
                text = "Nice to meet you, %s. Ask me anything about %s from your notes." % (name, course)
                pages = []
                st.markdown(text)
            else:
                try:
                    text, pages = ask(course, question, model, collection, history)
                except Exception as error:
                    text, pages = "Could not get an answer. Is Ollama running? " + str(error), []
                    st.error(text)
                if pages:
                    st.caption("From pages " + ", ".join(str(p) for p in pages))
        st.session_state["chat"].append({"role": "assistant", "text": text, "pages": pages})