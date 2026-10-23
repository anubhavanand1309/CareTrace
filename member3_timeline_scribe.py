"""
member3_timeline_scribe.py  -  MEMBER 3   (the SCREEN; the brains are in member3_logic.py)

Two sub-tabs:
  Timeline & Labs : all records in date order + a lab chart with the reference range
  AI Scribe       : transcript -> draft SOAP note -> save draft -> a DOCTOR approves

Contract:  class TimelineScribePage(parent, app)  with a  refresh()  method.
Reads:     self.app.current_patient_id, self.app.user  (role = "Doctor" or "Nurse")
"""

import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import db
import member3_logic as logic
from common import NAVY, GREEN, RED


class TimelineScribePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="white")
        self.app = app
        self.series = {}
        self.notes = []
        self.current_note_id = None
        self.current_status = None
        self.test_var = tk.StringVar()
        self.status_var = tk.StringVar(value="No note open")

        inner = ttk.Notebook(self)
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        self.tab_timeline = tk.Frame(inner, bg="white", padx=10, pady=8)
        self.tab_scribe = tk.Frame(inner, bg="white", padx=10, pady=8)
        inner.add(self.tab_timeline, text="  Timeline & Labs  ")
        inner.add(self.tab_scribe, text="  AI Scribe  ")

        self._build_timeline(self.tab_timeline)
        self._build_scribe(self.tab_scribe)
        self.refresh()

    # ---------------------------------------------------------- #
    # building the screens
    # ---------------------------------------------------------- #
    def _build_timeline(self, tab):
        tk.Label(tab, text="Patient timeline", font=("Arial", 13, "bold"), bg="white", fg=NAVY).pack(anchor="w")
        cols = ("date", "type", "details")
        self.timeline_table = ttk.Treeview(tab, columns=cols, show="headings", height=7)
        widths = {"date": 90, "type": 120, "details": 560}
        for c in cols:
            self.timeline_table.heading(c, text=c.title())
            self.timeline_table.column(c, width=widths[c], anchor="w")
        self.timeline_table.tag_configure("abnormal", foreground=RED)
        self.timeline_table.tag_configure("note_draft", foreground="grey")
        self.timeline_table.tag_configure("note_approved", foreground=GREEN)
        self.timeline_table.pack(fill="x", pady=4)
        tk.Label(tab, text="Red = abnormal lab values. Grey = draft note. Green = approved note.",
                 bg="white", fg="grey", font=("Arial", 9)).pack(anchor="w")

        ctrl = tk.Frame(tab, bg="white")
        ctrl.pack(fill="x", pady=(8, 0))
        tk.Label(ctrl, text="Lab chart:", bg="white", font=("Arial", 11, "bold"), fg=NAVY).pack(side="left")
        self.test_box = ttk.Combobox(ctrl, textvariable=self.test_var, state="readonly", width=22)
        self.test_box.pack(side="left", padx=8)
        self.test_box.bind("<<ComboboxSelected>>", lambda e: self.plot_labs())

        self.fig = Figure(figsize=(7.5, 2.6), dpi=90)
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_scribe(self, tab):
        left = tk.Frame(tab, bg="white")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = tk.Frame(tab, bg="white")
        right.pack(side="left", fill="both", expand=True)

        # ---- left: transcript + saved notes
        tk.Label(left, text="Consultation transcript (paste or type)", font=("Arial", 11, "bold"),
                 bg="white", fg=NAVY).pack(anchor="w")
        self.transcript = tk.Text(left, height=9, width=40, wrap="word", font=("Arial", 10))
        self.transcript.pack(fill="x")
        row = tk.Frame(left, bg="white")
        row.pack(fill="x", pady=6)
        tk.Button(row, text="Draft SOAP note", command=self.draft, bg=NAVY, fg="white",
                  font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(row, text="Insert sample", command=self.insert_sample, bg="#555", fg="white",
                  font=("Arial", 10)).pack(side="left", padx=6)
        tk.Button(row, text="Clear", command=self.clear_all, bg="grey", fg="white",
                  font=("Arial", 10)).pack(side="left")

        tk.Label(left, text="Saved notes for this patient (click to open)", font=("Arial", 11, "bold"),
                 bg="white", fg=NAVY).pack(anchor="w", pady=(8, 0))
        self.note_list = tk.Listbox(left, height=6, font=("Arial", 10), exportselection=False)
        self.note_list.pack(fill="x")
        self.note_list.bind("<<ListboxSelect>>", self.open_note)

        # ---- right: editor + buttons
        tk.Label(right, text="Note editor", font=("Arial", 11, "bold"), bg="white", fg=NAVY).pack(anchor="w")
        tk.Label(right, textvariable=self.status_var, bg="white", fg="#d68910",
                 font=("Arial", 10, "bold")).pack(anchor="w")
        self.editor = tk.Text(right, height=17, width=48, wrap="word", font=("Arial", 10), bg="#fafafa")
        self.editor.pack(fill="both", expand=True)
        btns = tk.Frame(right, bg="white")
        btns.pack(fill="x", pady=6)
        tk.Button(btns, text="Save draft", command=self.save_draft, bg=NAVY, fg="white",
                  font=("Arial", 10, "bold")).pack(side="left")
        self.approve_btn = tk.Button(btns, text="Approve (Doctor only)", command=self.approve, bg=GREEN,
                                     fg="white", font=("Arial", 10, "bold"))
        self.approve_btn.pack(side="left", padx=8)
        tk.Label(right, text="The AI only drafts. The note enters the record only after a Doctor approves it.",
                 bg="white", fg="grey", font=("Arial", 9)).pack(anchor="w")

    # ---------------------------------------------------------- #
    # small helpers
    # ---------------------------------------------------------- #
    def _text(self, widget):
        return widget.get("1.0", "end").strip()

    def _set_text(self, widget, text, editable=True):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        if not editable:
            widget.config(state="disabled")

    def _log(self, action, target=""):
        db.log_action(self.app.user["username"], action, target)

    # ---------------------------------------------------------- #
    # refresh (called by main.py when the patient changes)
    # ---------------------------------------------------------- #
    def refresh(self):
        self.current_note_id = None
        self.current_status = None
        self._set_text(self.transcript, "")
        self._set_text(self.editor, "")
        self.status_var.set("No note open")
        is_doctor = bool(self.app.user) and self.app.user["role"] == "Doctor"
        self.approve_btn.config(state="normal" if is_doctor else "disabled")
        self.load_timeline()
        self.load_tests()
        self.load_notes()

    def load_timeline(self):
        self.timeline_table.delete(*self.timeline_table.get_children())
        pid = self.app.current_patient_id
        if pid is None:
            return
        for item in logic.get_timeline(pid):
            tag = ()
            if item["abnormal"]:
                tag = ("abnormal",)
            elif item["type"] == "Note (draft)":
                tag = ("note_draft",)
            elif item["type"] == "Note (approved)":
                tag = ("note_approved",)
            self.timeline_table.insert("", "end", tags=tag,
                                       values=(item["date"], item["type"], item["summary"]))

    def load_tests(self):
        pid = self.app.current_patient_id
        self.series = logic.get_lab_series(pid) if pid is not None else {}
        names = list(self.series)
        self.test_box.config(values=names)
        self.test_var.set(names[0] if names else "")
        self.plot_labs()

    def plot_labs(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        rows = self.series.get(self.test_var.get())
        if not rows:
            ax.text(0.5, 0.5, "No lab data for this patient", ha="center", va="center")
            ax.set_axis_off()
        else:
            xs = list(range(len(rows)))
            values = [r["value"] for r in rows]
            low, high = rows[0]["low"], rows[0]["high"]
            if low is not None and high is not None:
                ax.axhspan(low, high, color="green", alpha=0.15, label=f"normal {low}-{high}")
            ax.plot(xs, values, marker="o", color=NAVY, linewidth=2)
            bad = [i for i, r in enumerate(rows) if r["status"] != "normal"]
            ax.scatter(bad, [values[i] for i in bad], color="red", zorder=5, s=70, label="abnormal")
            ax.set_xticks(xs)
            ax.set_xticklabels([r["date"] for r in rows], fontsize=8)
            ax.set_title(f"{self.test_var.get()} ({rows[0]['unit']})", fontsize=10)
            ax.legend(fontsize=8, loc="best")
        self.fig.tight_layout()
        self.canvas.draw()

    def load_notes(self):
        pid = self.app.current_patient_id
        self.notes = logic.list_notes(pid) if pid is not None else []
        self.note_list.delete(0, "end")
        for n in self.notes:
            self.note_list.insert("end", f"#{n['id']}  {n['status'].upper()}  {n['created_time'][:16]}")

    # ---------------------------------------------------------- #
    # scribe actions
    # ---------------------------------------------------------- #
    def insert_sample(self):
        self._set_text(self.transcript, logic.SAMPLE_TRANSCRIPT)

    def clear_all(self):
        self.current_note_id = None
        self.current_status = None
        self._set_text(self.transcript, "")
        self._set_text(self.editor, "")
        self.status_var.set("No note open")

    def draft(self):
        pid = self.app.current_patient_id
        if pid is None:
            messagebox.showerror("Error", "Select a patient first.")
            return
        transcript = self._text(self.transcript)
        if len(transcript.split()) < 8:
            messagebox.showerror("Error", "Paste or type a consultation transcript first (at least 8 words).")
            return
        self.current_note_id = None
        self.current_status = None
        self._set_text(self.editor, logic.draft_soap(pid, transcript))
        self.status_var.set("DRAFT: not saved yet. Review, edit and save.")
        self._log("DRAFT_NOTE", f"patient:{pid}")

    def save_draft(self):
        pid = self.app.current_patient_id
        text = self._text(self.editor)
        if pid is None or not text:
            messagebox.showerror("Error", "There is no note to save. Draft one first.")
            return
        if self.current_status == "approved":
            messagebox.showerror("Error", "Approved notes are locked and cannot be edited.")
            return
        try:
            if self.current_note_id is None:
                self.current_note_id = logic.save_note(pid, text)
                action = "SAVE_NOTE"
            else:
                logic.update_note(self.current_note_id, text)
                action = "EDIT_NOTE"
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.current_status = "draft"
        self._log(action, f"note:{self.current_note_id}")
        self.status_var.set(f"DRAFT saved (note #{self.current_note_id}): waiting for a Doctor to approve")
        self.load_notes()
        self.load_timeline()

    def approve(self):
        user = self.app.user
        if user["role"] != "Doctor":
            self._log("APPROVE_DENIED", f"role:{user['role']}")
            messagebox.showerror("Not allowed", "Only a Doctor can approve notes.")
            return
        pid = self.app.current_patient_id
        text = self._text(self.editor)
        if pid is None or not text:
            messagebox.showerror("Error", "There is no note to approve. Draft one first.")
            return
        if self.current_status == "approved":
            messagebox.showerror("Error", "This note is already approved.")
            return
        if not messagebox.askyesno("Approve note", "Approve this note?\nIt becomes part of the record and "
                                                   "can no longer be edited."):
            return
        try:
            if self.current_note_id is None:
                self.current_note_id = logic.save_note(pid, text)
            else:
                logic.update_note(self.current_note_id, text)
            text = logic.approve_note(self.current_note_id, user)   # header now says "approved by ..."
        except (PermissionError, ValueError) as e:
            messagebox.showerror("Error", str(e))
            return
        self.current_status = "approved"
        self._log("APPROVE_NOTE", f"note:{self.current_note_id}")
        self._set_text(self.editor, text, editable=False)
        self.status_var.set(f"APPROVED by {user['name']} (note #{self.current_note_id}). Locked.")
        self.load_notes()
        self.load_timeline()

    def open_note(self, event=None):
        selected = self.note_list.curselection()
        if not selected:
            return
        note = self.notes[selected[0]]
        self.current_note_id = note["id"]
        self.current_status = note["status"]
        self._set_text(self.editor, note["text"], editable=(note["status"] != "approved"))
        if note["status"] == "approved":
            self.status_var.set(f"APPROVED by {note['approved_by']} (note #{note['id']}). Locked.")
        else:
            self.status_var.set(f"DRAFT (note #{note['id']}): waiting for a Doctor to approve")
