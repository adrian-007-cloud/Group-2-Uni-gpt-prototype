## 2026-10-26: Environment setup
- Created project folder UNI-GPT on Desktop
- Created data/ folder
- Created venv with: python -m venv venv
- Activated with: .\venv\Scripts\activate

installed libraries:
- streamlit: builds the chat web page you’ll open in the browser.
- chromadb: the vector database that stores the notes and finds matching sections.
- sentence-transformers: runs the local embedding model that turns text into numbers.
- pypdf: reads text from PDF files.
- python-pptx: reads text from PowerPoint slides.
- requests: sends your questions to the local Ollama model and gets the answers back.
Verified that all libraries were working

Install Ollama later, not needed for initial setup
tested the pdf reader with read_test.py

- Chunking works. 240 chunks from 122 pages. Average 150 words per chunk.
- Storage works. Test question "what are types of AI" found pages 9 and 10 in the top 3.
- Page 112 also ranked high (related topic, not the same answer).
- Flow diagram on page 9 isn't readable as text, as expected.