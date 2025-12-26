import os, paramiko, io, json, threading, time, subprocess, sys
from PIL import Image, ImageTk
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
import xml.etree.ElementTree as ET

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
        
        self.line_key_buttons = []
        self.voicemail_canvas = None
        self.circle_id = None
        
        self.LINE_STATE_COLORS = {
            "IDLE": ("#1a1a1a", "#555555"),
            "INACTIVE": ("#1a1a1a", "#555555"),
            "ONHOOK": ("#1a1a1a", "#555555"),
            "RINGING": ("#ff6b00", "white"),
            "CONNECTED": ("#00ff00", "black"),
            "ONHOLD": ("#ffff00", "black"),
            "REMOTELY_IN_USE": ("#ff0000", "white"),
            "REGISTERING": ("#ff6b00", "white"),
            "BLF_UNKNOWN": ("#1a1a1a", "#555555"),
            "BLF_BUSY": ("#ff0000", "white"),
            "OFFHOOK": ("#00ff00", "black"),
            "UNKNOWN": ("#1a1a1a", "#555555")
        }
        
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
        
        print(f"DEBUG: Application using config directory: {get_config_dir()}")

        if not self.setup_ssh():
            if hasattr(self.parent_app, 'active_sessions'):
                if self in self.parent_app.active_sessions:
                    self.parent_app.active_sessions.remove(self)
            self.destroy()
            return
            
        self.build_ui()
        self.check_voicemail()
        self.check_line_status()
        self.add_log("system", f"Started Remote Control for {self.phone_ip}")
        self.refresh_loop()
        self.refresh_screen()
        
        try:
            icon_p = resource_path("icon.ico")
            if os.path.exists(icon_p):
                self.iconbitmap(icon_p)
        except: 
            pass

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
            if not self.winfo_exists(): 
                return
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
        self.add_log("config_load", f"Attempting to load config from {self.config_file}")
        try:
            if os.path.exists(self.config_file):
                self.add_log("config_load", f"Config file found at {self.config_file}")
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                self.add_log("config_load", f"Config loaded successfully from {self.config_file}")
            else:
                self.add_log("config_load", f"Config file not found at {self.config_file}. Checking fallback path.")
                fallback_path = resource_path(f"config/keys_{self.device_type}.json")
                if os.path.exists(fallback_path):
                    self.add_log("config_load", f"Fallback config found at {fallback_path}")
                    with open(fallback_path, 'r') as f:
                        self.config = json.load(f)
                    self.add_log("config_load", f"Fallback config loaded successfully from {fallback_path}")
                else:
                    self.config = {}
                    self.add_log("warning", f"No config file found. Loading empty default config.")
        except json.JSONDecodeError as e: 
            self.config = {}
            self.add_log("error", f"JSON decoding error in {self.config_file}: {e}. Loading empty default config.")
        except Exception as e: 
            self.config = {}
            self.add_log("error", f"Error loading {self.config_file}: {e}. Loading empty default config.")

    def load_ssh_configs(self):
        ssh_conf_path = os.path.join(get_config_dir(), "ssh.conf")
        self.add_log("config_load", f"Attempting to load SSH configs from {ssh_conf_path}")
        if os.path.exists(ssh_conf_path):
            self.add_log("config_load", f"SSH config file found at {ssh_conf_path}")
            try:
                with open(ssh_conf_path, 'r') as f:
                    configs = json.load(f)
                self.add_log("config_load", f"SSH configs loaded successfully from {ssh_conf_path}")
                return configs
            except json.JSONDecodeError as e:
                self.add_log("error", f"JSON decoding error in {ssh_conf_path}: {e}. Loading default SSH config.")
                return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}
            except Exception as e:
                self.add_log("error", f"Error loading SSH configs from {ssh_conf_path}: {e}. Loading default SSH config.")
                return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}
        else:
            self.add_log("warning", f"SSH config file not found at {ssh_conf_path}. Loading default SSH config.")
            return {"default": {"host": "127.0.0.1", "user": "admin", "pass": "password"}}

    def load_cgi_configs(self):
        cgi_conf_path = os.path.join(get_config_dir(), "cgi.conf")
        self.add_log("config_load", f"Attempting to load CGI configs from {cgi_conf_path}")
        if os.path.exists(cgi_conf_path):
            self.add_log("config_load", f"CGI config file found at {cgi_conf_path}")
            try:
                with open(cgi_conf_path, 'r') as f:
                    configs = json.load(f)
                self.add_log("config_load", f"CGI configs loaded successfully from {cgi_conf_path}")
                return configs
            except json.JSONDecodeError as e:
                self.add_log("error", f"JSON decoding error in {cgi_conf_path}: {e}. Loading default CGI config.")
                return {"default": {"user": "admin", "pass": "admin"}}
            except Exception as e:
                self.add_log("error", f"Error loading CGI configs from {cgi_conf_path}: {e}. Loading default CGI config.")
                return {"default": {"user": "admin", "pass": "admin"}}
        else:
            self.add_log("warning", f"CGI config file not found at {cgi_conf_path}. Loading default CGI config.")
            return {"default": {"user": "admin", "pass": "admin"}}

    def setup_ssh(self):
        if self.connection_mode == "local":
            self.add_log("system", "Using local/direct connection mode")
            return True
        
        self.ssh_configs = self.load_ssh_configs()
        config = self.ssh_configs.get(self.ssh_config_name, self.ssh_configs.get("default"))
        self.SSH_HOST = config["host"]
        self.SSH_USER = config["user"]
        self.SSH_PASS = config["pass"]
        
        self.add_log("system", f"Connecting to SSH Host: {self.SSH_HOST} (Profile: {self.ssh_config_name})...")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Use banner_timeout and auth_timeout to prevent hanging
            self.ssh.connect(
                self.SSH_HOST, 
                username=self.SSH_USER, 
                password=self.SSH_PASS, 
                timeout=10,
                banner_timeout=10,
                auth_timeout=10,
                look_for_keys=False,
                allow_agent=False
            )
            self.add_log("system", "SSH Connection Established")
            return True
        except paramiko.AuthenticationException:
            self.add_log("error", "SSH Authentication Failed - Check username/password")
            messagebox.showerror("SSH Authentication Error", f"Failed to authenticate to SSH bridge: {self.ssh_config_name}\n\nPlease check your username and password in the SSH configuration.")
            return False
        except paramiko.SSHException as e:
            self.add_log("error", f"SSH Error: {e}")
            messagebox.showerror("SSH Error", f"SSH connection error: {str(e)}")
            return False
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
        if self.is_refreshing: 
            return
        self.waiting_for_image = True 
        threading.Thread(target=self._fetch_image_thread, daemon=True).start()
        self.check_voicemail()
        self.check_line_status()

    def _fetch_image_thread(self):
        self.is_refreshing = True
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
        if not uri: 
            return
        self.time_left = self.refresh_interval
        def _send():
            payload = f"XML=<CiscoIPPhoneExecute><ExecuteItem URL='{uri}'/></CiscoIPPhoneExecute>"
            cmd = f"curl -s -u {self.CGI_USER}:{self.CGI_PASS} --data-urlencode \"{payload}\" http://{self.phone_ip}/CGI/Execute"
            self.add_log("key_send", f"CURL: {cmd}")
            resp_data, err_data = self.exec_cmd(cmd)
            resp = resp_data.decode().strip() if resp_data else ""
            err = err_data.decode().strip() if err_data else ""
            if resp: 
                self.add_log("cgi_resp", resp)
            if err: 
                self.add_log("error", err)
            self.after(400, self.refresh_screen)
        threading.Thread(target=_send, daemon=True).start()

    def _update_canvas(self, photo):
        if not self.winfo_exists(): 
            return
        self.phone_display = photo
        if hasattr(self, 'screen_canvas') and self.screen_canvas.winfo_exists():
            self.screen_canvas.create_image(0, 0, anchor="nw", image=self.phone_display)

    def check_voicemail(self):
        threading.Thread(target=self._check_voicemail_thread, daemon=True).start()

    def _check_voicemail_thread(self):
        cmd = f"curl -s -u {self.CGI_USER}:{self.CGI_PASS} http://{self.phone_ip}/CGI/LineInfo"
        self.add_log("voicemail_check", f"CURL: {cmd}")
        try:
            data, err = self.exec_cmd(cmd)
            if data:
                root = ET.fromstring(data.decode())
                has_voicemail = any(mw.text == 'YES' for mw in root.iter('MessageWaiting'))
                self.after(0, self._update_voicemail_ui, has_voicemail)
            else:
                self.add_log("error", "Failed to fetch LineInfo")
        except Exception as e:
            self.add_log("error", f"Voicemail check error: {e}")

    def _update_voicemail_ui(self, has_voicemail):
        if hasattr(self, 'voicemail_canvas') and self.voicemail_canvas and self.voicemail_canvas.winfo_exists():
            if has_voicemail:
                self.voicemail_canvas.itemconfig(self.circle_id, fill="red")
                self.add_log("voicemail_ui", "Voicemail light set to RED (Message Waiting)")
            else:
                self.voicemail_canvas.itemconfig(self.circle_id, fill="black")
                self.add_log("voicemail_ui", "Voicemail light set to BLACK (No Message)")
    
    def check_line_status(self):
        threading.Thread(target=self._check_line_status_thread, daemon=True).start()

    def _check_line_status_thread(self):
        cmd = f"curl -s -u {self.CGI_USER}:{self.CGI_PASS} http://{self.phone_ip}/CGI/LineInfo"
        self.add_log("line_status_request", f"CURL: {cmd}")
        try:
            data, err = self.exec_cmd(cmd)
            if data:
                # Log the raw XML response for debugging
                xml_str = data.decode()
                self.add_log("line_status_xml", f"Raw XML response:\n{xml_str[:500]}...")
                
                root = ET.fromstring(xml_str)
                line_icon_states = []
                
                # Try multiple possible XML structures
                # Structure 1: Direct LineIconState elements
                for icon_state in root.findall('.//LineIconState'):
                    if icon_state.text:
                        line_icon_states.append(icon_state.text)
                        self.add_log("line_status_parse", f"Found LineIconState: {icon_state.text}")
                
                # Structure 2: Inside CiscoIPPhoneLine elements
                if not line_icon_states:
                    for line in root.findall('.//CiscoIPPhoneLine'):
                        icon_state = line.find('LineIconState')
                        if icon_state is not None and icon_state.text:
                            line_icon_states.append(icon_state.text)
                        else:
                            line_icon_states.append("UNKNOWN")
                
                # Structure 3: Inside Line elements
                if not line_icon_states:
                    for line in root.findall('.//Line'):
                        icon_state = line.find('LineIconState')
                        if icon_state is not None and icon_state.text:
                            line_icon_states.append(icon_state.text)
                        else:
                            line_icon_states.append("UNKNOWN")
                
                self.add_log("line_status_response", f"Found {len(line_icon_states)} line states: {line_icon_states}")
                
                if line_icon_states:
                    self.after(0, self._update_line_key_ui, line_icon_states)
                else:
                    self.add_log("warning", "No line icon states found in XML response")
            else:
                self.add_log("error", "Failed to fetch LineInfo for line status")
        except Exception as e:
            self.add_log("error", f"Line status check error: {e}")

    def _update_line_key_ui(self, line_icon_states):
        self.add_log("line_key_ui", f"Updating {len(line_icon_states)} line keys from {len(self.line_key_buttons)} buttons")
        for i, icon_state in enumerate(line_icon_states):
            if i < len(self.line_key_buttons):
                button = self.line_key_buttons[i]
                if button and button.winfo_exists():
                    colors = self.LINE_STATE_COLORS.get(icon_state.upper(), ("dark gray", "white"))
                    bg_color, fg_color = colors
                    button.config(bg=bg_color, fg=fg_color)
                    self.add_log("line_key_ui", f"Line key {i+1} updated to {icon_state} (BG: {bg_color}, FG: {fg_color})")
                else:
                    self.add_log("line_key_ui", f"Line key button {i+1} no longer exists")
            else:
                self.add_log("line_key_ui", f"No button found for line {i+1} (State: {icon_state})")

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
        
        if hasattr(self, 'countdown_label') and self.countdown_label.winfo_exists():
            status = "FETCHING..." if self.waiting_for_image else f"Next Refresh: {self.time_left}s"
            self.countdown_label.config(text=status)
        self.after(1000, self.refresh_loop)

    def reload_btn_config(self):
        self.load_config()
        self.check_line_status()
        for widget in self.main_container.winfo_children(): 
            widget.destroy()
        self.line_key_buttons = []
        self.build_ui()
        self.refresh_screen()

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
        # Base UI Elements (overridden by child classes)
        self.screen_canvas = tk.Canvas(self.main_container, width=self.screen_w, height=self.screen_h, bg="black")
        self.screen_canvas.pack(pady=10)
        self.countdown_label = tk.Label(self.main_container, text="", bg="#121212", fg="white")
        self.countdown_label.pack()
        btn_frame = tk.Frame(self.main_container, bg="#121212")
        btn_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(btn_frame, text="Toggle Logs", command=self.toggle_logs).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Refresh Now", command=self.refresh_screen).pack(side="left", padx=5)