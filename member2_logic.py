"""
member2_logic.py  -  MEMBER 2   (pure Python logic: NO tkinter in this file)

1. search_documents()  cited search: TF-IDF + cosine similarity over one patient's records
2. check_safety()      allergy, duplicate-drug, drug-interaction and lab-trend flags
The screen (member2_search_safety.py) only calls these two functions.

SAFETY NOTE: the interaction table below is a small DEMO table of well-known pairs.
It is decision support for a college project, not clinical advice. Cross-check pairs
against a drug reference (for example Stockley's Drug Interactions or the WHO Essential Medicines
List) and mention that reference in your report.
"""

import re
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.linear_model import LinearRegression
from sklearn.metrics.pairwise import cosine_similarity

import db

# ================================================================== #
# PART 1: CITED SEARCH
# ================================================================== #
MATCH_THRESHOLD = 0.10     # below this the answer is "not found in records"
TOP_K = 3                  # how many source documents to show

STOP_WORDS = list(ENGLISH_STOP_WORDS | {"patient", "show", "tell", "give"})

# Query expansion: add the words that actually appear in the records
SYNONYMS = {
    "allergic": "allergies", "allergy": "allergies",
    "medicine": "prescription", "medicines": "prescription", "medication": "prescription",
    "medications": "prescription", "drug": "prescription", "drugs": "prescription",
    "tablet": "prescription", "tablets": "prescription",
    "sugar": "hba1c glucose", "diabetes": "hba1c glucose",
    "cholesterol": "ldl", "anemia": "hemoglobin ferritin", "anaemia": "hemoglobin ferritin",
    "kidney": "creatinine", "iron": "ferrous", "prescribed": "prescription",
}


def cite(doc):
    """Text used as the citation, e.g.  [Doc #3 | lab_report | 2026-07-15]"""
    if doc.get("id") in (None, 0):
        return "[Patient profile]"
    return f"[Doc #{doc['id']} | {doc['type']} | {doc['doc_date']}]"


def _patient_documents(pid):
    """All documents of the patient + a virtual 'profile' document (so allergies are searchable)."""
    docs = db.query("SELECT * FROM documents WHERE patient_id = ? ORDER BY doc_date", (pid,))
    p = db.get_patient(pid)
    if p:
        allergies = p["allergies"] or "none recorded"
        docs.append({"id": 0, "patient_id": pid, "type": "patient_profile", "doc_date": "",
                     "text": f"Patient profile. Name: {p['name']}. Age: {p['age']}. "
                             f"Sex: {p['sex']}. Allergies: {allergies}."})
    return docs


def _expand(question):
    words = re.findall(r"[a-z0-9]+", question.lower())
    extra = [SYNONYMS[w] for w in words if w in SYNONYMS]
    return question + " " + " ".join(extra)


def _best_sentences(text, query_terms, n=2):
    """Pick the sentences of a document that contain the query words."""
    sentences = re.split(r"(?<=\.)\s+(?=[A-Z])", text)
    scored = []
    for i, s in enumerate(sentences):
        hits = sum(1 for t in query_terms if t in s.lower())
        scored.append((hits, i, s))
    best = sorted([x for x in scored if x[0] > 0], key=lambda x: (-x[0], x[1]))[:n]
    if not best:
        return " ".join(sentences[:n])
    return " ".join(s for _, _, s in sorted(best, key=lambda x: x[1]))


def search_documents(pid, question, top_k=TOP_K, threshold=MATCH_THRESHOLD):
    """
    Returns a list of results (best first). Empty list = "not found in records".
    Each result: {"doc": <document dict>, "score": 0..1, "snippet": str, "citation": str}
    """
    docs = _patient_documents(pid)
    if not docs or not question.strip():
        return []

    vec = TfidfVectorizer(stop_words=STOP_WORDS, ngram_range=(1, 2), sublinear_tf=True)
    try:
        matrix = vec.fit_transform([d["text"] for d in docs])
    except ValueError:                     # empty vocabulary
        return []
    q = vec.transform([_expand(question)])
    scores = cosine_similarity(q, matrix)[0]

    terms = [t for t in re.findall(r"[a-z0-9]+", _expand(question).lower())
             if t not in STOP_WORDS and len(t) > 1]
    results = []
    for idx in np.argsort(scores)[::-1][:top_k]:
        if scores[idx] < threshold:
            break
        d = docs[idx]
        if d["type"] == "prescription":      # show the drug lines, not the heading
            snippet = " ".join(re.split(r"(?<=\.)\s+(?=[A-Z])", d["text"])[2:])
        else:
            snippet = _best_sentences(d["text"], terms)
        results.append({"doc": d, "score": float(scores[idx]),
                        "snippet": snippet, "citation": cite(d)})
    return results


# ================================================================== #
# PART 2: SAFETY CHECKS (rules decide, the screen only explains)
# ================================================================== #
ALLERGY_CLASSES = {
    "penicillin": {"penicillin", "amoxicillin", "ampicillin", "piperacillin", "cloxacillin",
                   "flucloxacillin"},
    "sulfa": {"sulfamethoxazole", "cotrimoxazole", "co-trimoxazole", "sulfasalazine", "sulfadiazine"},
    "nsaid": {"ibuprofen", "diclofenac", "naproxen", "aspirin", "ketorolac", "indomethacin"},
    "aspirin": {"aspirin"},
}

# (drug A, drug B): (level, what can happen)
INTERACTIONS = {
    ("aspirin", "ibuprofen"): ("MEDIUM", "Ibuprofen can weaken aspirin's heart-protective effect and adds to stomach bleeding risk."),
    ("aspirin", "warfarin"): ("HIGH", "Higher risk of bleeding."),
    ("ibuprofen", "warfarin"): ("HIGH", "Higher risk of bleeding."),
    ("ciprofloxacin", "warfarin"): ("MEDIUM", "Can raise warfarin effect (INR) and bleeding risk."),
    ("clopidogrel", "omeprazole"): ("MEDIUM", "Omeprazole may reduce the effect of clopidogrel."),
    ("clarithromycin", "simvastatin"): ("HIGH", "Raised statin level: risk of serious muscle damage."),
    ("atorvastatin", "clarithromycin"): ("MEDIUM", "Raised statin level: risk of muscle damage."),
    ("nitroglycerin", "sildenafil"): ("HIGH", "Severe fall in blood pressure."),
    ("lisinopril", "spironolactone"): ("MEDIUM", "Risk of high potassium."),
    ("lisinopril", "potassium chloride"): ("MEDIUM", "Risk of high potassium."),
    ("amiodarone", "digoxin"): ("HIGH", "Raised digoxin level: risk of toxicity."),
    ("ibuprofen", "methotrexate"): ("HIGH", "Raised methotrexate level: risk of toxicity."),
    ("fluoxetine", "tramadol"): ("HIGH", "Risk of serotonin syndrome and seizures."),
    ("ciprofloxacin", "glibenclamide"): ("MEDIUM", "Risk of low blood sugar."),
    ("amlodipine", "simvastatin"): ("MEDIUM", "Raised simvastatin level: dose limit applies."),
}

LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _doc_cite(doc_id):
    rows = db.query("SELECT * FROM documents WHERE id = ?", (doc_id,)) if doc_id else []
    return cite(rows[0]) if rows else ""


def _allergy_flags(patient, meds):
    flags = []
    for raw in re.split(r"[,;]", patient["allergies"] or ""):
        allergy = raw.strip().lower()
        if not allergy:
            continue
        key = next((k for k in ALLERGY_CLASSES if k in allergy), None)
        risky = ALLERGY_CLASSES.get(key, set()) | {allergy}
        for m in meds:
            if m["drug"].lower() in risky:
                flags.append({"level": "HIGH", "kind": "Allergy",
                              "message": f"{m['drug']} prescribed but the patient is allergic to {raw.strip()}.",
                              "source": _doc_cite(m["source_document_id"])})
    return flags


def _duplicate_flags(meds):
    seen, flags = {}, []
    for m in meds:
        name = m["drug"].lower()
        if name in seen:
            flags.append({"level": "MEDIUM", "kind": "Duplicate",
                          "message": f"{m['drug']} appears more than once in the prescriptions.",
                          "source": _doc_cite(m["source_document_id"])})
        seen[name] = True
    return flags


def _interaction_flags(meds):
    names = {m["drug"].lower(): m for m in meds}
    flags = []
    for (a, b), (level, msg) in INTERACTIONS.items():
        if a in names and b in names:
            flags.append({"level": level, "kind": "Interaction",
                          "message": f"{names[a]['drug']} + {names[b]['drug']}: {msg}",
                          "source": _doc_cite(names[a]["source_document_id"])})
    return flags


def _trend_flags(pid):
    """Flag a lab test that keeps moving further out of its reference range over 3+ visits."""
    rows = db.query("SELECT * FROM observations WHERE patient_id = ? ORDER BY test, obs_date", (pid,))
    by_test = {}
    for r in rows:
        by_test.setdefault(r["test"], []).append(r)

    flags = []
    for test, obs in by_test.items():
        if len(obs) < 3:
            continue
        values = [o["value"] for o in obs]
        last3 = values[-3:]
        rising = last3[0] < last3[1] < last3[2]
        falling = last3[0] > last3[1] > last3[2]
        last = obs[-1]
        above = rising and last["ref_high"] is not None and last["value"] > last["ref_high"]
        below = falling and last["ref_low"] is not None and last["value"] < last["ref_low"]
        if not (above or below):
            continue

        # simple linear regression: value vs days since the first visit
        d0 = datetime.strptime(obs[0]["obs_date"], "%Y-%m-%d")
        days = np.array([(datetime.strptime(o["obs_date"], "%Y-%m-%d") - d0).days for o in obs]).reshape(-1, 1)
        slope_per_month = float(LinearRegression().fit(days, values).coef_[0]) * 30

        direction = "rising above" if above else "falling below"
        flags.append({"level": "MEDIUM", "kind": "Trend",
                      "message": (f"{test} is {direction} the reference range "
                                  f"({last['ref_low']}-{last['ref_high']} {last['unit']}): "
                                  f"{' -> '.join(str(v) for v in values)} over {len(obs)} visits "
                                  f"(about {slope_per_month:+.2f} {last['unit']} per month)."),
                      "source": _doc_cite(last["source_document_id"])})
    return flags


def check_safety(pid):
    """Returns a list of flags (HIGH first). Each flag: level, kind, message, source."""
    patient = db.get_patient(pid)
    if patient is None:
        return []
    meds = db.query("SELECT * FROM medications WHERE patient_id = ?", (pid,))
    flags = (_allergy_flags(patient, meds) + _duplicate_flags(meds)
             + _interaction_flags(meds) + _trend_flags(pid))
    return sorted(flags, key=lambda f: LEVEL_ORDER[f["level"]])
