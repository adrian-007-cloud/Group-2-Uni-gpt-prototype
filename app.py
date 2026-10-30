import os
os.environ["HF_HUB_OFFLINE"] = "1"

# Step 1: bring in the tools this page needs
import streamlit as st
from core.rag_pipeline import load_search, answer_question, prepare_question
from core.llm_client import ask_model_stream

# The model choices the student can pick from
MODEL_CHOICES = {
    "Faster, less detailed: llama3.2:1b": "llama3.2:1b",
    "Smarter, slower on weak computers: llama3.2": "llama3.2",
}

# The sidebar where the student picks a model
with st.sidebar:
    st.subheader("Choose a model")
    choice = st.radio("Model", list(MODEL_CHOICES.keys()))
    st.caption("The faster model answers quickly but explains less. The smarter model explains more clearly but takes longer.")

selected_model = MODEL_CHOICES[choice]

# Step 2: the title and a short description
st.title("Uni-GPT: Course Assistant")
st.write("Ask a question about the course notes. The answer shows the pages it came from.")


# Step 3: load the search and the database once, so the page stays fast
@st.cache_resource
def get_search():
    return load_search()

with st.spinner("Loading the search model. This takes a moment the first time..."):
    model, collection = get_search()


# Step 4: the box where the student types a question
question = st.text_input("Your question")


# Step 5: when a question is typed, find the notes and write the answer
if question:
    try:
        messages, notes = prepare_question(model, collection, question)
    except Exception as error:
        st.error("Could not search the notes. Details: " + str(error))
        st.stop()

    # Show the answer as it is written
    st.subheader("Answer")
    answer_box = st.empty()
    answer = ""
    try:
        for piece in ask_model_stream(messages, selected_model):
            answer = answer + piece
            answer_box.write(answer)
    except Exception as error:
        st.error("Could not get an answer. Is Ollama running? Details: " + str(error))
        st.stop()

    # Show the pages the answer was based on, without repeats
    st.subheader("Sources")
    page_numbers = []
    for note in notes:
        if note["page"] not in page_numbers:
            page_numbers.append(note["page"])
    st.write("Pages: " + ", ".join(str(p) for p in page_numbers))

    # Show the notes behind the answer, hidden until the student opens them
    with st.expander("Notes that were found"):
        for note in notes:
            st.markdown("**Page " + str(note["page"]) + "**")
            st.write(note["text"])
            st.divider()