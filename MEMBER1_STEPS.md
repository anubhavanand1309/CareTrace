# MEMBER 1: Access, Roles, Audit Log and the App Shell
**Your files:** `member1_login.py`, `member1_patient_audit.py`, `main.py`, `db.py`, `common.py`
**First finish the setup in `README_TEAM.md`.**

Your job: you are the **foundation** of CareTrace. Nobody can use the app without your login, everybody's data lives in your database layer, and your `main.py` joins all the pages together. Members 2 and 3 depend on what you build, so keep the contracts unchanged.

---

## PART A: Understand what you have (Day 1, about 2 hours)

### Step 1. Run it
```
cd Desktop\caretrace
pip install -r requirements.txt
python main.py
```
Log in as `dr.rao` / `demo123` (Doctor). Look at the 4 tabs, switch the patient in the top-right dropdown, and open **Audit Log**. Then log out and log in as `nurse.mala` / `demo123` (Nurse). **The Nurse does not see the Audit Log tab.** That is role-based access.

### Step 2. Try to break it (this proves you understand it)
1. Type a wrong password 3 times. The 4th attempt is locked for 30 seconds, even with the right password.
2. Register a new user, then log in with it.
3. Click **+ Add new patient** and add a fake patient. Check that the dropdown updates.
4. Open the Audit Log as the Doctor and find all of your actions.

### Step 3. Read the files in this order
| File | What to focus on |
|---|---|
| `common.py` | Colours and the `ROLES` list. Tiny. |
| `db.py` | The `SCHEMA` (7 tables), `hash_pw` / `check_pw`, `verify_user`, `log_action`, `get_audit`, and the `DEMO` data. |
| `member1_login.py` | `login()` (lockout logic and audit logging) and `register()` (validation). |
| `member1_patient_audit.py` | `PatientInfoPage.refresh()`, the Add Patient dialog, and `AuditPage`. |
| `main.py` | `start_session()`, `reload_patients()`, `set_patient()`, `refresh_pages()`, `logout()`. |

### Step 4. Understand the 3 key ideas
1. **Shared state:** `app.user` (who is logged in) and `app.current_patient_id` (which patient is selected). Every page reads these.
2. **`refresh()` contract:** every page has a `refresh()` method. When the patient changes, `main.py` calls `refresh()` on all pages.
3. **Audit log:** `db.log_action(user, action, target)` is called for every important event. Members 2 and 3 call it too.

### Step 5. Small experiments
1. Change `LOCK_AFTER` to 2 in `member1_login.py` and test it.
2. Change the header colour by editing `NAVY` in `common.py`.
3. Add a third demo patient in the `DEMO` list in `db.py`. **Delete `caretrace.db` first**, because demo data is only created when the database is new.

---

## PART B: Your improvement tasks (Days 2-4)

### TASK 1: Auto-logout after inactivity (security feature, 30 mins)
Real hospital systems log you out when you walk away.

**Step 1.** In `main.py`, change the tkinter import and add a constant below the imports:
```python
from tkinter import ttk, messagebox

IDLE_LIMIT_MS = 5 * 60 * 1000     # 5 minutes. Use 10000 (10 s) while testing
```
**Step 2.** In `App.__init__`, add `self.idle_job = None` next to the other variables.

**Step 3.** Add these two methods to the `App` class:
```python
def reset_idle(self, event=None):
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
```
**Step 4.** At the end of `start_session`, add:
```python
self.root.bind_all("<Key>", self.reset_idle)
self.root.bind_all("<Motion>", self.reset_idle)
self.reset_idle()
```
**Step 5.** At the start of `logout`, add:
```python
if self.idle_job:
    self.root.after_cancel(self.idle_job)
    self.idle_job = None
```
**Test:** set the limit to 10 seconds, log in, and do nothing. You should be logged out and see `AUTO_LOGOUT` in the audit log. **Set it back to 5 minutes afterwards.**

### TASK 2: Audit log filter and red failed logins (30 mins)
In `AuditPage` (`member1_patient_audit.py`):

**Step 1.** Right after `self.app = app`, add (it must be before the table is created):
```python
self.filter_var = tk.StringVar(value="All")
top = tk.Frame(self, bg="white")
top.pack(fill="x", pady=(0, 6))
tk.Label(top, text="Action:", bg="white").pack(side="left")
box = ttk.Combobox(top, textvariable=self.filter_var, state="readonly", width=16,
                   values=["All", "LOGIN_OK", "LOGIN_FAIL", "LOGOUT", "REGISTER",
                           "VIEW_PATIENT", "ADD_PATIENT", "APPROVE_NOTE", "AUTO_LOGOUT"])
box.pack(side="left", padx=6)
box.bind("<<ComboboxSelected>>", lambda e: self.refresh())
```
**Step 2.** After the `for c in cols:` loop, add: `self.table.tag_configure("fail", foreground="#c0392b")`

**Step 3.** Replace the loop in `refresh()` with:
```python
for r in db.get_audit():
    if self.filter_var.get() not in ("All", r["action"]):
        continue
    tag = ("fail",) if r["action"] == "LOGIN_FAIL" else ()
    self.table.insert("", "end", tags=tag,
                      values=(r["time"], r["user"], r["action"], r["target"]))
```
**Test:** make 2 wrong logins, then filter by `LOGIN_FAIL`. The rows should be red.

### TASK 3: Change password (45 mins)
**Step 1.** Add to `db.py` (anywhere in the users section):
```python
def change_password(username, old_pw, new_pw):
    if verify_user(username, old_pw) is None:
        return False
    execute("UPDATE users SET password = ? WHERE username = ?", (hash_pw(new_pw), username))
    return True
```
**Step 2.** In `main.py`, change the import to `from tkinter import ttk, messagebox, simpledialog` and add this method to `App`:
```python
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
```
**Step 3.** In `start_session`, next to the Logout button, add:
```python
tk.Button(header, text="Change password", command=self.change_password, bg="#555", fg="white",
          font=("Arial", 10)).pack(side="right", padx=4)
```
**Test:** change the password, log out, and log in with the new one.

### TASK 4: Pick ONE extra (optional)
- **Search box in the patient dropdown area:** filter patients by typing a name.
- **Edit patient allergies:** a button on the Patient tab that updates `patients.allergies` (add `db.update_allergies(pid, text)` and log `EDIT_ALLERGIES`).
- **Export the audit log to CSV** with `filedialog` and the `csv` module.

---

## PART C: Your responsibility to the team
1. **Never rename** `refresh()`, `start_session`, `reload_patients`, `set_patient`, `current_patient_id`, `user`, or any function in `db.py`.
2. Collect Member 2's and Member 3's files on **22 Oct**. Put them into the folder, **delete `caretrace.db`**, run `python main.py` and test everything (checklist in `README_TEAM.md`).
3. If a teammate's page crashes the app, the error appears in the Command Prompt window. Send them that error message.

## PART D: Testing checklist
- [ ] Wrong password shows an error and adds `LOGIN_FAIL` to the audit log
- [ ] 3 wrong attempts lock the account for 30 seconds
- [ ] Register works, a duplicate username is rejected, a short password is rejected
- [ ] The Doctor sees the Audit Log tab, the Nurse does not
- [ ] Add patient works and the new patient appears in the dropdown
- [ ] Changing the patient updates the Patient tab
- [ ] Logout and login again works
- [ ] (Task 1) Auto-logout works and the time limit is set back to 5 minutes
- [ ] No red errors in the Command Prompt window

## PART E: Common problems
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'db'` | Run `python main.py` from inside the `caretrace` folder |
| Demo patients or users look old or wrong | Close the app and delete `caretrace.db`, then run again |
| `sqlite3.OperationalError: database is locked` | Close other copies of the app or any DB viewer |
| Dropdown is empty | Run once with `caretrace.db` deleted so demo data is created |
| Forgot a demo password | Delete `caretrace.db`. Demo logins return: `dr.rao` / `nurse.mala`, password `demo123` |

## PART F: Viva questions for you
1. Why do we store a **hash** and not the password? What is a **salt**? What is PBKDF2?
2. What is **role-based access control**? Where is it enforced in the code? (Audit tab only for Doctor; Doctor-only approval in Member 3's page)
3. Why does a medical system need an **audit log**?
4. Why SQLite and not a CSV file? (queries, relationships, integrity)
5. Why does the account lock after 3 wrong attempts? (stops password guessing)
6. How do the pages know which patient is selected? (`app.current_patient_id` plus `refresh()`)
7. All data is fake. Why is that important? (privacy, no real patient data)

## PART G: Hand-over
By **22 Oct** you should have the merged folder working. Delete `caretrace.db` before taking final screenshots so everything is fresh.
