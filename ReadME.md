# Uni-GPT

A study assistant for university course notes. It answers questions only from the course notes, shows the page each answer came from, and runs fully offline on the student's own computer. It uses no paid API and no cloud service.

Developed at the **National Centre for Artificial Intelligence and Robotics (NCAIR)**, NITDA, Abuja, during the SIWES placement.

**Facilitator:** Mr. Stephen Ayuba

**Team (Group 2):**
- Ejikemadu Ibuchi: RAG pipeline and front end
- Richard Odey: text chunking
- Emmanuel Godwin-akor: PDF cleaning
- Iember Apebo: LLM integration

Each member evaluated their own part.

---

## What it does

- **Notes-only chatbot.** Answers come only from the notes. If the notes do not cover a question, the app says "I cannot find this in the course notes." and does not call the model.
- **Page numbers.** Each answer lists the pages it was built from. The pages are hidden when the answer is the refusal sentence.
- **Guided course path.** An overview with learning objectives, then one slide per topic in lecture-note order.
- **Quizzes.** A middle quiz and an end quiz. Wrong answers get an explanation with the notes page.
- **Progress.** Ticked topics are saved on the laptop. Chat history and ticks clear when the page is refreshed.

## Requirements

- Windows, macOS or Linux. Tested on Windows with 8 GB RAM and CPU only.
- Python 3.10 or newer.
- [Ollama](https://ollama.com) for the local language model.
- Internet access for the first setup only.

## Setup (first time)

1. Open a terminal in the project folder.

2. Create and turn on a virtual environment.
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   On macOS or Linux, use `source venv/bin/activate`.

3. Install the Python packages.
   ```
   pip install -r requirements.txt
   ```

4. Download the language model with Ollama.
   ```
   ollama pull llama3.2
   ```

5. Download the embedding model once (internet needed).
   ```
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
   ```

## Adding a course

Each course has its own folder in `data/`. The folder name is the course code, for example `COS331`.

```
data/
  COS331/
    COS331 Lecture Notes.pdf      <- the course PDF, directly in the folder
    outline.txt                   <- one topic per line, from the course outline
```

Then run, from the project folder with the virtual environment on:

```
python -m core.embed_store COS331
```

This cleans the PDF, splits it into chunks, and stores them in the `chroma_db/` folder. Use `--rebuild` after changing the PDF, for example `python -m core.embed_store COS331 --rebuild`. Only that course is replaced.

The topic pages and check questions are created with the commands in the project's setup notes. Check the page numbers in `topics.json` against the PDF before students use them.

## Running the app

1. Start Ollama in one terminal and leave it open:
   ```
   ollama serve
   ```
   If you see "address already in use", Ollama is already running.

2. In a second terminal, turn on the virtual environment and start the app:
   ```
   venv\Scripts\activate
   streamlit run app.py
   ```

3. The app opens in the browser. Choose a course in the sidebar. The first answer after starting is the slowest.

## How the chatbot works

1. The question is turned into 384 numbers by the `all-MiniLM-L6-v2` embedding model.
2. ChromaDB returns the 5 closest note chunks for that course. Each chunk carries its page number.
3. Relevance cutoff: if the closest chunk is farther than **1.2** (squared L2 distance), the app refuses and does not call the model.
4. A short follow-up question ("give me an example of it") is searched together with the question before it. A multi-part question ("what is X, what is Y and what is Z") is searched once per part.
5. The model (`llama3.2` through Ollama, temperature 0.1) receives the rules, the chunks with their page labels, the last exchange and the question. It writes the answer.
6. The app shows the answer and the page numbers.

Full explanations are in `Uni-GPT_RAG_Guide_v2.pdf` and `Uni-GPT_Research_Report.docx`.

## Project layout

```
app.py                    the Streamlit web app
core/
  rag_pipeline.py         search, cutoff and prompt building
  embed_store.py          cleans, chunks and stores the notes in ChromaDB
  llm_client.py           sends messages to Ollama
  cleaner.py              cleans the PDF text
  chunker.py              splits pages into chunks of up to 200 words
  topics.py               finds the pages for each outline topic
  checkpoint.py           checkpoint questions
  progress.py             saves the last finished topic
eval/
  evaluate.py             measures search and the cutoff on a test set
  test_questions.json     COS331 test questions (18)
  eval_COS335.json        COS335 test questions (12)
data/                     course PDFs, outlines and study files (not on GitHub)
chroma_db/                the search index (not on GitHub)
requirements.txt          Python packages
```

## Testing

From the project folder:

```
python eval/evaluate.py                    # COS331 test set
python eval/evaluate.py eval_COS335.json   # COS335 test set
```

Each run writes `evaluation_results.csv` (one row per question) and `evaluation_summary.txt` (the numbers). A new run overwrites both, so rename the files first if you want to keep them.

### Results

| Measure | COS331 (18 questions) | COS335 (12 questions) |
|---|---|---|
| Right page in top 5 (recall at 5) | 10 of 10 course questions | 8 of 10 course questions |
| First place (recall at 1) | 0.70 | not recorded |
| MRR | 0.817 | 0.725 |
| Refusals correct | 18 of 18 | not recorded |
| Average answer time | about 17 seconds (second run); about 61 seconds (first run, model loading) | not recorded |

COS331 was measured on 8 November 2026. The COS335 result is from the latest run. The first COS335 run found 4 of 10 because several expected pages were wrong; they were corrected before the latest run.

The COS331 answer wording has not been checked by hand yet. The `correct_by_hand` column in the results file is empty.

## Limits

- **Speed.** Answers take about 15 seconds to over two minutes on a laptop CPU.
- **Model mistakes.** The small model sometimes adds details that are not in the notes, and sometimes breaks its rules on topics close to the notes (for example, a joke about a topic in the notes). Page numbers are shown so a student can check.
- **Informal wording.** Filler words can move a question away from the notes, and the app may refuse a question it should answer.
- **Small test sets.** 18 questions for COS331 and 12 for COS335. Treat the results as a first check.
- **Cutoff.** 1.2 was chosen from the gap between course and unrelated questions in our tests. For COS335 it is tight, so 1.3 may be safer.
- **Scanned pages.** Pages with very little text are flagged as weak, and their text may be missing.

## Privacy

- The notes, the database, and every question and answer stay on the computer where the app runs.
- There are no accounts, logins or analytics.
- The Inter font loads from Google Fonts. This is the only request that leaves the computer, and it carries no course content.
- The notes and the database are not encrypted. Anyone with access to the computer can read them.
- To delete a course, remove its folder in `data/` and rebuild the index. To delete everything, remove `data/` and `chroma_db/`.

## Sources and acknowledgements

- Lewis et al. (2020), retrieval-augmented generation.
- Reimers and Gurevych (2019), Sentence-BERT embeddings.
- Wang et al. (2020), MiniLM, the basis for all-MiniLM-L6-v2.
- Tools: Streamlit, ChromaDB, Sentence-Transformers, pdfplumber, Ollama (llama3.2).

## Licence and course material

The lecture notes belong to the university and the lecturer. Check that you have permission before sharing this repository with the notes included. The repository here does not include the notes.