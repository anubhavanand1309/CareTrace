"""
search_safety_page.py  -  Search & Safety screen   (the logic is in search_safety_logic.py)

Shows:  1) safety flags for the selected patient
        2) "Ask the records": cited search (answer + source documents)

Contract:  class SearchSafetyPage(parent, app)  with a  refresh()  method.
Reads:     self.app.current_patient_id, self.app.user
"""

import tkinter as tk
from tkinter import ttk, messagebox

import db
import search_safety_logic as logic
from common import NAVY

LEVEL_COLOURS = {"HIGH": "#c0392b", "MEDIUM": "#d68910", "LOW": "#555555"}


class SearchSafetyPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="white", padx=15, pady=10)
        self.app = app
        self.results = []
        self.question_var = tk.StringVar()

        # ---------------- safety section ----------------
        top = tk.Frame(self, bg="white")
        top.pack(fill="x")
        tk.Label(top, text="Safety checks", font=("Arial", 13, "bold"), bg="white", fg=NAVY).pack(side="left")
        tk.Button(top, text="Re-check", command=lambda: self.run_safety(log=True), bg=NAVY, fg="white",
                  font=("Arial", 9, "bold")).pack(side="right")

        cols = ("level", "kind", "message", "source")
        self.flag_table = ttk.Treeview(self, columns=cols, show="headings", height=6)
        widths = {"level": 70, "kind": 90, "message": 480, "source": 190}
        for c in cols:
            self.flag_table.heading(c, text=c.title())
            self.flag_table.column(c, width=widths[c], anchor="w")
        for level, colour in LEVEL_COLOURS.items():
            self.flag_table.tag_configure(level, foreground=colour)
        self.flag_table.bind("<Double-Button-1>", self.show_flag)
        self.flag_table.pack(fill="x", pady=4)
        tk.Label(self, text="Flags come from fixed rules (not AI guesses). Double-click a row for details. "
                            "A Doctor makes every decision.", bg="white", fg="grey",
                 font=("Arial", 9)).pack(anchor="w")

        # ---------------- search section ----------------
        tk.Label(self, text="Ask the records", font=("Arial", 13, "bold"), bg="white", fg=NAVY
                 ).pack(anchor="w", pady=(12, 0))
        row = tk.Frame(self, bg="white")
        row.pack(fill="x", pady=4)
        entry = tk.Entry(row, textvariable=self.question_var, font=("Arial", 11))
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.ask())
        tk.Button(row, text="Ask", command=self.ask, bg=NAVY, fg="white",
                  font=("Arial", 10, "bold"), width=8).pack(side="left", padx=6)

        self.answer = tk.Text(self, height=8, wrap="word", font=("Arial", 10), bg="#fafafa", state="disabled")
        self.answer.pack(fill="x")

        tk.Label(self, text="Sources (double-click to open the full document):", bg="white",
                 fg="grey", font=("Arial", 9)).pack(anchor="w", pady=(6, 0))
        self.source_list = tk.Listbox(self, height=3, font=("Arial", 10))
        self.source_list.pack(fill="x")
        self.source_list.bind("<Double-Button-1>", self.open_source)

        self.refresh()

    # ---------------------------------------------------------- #
    def refresh(self):
        """Called by main.py whenever the selected patient changes."""
        self.results = []
        self.question_var.set("")
        self._set_answer("")
        self.source_list.delete(0, "end")
        self.run_safety(log=False)

    # ---------------- safety ---------------- #
    def run_safety(self, log=True):
        self.flag_table.delete(*self.flag_table.get_children())
        pid = self.app.current_patient_id
        if pid is None:
            return
        flags = logic.check_safety(pid)
        if not flags:
            self.flag_table.insert("", "end", values=("OK", "-", "No safety flags found.", ""))
        for f in flags:
            self.flag_table.insert("", "end", tags=(f["level"],),
                                   values=(f["level"], f["kind"], f["message"], f["source"]))
        if log and self.app.user:
            db.log_action(self.app.user["username"], "SAFETY_CHECK", f"patient:{pid}")

    def show_flag(self, event=None):
        selected = self.flag_table.selection()
        if selected:
            level, kind, message, source = self.flag_table.item(selected[0], "values")
            messagebox.showinfo(f"{level}: {kind}", f"{message}\n\nSource: {source or '-'}")

    # ---------------- search ---------------- #
    def ask(self):
        pid = self.app.current_patient_id
        question = self.question_var.get().strip()
        if pid is None:
            messagebox.showerror("Error", "Select a patient first.")
            return
        if len(question.split()) < 2:
            messagebox.showerror("Error", "Type a question (at least 2 words).")
            return

        self.results = logic.search_documents(pid, question)
        db.log_action(self.app.user["username"], "SEARCH", f"patient:{pid}")
        self.source_list.delete(0, "end")

        if not self.results:
            self._set_answer("Not found in records.\n\nNothing in this patient's documents matches the "
                             "question closely enough, so no answer is given.")
            return

        parts = []
        for r in self.results:
            parts.append(f"- {r['snippet']}\n  Source: {r['citation']}   (match {r['score'] * 100:.0f}%)")
            self.source_list.insert("end", r["citation"])
        self._set_answer("\n\n".join(parts))

    def open_source(self, event=None):
        selected = self.source_list.curselection()
        if not selected:
            return
        r = self.results[selected[0]]
        db.log_action(self.app.user["username"], "OPEN_SOURCE", r["citation"])
        win = tk.Toplevel(self)
        win.title(r["citation"])
        box = tk.Text(win, wrap="word", width=70, height=10, font=("Arial", 11))
        box.insert("1.0", r["doc"]["text"])
        box.config(state="disabled")
        box.pack(padx=10, pady=10)

    def _set_answer(self, text):
        self.answer.config(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", text)
        self.answer.config(state="disabled")
