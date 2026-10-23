# MEMBER 2: Cited Search, Safety Checks and Lab Trends (the ML part)
**Your files:** `member2_logic.py`, `member2_search_safety.py`, `test_search.py`
**First finish the setup in `README_TEAM.md`.**

Your job: the intelligence of CareTrace. You make sure the AI **never answers without evidence**: every search answer shows its source document, and when the records don't contain the answer, the app says **"Not found in records"** instead of guessing. You also build the safety flags a doctor would want to see.

The code is already written and working. **Your work is to understand it, test it, improve it and be able to defend it in the viva.**

---

## PART A: Understand what you have (Day 1, about 2 hours)

### Step 1. Run it and explore
```
cd Desktop\CareTrace
python main.py
```
Log in as `dr.rao` / `demo123` and open the **Search & Safety** tab. Switch patients in the top-right dropdown:

| Patient | Flags you should see |
|---|---|
| Asha Verma | HIGH: Amoxicillin prescribed but she is allergic to Penicillin. Trends: HbA1c and Creatinine rising |
| Ravi Kumar | Aspirin + Ibuprofen interaction. Trends: LDL and fasting glucose rising |
| Meena Iyer | Trends: Hemoglobin and Ferritin falling |

Double-click a flag row for the full message and its source.

Now try these questions for Asha:
- `How has her HbA1c changed?`: 3 lab reports, each with its source
- `What is she allergic to?`: the patient profile
- `What medicines is she taking?`: the prescription
- `Who won the cricket match?`: **Not found in records**

Double-click a source in the list to open the full document.

### Step 2. Run the test script
```
python test_search.py
```
It runs 14 questions and prints PASS/FAIL. **Your starting score is 12/14 (86%).** Two cases fail on purpose. You will fix them in Task 1.

### Step 3. Understand the ML in simple words (important for the viva)

**TF-IDF** turns each document into a list of numbers.
- *TF* (term frequency): how often a word appears in this document.
- *IDF* (inverse document frequency): how rare the word is across all documents. A word that appears in every document (like "patient") says little, so it scores low. A word like "HbA1c" appears in few documents, so it scores high.

**Cosine similarity** measures how close the question is to each document. Both are lists of numbers, and cosine measures the angle between them (1 = same direction, 0 = nothing in common).

**Our search = TF-IDF + cosine similarity + a threshold:**
1. Take all documents of the selected patient (plus a small "profile" document with allergies).
2. Convert them and the question into TF-IDF vectors.
3. Score each document. Show the top 3 that score at least `0.10`.
4. If none reaches 0.10: **"Not found in records."** This is our protection against making things up.

**Lab trend = linear regression.** For a test with 3 or more results, we fit a straight line (value against days) with scikit-learn's `LinearRegression`. The slope gives "about +0.19 % per month". A flag appears only when the last 3 values keep moving **and** the latest one is outside the reference range.

**Why rules and not AI for safety flags?** A rule is predictable and explainable: you can always say exactly why a flag appeared. In medicine that matters more than cleverness.

### Step 4. Read `member2_logic.py` in this order
| Part | Read |
|---|---|
| `SYNONYMS` and `_expand()` | Adds words the records actually use (e.g. "allergic" becomes "allergies") |
| `_patient_documents()` | Gets the documents and adds the profile document |
| `search_documents()` | The whole search pipeline (TF-IDF, cosine, threshold, snippets) |
| `ALLERGY_CLASSES`, `INTERACTIONS` | The rule tables |
| `_allergy_flags`, `_duplicate_flags`, `_interaction_flags` | One small function per rule |
| `_trend_flags()` | Regression and the "rising above / falling below" logic |
| `check_safety()` | Joins all rules and sorts HIGH first |

Then skim `member2_search_safety.py`. It only shows what `logic` returns, and it logs `SEARCH`, `SAFETY_CHECK` and `OPEN_SOURCE` to the audit log.

### Step 5. Small experiments (10 minutes)
1. Change `TOP_K = 3` to `1` and ask the HbA1c question again.
2. Change `MATCH_THRESHOLD` to `0.30` and see how many questions become "not found". Set it back to `0.10`.
3. Ask the same question with different wording ("blood sugar trend" vs "HbA1c") and compare the sources.

---

## PART B: Your improvement tasks (Days 2-4)

### TASK 1: Fix the 2 failing questions (20 min)
The two failures:
- `Which drugs was he prescribed?` returned the **patient profile**, because the word "drugs" appears in Ravi's allergy text ("Sulfa drugs").
- `Is she taking iron tablets?` returned **lab reports**, because "iron" is expanded to "hemoglobin ferritin", but the prescription says "Ferrous sulfate".

**Fix (in `member2_logic.py`, inside `SYNONYMS`):** find the line
```python
    "kidney": "creatinine", "iron": "hemoglobin ferritin",
```
and change it to
```python
    "kidney": "creatinine", "iron": "ferrous", "prescribed": "prescription",
```
Run `python test_search.py` again. You should get **14/14 (100%)**.

**Write this in your report:** *"Initial accuracy 86% (12/14). After analysing the 2 failures and improving the query synonyms, accuracy rose to 100% (14/14)."*

> **Be honest in the viva:** 100% on questions you tuned against is not proof that it works everywhere. That is exactly why Task 2 exists.

### TASK 2: Test on NEW questions (30 min, gives you real numbers)
Add **10 new questions** to `CASES` in `test_search.py`. They must be questions you did **not** use while tuning. Include both kinds:
- answers that exist in the records (expected type: `lab_report`, `prescription`, `consult_note` or `patient_profile`)
- questions that should say "not found" (expected `None`)

Run the script and record the score. Expect it to be **lower than 100%**. List every failure and explain why it failed. A failure you can explain scores better in the viva than a perfect score you can't.

Report table template:

| Test set | Questions | Correct | Accuracy |
|---|---|---|---|
| Original (used for tuning) | 14 | | |
| New (never seen) | 10 | | |

### TASK 3: Threshold experiment (20 min)
The threshold decides when the app says "not found". Run `test_search.py` with `MATCH_THRESHOLD` set to `0.05`, `0.10`, `0.15` and `0.20`, and fill in:

| Threshold | Accuracy | What went wrong |
|---|---|---|
| 0.05 | | (too low: nonsense questions get answers) |
| 0.10 | | |
| 0.15 | | |
| 0.20 | | (too high: real questions get "not found") |

This shows you understand the trade-off between **false answers** and **missed answers**. Set the best value back in the file.

### TASK 4: Add a new safety rule (45 min)
**Rule: an NSAID in a patient aged 65 or older.**

**Step 1.** Add this function in `member2_logic.py`, right after `_interaction_flags`:
```python
def _age_flags(patient, meds):
    flags = []
    if patient["age"] is not None and patient["age"] >= 65:
        for m in meds:
            if m["drug"].lower() in ALLERGY_CLASSES["nsaid"]:
                flags.append({"level": "MEDIUM", "kind": "Age",
                              "message": f"{m['drug']} (an NSAID) at age {patient['age']}: higher risk "
                                         f"of stomach bleeding and kidney problems.",
                              "source": _doc_cite(m["source_document_id"])})
    return flags
```
**Step 2.** In `check_safety`, change the `flags = (...)` line to include it:
```python
    flags = (_allergy_flags(patient, meds) + _duplicate_flags(meds)
             + _interaction_flags(meds) + _age_flags(patient, meds) + _trend_flags(pid))
```
**Step 3. Test without the app.** Open a new file `try_rule.py` in the project folder:
```python
import member2_logic as L
print(L._age_flags({"age": 70}, [{"drug": "Ibuprofen", "source_document_id": None}]))
```
Run it. You should see one MEDIUM flag. Change the age to 40 and the list should be empty.

**Step 4 (optional).** Add 3 more pairs to `INTERACTIONS`. Only add pairs you can **verify in a drug reference**, and note the reference in your report.

### TASK 5: Show a flag summary on the screen (20 min)
In `member2_search_safety.py`:

**Step 1.** In `__init__`, right after the Re-check button, add:
```python
self.summary_var = tk.StringVar()
tk.Label(top, textvariable=self.summary_var, bg="white", fg="grey",
         font=("Arial", 10)).pack(side="right", padx=10)
```
**Step 2.** In `run_safety`, right after the line `self.flag_table.delete(...)`, add `self.summary_var.set("")`. Then, right after `flags = logic.check_safety(pid)`, add:
```python
high = sum(1 for f in flags if f["level"] == "HIGH")
self.summary_var.set(f"{high} high, {len(flags) - high} other")
```
**Test:** Asha should show "1 high, 2 other".

### TASK 6: Harder ideas (pick one if you have time)
- **Reduce false answers.** The question "What is his blood pressure?" is correctly "not found" today, but only because the word "pressure" never appears. Think about how to require that *most* of the question's words appear in the records. Measure the effect with `test_search.py`.
- **Show matched words.** Highlight which question words appeared in the snippet.
- **Add a drug dose check** (for example flag a dose that looks too high), but only if you can justify the numbers with a reference.

---

## PART C: Testing checklist
- [ ] `python test_search.py` runs with no errors, and the before/after accuracy is written down
- [ ] Asha shows the Penicillin/Amoxicillin HIGH flag
- [ ] Ravi shows the Aspirin + Ibuprofen flag
- [ ] Meena shows the Hemoglobin and Ferritin trend flags
- [ ] An unrelated question shows "Not found in records"
- [ ] Double-clicking a source opens the full document
- [ ] Switching patients clears the answer and refreshes the flags
- [ ] The Doctor's Audit Log shows `SEARCH`, `SAFETY_CHECK` and `OPEN_SOURCE` entries
- [ ] No red errors in the Command Prompt window

## PART D: Common problems
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: sklearn` | `pip install scikit-learn` |
| Every question says "Not found" | `MATCH_THRESHOLD` is too high, or no patient is selected |
| No flags for any patient | `caretrace.db` is old: close the app, delete it, run again |
| Edited `SYNONYMS` but nothing changed | Save the file, and close and reopen the app |
| `test_search.py` fails to import | Run it from inside the `CareTrace` folder |

## PART E: Viva questions for you
1. What is TF-IDF? Why not just count words?
2. What is cosine similarity?
3. What is the threshold, and what happens if it is too low or too high?
4. How does the app avoid making things up? (retrieval-only answers, citations, "not found")
5. Why are safety flags rules and not an AI model?
6. What does linear regression do in the trend check? What does the slope mean?
7. How did you measure accuracy? What is wrong with testing only on questions you tuned on?
8. What are the limits? (keyword matching, no understanding of meaning, small synthetic data, small interaction table)
9. How would you improve it? (embeddings, a larger interaction database, an LLM only to explain flags, OCR for scanned reports)

## PART F: Hand-over
Send these files to Member 1 by **22 Oct**:
- `member2_logic.py`
- `member2_search_safety.py`
- `test_search.py`

Also send your accuracy tables for the report. Don't edit `db.py`, and keep `refresh()` and the `SearchSafetyPage(parent, app)` signature unchanged.
