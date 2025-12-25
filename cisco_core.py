import os, paramiko, io, json, threading, time, subprocess, sys
from PIL import Image, ImageTk
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox  # FIXED: Added missing imports

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_config_dir():
    """Consistency helper to find the persistent AppData folder so settings load correctly"""
    if getattr(sys, 'frozen', False):
        if os.name == 'nt':
            base_dir = os.path.join(os.environ.get('APPDATA', ''), 'CGI_Remote_Control')
        else:
            base_dir = os.path.join(os.path.expanduser('~'), '.cgi_remote_control')
    else:
        # If running as script, check for 'config' folder
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
    return base_dir

class CiscoBasePhone(tk.Toplevel):
    def __init__(self, parent, phone_ip, device_type, connection_mode, ssh_config_name="default", cgi_config_name="default"):
        super().__init__(parent)
        self.phone_ip = phone_ip
        self.device_type = device_type
        self.connection_mode = connection_mode
        self.ssh_config_name = ssh_config_name
        self.cgi_config_name = cgi_config_name
        self.title(f"Cisco {device_type} - {phone_ip} ({connection_mode.upper()}: {ssh_config_name if connection_mode == 'ssh' else 'Direct'})")
        self.configure(bg="#121212")
        
        # FIXED: Use the persistent path for keys
        self.config_file = os.path.join(get_config_dir(), f"keys_{device_type}.json")
        
        self.log_extra_window = None
        self.log_txt = None
        self.log_history = []
        self.is_refreshing = False
        self.refresh_interval = 5 
        self.time_left = self.refresh_interval
        self.waiting_for_image = False 

        # Track this session in the home page
        self.parent_app = parent
        if hasattr(self.parent_app, 'active_sessions'):
            self.parent_app.active_sessions.append(self)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.set_screen_dims()
        
        self.main_container = tk.Frame(self, bg="#121212")
        self.main_container.pack(fill="both", expand=True)

        self.load_config()
        self.cgi_configs = self.load_cgi_configs()
        cgi_config = self.cgi_configs.get(self.cgi_config_name, self.cgi_configs.get("default"))
        self.CGI_USER = cgi_config["user"]
        self.CGI_PASS = cgi_config["pass"]
        if not self.setup_ssh():
            # SSH connection failed, close the window
            if hasattr(self.parent_app, 'active_sessions'):
                if self in self.parent_app.active_sessions:
                    self.parent_app.active_sessions.remove(self)
            self.destroy()
            return
        self.build_ui()
        self.add_log("system", f"Started Remote Control for {self.phone_ip}")
        self.refresh_loop()
        self.refresh_screen()
        try:
            icon_p = resource_path("icon.ico")
            if os.path.exists(icon_p):
                self.root.iconbitmap(icon_p)
                icon_p = resource_path("icon.png")
        except: pass
        

    def set_screen_dims(self):
        self.screen_w, self.screen_h = 480, 272

    def add_log(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        text = f"[{timestamp}] [{category.upper()}] {message}\n"
        entry = {"type": "text", "content": text}
        self.log_history.append(entry)
        self._append_to_log_widget(entry)

    def add_image_log(self, img):
        thumb_w = 120
        thumb_h = int(thumb_w * self.screen_h / self.screen_w)
        log_img = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(log_img)
        entry = {"type": "image", "content": photo}
        self.log_history.append(entry)
        self._append_to_log_widget(entry)

    def _append_to_log_widget(self, entry):
        def _task():
            if not self.winfo_exists(): return
            # Check if log window exists and is open
            if self.log_extra_window and self.log_extra_window.winfo_exists():
                try:
                    self.log_txt.config(state=tk.NORMAL)
                    if entry["type"] == "text":
                        self.log_txt.insert(tk.END, entry["content"])
                    elif entry["type"] == "image":
                        self.log_txt.image_create(tk.END, image=entry["content"])
                        self.log_txt.insert(tk.END, "\n")
                    self.log_txt.config(state=tk.DISABLED)
                    self.log_txt.see(tk.END)
                except Exception:
                    pass
        self.after(0, _task)

    def load_config(self):
        try:
            # Check persistent path first
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                # Fallback to resource_path for default keys bundled in EXE
                fallback_path = resource_path(f"config/keys_{self.device_type}.json")
                if os.path.exists(fallback_path):
                    with open(fallback_path, 'r') as f:
                        self.config = json.load(f)
                else:
                    self.config = {}
                    self.add_log("error", f"Config file not found")
        except Exception as e: 
            self.add_log("error", f"JSON Error: {e}")

    def load_ssh_configs(self):
        # FIXED: Use persistent path so it finds profiles created in the UI
        ssh_conf_path = os.path.join(get_config_dir(), "ssh.conf")
        if os.path.exists(ssh_conf_path):
            try:
                with open(ssh_conf_path, 'r') as f:
                    return json.load(f)
            except:
                return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}
        else:
            return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}

    def load_cgi_configs(self):
        cgi_conf_path = os.path.join(get_config_dir(), "cgi.conf")
        if os.path.exists(cgi_conf_path):
            try:
                with open(cgi_conf_path, 'r') as f:
                    return json.load(f)
            except:
                return {"default": {"user": "admin_admin", "pass": "alka"}}
        else:
            return {"default": {"user": "admin_admin", "pass": "alka"}}

    def setup_ssh(self):
        if self.connection_mode == "local":
            self.add_log("system", "Using local/direct connection mode")
            return True
        
        self.ssh_configs = self.load_ssh_configs()
        # Ensure we use the exact profile name selected in main.py
        config = self.ssh_configs.get(self.ssh_config_name, self.ssh_configs.get("default"))
        self.SSH_HOST = config["host"]
        self.SSH_USER = config["user"]
        self.SSH_PASS = config["pass"]
        
        self.add_log("system", f"Connecting to SSH Host: {self.SSH_HOST} (Profile: {self.ssh_config_name})...")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try: 
            self.ssh.connect(self.SSH_HOST, username=self.SSH_USER, password=self.SSH_PASS, timeout=15)
            self.add_log("system", "SSH Connection Established")
            return True
        except Exception as e: 
            self.add_log("error", f"SSH Connection Failed: {e}")
            messagebox.showerror("SSH Connection Error", f"Failed to connect to SSH bridge: {self.ssh_config_name}\n\nError: {str(e)}")
            return False

    def exec_cmd(self, cmd):
        if self.connection_mode == "local":
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                return result.stdout.encode(), result.stderr.encode()
            except subprocess.TimeoutExpired:
                return b"", b"Command timed out"
            except Exception as e:
                return b"", str(e).encode()
        else:
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            return stdout.read(), stderr.read()

    def refresh_screen(self):
        if self.is_refreshing: return
        self.waiting_for_image = True 
        threading.Thread(target=self._fetch_image_thread, daemon=True).start()

    def _fetch_image_thread(self):
        self.is_refreshing = True
        # Basic Cisco Screen Shot CGI
        cmd = f"curl -s -u {self.CGI_USER}:{self.CGI_PASS} http://{self.phone_ip}/CGI/Screenshot"
        try:
            img_data, err_data = self.exec_cmd(cmd)
            if img_data and len(img_data) > 500:
                img = Image.open(io.BytesIO(img_data))
                self.add_image_log(img)
                img_display = img.resize((self.screen_w, self.screen_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_display)
                self.after(0, self._update_canvas, photo)
            else:
                err_msg = err_data.decode().strip() if err_data else "No data received"
                self.add_log("error", f"Screenshot failed. {err_msg}")
        except Exception as e:
            self.add_log("error", f"Screenshot error: {e}")
        finally:
            self.is_refreshing = False
            self.waiting_for_image = False 
            self.time_left = self.refresh_interval 

    def press(self, uri):
        if not uri: return
        self.time_left = self.refresh_interval
        def _send():
            payload = f"XML=<CiscoIPPhoneExecute><ExecuteItem URL='{uri}'/></CiscoIPPhoneExecute>"
            cmd = f"curl -s -u {self.CGI_USER}:{self.CGI_PASS} --data-urlencode \"{payload}\" http://{self.phone_ip}/CGI/Execute"
            self.add_log("key_send", f"CURL: {cmd}")
            resp_data, err_data = self.exec_cmd(cmd)
            resp = resp_data.decode().strip() if resp_data else ""
            err = err_data.decode().strip() if err_data else ""
            if resp: self.add_log("cgi_resp", resp)
            if err: self.add_log("error", err)
            self.after(400, self.refresh_screen)
        threading.Thread(target=_send, daemon=True).start()

    def _update_canvas(self, photo):
        if not self.winfo_exists(): return
        self.phone_display = photo
        if hasattr(self, 'screen_canvas') and self.screen_canvas.winfo_exists():
            self.screen_canvas.create_image(0, 0, anchor="nw", image=self.phone_display)

    def toggle_logs(self):
        if self.log_extra_window is None or not self.log_extra_window.winfo_exists():
            self.log_extra_window = tk.Toplevel(self)
            self.log_extra_window.title(f"Logs - {self.phone_ip}")
            self.log_extra_window.geometry("600x400")
            self.log_txt = scrolledtext.ScrolledText(
                self.log_extra_window, 
                bg="#000", 
                fg="#0F0", 
                font=("Consolas", 9), 
                state=tk.DISABLED
            )
            self.log_txt.pack(fill="both", expand=True)
            self.log_txt.config(state=tk.NORMAL)
            for entry in self.log_history:
                if entry["type"] == "text":
                    self.log_txt.insert(tk.END, entry["content"])
                elif entry["type"] == "image":
                    self.log_txt.image_create(tk.END, image=entry["content"])
                    self.log_txt.insert(tk.END, "\n")
            self.log_txt.config(state=tk.DISABLED)
            self.log_txt.see(tk.END)
        else:
            self.log_extra_window.destroy()
            self.log_extra_window = None

    def refresh_loop(self):
        if not self.waiting_for_image:
            if self.time_left <= 0: 
                self.refresh_screen()
            else: 
                self.time_left -= 1
        
        if hasattr(self, 'countdown_label'):
            status = "FETCHING..." if self.waiting_for_image else f"Next Refresh: {self.time_left}s"
            self.countdown_label.config(text=status)
        self.after(1000, self.refresh_loop)

    def reload_btn_config(self):
        self.load_config()
        for widget in self.main_container.winfo_children(): 
            widget.destroy()
        self.build_ui()

    def on_close(self):
        if hasattr(self.parent_app, 'active_sessions') and self in self.parent_app.active_sessions:
            self.parent_app.active_sessions.remove(self)
        if self.log_extra_window and self.log_extra_window.winfo_exists():
            self.log_extra_window.destroy()
        if hasattr(self, 'ssh') and self.ssh:
            try:
                self.ssh.close()
            except:
                pass
        self.destroy()

    def build_ui(self):
        # Base UI Elements (overridden by child classes but used as fallback)
        self.screen_canvas = tk.Canvas(self.main_container, width=self.screen_w, height=self.screen_h, bg="black")
        self.screen_canvas.pack(pady=10)
        self.countdown_label = tk.Label(self.main_container, text="", bg="#121212", fg="white")
        self.countdown_label.pack()
        btn_frame = tk.Frame(self.main_container, bg="#121212")
        btn_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(btn_frame, text="Toggle Logs", command=self.toggle_logs).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Refresh Now", command=self.refresh_screen).pack(side="left", padx=5)