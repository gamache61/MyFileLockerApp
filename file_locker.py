import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import os
import stat
import json
import hashlib
import subprocess
import sys

DATA_FILE = os.path.join(os.path.expanduser("~"), ".file_locker_data.json")

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"password_hash": None, "files": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def set_readonly(path, readonly):
    if not os.path.exists(path):
        return False
    try:
        if os.name == 'nt':
            import ctypes
            FILE_ATTRIBUTE_READONLY = 0x1
            attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
            if attrs == -1:
                return False
            if readonly:
                new_attrs = attrs | FILE_ATTRIBUTE_READONLY
            else:
                new_attrs = attrs & ~FILE_ATTRIBUTE_READONLY
            result = ctypes.windll.kernel32.SetFileAttributesW(path, new_attrs)
            return result != 0
        else:
            current = os.stat(path).st_mode
            if readonly:
                new_mode = current & ~(stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH)
            else:
                new_mode = current | stat.S_IWRITE
            os.chmod(path, new_mode)
            return True
    except Exception as e:
        print(f"set_readonly failed for {path}: {e}")
        return False

class FileLockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Locker")
        self.root.geometry("560x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f0")

        self.data = load_data()
        self.build_ui()

        if not self.data["password_hash"]:
            self.setup_password()

    def build_ui(self):
        header = tk.Frame(self.root, bg="#1a1a1a", pady=16)
        header.pack(fill="x")
        tk.Label(header, text="🔒  File Locker", font=("Segoe UI", 16, "bold"),
                 bg="#1a1a1a", fg="white").pack()
        tk.Label(header, text="Protect your files from accidental deletion",
                 font=("Segoe UI", 10), bg="#1a1a1a", fg="#aaaaaa").pack()

        list_frame = tk.Frame(self.root, bg="#f5f5f0", padx=20, pady=16)
        list_frame.pack(fill="both", expand=True)

        tk.Label(list_frame, text="Protected Files", font=("Segoe UI", 11, "bold"),
                 bg="#f5f5f0", fg="#333").pack(anchor="w", pady=(0, 8))

        lb_frame = tk.Frame(list_frame, bg="#e0e0d8", bd=1, relief="flat")
        lb_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(lb_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(lb_frame, yscrollcommand=scrollbar.set,
                                  font=("Courier New", 10), bg="white", fg="#333",
                                  selectbackground="#1a1a1a", selectforeground="white",
                                  borderwidth=0, highlightthickness=0, activestyle="none",
                                  height=10)
        self.listbox.pack(fill="both", expand=True, padx=1, pady=1)
        scrollbar.config(command=self.listbox.yview)

        for f in self.data["files"]:
            self.listbox.insert("end", f)

        btn_row = tk.Frame(list_frame, bg="#f5f5f0", pady=10)
        btn_row.pack(fill="x")

        self._btn(btn_row, "＋  Add File", self.add_file, "#ffffff", "#333").pack(side="left", padx=(0, 6))
        self._btn(btn_row, "－  Remove Selected", self.remove_file, "#ffffff", "#333").pack(side="left")

        action_frame = tk.Frame(self.root, bg="#e8e8e0", pady=14, padx=20)
        action_frame.pack(fill="x")

        self._btn(action_frame, "🔒  Lock Files", self.lock_files, "#1a1a1a", "white", padx=20).pack(side="left", padx=(0, 10))
        self._btn(action_frame, "🔓  Unlock Files", self.unlock_files, "#f0f0ea", "#333", padx=20).pack(side="left", padx=(0, 10))
        self._btn(action_frame, "🔑  Change Password", self.change_password, "#f0f0ea", "#333", padx=10).pack(side="right")

        self.status_var = tk.StringVar(value="Ready.")
        status = tk.Label(self.root, textvariable=self.status_var,
                          font=("Segoe UI", 10), bg="#deded6", fg="#555",
                          anchor="w", padx=14, pady=6)
        status.pack(fill="x", side="bottom")

    def _btn(self, parent, text, cmd, bg, fg, padx=14):
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, font=("Segoe UI", 10),
                         relief="flat", padx=padx, pady=7,
                         cursor="hand2", activebackground="#dddddd",
                         activeforeground=fg, bd=0)

    def setup_password(self):
        self.root.withdraw()
        pw = simpledialog.askstring("Set Password",
            "Welcome! Set a password to protect your files.\n\nThis password is required to unlock files.",
            show="*", parent=self.root)
        self.root.deiconify()
        if not pw:
            messagebox.showerror("Error", "A password is required to use File Locker.")
            self.root.destroy()
            return
        pw2 = simpledialog.askstring("Confirm Password", "Confirm your password:", show="*", parent=self.root)
        if pw != pw2:
            messagebox.showerror("Error", "Passwords do not match. Please restart.")
            self.root.destroy()
            return
        self.data["password_hash"] = hash_password(pw)
        save_data(self.data)
        self.set_status("Password set. Add files and lock them.")

    def verify_password(self, prompt="Enter your password:"):
        pw = simpledialog.askstring("Password Required", prompt, show="*", parent=self.root)
        if pw is None:
            return False
        if hash_password(pw) != self.data["password_hash"]:
            messagebox.showerror("Wrong Password", "Incorrect password.")
            return False
        return True

    def add_file(self):
        paths = filedialog.askopenfilenames(title="Select files to protect", parent=self.root)
        added = 0
        for path in paths:
            if path and path not in self.data["files"]:
                self.data["files"].append(path)
                added += 1
        if added:
            self.data["files"].sort(key=lambda p: os.path.basename(p).lower())
            self.listbox.delete(0, "end")
            for f in self.data["files"]:
                self.listbox.insert("end", f)
            save_data(self.data)
            self.set_status(f"Added {added} file(s).")

    def remove_file(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showinfo("Select a file", "Please select a file to remove.")
            return
        if not self.verify_password("Enter your password to remove and unlock this file:"):
            return
        idx = selected[0]
        path = self.data["files"][idx]
        set_readonly(path, False)
        self.data["files"].pop(idx)
        self.listbox.delete(idx)
        save_data(self.data)
        self.set_status(f"Removed and unlocked: {os.path.basename(path)}")

    def lock_files(self):
        if not self.data["files"]:
            messagebox.showinfo("No files", "Add some files first.")
            return
        count, failed = 0, []
        for path in self.data["files"]:
            if set_readonly(path, True):
                count += 1
            else:
                failed.append(path)
        msg = f"🔒 Locked {count} file(s)."
        if failed:
            msg += f"\n⚠ Could not find: {len(failed)} file(s)."
        self.set_status(msg)
        messagebox.showinfo("Files Locked", msg)

    def unlock_files(self):
        if not self.data["files"]:
            messagebox.showinfo("No files", "No files to unlock.")
            return
        if not self.verify_password("Enter your password to unlock files:"):
            return
        count, failed = 0, []
        for path in self.data["files"]:
            if set_readonly(path, False):
                count += 1
            else:
                failed.append(path)
        msg = f"🔓 Unlocked {count} file(s)."
        if failed:
            msg += f"\n⚠ Could not find: {len(failed)} file(s)."
        self.set_status(msg)
        messagebox.showinfo("Files Unlocked", msg)

    def change_password(self):
        if not self.verify_password("Enter your current password:"):
            return
        pw = simpledialog.askstring("New Password", "Enter new password:", show="*", parent=self.root)
        if not pw:
            return
        pw2 = simpledialog.askstring("Confirm", "Confirm new password:", show="*", parent=self.root)
        if pw != pw2:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        self.data["password_hash"] = hash_password(pw)
        save_data(self.data)
        self.set_status("Password updated.")

    def set_status(self, msg):
        self.status_var.set(msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = FileLockerApp(root)
    root.mainloop()