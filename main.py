"""
main.py  -  RUN THIS FILE:   python main.py
Joins the modules, holds the logged-in user and the selected patient.

Shared state that every page can read:
    self.app.user                 {"username", "name", "role"}   (role = Doctor / Nurse)
    self.app.current_patient_id   int or None
Every page must have a  refresh()  method.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import db
from common import NAVY, BG, RED
from login_page import LoginPage
from patient_audit_pages import PatientInfoPage, AuditPage
from search_safety_page import SearchSafetyPage
from timeline_scribe_page import TimelineScribePage

IDLE_LIMIT_MS = 5 * 60 * 1000     # 5 minutes. Use 10000 (10 seconds) while testing


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("CareTrace - AI-assisted EMR")
        self.root.geometry("900x660")
        self.root.config(bg=BG)

        db.init_db()                      # creates tables + demo data the first time
        self.user = None
        self.current_patient_id = None
        self.patient_map = {}             # "1 - Asha Verma" -> 1
        self.pages = []
        self.idle_job = None

        self.login_page = LoginPage(root, self)
        self.login_page.pack(fill="both", expand=True)
        self.main_frame = None

    # ---------------------------------------------------------- #
    def start_session(self, user):
        self.user = user
        self.login_page.pack_forget()

        self.main_frame = tk.Frame(self.root, bg=BG)
        self.main_frame.pack(fill="both", expand=True)

        # ---- header: user, patient picker, change password, logout
        header = tk.Frame(self.main_frame, bg=NAVY)
        header.pack(fill="x")
        tk.Label(header, text=f"{user['name']}  [{user['role']}]", bg=NAVY, fg="white",
                 font=("Arial", 11, "bold")).pack(side="left", padx=12, pady=8)
        tk.Button(header, text="Logout", command=self.logout, bg=RED, fg="white",
                  font=("Arial", 10, "bold")).pack(side="right", padx=12)
        tk.Button(header, text="Change password", command=self.change_password, bg="#555", fg="white",
                  font=("Arial", 10)).pack(side="right", padx=4)
        self.patient_box = ttk.Combobox(header, state="readonly", width=28)
        self.patient_box.pack(side="right", padx=6)
        self.patient_box.bind("<<ComboboxSelected>>", self.on_patient_selected)
        tk.Label(header, text="Patient:", bg=NAVY, fg="white").pack(side="right")

        # ---- tabs
        tabs = ttk.Notebook(self.main_frame)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.pages = []
        for title, page_class in (("  Patient  ", PatientInfoPage),
                                  ("  Search & Safety  ", SearchSafetyPage),
                                  ("  Timeline & Scribe  ", TimelineScribePage)):
            page = page_class(tabs, self)
            tabs.add(page, text=title)
            self.pages.append(page)

        if user["role"] == "Doctor":      # audit log is for doctors only
            audit = AuditPage(tabs, self)
            tabs.add(audit, text="  Audit Log  ")
            self.pages.append(audit)

        self.reload_patients()

        # ---- auto-logout after inactivity
        self.root.bind_all("<Key>", self.reset_idle)
        self.root.bind_all("<Motion>", self.reset_idle)
        self.reset_idle()

    # ---------------------------------------------------------- #
    def reload_patients(self, select_id=None):
        """Refill the patient dropdown. Call after adding a patient."""
        patients = db.list_patients()
        self.patient_map = {f"{p['id']} - {p['name']}": p["id"] for p in patients}
        labels = list(self.patient_map)
        self.patient_box.config(values=labels)
        if not labels:
            self.current_patient_id = None
            self.refresh_pages()
            return

        wanted = select_id if select_id is not None else self.current_patient_id
        chosen = labels[0]
        for label, pid in self.patient_map.items():
            if pid == wanted:
                chosen = label
        self.patient_box.set(chosen)
        self.set_patient(self.patient_map[chosen])

    def on_patient_selected(self, event=None):
        self.set_patient(self.patient_map[self.patient_box.get()])

    def set_patient(self, pid):
        self.current_patient_id = pid
        db.log_action(self.user["username"], "VIEW_PATIENT", f"patient:{pid}")
        self.refresh_pages()

    def refresh_pages(self):
        for page in self.pages:
            page.refresh()

    # ---------------------------------------------------------- #
    def logout(self):
        if self.idle_job:
            self.root.after_cancel(self.idle_job)
            self.idle_job = None
        db.log_action(self.user["username"], "LOGOUT")
        self.main_frame.destroy()
        self.user = None
        self.current_patient_id = None
        self.login_page.clear()
        self.login_page.pack(fill="both", expand=True)

    def reset_idle(self, event=None):
        """Restart the inactivity timer (called on every key press / mouse move)."""
        if self.user is None:
            return
        if self.idle_job:
            self.root.after_cancel(self.idle_job)
        self.idle_job = self.root.after(IDLE_LIMIT_MS, self.auto_logout)

    def auto_logout(self):
        if self.user is None:
            return
        db.log_action(self.user["username"], "AUTO_LOGOUT")
        messagebox.showinfo("Session ended", "You were logged out due to inactivity.")
        self.logout()

    def change_password(self):
        old = simpledialog.askstring("Change password", "Current password:", show="*")
        if old is None:
            return
        new = simpledialog.askstring("Change password", "New password (min 6 characters):", show="*")
        if not new or len(new) < 6:
            messagebox.showerror("Error", "New password must be at least 6 characters.")
            return
        if db.change_password(self.user["username"], old, new):
            db.log_action(self.user["username"], "CHANGE_PASSWORD")
            messagebox.showinfo("Done", "Password changed.")
        else:
            messagebox.showerror("Error", "Current password is wrong.")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
