# CareTrace: AI-assisted Electronic Medical Record (Tkinter + ML)
Team of 3 | Guide: Dr. Kavitha D | All patient data is **synthetic (fake)**

**Idea:** a desktop EMR where the AI never works without evidence or oversight. Every search answer cites its source record, safety flags come from clear rules, and every AI-written note stays a draft until a Doctor approves it.

READ THIS FIRST (everyone), then open your own steps file.

---

## 1. Who builds what
| Member | Files | What you build |
|---|---|---|
| **1** | `member1_login.py`, `member1_patient_audit.py`, `main.py`, `db.py`, `common.py` | Login + roles (Doctor/Nurse), lockout, audit log, patient picker, app shell, database. **Already working: you extend it.** |
| **2** | `member2_search_safety.py`, `member2_logic.py`, `test_search.py` | **Cited search:** TF-IDF + cosine similarity over the patient's documents, results show the source document, and "not found in records" when the match is weak. **Safety rules:** allergy vs drug, duplicate drug, a small table of known interacting pairs. **Lab trend:** flag a test that worsens across 3 visits (regression slope). |
| **3** | `member3_timeline_scribe.py` | **Timeline:** all documents, labs and prescriptions in date order. **Lab chart** (matplotlib) with the reference range and abnormal points highlighted. **AI scribe:** paste a consultation transcript, create a draft SOAP note from keyword rules and templates, a Doctor edits and approves it (a Nurse cannot). |

Each member has a detailed steps file (`MEMBER1_STEPS.md`, `MEMBER2_STEPS.md`; Member 3's is coming). **Member 2's page is already built and working**, and Member 3's page is a placeholder that already runs, so the whole app works from day one.

## 2. Setup (everyone, once)
1. `python --version` must show 3.9 or higher (install from python.org, tick "Add Python to PATH").
2. `python -m tkinter` should open a small test window.
3. Copy the whole `caretrace` folder to your Desktop.
4. In Command Prompt:
   ```
   cd Desktop\caretrace
   pip install -r requirements.txt
   python main.py
   ```
5. Log in with `dr.rao` / `demo123` (Doctor) or `nurse.mala` / `demo123` (Nurse).

## 3. Rules
1. **Only edit your own files.** Need a change elsewhere? Message the owner.
2. Do not rename anything in the contracts below.
3. Keep a backup of your file before big edits.
4. Delete `caretrace.db` when you want to reset to fresh demo data.

## 4. Contracts (what every page can rely on)
Every page class is `PageName(parent, app)` and has a **`refresh()`** method. It reads:
```python
self.app.user                  # {"username": ..., "name": ..., "role": "Doctor" or "Nurse"}
self.app.current_patient_id    # int, or None
```
`main.py` calls `refresh()` on every page whenever the selected patient changes.

**Log important actions** (the Doctor sees them in the Audit Log tab):
```python
db.log_action(self.app.user["username"], "APPROVE_NOTE", f"note:{note_id}")
```

### Database helpers (`db.py`)
```python
db.query("SELECT ... WHERE patient_id = ?", (pid,))   # returns a list of dicts
db.execute("INSERT ...", (...))                        # returns the new row id
db.get_patient(pid)                                    # dict with name, age, sex, allergies
```
### Tables
| Table | Columns |
|---|---|
| patients | id, name, age, sex, allergies |
| documents | id, patient_id, type (`lab_report` / `prescription` / `consult_note`), text, doc_date, upload_time |
| observations | id, patient_id, test, value, unit, ref_low, ref_high, obs_date, source_document_id |
| medications | id, patient_id, drug, dose, frequency, start_date, source_document_id |
| notes | id, patient_id, text, status (`draft` / `approved`), created_time, approved_by |
| audit_log | id, user, action, target, time |
| users | username, name, role, password (hashed) |

Every observation and medication keeps a `source_document_id`. **That field is what makes citations possible.**

### Built-in demo cases (so the safety checks have something to find)
- **Asha Verma:** Penicillin allergy **and** prescribed Amoxicillin (allergy conflict). HbA1c rising 6.9, 7.4, 8.1.
- **Ravi Kumar:** Aspirin + Ibuprofen together (interaction). LDL rising 130, 150, 172.
- **Meena Iyer:** Hemoglobin falling 11.2, 10.8, 10.1 (worsening trend).

## 3b. Same libraries for everyone
`scikit-learn` and `matplotlib` (installed by `requirements.txt`). `sqlite3` comes with Python.

## 5. Timeline (keep 24 Oct as your own deadline)
| Date | Plan |
|---|---|
| 19-20 Oct | Setup, run the app, read the code, start your tasks |
| 21-22 Oct | Finish your tasks and test them alone |
| 22 Oct | Send your file(s) to Member 1 |
| 23 Oct | Merge, delete `caretrace.db`, test together |
| 24 Oct | Screenshots, report, viva practice |

## 6. Final test checklist
- [ ] Login works for Doctor and Nurse, and the Nurse has no Audit tab
- [ ] Switching patients updates every tab
- [ ] Search answers show the source document and say "not found" for unrelated questions
- [ ] Asha shows an allergy flag, Ravi an interaction flag, Meena a worsening trend
- [ ] Lab chart draws with the reference range
- [ ] A scribe note stays a draft until a Doctor approves it; a Nurse cannot approve
- [ ] The Audit Log shows logins, patient views and approvals
- [ ] Restart the app: saved notes are still there

## 7. Honest limits (say these in the viva, they earn respect)
- It is decision support, **not** diagnosis.
- It uses synthetic data only. A real system would need encryption, consent and compliance review.
- Search uses TF-IDF (keywords), not deep language understanding. A bigger version could use embeddings and an LLM.
- The scribe is rule-based. An LLM would write better notes, but needs an API key and internet.

## 8. Viva questions (everyone)
1. What problem does CareTrace solve?
2. How do you stop the AI from making things up? (retrieval-only answers, citations, "not found")
3. Who is responsible for AI output? (the Doctor approves everything)
4. What is TF-IDF and cosine similarity?
5. How do the three modules connect? (`main.py`, `refresh()`, shared `app.user` and `current_patient_id`)
6. Why SQLite? Why is there an audit log?
7. What would you improve? (embeddings, OCR for scanned reports, FHIR format, encryption)
