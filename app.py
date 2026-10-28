# Step 1: bring in the tools this page needs
import streamlit as st
from core.rag_pipeline import load_search, answer_question

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
    with st.spinner("Searching the notes and writing an answer..."):
        try:
            answer, notes = answer_question(model, collection, question)
        except Exception as error:
            st.error("Could not get an answer. Is Ollama running? Details: " + str(error))
            st.stop()

    # Show the answer
    st.subheader("Answer")
    st.write(answer)

    # Show the pages the answer was based on, without repeats
    st.subheader("Sources")
    page_numbers = []
    for note in notes:
        if note["page"] not in page_numbers:
            page_numbers.append(note["page"])
    st.write("Pages: " + ", ".join(str(p) for p in page_numbers))

    # Show the full text of each note that was found
    st.subheader("Notes that were found")
    for note in notes:
        st.markdown("**Page " + str(note["page"]) + "**")
        st.write(note["text"])
        st.divider()