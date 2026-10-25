"""
patient_audit_pages.py  -  patient details and audit log screens
PatientInfoPage : shows the selected patient + Add Patient dialog
AuditPage       : audit log viewer with action filter (Doctor only; main.py hides it for Nurses)

Both pages need a  refresh()  method (main.py calls it when the patient changes).
"""

import tkinter as tk
from tkinter import ttk, messagebox

import db
from common import NAVY, GREEN, RED


class PatientInfoPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="white", padx=25, pady=20)
        self.app = app
        self.vars = {k: tk.StringVar(value="-") for k in ("name", "age_sex", "allergies", "counts")}

        tk.Label(self, text="Patient details", font=("Arial", 14, "bold"), bg="white", fg=NAVY
                 ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        rows = [("Name:", "name", "black"), ("Age / Sex:", "age_sex", "black"),
                ("Allergies:", "allergies", RED), ("On record:", "counts", "black")]
        for i, (label, key, colour) in enumerate(rows, start=1):
            tk.Label(self, text=label, bg="white", font=("Arial", 11)).grid(row=i, column=0, sticky="nw", pady=6)
            tk.Label(self, textvariable=self.vars[key], bg="white", fg=colour, justify="left",
                     font=("Arial", 11, "bold")).grid(row=i, column=1, sticky="w", padx=15, pady=6)

        tk.Button(self, text="+ Add new patient", command=self.open_add_dialog, bg=GREEN, fg="white",
                  font=("Arial", 11, "bold")).grid(row=6, column=0, columnspan=2, sticky="w", pady=25)
        self.refresh()

    def refresh(self):
        pid = self.app.current_patient_id
        patient = db.get_patient(pid) if pid is not None else None
        if patient is None:
            for v in self.vars.values():
                v.set("-")
            return
        c = db.patient_counts(pid)
        self.vars["name"].set(patient["name"])
        self.vars["age_sex"].set(f"{patient['age']} / {patient['sex']}")
        self.vars["allergies"].set(patient["allergies"] or "None recorded")
        self.vars["counts"].set(f"{c['documents']} documents, {c['observations']} lab values, "
                                f"{c['medications']} medications, {c['notes']} notes")

    # ---------------- add patient ---------------- #
    def open_add_dialog(self):
        win = tk.Toplevel(self)
        win.title("Add patient")
        win.config(bg="white", padx=20, pady=20)

        name_var, age_var = tk.StringVar(), tk.StringVar()
        sex_var, allergy_var = tk.StringVar(value="F"), tk.StringVar()

        fields = [("Name:", tk.Entry(win, textvariable=name_var, width=30)),
                  ("Age:", tk.Entry(win, textvariable=age_var, width=30)),
                  ("Sex:", ttk.Combobox(win, textvariable=sex_var, state="readonly", width=27,
                                        values=["F", "M", "Other"])),
                  ("Allergies (comma separated):", tk.Entry(win, textvariable=allergy_var, width=30))]
        for i, (label, widget) in enumerate(fields):
            tk.Label(win, text=label, bg="white").grid(row=i, column=0, sticky="w", pady=6)
            widget.grid(row=i, column=1, pady=6, padx=8)

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required.", parent=win)
                return
            if not age_var.get().strip().isdigit() or not 0 <= int(age_var.get()) <= 120:
                messagebox.showerror("Error", "Age must be a number from 0 to 120.", parent=win)
                return
            pid = db.add_patient(name, int(age_var.get()), sex_var.get(), allergy_var.get().strip())
            db.log_action(self.app.user["username"], "ADD_PATIENT", f"patient:{pid}")
            win.destroy()
            self.app.reload_patients(select_id=pid)

        tk.Button(win, text="Save", command=save, bg=NAVY, fg="white", font=("Arial", 11, "bold"),
                  width=10).grid(row=4, column=0, columnspan=2, pady=12)


class AuditPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="white", padx=10, pady=10)
        self.app = app

        # ---- filter bar (created BEFORE the table, because refresh() uses it)
        self.filter_var = tk.StringVar(value="All")
        top = tk.Frame(self, bg="white")
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="Action:", bg="white").pack(side="left")
        box = ttk.Combobox(top, textvariable=self.filter_var, state="readonly", width=18,
                           values=["All", "LOGIN_OK", "LOGIN_FAIL", "LOGOUT", "AUTO_LOGOUT", "REGISTER",
                                   "CHANGE_PASSWORD", "VIEW_PATIENT", "ADD_PATIENT", "SEARCH",
                                   "SAFETY_CHECK", "OPEN_SOURCE", "DRAFT_NOTE", "SAVE_NOTE", "EDIT_NOTE",
                                   "APPROVE_NOTE", "APPROVE_DENIED"])
        box.pack(side="left", padx=6)
        box.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # ---- table
        cols = ("time", "user", "action", "target")
        self.table = ttk.Treeview(self, columns=cols, show="headings", height=18)
        widths = {"time": 150, "user": 120, "action": 140, "target": 220}
        for c in cols:
            self.table.heading(c, text=c.title())
            self.table.column(c, width=widths[c], anchor="w")
        self.table.tag_configure("fail", foreground="#c0392b")     # failed logins in red
        self.table.pack(fill="both", expand=True)

        tk.Button(self, text="Refresh", command=self.refresh, bg=NAVY, fg="white",
                  font=("Arial", 10, "bold"), width=10).pack(anchor="e", pady=6)
        self.refresh()

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for r in db.get_audit():
            if self.filter_var.get() not in ("All", r["action"]):
                continue
            tag = ("fail",) if r["action"] == "LOGIN_FAIL" else ()
            self.table.insert("", "end", tags=tag,
                              values=(r["time"], r["user"], r["action"], r["target"]))
