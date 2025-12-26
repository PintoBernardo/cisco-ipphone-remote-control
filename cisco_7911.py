import tkinter as tk
from cisco_core import CiscoBasePhone

class Cisco7911Phone(CiscoBasePhone):
    def set_screen_dims(self):
        self.screen_w, self.screen_h = 192, 64

    def build_ui(self):
        # Create a container for the top section (voicemail, screen, line status label)
        top_section_container = tk.Frame(self.main_container, bg="#121212")
        top_section_container.pack(fill="x", pady=10)
        
        # Grid configuration for top_section_container
        top_section_container.grid_columnconfigure(0, weight=0)
        top_section_container.grid_columnconfigure(1, weight=1)
        top_section_container.grid_columnconfigure(2, weight=0)
        top_section_container.grid_rowconfigure(0, weight=1)

        # Voicemail light
        vm_f = tk.Frame(top_section_container, bg="#121212")
        vm_f.grid(row=0, column=0, padx=5, sticky="ns")
        self.voicemail_canvas = tk.Canvas(vm_f, width=20, height=20, bg="#121212", highlightthickness=0)
        self.voicemail_canvas.pack(pady=5)
        self.circle_id = self.voicemail_canvas.create_oval(2, 2, 18, 18, fill="black")

        # Screen Frame - centers the canvas
        sf = tk.Frame(top_section_container, bg="#121212", bd=2, relief="sunken")
        sf.grid(row=0, column=1, padx=5, sticky="nsew")
        self.screen_canvas = tk.Canvas(sf, width=self.screen_w, height=self.screen_h, bg="black", highlightthickness=0)
        self.screen_canvas.pack(expand=True, fill="both")
        
        # Single Line Status Button
        line_status_f = tk.Frame(top_section_container, bg="#121212")
        line_status_f.grid(row=0, column=2, padx=5, sticky="ns")
        
        # Get line key config
        line_keys = self.config.get('line_keys', {})
        line_1_uri = line_keys.get('Line 1')
        
        line_label_button = tk.Button(
            line_status_f, 
            text="●", 
            width=3, 
            bg="#1a1a1a",
            fg="#555555", 
            relief="flat", 
            font=("Segoe UI", 10, "bold"), 
            activebackground="#333", 
            pady=7,
            command=lambda: self.press(line_1_uri) if line_1_uri else None
        )
        line_label_button.pack(pady=15, fill="x")
        self.line_key_buttons.append(line_label_button)
        self.add_log("build_ui", f"Created line key button for Line 1, URI: {line_1_uri}")
        
        # Softkeys
        skf = tk.Frame(self.main_container, bg="#121212")
        skf.pack(pady=5, fill="x")
        softkeys = self.config.get('softkeys', {})
        for l, u in softkeys.items():
            tk.Button(skf, text=l.upper(), width=14, bg="#34495e" if u else "#1a1a1a", fg="#00d2ff" if u else "#555555", relief="flat", font=("Segoe UI", 8, "bold"), activebackground="#2c3e50" if u else "#1a1a1a", command=lambda x=u: self.press(x) if x else None).pack(side="left", padx=5, expand=True)

        # Dial/Control Section
        mid_f = tk.Frame(self.main_container, bg="#121212")
        mid_f.pack(pady=10)
        ak = self.config.get('app_keys', {})
        
        # Apps & Hold
        cf = tk.Frame(mid_f, bg="#121212")
        cf.grid(row=0, column=0, padx=10)
        hold_uri = ak.get('HOLD')
        tk.Button(cf, text="HOLD", width=12, bg="#d35400" if hold_uri else "#1a1a1a", fg="white" if hold_uri else "#555555", relief="flat", font=("Segoe UI", 8, "bold"), activebackground="#c0392b" if hold_uri else "#1a1a1a", command=lambda: self.press(hold_uri) if hold_uri else None).pack(pady=5)
        menu_uri = ak.get('MENU')
        tk.Button(cf, text="MENU", width=12, bg="#2c3e50" if menu_uri else "#1a1a1a", fg="white" if menu_uri else "#555555", relief="flat", font=("Segoe UI", 8, "bold"), activebackground="#1e1e1e" if menu_uri else "#1a1a1a", command=lambda: self.press(menu_uri) if menu_uri else None).pack(pady=5)

        # Nav
        nf = tk.Frame(mid_f, bg="#121212")
        nf.grid(row=0, column=1, padx=10)
        nk = self.config.get('nav_keys', {})
        up_uri = nk.get('Up')
        tk.Button(nf, text="▲", width=6, bg="#333" if up_uri else "#1a1a1a", fg="white" if up_uri else "#555555", relief="flat", font=("Segoe UI", 9, "bold"), activebackground="#444" if up_uri else "#1a1a1a", command=lambda: self.press(up_uri) if up_uri else None).pack()
        select_uri = nk.get('Select')
        tk.Button(nf, text="Select", width=6, bg="#2980b9" if select_uri else "#1a1a1a", fg="white" if select_uri else "#555555", relief="flat", font=("Segoe UI", 9, "bold"), activebackground="#1e5a8a" if select_uri else "#1a1a1a", command=lambda: self.press(select_uri) if select_uri else None).pack(pady=2)
        down_uri = nk.get('Down')
        tk.Button(nf, text="▼", width=6, bg="#333" if down_uri else "#1a1a1a", fg="white" if down_uri else "#555555", relief="flat", font=("Segoe UI", 9, "bold"), activebackground="#444" if down_uri else "#1a1a1a", command=lambda: self.press(down_uri) if down_uri else None).pack()

        # Volume
        vf = tk.Frame(mid_f, bg="#121212")
        vf.grid(row=0, column=2, padx=10)
        vol_up_uri = ak.get('VOL_UP')
        tk.Button(vf, text="VOL +", width=10, bg="#555" if vol_up_uri else "#1a1a1a", fg="white" if vol_up_uri else "#555555", relief="flat", font=("Segoe UI", 8, "bold"), activebackground="#666" if vol_up_uri else "#1a1a1a", command=lambda: self.press(vol_up_uri) if vol_up_uri else None).pack(pady=5)
        vol_down_uri = ak.get('VOL_DOWN')
        tk.Button(vf, text="VOL -", width=10, bg="#555" if vol_down_uri else "#1a1a1a", fg="white" if vol_down_uri else "#555555", relief="flat", font=("Segoe UI", 8, "bold"), activebackground="#666" if vol_down_uri else "#1a1a1a", command=lambda: self.press(vol_down_uri) if vol_down_uri else None).pack(pady=5)

        # Keypad
        kf = tk.Frame(self.main_container, bg="#121212")
        kf.pack(pady=10)
        kd = self.config.get('keypad', {})
        for r, row in enumerate([["1","2","3"], ["4","5","6"], ["7","8","9"], ["*","0","#"]]):
            for c, val in enumerate(row):
                uri = kd.get(val)
                tk.Button(kf, text=val, width=6, bg="#2a2a2a" if uri else "#1a1a1a", fg="white" if uri else "#555555", relief="flat", font=("Segoe UI", 10), activebackground="#444" if uri else "#1a1a1a", command=lambda u=uri: self.press(u) if u else None).grid(row=r, column=c, padx=2, pady=2)

        # Footer
        ff = tk.Frame(self.main_container, bg="#1e1e1e")
        ff.pack(fill="x", side="bottom")
        tk.Button(ff, text="CONSOLE LOGS", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"), relief="flat", command=self.toggle_logs).pack(side="left", padx=10, pady=5)
        tk.Button(ff, text="RELOAD CONFIG", bg="#34495e", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", command=self.reload_btn_config).pack(side="left", padx=5)
        self.countdown_label = tk.Label(ff, text="Next Refresh: 5s", bg="#1e1e1e", fg="#0F0", font=("Segoe UI", 9, "bold"))
        self.countdown_label.pack(side="left", padx=20)
        tk.Button(ff, text="REFRESH SCREEN", bg="#27ae60", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", command=self.refresh_screen).pack(side="right", padx=10)