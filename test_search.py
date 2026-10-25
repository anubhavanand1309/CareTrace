"""
test_search.py  -  measures how good the cited search is.
Run:   python test_search.py
It uses a temporary copy of the demo data, so your real caretrace.db is not touched.

Two test sets are reported separately:
  ORIGINAL : questions used while building / tuning the search
  NEW      : questions the search was NOT tuned on (the honest number)
"""

import os
import tempfile

import db

db.DB_FILE = os.path.join(tempfile.mkdtemp(), "test.db")   # fresh demo data every run
db.init_db()

import search_safety_logic as logic   # noqa: E402  (import after db is set up)

# (patient_id, question, document type that SHOULD be the top result,
#  or None when the answer is NOT in the records and the app should say "not found")
ORIGINAL = [
    (1, "How has her HbA1c changed?", "lab_report"),
    (1, "What is she allergic to?", "patient_profile"),
    (1, "What medicines is she taking?", "prescription"),
    (1, "Does she have thirst or tiredness?", "consult_note"),
    (1, "How is her kidney function?", "lab_report"),
    (2, "What is his cholesterol trend?", "lab_report"),
    (2, "Which drugs was he prescribed?", "prescription"),
    (2, "Does he have chest discomfort?", "consult_note"),
    (3, "What is her hemoglobin?", "lab_report"),
    (3, "Is she taking iron tablets?", "prescription"),
    (1, "Who won the cricket match?", None),
    (2, "What is the weather tomorrow?", None),
    (3, "Does she have a broken leg?", None),
    (2, "What is his blood pressure?", None),
]

NEW = [
    (1, "Is her blood sugar getting worse?", "lab_report"),
    (1, "What is her age?", "patient_profile"),
    (2, "Is he allergic to anything?", "patient_profile"),
    (2, "What is his fasting glucose?", "lab_report"),
    (2, "Does he take aspirin?", "prescription"),
    (3, "Why is she feeling tired?", "consult_note"),
    (3, "What is her ferritin level?", "lab_report"),
    (1, "Does she have a fever?", None),
    (3, "What is her cholesterol?", None),
    (2, "Has he had surgery?", None),
]


def run(name, cases):
    print(f"\n=== {name} ===")
    correct = 0
    for pid, question, expected in cases:
        results = logic.search_documents(pid, question)
        got = results[0]["doc"]["type"] if results else None
        ok = got == expected
        correct += ok
        print(("PASS" if ok else "FAIL"), "|", question, "| expected:", expected, "| got:", got)
    print(f"{name} accuracy: {correct}/{len(cases)} = {correct / len(cases) * 100:.0f}%")
    return correct


if __name__ == "__main__":
    total_ok = run("ORIGINAL", ORIGINAL) + run("NEW", NEW)
    total = len(ORIGINAL) + len(NEW)
    print(f"\nOVERALL: {total_ok}/{total} = {total_ok / total * 100:.0f}%")
