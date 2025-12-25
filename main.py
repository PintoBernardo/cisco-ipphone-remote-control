from tkinter import simpledialog, messagebox, ttk, Tk
import tkinter as tk
import os, json, sys
from dotenv import load_dotenv
from PIL import Image, ImageTk
from cisco_core import resource_path

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# Import phone versions
from cisco_8841 import Cisco8841Phone
from cisco_7911 import Cisco7911Phone
from cisco_7945 import Cisco7945Phone

def get_config_dir():
    if getattr(sys, 'frozen', False):
        if os.name == 'nt':
            base_dir = os.path.join(os.environ.get('APPDATA', ''), 'CGI_Remote_Control')
        else:
            base_dir = os.path.join(os.path.expanduser('~'), '.cgi_remote_control')
    else:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
    return base_dir

# Initialize paths
load_dotenv()
config_dir = get_config_dir()
SESSIONS_FILE = os.path.join(config_dir, "sessions.json")
SSH_FILE = os.path.join(config_dir, "ssh.conf")
CGI_FILE = os.path.join(config_dir, "cgi.conf")

# Default Files Setup
if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, 'w') as f: json.dump([], f)
if not os.path.exists(SSH_FILE):
    with open(SSH_FILE, 'w') as f: 
        json.dump({"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}, f, indent=4)
if not os.path.exists(CGI_FILE):
    with open(CGI_FILE, 'w') as f: 
        json.dump({"default": {"user": "admin", "pass": "admin"}}, f, indent=4)


ssh_conf_path = os.path.join(config_dir, "ssh.conf")
if not os.path.exists(ssh_conf_path):
    default_ssh = {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}
    with open(ssh_conf_path, 'w') as f:
        json.dump(default_ssh, f, indent=4)

# Create default key files if not exist
for device in ["7911", "7945", "8841"]:
    key_file = os.path.join(config_dir, f"keys_{device}.json")
    if not os.path.exists(key_file):
        with open(key_file, 'w') as f:
            json.dump({}, f)

class MultiFieldDialog:
    def __init__(self, parent, title, fields, dropdowns=None):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x350")
        self.dialog.configure(bg="#121212")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        tk.Label(self.dialog, text=title, bg="#121212", fg="#00d2ff", 
                 font=("Segoe UI", 12, "bold")).pack(pady=(15, 10))
        
        self.entries = {}
        if dropdowns is None:
            dropdowns = {}
        
        for field_name, field_label, initial_value in fields:
            frame = tk.Frame(self.dialog, bg="#121212")
            frame.pack(fill="x", padx=20, pady=2)
            
            tk.Label(frame, text=field_label, bg="#121212", fg="#888", 
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            
            if field_name in dropdowns:
                # Create combobox for dropdown fields
                combo = ttk.Combobox(frame, values=dropdowns[field_name], state="readonly", font=("Segoe UI", 10))
                combo.set(initial_value)
                combo.pack(fill="x", pady=(2, 5), ipady=4)
                self.entries[field_name] = combo
            else:
                # Create entry for text fields
                entry = tk.Entry(frame, bg="#1e1e1e", fg="white", insertbackground="white",
                                font=("Consolas", 10), borderwidth=0, highlightthickness=1, 
                                highlightbackground="#444")
                entry.insert(0, initial_value)
                entry.pack(fill="x", pady=(2, 5), ipady=4)
                self.entries[field_name] = entry
        
        btn_frame = tk.Frame(self.dialog, bg="#121212")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        tk.Button(btn_frame, text="SAVE", bg="#121212", fg="#27ae60", font=("Segoe UI", 8, "bold"),
                  relief="flat", command=self.save).pack(side="left")
        tk.Button(btn_frame, text="CANCEL", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"),
                  relief="flat", command=self.cancel).pack(side="right")
        
        self.dialog.bind('<Return>', lambda e: self.save())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        parent.wait_window(self.dialog)
    
    def save(self):
        self.result = {}
        for name, widget in self.entries.items():
            if hasattr(widget, 'get'):  # Entry or Combobox
                self.result[name] = widget.get()
        self.dialog.destroy()
    
    def cancel(self):
        self.result = None
        self.dialog.destroy()

class HomePage:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Phone Control")
        self.root.geometry("1400x900")
        self.root.configure(bg="#121212")

        # Set Icon if exists
        try:
            icon_p = resource_path("icon.ico")
            if os.path.exists(icon_p):
                self.root.iconbitmap(icon_p)
                icon_p = resource_path("icon.png")
        except: pass
        
        self.config_dir = get_config_dir()
        self.sessions_file = os.path.join(self.config_dir, "sessions.json")
        self.sessions = self.load_sessions()
        self.active_sessions = []
        
        # Track popup windows
        self.ssh_manager_window = None
        self.cgi_manager_window = None
        
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
        self.ip_entry.insert(0, "0.0.0.0")
        self.ip_entry.pack(fill="x", pady=(5, 15), ipady=8)
        
        tk.Label(form_f, text="PHONE MODEL", bg="#1e1e1e", fg="#888", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.type_combo = ttk.Combobox(form_f, values=["8841", "7911", "7945"], state="readonly", font=("Segoe UI", 10))
        self.type_combo.set("8841")
        self.type_combo.pack(fill="x", pady=(5, 10))
        
        tk.Label(form_f, text="CONNECTION MODE", bg="#1e1e1e", fg="#888", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.connection_mode = tk.StringVar(value="ssh")
        mode_frame = tk.Frame(form_f, bg="#1e1e1e")
        mode_frame.pack(fill="x", pady=(5, 10))
        
        tk.Radiobutton(mode_frame, text="SSH Bridge", variable=self.connection_mode, value="ssh", 
                      bg="#1e1e1e", fg="#00d2ff", selectcolor="#121212", activebackground="#1e1e1e", 
                      activeforeground="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 20))
        tk.Radiobutton(mode_frame, text="Direct/Local", variable=self.connection_mode, value="local", 
                      bg="#1e1e1e", fg="#888", selectcolor="#121212", activebackground="#1e1e1e", 
                      activeforeground="white", font=("Segoe UI", 9)).pack(side="left")
        
        tk.Label(form_f, text="SSH CONFIG", bg="#1e1e1e", fg="#888", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        ssh_frame = tk.Frame(form_f, bg="#1e1e1e")
        ssh_frame.pack(fill="x", pady=(5, 10))
        self.ssh_combo = ttk.Combobox(ssh_frame, values=self.load_ssh_configs(), state="readonly", font=("Segoe UI", 10))
        self.ssh_combo.set("default")
        self.ssh_combo.pack(side="left", fill="x", expand=True)
        tk.Button(ssh_frame, text="⚙", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=self.open_ssh_manager).pack(side="right", padx=(5, 0))
        
        tk.Label(form_f, text="CGI CONFIG", bg="#1e1e1e", fg="#888", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        cgi_frame = tk.Frame(form_f, bg="#1e1e1e")
        cgi_frame.pack(fill="x", pady=(5, 10))
        self.cgi_combo = ttk.Combobox(cgi_frame, values=self.load_cgi_configs(), state="readonly", font=("Segoe UI", 10))
        self.cgi_combo.set("default")
        self.cgi_combo.pack(side="left", fill="x", expand=True)
        tk.Button(cgi_frame, text="⚙", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=self.open_cgi_manager).pack(side="right", padx=(5, 0))
        
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
        tk.Button(head_f, text="LOAD", bg="#121212", fg="#27ae60", font=("Segoe UI", 8, "bold"), 
                  relief="flat", cursor="hand2", command=self.load_preset_to_form).pack(side="right", padx=5)
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

        self.tree = ttk.Treeview(tree_container, columns=("Name", "Type", "IP", "Connection", "SSH", "CGI"), show="headings", height=10)
        self.tree.heading("Name", text=" NAME")
        self.tree.heading("Type", text=" MODEL")
        self.tree.heading("IP", text=" NETWORK IP")
        self.tree.heading("Connection", text=" MODE")
        self.tree.heading("SSH", text=" SSH CONFIG")
        self.tree.heading("CGI", text=" CGI CONFIG")
        
        self.tree.column("Name", width=100)
        self.tree.column("Type", width=50, anchor="center")
        self.tree.column("IP", width=90, anchor="center")
        self.tree.column("Connection", width=60, anchor="center")
        self.tree.column("SSH", width=70, anchor="center")
        self.tree.column("CGI", width=70, anchor="center")
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.open_selected_session())
        
        tk.Label(right_p, text="* Double-click a row to launch immediately | Use LOAD to edit presets", bg="#121212", fg="#444", font=("Segoe UI", 8, "italic")).pack(pady=5, anchor="e")
        
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

    def load_ssh_configs(self):
        ssh_conf_path = os.path.join(self.config_dir, "ssh.conf")
        if os.path.exists(ssh_conf_path):
            try:
                with open(ssh_conf_path, 'r') as f:
                    configs = json.load(f)
                    return list(configs.keys())
            except:
                return ["default"]
        return ["default"]

    def refresh_ssh_combo(self):
        self.ssh_combo['values'] = self.load_ssh_configs()
        if self.ssh_combo.get() not in self.ssh_combo['values']:
            self.ssh_combo.set("default")

    def load_ssh_dict(self):
        ssh_conf_path = os.path.join(self.config_dir, "ssh.conf")
        if os.path.exists(ssh_conf_path):
            try:
                with open(ssh_conf_path, 'r') as f:
                    return json.load(f)
            except:
                return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}
        return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}

    def save_ssh_dict(self, configs):
        ssh_conf_path = os.path.join(self.config_dir, "ssh.conf")
        with open(ssh_conf_path, 'w') as f:
            json.dump(configs, f, indent=4)

    def refresh_ssh_list(self, manager):
        self.ssh_listbox.delete(0, tk.END)
        configs = self.load_ssh_dict()
        for name in configs:
            self.ssh_listbox.insert(tk.END, name)

    def load_cgi_configs(self):
        cgi_conf_path = os.path.join(self.config_dir, "cgi.conf")
        if os.path.exists(cgi_conf_path):
            try:
                with open(cgi_conf_path, 'r') as f:
                    configs = json.load(f)
                    return list(configs.keys())
            except:
                return ["default"]
        return ["default"]

    def refresh_cgi_combo(self):
        self.cgi_combo['values'] = self.load_cgi_configs()
        if self.cgi_combo.get() not in self.cgi_combo['values']:
            self.cgi_combo.set("default")

    def load_cgi_dict(self):
        cgi_conf_path = os.path.join(self.config_dir, "cgi.conf")
        if os.path.exists(cgi_conf_path):
            try:
                with open(cgi_conf_path, 'r') as f:
                    return json.load(f)
            except:
                return {"default": {"user": "admin", "pass": "admin"}}
        return {"default": {"user": "admin", "pass": "admin"}}

    def save_cgi_dict(self, configs):
        cgi_conf_path = os.path.join(self.config_dir, "cgi.conf")
        with open(cgi_conf_path, 'w') as f:
            json.dump(configs, f, indent=4)

    def refresh_cgi_list(self, manager):
        self.cgi_listbox.delete(0, tk.END)
        configs = self.load_cgi_dict()
        for name in configs:
            self.cgi_listbox.insert(tk.END, name)

    def open_ssh_manager(self):
        # Check if SSH manager is already open
        if self.ssh_manager_window and self.ssh_manager_window.winfo_exists():
            self.ssh_manager_window.lift()
            self.ssh_manager_window.focus_force()
            return
        
        manager = tk.Toplevel(self.root)
        self.ssh_manager_window = manager
        manager.title("SSH Configuration Manager")
        manager.geometry("450x350")
        manager.configure(bg="#121212")
        manager.resizable(False, False)
        
        # Handle window close
        def on_manager_close():
            self.ssh_manager_window = None
            manager.destroy()
        
        manager.protocol("WM_DELETE_WINDOW", on_manager_close)
        
        tk.Label(manager, text="SSH CONFIGURATIONS", bg="#121212", fg="#00d2ff", 
                 font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        # Listbox for configs
        list_frame = tk.Frame(manager, bg="#1e1e1e", bd=1, relief="sunken")
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.ssh_listbox = tk.Listbox(list_frame, bg="#1e1e1e", fg="white", selectbackground="#2980b9", 
                                      font=("Segoe UI", 10), selectmode="single")
        self.ssh_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.refresh_ssh_list(manager)
        
        # Buttons
        btn_frame = tk.Frame(manager, bg="#121212")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        tk.Button(btn_frame, text="ADD", bg="#121212", fg="#27ae60", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=lambda: self.add_ssh_config(manager)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="EDIT", bg="#121212", fg="#f39c12", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=lambda: self.edit_ssh_config(manager)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="DELETE", bg="#121212", fg="#e74c3c", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=lambda: self.delete_ssh_config(manager)).pack(side="left", padx=2)
        
        tk.Button(btn_frame, text="CLOSE", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=on_manager_close).pack(side="right", padx=2)

    def add_ssh_config(self, manager=None):
        fields = [
            ("name", "CONFIG NAME", ""),
            ("host", "HOST", ""),
            ("user", "USERNAME", ""),
            ("pass", "PASSWORD", "")
        ]
        
        dialog = MultiFieldDialog(self.root, "Add SSH Configuration", fields)
        if dialog.result and dialog.result["name"]:
            configs = self.load_ssh_dict()
            if dialog.result["name"] in configs:
                messagebox.showerror("Configuration Error", "An SSH configuration with this name already exists.\n\nPlease choose a different name for your new configuration.")
                return
            configs[dialog.result["name"]] = {
                "host": dialog.result["host"],
                "user": dialog.result["user"], 
                "pass": dialog.result["pass"]
            }
            self.save_ssh_dict(configs)
            self.refresh_ssh_combo()
            if manager:
                self.refresh_ssh_list(manager)
            self.ssh_combo.set(dialog.result["name"])

    def edit_ssh_config(self, manager=None):
        if not manager or not hasattr(self, 'ssh_listbox'):
            messagebox.showerror("SSH Manager Required", "Please open the SSH Configuration Manager first by clicking the settings button next to the SSH dropdown.")
            return
        selection = self.ssh_listbox.curselection()
        if not selection:
            messagebox.showerror("Selection Required", "Please select an SSH configuration from the list to edit.")
            return
        current = self.ssh_listbox.get(selection[0])
        configs = self.load_ssh_dict()
        config = configs[current]
        
        fields = [
            ("host", "HOST", config["host"]),
            ("user", "USERNAME", config["user"]),
            ("pass", "PASSWORD", config["pass"])
        ]
        
        dialog = MultiFieldDialog(self.root, f"Edit SSH Configuration - {current}", fields)
        if dialog.result:
            configs[current] = {
                "host": dialog.result["host"],
                "user": dialog.result["user"],
                "pass": dialog.result["pass"]
            }
            self.save_ssh_dict(configs)
            self.refresh_ssh_combo()
            if manager:
                self.refresh_ssh_list(manager)

    def delete_ssh_config(self, manager=None):
        if not manager or not hasattr(self, 'ssh_listbox'):
            messagebox.showerror("SSH Manager Required", "Please open the SSH Configuration Manager first by clicking the settings button next to the SSH dropdown.")
            return
        selection = self.ssh_listbox.curselection()
        if not selection:
            messagebox.showerror("Selection Required", "Please select an SSH configuration from the list to delete.")
            return
        current = self.ssh_listbox.get(selection[0])
        if current == "default":
            messagebox.showerror("Cannot Delete Default", "The 'default' SSH configuration cannot be deleted as it is required for the application to function.\n\nYou can modify its settings but not remove it.")
            return
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the SSH configuration '{current}'?\n\nThis action cannot be undone."):
            configs = self.load_ssh_dict()
            if current in configs:
                del configs[current]
                self.save_ssh_dict(configs)
                self.refresh_ssh_combo()
                if manager:
                    self.refresh_ssh_list(manager)
                self.ssh_combo.set("default")

    def open_cgi_manager(self):
        # Check if CGI manager is already open
        if self.cgi_manager_window and self.cgi_manager_window.winfo_exists():
            self.cgi_manager_window.lift()
            self.cgi_manager_window.focus_force()
            return
        
        manager = tk.Toplevel(self.root)
        self.cgi_manager_window = manager
        manager.title("CGI Configuration Manager")
        manager.geometry("450x350")
        manager.configure(bg="#121212")
        manager.resizable(False, False)
        
        # Handle window close
        def on_manager_close():
            self.cgi_manager_window = None
            manager.destroy()
        
        manager.protocol("WM_DELETE_WINDOW", on_manager_close)
        
        tk.Label(manager, text="CGI CONFIGURATIONS", bg="#121212", fg="#00d2ff", 
                 font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        # Listbox for configs
        list_frame = tk.Frame(manager, bg="#1e1e1e", bd=1, relief="sunken")
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.cgi_listbox = tk.Listbox(list_frame, bg="#1e1e1e", fg="white", selectbackground="#2980b9", 
                                      font=("Segoe UI", 10), selectmode="single")
        self.cgi_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.refresh_cgi_list(manager)
        
        # Buttons
        btn_frame = tk.Frame(manager, bg="#121212")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        tk.Button(btn_frame, text="ADD", bg="#121212", fg="#27ae60", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=lambda: self.add_cgi_config(manager)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="EDIT", bg="#121212", fg="#f39c12", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=lambda: self.edit_cgi_config(manager)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="DELETE", bg="#121212", fg="#e74c3c", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=lambda: self.delete_cgi_config(manager)).pack(side="left", padx=2)
        
        tk.Button(btn_frame, text="CLOSE", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), 
                  relief="flat", command=on_manager_close).pack(side="right", padx=2)

    def add_cgi_config(self, manager=None):
        fields = [
            ("name", "CONFIG NAME", ""),
            ("user", "USERNAME", ""),
            ("pass", "PASSWORD", "")
        ]
        
        dialog = MultiFieldDialog(self.root, "Add CGI Configuration", fields)
        if dialog.result and dialog.result["name"]:
            configs = self.load_cgi_dict()
            if dialog.result["name"] in configs:
                messagebox.showerror("Configuration Error", "A CGI configuration with this name already exists.\n\nPlease choose a different name for your new configuration.")
                return
            configs[dialog.result["name"]] = {
                "user": dialog.result["user"],
                "pass": dialog.result["pass"]
            }
            self.save_cgi_dict(configs)
            self.refresh_cgi_combo()
            if manager:
                self.refresh_cgi_list(manager)
            self.cgi_combo.set(dialog.result["name"])

    def edit_cgi_config(self, manager=None):
        if not manager or not hasattr(self, 'cgi_listbox'):
            messagebox.showerror("CGI Manager Required", "Please open the CGI Configuration Manager first by clicking the settings button next to the CGI dropdown.")
            return
        selection = self.cgi_listbox.curselection()
        if not selection:
            messagebox.showerror("Selection Required", "Please select a CGI configuration from the list to edit.")
            return
        current = self.cgi_listbox.get(selection[0])
        configs = self.load_cgi_dict()
        config = configs[current]
        
        fields = [
            ("user", "USERNAME", config["user"]),
            ("pass", "PASSWORD", config["pass"])
        ]
        
        dialog = MultiFieldDialog(self.root, f"Edit CGI Configuration - {current}", fields)
        if dialog.result:
            configs[current] = {
                "user": dialog.result["user"],
                "pass": dialog.result["pass"]
            }
            self.save_cgi_dict(configs)
            self.refresh_cgi_combo()
            if manager:
                self.refresh_cgi_list(manager)

    def delete_cgi_config(self, manager=None):
        if not manager or not hasattr(self, 'cgi_listbox'):
            messagebox.showerror("CGI Manager Required", "Please open the CGI Configuration Manager first by clicking the settings button next to the CGI dropdown.")
            return
        selection = self.cgi_listbox.curselection()
        if not selection:
            messagebox.showerror("Selection Required", "Please select a CGI configuration from the list to delete.")
            return
        current = self.cgi_listbox.get(selection[0])
        if current == "default":
            messagebox.showerror("Cannot Delete Default", "The 'default' CGI configuration cannot be deleted as it is required for the application to function.\n\nYou can modify its settings but not remove it.")
            return
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the CGI configuration '{current}'?\n\nThis action cannot be undone."):
            configs = self.load_cgi_dict()
            if current in configs:
                del configs[current]
                self.save_cgi_dict(configs)
                self.refresh_cgi_combo()
                if manager:
                    self.refresh_cgi_list(manager)
                self.cgi_combo.set("default")

    def save_sessions(self):
        with open(self.sessions_file, 'w') as f: json.dump(self.sessions, f, indent=4)

    def refresh_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, sess in enumerate(self.sessions):
            connection = sess.get('connection', 'ssh')  # Default to ssh for backward compatibility
            ssh = sess.get('ssh', 'default') if connection == 'ssh' else 'N/A'
            cgi = sess.get('cgi', 'default')
            self.tree.insert("", "end", iid=i, values=(sess['name'], sess['type'], sess['ip'], connection.upper(), ssh, cgi))

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
        connection_mode = self.connection_mode.get()
        ssh_config = self.ssh_combo.get() if connection_mode == "ssh" else None
        cgi_config = self.cgi_combo.get()
        if not ip: return
        self.launch_session(ip, dtype, connection_mode, ssh_config, cgi_config)

    def launch_session(self, ip, dtype, connection_mode, ssh_config="default", cgi_config="default"):
        if dtype == "8841":
            Cisco8841Phone(self.root, ip, dtype, connection_mode, ssh_config, cgi_config)
        elif dtype == "7911":
            Cisco7911Phone(self.root, ip, dtype, connection_mode, ssh_config, cgi_config)
        elif dtype == "7945":
            Cisco7945Phone(self.root, ip, dtype, connection_mode, ssh_config, cgi_config)
        else:
            messagebox.showerror("Unsupported Device", f"The device type '{dtype}' is not supported by this application.\n\nSupported devices: 8841, 7911, 7945")

    def save_current_session(self):
        ip = self.ip_entry.get().strip()
        dtype = self.type_combo.get()
        connection_mode = self.connection_mode.get()
        ssh_config = self.ssh_combo.get() if connection_mode == "ssh" else None
        cgi_config = self.cgi_combo.get()
        if not ip: return
        
        fields = [
            ("name", "PRESET NAME", ""),
            ("ip", "IP ADDRESS", ip),
            ("connection", "CONNECTION MODE", connection_mode),
            ("ssh", "SSH CONFIG", ssh_config if ssh_config else ""),
            ("cgi", "CGI CONFIG", cgi_config)
        ]
        
        dropdowns = {
            "connection": ["ssh", "local"],
            "ssh": self.load_ssh_configs(),
            "cgi": self.load_cgi_configs()
        }
        
        dialog = MultiFieldDialog(self.root, "Save Preset", fields, dropdowns)
        if dialog.result and dialog.result["name"]:
            self.sessions.append({
                "name": dialog.result["name"], 
                "ip": dialog.result["ip"], 
                "type": dtype, 
                "connection": dialog.result["connection"],
                "ssh": dialog.result["ssh"] if dialog.result["connection"] == "ssh" else None,
                "cgi": dialog.result["cgi"]
            })
            self.save_sessions()
            self.refresh_tree()

    def open_selected_session(self):
        selected = self.tree.selection()
        if not selected: return
        sess = self.sessions[int(selected[0])]
        connection_mode = sess.get('connection', 'ssh')  # Default to ssh for backward compatibility
        ssh_config = sess.get('ssh', 'default') if connection_mode == 'ssh' else None
        self.launch_session(sess['ip'], sess['type'], connection_mode, ssh_config)

    def edit_preset(self):
        selected = self.tree.selection()
        if not selected: return
        idx = int(selected[0])
        sess = self.sessions[idx]
        
        connection_mode = sess.get('connection', 'ssh')  # Default to ssh for backward compatibility
        ssh_config = sess.get('ssh', 'default') if connection_mode == 'ssh' else ''
        cgi_config = sess.get('cgi', 'default')
        
        fields = [
            ("name", "PRESET NAME", sess['name']),
            ("ip", "IP ADDRESS", sess['ip']),
            ("connection", "CONNECTION MODE", connection_mode),
            ("ssh", "SSH CONFIG", ssh_config),
            ("cgi", "CGI CONFIG", cgi_config)
        ]
        
        dropdowns = {
            "connection": ["ssh", "local"],
            "ssh": self.load_ssh_configs(),
            "cgi": self.load_cgi_configs()
        }
        
        dialog = MultiFieldDialog(self.root, "Edit Preset", fields, dropdowns)
        if dialog.result:
            self.sessions[idx] = {
                "name": dialog.result["name"], 
                "ip": dialog.result["ip"], 
                "type": sess['type'], 
                "connection": dialog.result["connection"],
                "ssh": dialog.result["ssh"] if dialog.result["connection"] == "ssh" else None,
                "cgi": dialog.result["cgi"]
            }
            self.save_sessions()
            self.refresh_tree()

    def open_selected_session(self):
        selected = self.tree.selection()
        if not selected: return
        idx = int(selected[0])
        sess = self.sessions[idx]
        connection_mode = sess.get('connection', 'ssh')
        ssh_config = sess.get('ssh', 'default') if connection_mode == 'ssh' else None
        cgi_config = sess.get('cgi', 'default')
        self.launch_session(sess['ip'], sess['type'], connection_mode, ssh_config, cgi_config)

    def load_preset_to_form(self):
        selected = self.tree.selection()
        if not selected: return
        idx = int(selected[0])
        sess = self.sessions[idx]
        
        # Load values into form fields
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, sess.get('ip', ''))
        
        self.type_combo.set(sess.get('type', '8841'))
        
        connection_mode = sess.get('connection', 'ssh')
        self.connection_mode.set(connection_mode)
        
        if connection_mode == 'ssh':
            self.ssh_combo.set(sess.get('ssh', 'default'))
        
        self.cgi_combo.set(sess.get('cgi', 'default'))
        
        messagebox.showinfo("Preset Loaded", f"Preset '{sess['name']}' loaded into form fields. You can now modify and launch.")

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
        # Close any open popup windows
        if self.ssh_manager_window and self.ssh_manager_window.winfo_exists():
            self.ssh_manager_window.destroy()
        if self.cgi_manager_window and self.cgi_manager_window.winfo_exists():
            self.cgi_manager_window.destroy()
        
        if self.active_sessions:
            if messagebox.askyesno("Confirm Exit", f"There are {len(self.active_sessions)} active sessions. Still want to close the manager?"):
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = HomePage(root)
    root.mainloop()