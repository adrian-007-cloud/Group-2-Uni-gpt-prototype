# Step 1: bring in the tools this page needs
import chromadb                      # the database that stores the notes
import streamlit as st               # builds the web page
from sentence_transformers import SentenceTransformer   # turns text into numbers

# Step 2: settings, in one place so they're easy to change
DATABASE_FOLDER = "chroma_db"        # where the notes database is saved
COLLECTION_NAME = "notes"            # the name we gave the notes table
EMBEDDING_MODEL = "all-MiniLM-L6-v2" # the model that turns text into numbers
NUMBER_OF_RESULTS = 3                # how many matching notes to show


# Step 3: load the embedding model once.
# The "@st.cache_resource" line tells Streamlit to remember the result,
# so it doesn't reload the model every time you type something.
@st.cache_resource
def load_model():
    return SentenceTransformer(EMBEDDING_MODEL)


# Step 4: open the notes database once, using the same memory trick.
@st.cache_resource
def load_notes():
    database = chromadb.PersistentClient(path=DATABASE_FOLDER)
    return database.get_collection(COLLECTION_NAME)


# Step 5: the page itself
st.title("Uni-GPT: Course Search")
st.write("This version only finds the relevant notes. Answers come in the next step.")

model = load_model()
notes = load_notes()

# A box where the student types a question
question = st.text_input("Ask a question about the course notes")

# Step 6: when a question is typed, search for it
if question:
    # Turn the question into numbers, the same way the notes were stored
    question_numbers = model.encode([question], normalize_embeddings=True).tolist()

    # Ask the database for the closest matching notes
    results = notes.query(query_embeddings=question_numbers, n_results=NUMBER_OF_RESULTS)

    # The results come back as lists, so read each one in turn
    found_texts = results["documents"][0]
    found_info = results["metadatas"][0]

    st.subheader("Most relevant notes")

    for i in range(len(found_texts)):
        source_file = found_info[i]["source"]
        page_number = found_info[i]["page"]

        st.markdown(f"**Source:** {source_file}, page {page_number}")
        st.write(found_texts[i])
        st.divider()