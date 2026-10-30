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

To run the project, 
activate env :    .\venv\Scripts\activate
start ollama
run streamlit

### 2026-10-30

**Search (retrieval)**
- Tested: Recall@3 = 100% (10 of 10 questions), MRR = 0.85. One course only.
- Tested: the search returns the right page for the sample questions.

**Answers (model and prompt)**
- Tested: the fallback works. "What is the capital of France" returns "I cannot find this in the course notes."
- Tested: `llama3.2` gives clearer explanations than `llama3.2:1b`. It is slower on the same laptop. Decision: keep `llama3.2` for the final project, and report the speed trade-off honestly.
- Tested: the answer was cut off mid-sentence at `num_predict` = 120 and at 300. Raising the limit (and checking `num_ctx`) produced a complete explanation of alpha beta pruning.
- Pending: confirm the final `num_predict` value and time a full answer with it.

**Speed**
- Before changes: "what is alpha beta pruning" took about 80 seconds on the first run. A second question took 37 seconds (with `llama3.2`).
- Limitation: the answer step is slow on an 8 GB laptop CPU, mainly before the first word appears. This is a known limit for the report.
- Added, pending a timed test: `keep_alive` = 30m, so the model stays loaded between questions.
- Added, pending a timed test: streaming answers, so words appear as they are written.

**App**
- Tested: the app starts with `HF_HUB_OFFLINE` set. The offline warning appears, but the saved embedding model still loads.
- Fixed: an error about Ollama refusing connections happened because the Ollama service was not running. Solved by starting it (`ollama serve` or the Ollama app).
- Fixed: the notes were shown twice, because an old block was left in `app.py`. Now the notes are in one expander.
- Added, pending a test: the query is trimmed with `strip()` before searching. Test with extra spaces at the start and end.
Added a side expander to allow user pick the model they want to use