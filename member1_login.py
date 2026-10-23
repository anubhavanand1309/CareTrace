"""
member1_login.py  -  MEMBER 1
Login / register page with roles (Doctor / Nurse), wrong-password lockout
and audit logging.

Contract: on success call   self.app.start_session({"username":..., "name":..., "role":...})
"""

import time

import tkinter as tk
from tkinter import ttk, messagebox

import db
from common import NAVY, BG, GREEN, ROLES

LOCK_AFTER = 3        # wrong attempts before lockout
LOCK_SECONDS = 30     # how long the lockout lasts


class LoginPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.fails = {}   # username -> (wrong_count, time_of_last_wrong)

        tk.Label(self, text="CareTrace", font=("Arial", 24, "bold"), bg=BG, fg=NAVY).pack(pady=(30, 0))
        tk.Label(self, text="AI-assisted Electronic Medical Record", font=("Arial", 11),
                 bg=BG, fg="grey").pack(pady=(0, 15))

        card = tk.Frame(self, bg="white", padx=25, pady=20)
        card.pack(padx=40, pady=5)

        self.user_var = tk.StringVar()
        self.pw_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.role_var = tk.StringVar(value=ROLES[0])

        tk.Label(card, text="Username:", bg="white", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=8)
        tk.Entry(card, textvariable=self.user_var, width=28, font=("Arial", 11)).grid(row=0, column=1, pady=8)

        tk.Label(card, text="Password:", bg="white", font=("Arial", 11)).grid(row=1, column=0, sticky="w", pady=8)
        tk.Entry(card, textvariable=self.pw_var, show="*", width=28, font=("Arial", 11)).grid(row=1, column=1, pady=8)

        btns = tk.Frame(card, bg="white")
        btns.grid(row=2, column=0, columnspan=2, pady=(10, 15))
        tk.Button(btns, text="Login", command=self.login, bg=NAVY, fg="white",
                  font=("Arial", 11, "bold"), width=10).pack(side="left", padx=8)
        tk.Button(btns, text="Clear", command=self.clear, bg="grey", fg="white",
                  font=("Arial", 11), width=10).pack(side="left", padx=8)

        tk.Label(card, text="New staff? Fill these two and click Register:", bg="white",
                 fg="grey", font=("Arial", 9)).grid(row=3, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Full name:", bg="white", font=("Arial", 11)).grid(row=4, column=0, sticky="w", pady=8)
        tk.Entry(card, textvariable=self.name_var, width=28, font=("Arial", 11)).grid(row=4, column=1, pady=8)

        tk.Label(card, text="Role:", bg="white", font=("Arial", 11)).grid(row=5, column=0, sticky="w", pady=8)
        ttk.Combobox(card, textvariable=self.role_var, state="readonly", width=26,
                     values=list(ROLES)).grid(row=5, column=1, pady=8)

        tk.Button(card, text="Register", command=self.register, bg=GREEN, fg="white",
                  font=("Arial", 11, "bold"), width=10).grid(row=6, column=0, columnspan=2, pady=(10, 0))

        tk.Label(self, text="Demo logins:  dr.rao / demo123 (Doctor)   nurse.mala / demo123 (Nurse)",
                 bg=BG, fg="grey", font=("Arial", 9)).pack(pady=(12, 0))
        tk.Label(self, text="All patient data in this app is synthetic (fake).",
                 bg=BG, fg="grey", font=("Arial", 9)).pack()

    # ---------------------------------------------------------- #
    def login(self):
        username = self.user_var.get().strip()
        pw = self.pw_var.get()
        if not username or not pw:
            messagebox.showerror("Error", "Enter username and password.")
            return

        count, last = self.fails.get(username, (0, 0.0))
        now = time.time()
        if count >= LOCK_AFTER:
            if now - last < LOCK_SECONDS:
                wait = int(LOCK_SECONDS - (now - last))
                messagebox.showerror("Locked", f"Too many wrong attempts. Try again in {wait} seconds.")
                return
            count = 0   # lockout is over

        user = db.verify_user(username, pw)
        if user is None:
            self.fails[username] = (count + 1, now)
            db.log_action(username, "LOGIN_FAIL")
            messagebox.showerror("Error", "Invalid username or password.")
            return

        self.fails.pop(username, None)
        db.log_action(user["username"], "LOGIN_OK", f"role:{user['role']}")
        self.app.start_session(user)

    def register(self):
        username = self.user_var.get().strip().lower()
        pw = self.pw_var.get()
        name = self.name_var.get().strip()
        role = self.role_var.get()
        if not username or not pw or not name:
            messagebox.showerror("Error", "Fill username, password and full name to register.")
            return
        if not username.replace(".", "").replace("_", "").isalnum() or len(username) < 3:
            messagebox.showerror("Error", "Username: at least 3 letters/digits (dot and underscore allowed).")
            return
        if len(pw) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return
        if not db.add_user(username, name, role, pw):
            messagebox.showerror("Error", "That username is already taken.")
            return
        db.log_action(username, "REGISTER", f"role:{role}")
        messagebox.showinfo("Success", "Registered! Now click Login.")

    def clear(self):
        self.user_var.set("")
        self.pw_var.set("")
        self.name_var.set("")
