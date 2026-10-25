"""
timeline_scribe_logic.py  -  timeline, lab series, SOAP scribe, note approval   (pure Python logic: NO tkinter in this file)

1. get_timeline()      every document and note of a patient in date order
2. get_lab_series()    lab values over time (for the chart), with HIGH / LOW marks
3. draft_soap()        rule-based AI scribe: transcript -> draft SOAP note
4. save / update / approve notes   (only a Doctor can approve; approved notes are locked)
The screen (timeline_scribe_page.py) only calls these functions.
"""

import re
from datetime import datetime

import db

# ================================================================== #
# lab helpers + timeline
# ================================================================== #
def lab_status(value, low, high):
    """'HIGH', 'LOW' or 'normal' compared with the reference range."""
    if high is not None and value > high:
        return "HIGH"
    if low is not None and value < low:
        return "LOW"
    return "normal"


def get_lab_series(pid):
    """{test name: [ {date, value, unit, low, high, status}, ... oldest first ]}"""
    rows = db.query("SELECT * FROM observations WHERE patient_id = ? ORDER BY test, obs_date", (pid,))
    series = {}
    for r in rows:
        series.setdefault(r["test"], []).append({
            "date": r["obs_date"], "value": r["value"], "unit": r["unit"],
            "low": r["ref_low"], "high": r["ref_high"],
            "status": lab_status(r["value"], r["ref_low"], r["ref_high"])})
    return series


def get_timeline(pid):
    """List of {date, type, summary, abnormal}, newest first (documents + saved notes)."""
    items = []
    for d in db.query("SELECT * FROM documents WHERE patient_id = ?", (pid,)):
        abnormal = False
        if d["type"] == "lab_report":
            obs = db.query("SELECT * FROM observations WHERE source_document_id = ?", (d["id"],))
            parts = []
            for o in obs:
                st = lab_status(o["value"], o["ref_low"], o["ref_high"])
                abnormal = abnormal or st != "normal"
                mark = "" if st == "normal" else f" ({st})"
                parts.append(f"{o['test']} {o['value']} {o['unit']}{mark}")
            summary = ", ".join(parts)
            kind = "Lab report"
        elif d["type"] == "prescription":
            meds = db.query("SELECT * FROM medications WHERE source_document_id = ?", (d["id"],))
            summary = "; ".join(f"{m['drug']} {m['dose']} {m['frequency']}" for m in meds)
            kind = "Prescription"
        else:
            text = d["text"].split("Patient:", 1)[-1]
            text = text.split(".", 1)[-1].strip()
            summary = text[:110] + ("..." if len(text) > 110 else "")
            kind = "Consultation"
        items.append({"date": d["doc_date"], "type": kind, "summary": summary, "abnormal": abnormal})

    for n in list_notes(pid):
        items.append({"date": n["created_time"][:10], "type": f"Note ({n['status']})",
                      "summary": _note_summary(n["text"]), "abnormal": False})
    return sorted(items, key=lambda i: i["date"], reverse=True)


# ================================================================== #
# notes: draft -> save -> doctor approves
# ================================================================== #
DRAFT_HEADER = "DRAFT SOAP NOTE (written by rules, NOT approved)"


def _note_summary(text):
    """Short one-line summary for the timeline: the first bullet points of the note."""
    bullets = [line[2:] for line in text.splitlines() if line.startswith("- ")]
    summary = " | ".join(bullets[:2]) if bullets else text.replace("\n", " ")
    return summary[:110] + ("..." if len(summary) > 110 else "")


def list_notes(pid):
    return db.query("SELECT * FROM notes WHERE patient_id = ? ORDER BY id DESC", (pid,))


def get_note(note_id):
    rows = db.query("SELECT * FROM notes WHERE id = ?", (note_id,))
    return rows[0] if rows else None


def save_note(pid, text):
    """New note, always starts as a DRAFT. Returns the note id."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return db.execute("INSERT INTO notes (patient_id, text, status, created_time) VALUES (?,?, 'draft', ?)",
                      (pid, text, now))


def update_note(note_id, text):
    note = get_note(note_id)
    if note is None:
        raise ValueError("Note not found.")
    if note["status"] == "approved":
        raise ValueError("Approved notes cannot be edited.")
    db.execute("UPDATE notes SET text = ? WHERE id = ?", (text, note_id))


def approve_note(note_id, user):
    """Only a Doctor may approve. After approval the note is locked."""
    if user.get("role") != "Doctor":
        raise PermissionError("Only a Doctor can approve notes.")
    note = get_note(note_id)
    if note is None:
        raise ValueError("Note not found.")
    if note["status"] == "approved":
        raise ValueError("This note is already approved.")
    approved_text = note["text"].replace(
        DRAFT_HEADER, f"SOAP NOTE (drafted by rules, approved by {user.get('name', user['username'])})", 1)
    db.execute("UPDATE notes SET status = 'approved', approved_by = ?, text = ? WHERE id = ?",
               (user["username"], approved_text, note_id))
    return approved_text


# ================================================================== #
# AI scribe (rule-based): transcript -> draft SOAP note
# ================================================================== #
SECTION_WORDS = {
    "S": ("reports", "complains", "complaining", "feels", "feeling", "since", "for the last", "for the past",
          "days", "weeks", "months", "pain", "tired", "fatigue", "cough", "fever", "thirst", "thirsty",
          "nausea", "vomiting", "dizzy", "headache", "breathless", "history", "i have", "my "),
    "O": ("bp", "blood pressure", "pulse", "heart rate", "temperature", "spo2", "oxygen", "weight", "bmi",
          "examination", "on exam", "auscultation", "tender", "swelling", "hba1c", "x-ray", "ecg", "lab"),
    "A": ("likely", "suspect", "suspected", "diagnosis", "diagnosed", "consistent with", "impression",
          "suggests", "probably", "controlled", "uncontrolled", "poorly"),
    "P": ("advise", "advised", "prescribe", "prescribed", "start", "started", "continue", "stop",
          "follow-up", "follow up", "review", "repeat", "refer", "referred", "plan", "recommend",
          "diet", "exercise", "come back", "return"),
}
NUMBER_PATTERN = re.compile(r"\b\d{2,3}/\d{2,3}\b|\b\d+(\.\d+)?\s?(mg/dl|bpm|°c|kg|%)", re.I)
SPEAKER_PATTERN = re.compile(r"^\s*(doctor|dr\.?|patient|nurse)\s*:\s*", re.I)
TIE_ORDER = ["P", "A", "O", "S"]          # who wins when two sections score the same

SAMPLE_TRANSCRIPT = (
    "Patient: I have been feeling very tired for the last two weeks and I am always thirsty.\n"
    "Doctor: Your BP is 130/85 and your pulse is 78. Your HbA1c has been rising over the last visits. "
    "This is likely poorly controlled diabetes. I will continue metformin and advise diet control. "
    "Please repeat the HbA1c after three months and come back for follow-up."
)


def _classify(sentence, said_by_patient):
    scores = {k: 0 for k in SECTION_WORDS}
    low = sentence.lower()
    for section, words in SECTION_WORDS.items():
        scores[section] = sum(1 for w in words if w in low)
    if NUMBER_PATTERN.search(sentence):
        scores["O"] += 2
    if said_by_patient:
        scores["S"] += 2
    best = max(scores.values())
    if best == 0:
        return "S"
    return next(k for k in TIE_ORDER if scores[k] == best)


def draft_soap(pid, transcript):
    """Turn a consultation transcript into a DRAFT SOAP note (text). Rules, not an LLM."""
    patient = db.get_patient(pid)
    sections = {"S": [], "O": [], "A": [], "P": []}
    for raw in re.split(r"(?<=[.?!])\s+|\n+", transcript):
        if len(raw.split()) < 3:
            continue
        by_patient = bool(re.match(r"\s*patient\s*:", raw, re.I))
        sentence = SPEAKER_PATTERN.sub("", raw).strip()
        sections[_classify(sentence, by_patient)].append(sentence)

    def block(title, key):
        lines = sections[key] or ["(nothing recorded in the transcript)"]
        return f"{title}\n" + "\n".join(f"- {s}" for s in lines)

    # context pulled from the chart (not from the transcript)
    series = get_lab_series(pid)
    latest = []
    for test, rows in series.items():
        r = rows[-1]
        mark = "" if r["status"] == "normal" else f" ({r['status']})"
        latest.append(f"{test} {r['value']} {r['unit']}{mark}")
    meds = db.query("SELECT * FROM medications WHERE patient_id = ?", (pid,))
    med_text = "; ".join(f"{m['drug']} {m['dose']} {m['frequency']}" for m in meds) or "none recorded"

    return "\n".join([
        DRAFT_HEADER,
        f"Patient: {patient['name']}, {patient['age']} / {patient['sex']}",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        block("S (Subjective): what the patient says", "S"), "",
        block("O (Objective): measurements and findings", "O"), "",
        block("A (Assessment): the doctor's impression", "A"), "",
        block("P (Plan): what happens next", "P"), "",
        "Records context (auto-added from the chart, please verify):",
        f"- Allergies: {patient['allergies'] or 'none recorded'}",
        f"- Latest results: {', '.join(latest) or 'none'}",
        f"- Current medications: {med_text}",
    ])
