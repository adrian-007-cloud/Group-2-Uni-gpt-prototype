## 2026-10-26: Environment setup
- Created project folder UNI-GPT on Desktop
- Created data/ folder
- Created venv with: python -m venv venv
- Activated with: .\venv\Scripts\activate

Digital files: COS 335 Lecture Note 1.pdf
Scanned files:

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
Created a github repo and succesfully pushed the code


- Decision: students can upload their own notes (PDF/TXT) in the final project.
  Prototype uses one hardcoded file. Loader must accept file contents, not only paths.
  Affects: Notes Loader (Person 1), Streamlit page (Person 5), UML Data Manager box.

  Created eval, core and test folders to make the project modules more organized

Did a recall test for my search and it came out as:
- Recall test: Recall@3 = 10/10 (100%), MRR = 0.85. 10 questions, one digital PDF.
Ten questions is a small test. The report should say so.
The questions use the slides’ own words, which makes them easier to find. Add a few questions worded differently, such as “what kinds of AI agents are there?”, to see how the search copes with paraphrases.
Page 19 and page 23 appeared twice in the top results. That means two chunks from the same page matched, which is useful but means the top 3 can contain repeats. Note it as an observation.
Unification (page 88) ranked the wrong page first. Page 55 came top. Look at that page to see why it matched; it’s a good example for your limitations section.
- Answer step works end to end. Question "types of agents" returned five agent types, sources pages 11, 13, 51. Main source is page 13.

Prompt enginerring techniques:
1.  Role: “You are a study assistant for one university course.” This sets how the model behaves.
2.  Grounding: “Answer using ONLY the course notes.” This keeps answers tied to the source material.
3.  Fallback: “If the notes do not contain the answer, say...” This gives the model an honest exit, instead of guessing.

Eval: i asked the capital of france and it didnt generate a random answer, it just said it wasnt in the course notes

Limitation: The speed of the interface is quite slow for modern standards