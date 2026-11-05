app.py                  the Streamlit app
core/
  cleaner.py            cleans PDF text (special characters, broken words, headers)
  embed_store.py        splits notes into chunks and stores them in ChromaDB
  rag_pipeline.py       search and answer rules
  llm_client.py         talks to Ollama
  topics.py             finds the pages for each outline topic
  course_plan.py        topic list, topic pages, next topic
  tutor.py              the six tutor steps, with the number check
  checkpoint.py         checkpoint questions
  progress.py           saves the last finished topic
data/                   course PDFs, outlines, topics, questions, progress (not on GitHub)
chroma_db/              the search index (not on GitHub)