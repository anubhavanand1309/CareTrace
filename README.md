# CareTrace: AI-assisted Electronic Medical Record

A desktop EMR built with **Python (Tkinter)**, **scikit-learn** and **SQLite**.
Its main idea: the AI never works without evidence or oversight. Every search answer cites its
source record, safety flags come from clear rules, and every AI-written note stays a draft until
a Doctor approves it.

> Educational project. All patient data is **synthetic (fake)**. Not for clinical use.

## Features
- **Login and roles:** Doctor and Nurse accounts, salted PBKDF2 password hashing, lockout after 3 wrong attempts, auto-logout after 5 minutes
- **Cited search:** TF-IDF + cosine similarity over a patient's records; shows the source document and match score; says "Not found in records" when unsure
- **Safety checks:** allergy vs drug, duplicate drugs, known drug interactions, and worsening lab trends (linear regression)
- **Timeline and lab charts:** all records in date order, abnormal values in red, chart with the normal range shaded
- **AI scribe:** rule-based draft SOAP note from a consultation transcript; only a Doctor can approve, and approved notes are locked
- **Audit log:** every login, patient view, search, draft and approval is recorded (Doctor only)

## Screenshots
| | |
|---|---|
| ![Search and safety](docs/screenshots/search_safety.png) | ![Timeline and chart](docs/screenshots/timeline.png) |
| ![Audit log](docs/screenshots/audit_log.png) | ![AI scribe](docs/screenshots/ai_scribe.png) |

## Run it
Requires Python 3.9+ (Tkinter comes with the standard Windows installer).
```
git clone https://github.com/anubhavanand1309/CareTrace.git
cd CareTrace
pip install -r requirements.txt
python main.py
```
Demo logins (password `demo123`): `dr.rao` (Doctor), `nurse.mala` (Nurse).
Demo data is created automatically the first time. Delete `caretrace.db` to reset it.

## Project structure
```
main.py                    app window, tabs, shared user and selected patient
db.py                      SQLite layer, users, audit log, synthetic demo data
common.py                  colours and constants
login_page.py              login and register screen
patient_audit_pages.py     patient details and audit log screens
search_safety_logic.py     cited search, safety rules, lab trends (no GUI code)
search_safety_page.py      Search & Safety screen
timeline_scribe_logic.py   timeline, lab series, SOAP scribe, note approval (no GUI code)
timeline_scribe_page.py    Timeline & Scribe screen
test_search.py             measures search accuracy
threshold_test.py          threshold experiment
```
Each feature has a `*_logic.py` file with no GUI code (easy to test) and a `*_page.py` file that only draws the screen.

## Results
| Test set | Questions | Correct | Accuracy |
|---|---|---|---|
| Used while tuning | 14 | 14 | 100% |
| New, unseen | 10 | 8 | 80% |

Run `python test_search.py` to reproduce.

## Limits and future work
- Search matches words, not meaning (for example "tired" does not match "tiredness")
- Synthetic data only; small drug-interaction table; the scribe uses rules, not an LLM
- Future: word embeddings, OCR for scanned reports, a larger drug database, encryption, and an LLM used only to explain flags

## Author
Anubhav Anand, SRM KTR (guide: Dr. Kavitha D)
