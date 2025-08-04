import pandas as pd
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path
import requests
import base64

# File to store GitHub info locally
GITHUB_INFO_FILE = Path.home() / ".fedramp_github_info.json"

def save_github_info_locally(info):
    try:
        with open(GITHUB_INFO_FILE, "w") as f:
            json.dump(info, f)
    except Exception as e:
        print("Failed to save GitHub info:", e)

def load_github_info_locally():
    if GITHUB_INFO_FILE.exists():
        try:
            with open(GITHUB_INFO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def reset_ui():
    pass  # Placeholder for resetting UI state

def push_to_github(json_file_path):
    saved_info = load_github_info_locally()
    additional_files = []

    def select_additional_files():
        nonlocal additional_files
        files = filedialog.askopenfilenames(
            filetypes=[("All files", "*.*"), ("Markdown files", "*.md"), ("Text files", "*.txt")],
            title="Select additional files to include in commit"
        )
        root.deiconify()
        if files:
            additional_files = [Path(file) for file in files]
            messagebox.showinfo("Info", f"Selected {len(additional_files)} additional file(s) for commit.")
        else:
            additional_files = []
            messagebox.showinfo("Info", "No additional files selected.")

    def on_push(repo_url, branch, commit_msg, token, save_info, window, json_file_path, additional_files):
        if not repo_url or not token:
            messagebox.showerror("Error", "GitHub Repo URL and Token are required.")
            return

        if save_info:
            save_github_info_locally({
                "repo_url": repo_url,
                "branch": branch,
                "commit_msg": commit_msg,
                "token": token
            })
        else:
            if GITHUB_INFO_FILE.exists():
                try:
                    GITHUB_INFO_FILE.unlink()
                except Exception:
                    pass

        try:
            parts = repo_url.rstrip("/").replace(".git", "").split("/")
            owner = parts[-2]
            repo = parts[-1]
        except Exception:
            messagebox.showerror("Error", "Invalid GitHub repo URL format.")
            return

        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json"
            }

            # Handle JSON file
            with open(json_file_path, "r", encoding="utf-8") as f:
                json_content = f.read()
            json_content_b64 = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{json_file_path.name}"
            r = requests.get(api_url + f"?ref={branch}", headers=headers)
            json_sha = r.json().get("sha") if r.status_code == 200 else None

            if r.status_code not in (200, 404):
                messagebox.showerror("GitHub API Error", f"Failed to get JSON file info:\n{r.text}")
                return

            payload = {
                "message": commit_msg,
                "content": json_content_b64,
                "branch": branch
            }
            if json_sha:
                payload["sha"] = json_sha

            put_resp = requests.put(api_url, headers=headers, json=payload)
            if put_resp.status_code not in (200, 201):
                messagebox.showerror("GitHub API Error", f"Failed to push JSON file:\n{put_resp.text}")
                return

            # Handle additional files
            for file_path in additional_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

                api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path.name}"
                r = requests.get(api_url + f"?ref={branch}", headers=headers)
                sha = r.json().get("sha") if r.status_code == 200 else None

                if r.status_code not in (200, 404):
                    messagebox.showerror("GitHub API Error", f"Failed to get info for {file_path.name}:\n{r.text}")
                    return

                payload = {
                    "message": f"{commit_msg} (added {file_path.name})",
                    "content": content_b64,
                    "branch": branch
                }
                if sha:
                    payload["sha"] = sha

                put_resp = requests.put(api_url, headers=headers, json=payload)
                if put_resp.status_code not in (200, 201):
                    messagebox.showerror("GitHub API Error", f"Failed to push {file_path.name}:\n{put_resp.text}")
                    return

            messagebox.showinfo("Success", "All files pushed to GitHub successfully!")
            window.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Exception occurred:\n{e}")

    def create_new_repo():
        push_window = tk.Toplevel(root)
        push_window.title("Create New GitHub Repository")
        push_window.geometry("450x450")
        push_window.configure(bg="#121212")

        lbl_cfg = {
            "bg": "#121212",
            "fg": "#E0E0E0",
            "font": ("Segoe UI", 10),
        }

        tk.Label(push_window, text="GitHub Username:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        username_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        username_entry.pack(padx=10, pady=2)
        username_entry.insert(0, saved_info.get("username", ""))

        tk.Label(push_window, text="New Repository Name:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        repo_name_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        repo_name_entry.pack(padx=10, pady=2)

        tk.Label(push_window, text="Branch Name:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        branch_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        branch_entry.pack(padx=10, pady=2)
        branch_entry.insert(0, saved_info.get("branch", "main"))

        tk.Label(push_window, text="Commit Message:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        commit_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        commit_entry.pack(padx=10, pady=2)
        commit_entry.insert(0, saved_info.get("commit_msg", "Initial commit"))

        tk.Label(push_window, text="Personal Access Token:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        token_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0", show="*")
        token_entry.pack(padx=10, pady=2)
        token_entry.insert(0, saved_info.get("token", ""))

        save_var = tk.BooleanVar(value=bool(saved_info))
        tk.Checkbutton(push_window, text="Save GitHub Info", variable=save_var, bg="#121212", fg="#E0E0E0",
                       activebackground="#121212", activeforeground="#E0E0E0", selectcolor="#121212",
                       font=("Segoe UI", 10)).pack(pady=10)

        upload_btn_style = {
            "bg": "#1F1F1F",
            "fg": "#E0E0E0",
            "activebackground": "#333333",
            "activeforeground": "#FFFFFF",
            "font": ("Segoe UI", 12, "bold"),
            "bd": 0,
            "relief": "flat",
            "width": 20,
            "cursor": "hand2",
        }
        tk.Button(push_window, text="Upload Additional Files", command=select_additional_files, **upload_btn_style).pack(pady=10)

        def create_and_push():
            username = username_entry.get().strip()
            repo_name = repo_name_entry.get().strip()
            branch = branch_entry.get().strip() or "main"
            commit_msg = commit_entry.get().strip() or "Initial commit"
            token = token_entry.get().strip()
            save_info = save_var.get()

            if not username or not repo_name or not token:
                messagebox.showerror("Error", "Username, Repository Name, and Token are required.")
                return

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json"
            }
            payload = {
                "name": repo_name,
                "auto_init": True,
                "private": False
            }
            try:
                create_resp = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
                if create_resp.status_code != 201:
                    messagebox.showerror("GitHub API Error", f"Failed to create repository:\n{create_resp.text}")
                    return
            except Exception as e:
                messagebox.showerror("Error", f"Exception occurred while creating repo:\n{e}")
                return

            repo_url = f"https://github.com/{username}/{repo_name}.git"
            on_push(repo_url, branch, commit_msg, token, save_info, push_window, json_file_path, additional_files)

        push_btn_style = {
            "bg": "#1F1F1F",
            "fg": "#E0E0E0",
            "activebackground": "#333333",
            "activeforeground": "#FFFFFF",
            "font": ("Segoe UI", 12, "bold"),
            "bd": 0,
            "relief": "flat",
            "width": 20,
            "cursor": "hand2",
        }
        tk.Button(push_window, text="Create and Push", command=create_and_push, **push_btn_style).pack(pady=10)

    def use_existing_repo():
        push_window = tk.Toplevel(root)
        push_window.title("Push to Existing GitHub Repository")
        push_window.geometry("450x400")
        push_window.configure(bg="#121212")

        lbl_cfg = {
            "bg": "#121212",
            "fg": "#E0E0E0",
            "font": ("Segoe UI", 10),
        }

        tk.Label(push_window, text="GitHub Repo URL:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        repo_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        repo_entry.pack(padx=10, pady=2)
        repo_entry.insert(0, saved_info.get("repo_url", ""))

        tk.Label(push_window, text="Branch Name:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        branch_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        branch_entry.pack(padx=10, pady=2)
        branch_entry.insert(0, saved_info.get("branch", "main"))

        tk.Label(push_window, text="Commit Message:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        commit_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0")
        commit_entry.pack(padx=10, pady=2)
        commit_entry.insert(0, saved_info.get("commit_msg", "Update JSON file"))

        tk.Label(push_window, text="Personal Access Token:", **lbl_cfg).pack(anchor="w", padx=10, pady=(10,0))
        token_entry = tk.Entry(push_window, width=50, fg="#E0E0E0", bg="#1F1F1F", insertbackground="#E0E0E0", show="*")
        token_entry.pack(padx=10, pady=2)
        token_entry.insert(0, saved_info.get("token", ""))

        save_var = tk.BooleanVar(value=bool(saved_info))
        tk.Checkbutton(push_window, text="Save GitHub Info", variable=save_var, bg="#121212", fg="#E0E0E0",
                       activebackground="#121212", activeforeground="#E0E0E0", selectcolor="#121212",
                       font=("Segoe UI", 10)).pack(pady=10)

        upload_btn_style = {
            "bg": "#1F1F1F",
            "fg": "#E0E0E0",
            "activebackground": "#333333",
            "activeforeground": "#FFFFFF",
            "font": ("Segoe UI", 12, "bold"),
            "bd": 0,
            "relief": "flat",
            "width": 20,
            "cursor": "hand2",
        }
        tk.Button(push_window, text="Upload Additional Files", command=select_additional_files, **upload_btn_style).pack(pady=10)

        push_btn_style = {
            "bg": "#1F1F1F",
            "fg": "#E0E0E0",
            "activebackground": "#333333",
            "activeforeground": "#FFFFFF",
            "font": ("Segoe UI", 12, "bold"),
            "bd": 0,
            "relief": "flat",
            "width": 20,
            "cursor": "hand2",
        }
        tk.Button(push_window, text="Push to GitHub", command=lambda: on_push(
            repo_entry.get().strip(),
            branch_entry.get().strip() or "main",
            commit_entry.get().strip() or "Update JSON file",
            token_entry.get().strip(),
            save_var.get(),
            push_window,
            json_file_path,
            additional_files
        ), **push_btn_style).pack(pady=10)

    root.withdraw()
    action = messagebox.askyesnocancel("GitHub Action", "Do you want to create a new GitHub repository?\n(Select 'No' to push to an existing repository)")
    root.deiconify()

    if action is None:
        messagebox.showinfo("Info", "GitHub push canceled.")
        return
    elif action:
        create_new_repo()
    else:
        use_existing_repo()

def import_excel_and_convert():
    file_path = filedialog.askopenfilename(
        filetypes=[("Excel files", "*.xlsx *.xls")],
        title="Select an Excel file"
    )
    if not file_path:
        messagebox.showerror("User Canceled!", "User canceled file selection.")
        reset_ui()
        return

    try:
        df = pd.read_excel(file_path)
        desktop_path = Path.home() / "Desktop"
        target_folder = desktop_path / "FedRamp_20x_jsonify"
        if not target_folder.exists():
            target_folder.mkdir(parents=True, exist_ok=True)

        root.withdraw()
        action = messagebox.askyesnocancel("JSON Action", "Do you want to create a new JSON file?\n(Select 'No' to add to an existing JSON file)")
        root.deiconify()

        if action is None:
            messagebox.showerror("User Canceled!", "User canceled JSON action selection.")
            reset_ui()
            return

        if action:
            filename = simpledialog.askstring("Save JSON", "Enter JSON filename (without extension):")
            root.deiconify()
            if not filename:
                messagebox.showerror("User Canceled!", "User canceled filename input.")
                reset_ui()
                return
            filename = filename.strip()
            if not filename.lower().endswith(".json"):
                filename += ".json"
            json_file_path = target_folder / filename
            json_data = df.to_json(orient="records", indent=2)

            with open(json_file_path, "w") as f:
                f.write(json_data)

            messagebox.showinfo("Success", f"New JSON file created:\n{json_file_path}")

        else:
            json_file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Select an existing JSON file to append to",
                initialdir=target_folder
            )
            root.deiconify()
            if not json_file_path:
                messagebox.showerror("User Canceled!", "User canceled JSON file selection.")
                reset_ui()
                return

            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    messagebox.showerror("Error", "Existing JSON file does not contain a list of records.")
                    reset_ui()
                    return
                new_data = df.to_dict(orient="records")
                existing_data.extend(new_data)
                json_data = json.dumps(existing_data, indent=2)
                
                with open(json_file_path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                
                messagebox.showinfo("Success", f"Data appended to existing JSON file:\n{json_file_path}")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to append to JSON file:\n{e}")
                reset_ui()
                return

        if messagebox.askyesno("Push to GitHub?", "Do you want to push the JSON file to GitHub?"):
            push_to_github(Path(json_file_path))

    except Exception as e:
        messagebox.showerror("Error", f"Failed to process Excel file:\n{e}")
        reset_ui()

# Setup main Tkinter window
root = tk.Tk()
root.title("FedRamp 20x JSONifier")
root.geometry("400x250")
root.configure(bg="#121212")

button_style = {
    "bg": "#1F1F1F",
    "fg": "#E0E0E0",
    "activebackground": "#333333",
    "activeforeground": "#FFFFFF",
    "font": ("Segoe UI", 14, "bold"),
    "bd": 0,
    "relief": "flat",
    "width": 30,
    "height": 2,
    "cursor": "hand2",
}

btn = tk.Button(root, text="Import Excel and Convert to JSON", command=import_excel_and_convert, **button_style)
btn.pack(expand=True)

def on_enter(e):
    btn.config(bg="#333333")

def on_leave(e):
    btn.config(bg="#1F1F1F")

btn.bind("<Enter>", on_enter)
btn.bind("<Leave>", on_leave)

root.mainloop()