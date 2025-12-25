from tkinter import simpledialog, messagebox, ttk, Tk
import tkinter as tk
import os, json, sys
from dotenv import load_dotenv
from PIL import Image, ImageTk
from cisco_core import resource_path

# Import phone versions
from cisco_8841 import Cisco8841Phone
from cisco_7911 import Cisco7911Phone
from cisco_7945 import Cisco7945Phone

load_dotenv()
SESSIONS_FILE = "sessions.json"

class HomePage:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Phone Control")
        self.root.geometry("1200x800")
        self.root.configure(bg="#121212")

        # Set Icon if exists
        try:
            icon_p = resource_path("icon.png")
            if os.path.exists(icon_p):
                self.icon_img = ImageTk.PhotoImage(Image.open(icon_p))
                self.root.iconphoto(True, self.icon_img)
        except: pass
        
        self.sessions_file = SESSIONS_FILE
        self.sessions = self.load_sessions()
        self.active_sessions = []
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e", borderwidth=0, font=("Segoe UI", 10), rowheight=25)
        style.configure("Treeview.Heading", background="#2a2a2a", foreground="white", borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[('selected', '#2980b9')])
        style.map("Treeview.Heading", background=[('active', '#333')])
        
        # Core Layout: Left Panel (Form) | Right Panel (Presets)
        layout_f = tk.Frame(root, bg="#121212", pady=40, padx=40)
        layout_f.pack(fill="both", expand=True)
        
        # --- LEFT PANEL (Configuration) ---
        left_p = tk.Frame(layout_f, bg="#121212", width=400)
        left_p.pack(side="left", fill="y", padx=(0, 40))
        left_p.pack_propagate(False) # Keep width consistent

        tk.Label(left_p, text="REMOTE PHONE", bg="#121212", fg="#00d2ff", 
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(left_p, text="Session parameters", bg="#121212", fg="#444", 
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 20))

        # Form Container
        form_f = tk.Frame(left_p, bg="#1e1e1e", padx=20, pady=25, highlightthickness=1, highlightbackground="#333")
        form_f.pack(fill="x")
        
        tk.Label(form_f, text="IP ADDRESS", bg="#1e1e1e", fg="#888", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.ip_entry = tk.Entry(form_f, bg="#121212", fg="white", insertbackground="white", 
                                 font=("Consolas", 12), borderwidth=0, highlightthickness=1, highlightbackground="#444")
        self.ip_entry.insert(0, "192.168.1.180")
        self.ip_entry.pack(fill="x", pady=(5, 15), ipady=8)
        
        tk.Label(form_f, text="PHONE MODEL", bg="#1e1e1e", fg="#888", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.type_combo = ttk.Combobox(form_f, values=["8841", "7911", "7945"], state="readonly", font=("Segoe UI", 10))
        self.type_combo.set("8841")
        self.type_combo.pack(fill="x", pady=(5, 10))
        
        self.use_ssh_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form_f, text="Remote SSH Bridge Mode", variable=self.use_ssh_var, 
                       bg="#1e1e1e", fg="#00d2ff", selectcolor="#121212", activebackground="#1e1e1e", 
                       activeforeground="white", font=("Segoe UI", 9)).pack(anchor="w", pady=10)
        
        def create_btn(parent, text, color, cmd, pady=10):
            return tk.Button(parent, text=text, bg=color, fg="white", font=("Segoe UI", 10, "bold"),
                             relief="flat", activebackground=color, cursor="hand2", command=cmd, pady=12)

        create_btn(left_p, "START LIVE SESSION", "#27ae60", self.open_new_session).pack(fill="x", pady=(20, 10))
        create_btn(left_p, "SAVE TO PRESETS", "#2980b9", self.save_current_session).pack(fill="x")

        # --- RIGHT PANEL (Presets) ---
        right_p = tk.Frame(layout_f, bg="#121212")
        right_p.pack(side="left", fill="both", expand=True)

        # Preset Header & Controls
        head_f = tk.Frame(right_p, bg="#121212")
        head_f.pack(fill="x", pady=(0, 10))
        
        tk.Label(head_f, text="PRESET DASHBOARD", bg="#121212", fg="#555", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        # Management Bar (Mini buttons)
        tk.Button(head_f, text="REMOVE", bg="#121212", fg="#c0392b", font=("Segoe UI", 8, "bold"), 
                  relief="flat", cursor="hand2", command=self.delete_session).pack(side="right", padx=5)
        tk.Button(head_f, text="EDIT", bg="#121212", fg="#f39c12", font=("Segoe UI", 8, "bold"), 
                  relief="flat", cursor="hand2", command=self.edit_preset).pack(side="right", padx=5)
        tk.Label(head_f, text="|", bg="#121212", fg="#333").pack(side="right", padx=5)
        tk.Button(head_f, text="▼ DN", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), 
                  relief="flat", cursor="hand2", command=lambda: self.move_preset(1)).pack(side="right", padx=2)
        tk.Button(head_f, text="▲ UP", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), 
                  relief="flat", cursor="hand2", command=lambda: self.move_preset(-1)).pack(side="right", padx=2)

        # Table Container
        tree_container = tk.Frame(right_p, bg="#1e1e1e", bd=0, highlightthickness=1, highlightbackground="#333")
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_container, columns=("Name", "Type", "IP"), show="headings", height=10)
        self.tree.heading("Name", text=" NAME")
        self.tree.heading("Type", text=" MODEL")
        self.tree.heading("IP", text=" NETWORK IP")
        
        self.tree.column("Name", width=180)
        self.tree.column("Type", width=80, anchor="center")
        self.tree.column("IP", width=160, anchor="center")
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.open_selected_session())
        
        tk.Label(right_p, text="* Double-click a row to launch immediately", bg="#121212", fg="#444", font=("Segoe UI", 8, "italic")).pack(pady=5, anchor="e")
        
        self.refresh_tree()

    def load_sessions(self):
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r') as f:
                    data = json.load(f)
                    # Support both old dict format and new list format
                    if isinstance(data, dict):
                        return [{"name": k, **v} for k, v in data.items()]
                    return data
            except: return []
        return []

    def save_sessions(self):
        with open(self.sessions_file, 'w') as f: json.dump(self.sessions, f, indent=4)

    def refresh_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, sess in enumerate(self.sessions):
            self.tree.insert("", "end", iid=i, values=(sess['name'], sess['type'], sess['ip']))

    def move_preset(self, direction):
        selected = self.tree.selection()
        if not selected: return
        idx = int(selected[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self.sessions):
            self.sessions[idx], self.sessions[new_idx] = self.sessions[new_idx], self.sessions[idx]
            self.save_sessions()
            self.refresh_tree()
            self.tree.selection_set(new_idx)

    def open_new_session(self):
        ip = self.ip_entry.get().strip()
        dtype = self.type_combo.get()
        use_ssh = self.use_ssh_var.get()
        if not ip: return
        self.launch_session(ip, dtype, use_ssh)

    def launch_session(self, ip, dtype, use_ssh=True):
        if dtype == "8841":
            Cisco8841Phone(self.root, ip, dtype, use_ssh)
        elif dtype == "7911":
            Cisco7911Phone(self.root, ip, dtype, use_ssh)
        elif dtype == "7945":
            Cisco7945Phone(self.root, ip, dtype, use_ssh)
        else:
            messagebox.showerror("Error", f"Unknown device type: {dtype}")

    def save_current_session(self):
        ip = self.ip_entry.get().strip()
        dtype = self.type_combo.get()
        if not ip: return
        name = simpledialog.askstring("Save Session", "Enter name for this session:")
        if name:
            self.sessions.append({"name": name, "ip": ip, "type": dtype})
            self.save_sessions()
            self.refresh_tree()

    def open_selected_session(self):
        selected = self.tree.selection()
        if not selected: return
        sess = self.sessions[int(selected[0])]
        use_ssh = self.use_ssh_var.get()
        self.launch_session(sess['ip'], sess['type'], use_ssh)

    def edit_preset(self):
        selected = self.tree.selection()
        if not selected: return
        idx = int(selected[0])
        sess = self.sessions[idx]
        
        name = simpledialog.askstring("Edit Preset", "Name:", initialvalue=sess['name'])
        if name is None: return
        ip = simpledialog.askstring("Edit Preset", "IP Address:", initialvalue=sess['ip'])
        if ip is None: return
        
        self.sessions[idx] = {"name": name, "ip": ip, "type": sess['type']}
        self.save_sessions()
        self.refresh_tree()

    def delete_session(self):
        selected = self.tree.selection()
        if not selected: return
        idx = int(selected[0])
        name = self.sessions[idx]['name']
        if messagebox.askyesno("Delete", f"Delete preset '{name}'?"):
            self.sessions.pop(idx)
            self.save_sessions()
            self.refresh_tree()

    def on_closing(self):
        if self.active_sessions:
            if messagebox.askyesno("Confirm Exit", f"There are {len(self.active_sessions)} active sessions. Still want to close the manager?"):
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = HomePage(root)
    root.mainloop()