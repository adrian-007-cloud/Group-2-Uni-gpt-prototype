What I checked: the chunker, which cuts the COS331 notes into pieces for the chatbot to search. I looked at 171 pieces from 65 pages to see if they were the right size and if they ended properly.

How: I wrote a small script, eval/evaluate_chunking.py. It runs the chunker on the cleaned pages and saves a report. Then I compared the results with the PDF.

What I fixed: the chunker was splitting sentences at every line break in the PDF, so many pieces ended halfway through a sentence. It now joins those lines first. Pieces with no ending punctuation dropped from 72 to 22, and cut-off sentences from 30 to 4. The 4 that remain are at page ends, which I left alone so the page numbers stay correct.


RAG pipeline evaluation (retrieval and refusal)

Test set: 12 questions on COS331. 10 are answerable and have an expected page checked against the PDF. 2 are unrelated to the course and should be refused.

Settings: 5 chunks retrieved per question, relevance cutoff of 1.35, model llama3.2 running locally.

Metrics
Recall (hit rate) at k: the share of questions where the expected page appears in the top k chunks. At k=5, the setting the app uses, it is 10 of 10 (1.00).
Precision at k: the share of the top k chunks that come from the expected page. At k=5 it is 0.26. This is low by design, because each question has only one correct page and the other chunks are context.
Top-1 hit rate: the expected page is the first result. 7 of 10 (0.70).
MRR (mean reciprocal rank): how high the first correct chunk ranks, averaged over questions. A first-place hit scores 1, second scores 1/2, third scores 1/3. Result: 0.817.
nDCG@5: a ranking score for the top 5 that rewards correct chunks placed higher. Result: 0.735.
Refusal correct: whether the app refused when it should, and answered when it should. Result: 12 of 12.
Cutoff sweep: the test of the relevance cutoff across values from 1.0 to 1.6. At 1.35, all 10 course questions were answered and both unrelated questions were refused. At 1.6, the “lecturer” question was answered, so 1.6 is too loose.
Answer time: average seconds per answer. Result: about 61 seconds.
Findings
Search finds the right page reliably at the app’s setting of 5 chunks.
The relevance cutoff separates course and unrelated questions. Course questions had distances up to 0.96, and unrelated questions had 1.53 and 1.79. The 1.35 cutoff sits in the gap.
Answer time is too slow for a live demo and needs improving.


# RAG Pipeline Evaluation Log

**Date:** 8 November 2026
**Scope:** Retrieval, relevance cutoff, and refusals on COS331.
**Not yet done:** Checking the wording of the answers by hand.

---

## 1. What we tested

We tested two things:

1. Does the chatbot find the right page in the notes for a question?
2. Does it refuse questions the notes do not cover?

The test set has 18 questions:

- **10 course questions.** Each has an expected page, checked against the PDF.
- **8 unrelated questions.** For example, "Who won the 2022 World Cup?"

## 2. Settings

- Chunks retrieved per question: **5**
- Model: **llama3.2**, running locally through Ollama
- Relevance cutoff: **1.35** on the first run, changed to **1.2** after this run

## 3. Metrics

### Recall at k (hit rate)

Did the expected page appear in the top k chunks?

- k = 1: **0.70** (7 of 10)
- k = 3: **1.00**
- k = 5: **1.00** (the setting the app uses)
- k = 8: **1.00**
- k = 10: **1.00**

### Precision at k

What share of the top k chunks came from the expected page?

- k = 1: **0.70**
- k = 3: **0.40**
- k = 5: **0.26**
- k = 8: **0.20**
- k = 10: **0.17**

Precision falls as k grows because each question has only one correct page.

### MRR (Mean Reciprocal Rank)

How high the first correct chunk ranks, averaged over questions. A first-place hit scores 1, second place scores 1/2, third place scores 1/3.

- MRR: **0.817**

### nDCG@5

A ranking score for the top 5 chunks. It rewards correct chunks placed higher in the list.

- nDCG@5: **0.735**

### Refusal correct

Did the app answer when it should, and refuse when it should not?

- **18 of 18** correct

### Cutoff sweep

How many questions get answered at each relevance cutoff:

- Cutoff 1.0 to 1.35: 10 of 10 course questions answered, 0 of 8 unrelated answered. Precision of answering: 1.00.
- Cutoff 1.4: 10 of 10 course answered, 2 of 8 unrelated answered. Precision of answering: 0.83.
- Cutoff 1.5: 10 of 10 course answered, 2 of 8 unrelated answered. Precision of answering: 0.83.
- Cutoff 1.6: 10 of 10 course answered, 3 of 8 unrelated answered. Precision of answering: 0.77.

### Answer time

- First run: about **61 seconds** per answer (probably a cold model load)
- Second run: about **17 seconds** per answer

## 4. Findings

- The expected page was in the top 5 chunks for all 10 course questions.
- The expected page was ranked first for 7 of them.
- The cutoff separates course questions from unrelated ones cleanly.
- Course questions had a closest-match distance between **0.49 and 0.96**.
- Unrelated questions had a closest-match distance between **1.39 and 1.87**.

## 5. Decision

We set the relevance cutoff to **1.2**. It sits in the middle of the gap between the two groups, so it still answers real questions that score a little higher than our test set.

## 6. Open items

- Check the wording of the answers by hand. The `correct_by_hand` column is still empty.
- Some answers include details that are not in the notes:
  - Race condition: "critical section"
  - Thrashing: "overcommitted"
  - Paging: no mention of internal fragmentation
  - Virtual and physical address: does not explain the difference clearly
  - PCB: "privileges" and "pointer to parent process"
- The test set is small (10 course, 8 unrelated). Treat these results as a first check, not a final measure.