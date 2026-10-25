"""
db.py  -  database layer for CareTrace (SQLite).

Every module imports from here. All data is SYNTHETIC (fake): never put real
patient data in this project.
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "caretrace.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY, name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Doctor','Nurse')), password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
    age INTEGER, sex TEXT, allergies TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL,
    type TEXT, text TEXT, doc_date TEXT, upload_time TEXT);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL,
    test TEXT, value REAL, unit TEXT, ref_low REAL, ref_high REAL,
    obs_date TEXT, source_document_id INTEGER);
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL,
    drug TEXT, dose TEXT, frequency TEXT, start_date TEXT, source_document_id INTEGER);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL,
    text TEXT, status TEXT DEFAULT 'draft', created_time TEXT, approved_by TEXT);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, target TEXT, time TEXT);
"""


# ------------------------------------------------------------------ #
# basic helpers
# ------------------------------------------------------------------ #
def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql, params=()):
    """Run a SELECT and return a list of dicts."""
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE. Returns the new row id."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# passwords + users
# ------------------------------------------------------------------ #
def hash_pw(pw, salt=None):
    """Salted PBKDF2 hash. Stored as  salt$hash  (never the real password)."""
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def check_pw(pw, stored):
    salt = stored.split("$", 1)[0]
    return secrets.compare_digest(hash_pw(pw, salt), stored)


def add_user(username, name, role, pw):
    """Returns True if created, False if the username already exists."""
    try:
        execute("INSERT INTO users VALUES (?,?,?,?)", (username, name, role, hash_pw(pw)))
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username, pw):
    """Returns {"username","name","role"} if the login is right, else None."""
    rows = query("SELECT * FROM users WHERE username = ?", (username,))
    if rows and check_pw(pw, rows[0]["password"]):
        r = rows[0]
        return {"username": r["username"], "name": r["name"], "role": r["role"]}
    return None


def change_password(username, old_pw, new_pw):
    """Returns True if the old password was right and the new one was saved."""
    if verify_user(username, old_pw) is None:
        return False
    execute("UPDATE users SET password = ? WHERE username = ?", (hash_pw(new_pw), username))
    return True


# ------------------------------------------------------------------ #
# patients
# ------------------------------------------------------------------ #
def list_patients():
    return query("SELECT * FROM patients ORDER BY id")


def get_patient(pid):
    rows = query("SELECT * FROM patients WHERE id = ?", (pid,))
    return rows[0] if rows else None


def add_patient(name, age, sex, allergies=""):
    return execute("INSERT INTO patients (name, age, sex, allergies) VALUES (?,?,?,?)",
                   (name, age, sex, allergies))


def patient_counts(pid):
    out = {}
    for table in ("documents", "observations", "medications", "notes"):
        out[table] = query(f"SELECT COUNT(*) AS n FROM {table} WHERE patient_id = ?", (pid,))[0]["n"]
    return out


# ------------------------------------------------------------------ #
# audit log
# ------------------------------------------------------------------ #
def log_action(user, action, target=""):
    """Call this for every important action: LOGIN_OK, VIEW_PATIENT, APPROVE_NOTE ..."""
    execute("INSERT INTO audit_log (user, action, target, time) VALUES (?,?,?,?)",
            (user, action, target, _now()))


def get_audit(limit=300):
    return query("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))


# ------------------------------------------------------------------ #
# create tables + synthetic demo data (only the first time)
# ------------------------------------------------------------------ #
DEMO = [
    {"name": "Asha Verma", "age": 54, "sex": "F", "allergies": "Penicillin",
     "labs": {
         "2026-01-10": [("HbA1c", 6.9, "%", 4.0, 5.6), ("Creatinine", 0.9, "mg/dL", 0.6, 1.1)],
         "2026-04-12": [("HbA1c", 7.4, "%", 4.0, 5.6), ("Creatinine", 1.0, "mg/dL", 0.6, 1.1)],
         "2026-07-15": [("HbA1c", 8.1, "%", 4.0, 5.6), ("Creatinine", 1.2, "mg/dL", 0.6, 1.1)]},
     "rx": ("2026-07-15", [("Metformin", "500 mg", "twice daily"),
                           ("Amoxicillin", "500 mg", "three times daily")]),
     "consult": ("2026-07-15", "Patient reports increased thirst and tiredness for the last "
                 "month. Blood sugar is rising despite diet control. Advised follow-up and a "
                 "repeat HbA1c in three months.")},
    {"name": "Ravi Kumar", "age": 61, "sex": "M", "allergies": "Sulfa drugs",
     "labs": {
         "2026-01-20": [("LDL", 130, "mg/dL", 0, 100), ("Fasting glucose", 98, "mg/dL", 70, 99)],
         "2026-05-02": [("LDL", 150, "mg/dL", 0, 100), ("Fasting glucose", 102, "mg/dL", 70, 99)],
         "2026-08-18": [("LDL", 172, "mg/dL", 0, 100), ("Fasting glucose", 110, "mg/dL", 70, 99)]},
     "rx": ("2026-08-18", [("Atorvastatin", "10 mg", "once daily"),
                           ("Aspirin", "75 mg", "once daily"),
                           ("Ibuprofen", "400 mg", "twice daily")]),
     "consult": ("2026-08-18", "Patient complains of mild chest discomfort on climbing stairs "
                 "and knee pain. Advised a lipid-lowering diet and regular exercise. Review "
                 "in two months.")},
    {"name": "Meena Iyer", "age": 38, "sex": "F", "allergies": "",
     "labs": {
         "2026-02-05": [("Hemoglobin", 11.2, "g/dL", 12.0, 15.5), ("Ferritin", 18, "ng/mL", 15, 150)],
         "2026-05-20": [("Hemoglobin", 10.8, "g/dL", 12.0, 15.5), ("Ferritin", 14, "ng/mL", 15, 150)],
         "2026-09-10": [("Hemoglobin", 10.1, "g/dL", 12.0, 15.5), ("Ferritin", 11, "ng/mL", 15, 150)]},
     "rx": ("2026-09-10", [("Ferrous sulfate", "200 mg", "once daily"),
                           ("Vitamin C", "500 mg", "once daily")]),
     "consult": ("2026-09-10", "Patient reports fatigue, hair fall and breathlessness on "
                 "exertion. Diet advice given. Iron supplements started. Repeat blood tests "
                 "in six weeks.")},
]


def _seed_demo(conn):
    now = _now()
    for username, name, role in (("dr.rao", "Dr. Rao", "Doctor"),
                                 ("nurse.mala", "Nurse Mala", "Nurse")):
        conn.execute("INSERT INTO users VALUES (?,?,?,?)", (username, name, role, hash_pw("demo123")))

    for p in DEMO:
        pid = conn.execute("INSERT INTO patients (name, age, sex, allergies) VALUES (?,?,?,?)",
                           (p["name"], p["age"], p["sex"], p["allergies"])).lastrowid

        for d, rows in p["labs"].items():
            text = f"Lab report {d}. Patient: {p['name']}. " + " ".join(
                f"{t}: {v} {u} (reference {lo}-{hi})." for t, v, u, lo, hi in rows)
            did = conn.execute("INSERT INTO documents (patient_id, type, text, doc_date, upload_time) "
                               "VALUES (?,?,?,?,?)", (pid, "lab_report", text, d, now)).lastrowid
            for t, v, u, lo, hi in rows:
                conn.execute("INSERT INTO observations (patient_id, test, value, unit, ref_low, "
                             "ref_high, obs_date, source_document_id) VALUES (?,?,?,?,?,?,?,?)",
                             (pid, t, v, u, lo, hi, d, did))

        d, drugs = p["rx"]
        text = f"Prescription {d}. Patient: {p['name']}. " + " ".join(
            f"{drug} {dose} {freq}." for drug, dose, freq in drugs)
        did = conn.execute("INSERT INTO documents (patient_id, type, text, doc_date, upload_time) "
                           "VALUES (?,?,?,?,?)", (pid, "prescription", text, d, now)).lastrowid
        for drug, dose, freq in drugs:
            conn.execute("INSERT INTO medications (patient_id, drug, dose, frequency, start_date, "
                         "source_document_id) VALUES (?,?,?,?,?,?)", (pid, drug, dose, freq, d, did))

        d, text = p["consult"]
        conn.execute("INSERT INTO documents (patient_id, type, text, doc_date, upload_time) "
                     "VALUES (?,?,?,?,?)",
                     (pid, "consult_note", f"Consultation note {d}. Patient: {p['name']}. {text}", d, now))


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            _seed_demo(conn)
        conn.commit()
    finally:
        conn.close()
