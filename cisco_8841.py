import tkinter as tk
from cisco_core import CiscoBasePhone

class Cisco8841Phone(CiscoBasePhone):
    def set_screen_dims(self):
        self.screen_w, self.screen_h = 480, 272

    def build_ui(self):
        top_f = tk.Frame(self.main_container, bg="#121212")
        top_f.pack(pady=10)
        
        # Voicemail light (placed next to screen)
        vm_f = tk.Frame(top_f, bg="#121212")
        vm_f.grid(row=0, column=0, padx=0, sticky="nw")
        self.voicemail_canvas = tk.Canvas(vm_f, width=20, height=20, bg="#121212", highlightthickness=0)
        self.voicemail_canvas.pack(side="left", padx=5, pady=5)
        self.circle_id = self.voicemail_canvas.create_oval(2, 2, 18, 18, fill="black")

        # Left Side Line Keys (5 keys)
        lk_l = tk.Frame(top_f, bg="#121212")
        lk_l.grid(row=0, column=1, padx=5)
        self.add_log("build_ui", "Building left line keys.")
        left_keys_config = self.config.get('line_keys_left', {})
        for i in range(1, 6):
            line_label = f"Line {i}"
            uri = left_keys_config.get(line_label)
            
            button_text = "●"
            button_command = lambda x=uri: self.press(x) if x else None

            button = tk.Button(lk_l, text=button_text, width=3, bg="#1a1a1a", fg="#555555", 
                              relief="flat", activebackground="#333", font=("Segoe UI", 10, "bold"),
                              command=button_command, pady=7)
            button.pack(pady=10)
            self.line_key_buttons.append(button)
            self.add_log("build_ui", f"Left line key {i}: {line_label}, URI: {uri}")

        # Screen
        sf = tk.Frame(top_f, bg="#121212", bd=2, relief="sunken")
        sf.grid(row=0, column=2, padx=5)
        self.screen_canvas = tk.Canvas(sf, width=self.screen_w, height=self.screen_h, bg="black", highlightthickness=0)
        self.screen_canvas.pack()

        # Right Side Line Keys (5 keys)
        lk_r = tk.Frame(top_f, bg="#121212")
        lk_r.grid(row=0, column=3, padx=5)
        self.add_log("build_ui", "Building right line keys.")
        right_keys_config = self.config.get('line_keys_right', {})
        for i in range(1, 6):
            line_label = f"Sess {i}"
            uri = right_keys_config.get(line_label)
            
            button_text = "●"
            button_command = lambda x=uri: self.press(x) if x else None

            button = tk.Button(lk_r, text=button_text, width=3, bg="#1a1a1a", fg="#555555", 
                              relief="flat", activebackground="#333", font=("Segoe UI", 10, "bold"),
                              command=button_command, pady=7)
            button.pack(pady=10)
            self.line_key_buttons.append(button)
            self.add_log("build_ui", f"Right line key {i}: {line_label}, URI: {uri}")
        
        self.add_log("build_ui", f"Total line key buttons: {len(self.line_key_buttons)}")
        
        # Softkeys
        skf = tk.Frame(self.main_container, bg="#121212")
        skf.pack(pady=10)
        for l, u in self.config.get('softkeys', {}).items():
            tk.Button(skf, text=l.upper(), width=12, bg="#34495e", fg="#00d2ff", relief="flat", 
                      font=("Segoe UI", 8, "bold"), activebackground="#2c3e50", 
                      command=lambda x=u: self.press(x)).pack(side="left", padx=3)

        # Call Control (Remove MESSAGES from telephony keys)
        cc_f = tk.Frame(self.main_container, bg="#121212", pady=10)
        cc_f.pack(fill="none")
        telephony_keys = self.config.get('telephony_keys', {})
        for l, u in telephony_keys.items():
            if l.upper() != "MESSAGES":  # Skip MESSAGES button here
                btn_color = "#c0392b" if "RELEASE" in l else "#d35400"
                tk.Button(cc_f, text=l, width=13, bg=btn_color, fg="white", font=("Segoe UI", 8, "bold"), 
                          relief="flat", activebackground=btn_color, activeforeground="#ccc",
                          command=lambda x=u: self.press(x)).pack(side="left", padx=5)

        # Lower Grid
        lower_f = tk.Frame(self.main_container, bg="#121212")
        lower_f.pack(pady=10)
        
        # Apps - Create MESSAGES button on top, then other apps below in 2 columns
        af = tk.Frame(lower_f, bg="#121212")
        af.grid(row=0, column=0, padx=20)
        
        # Get MESSAGES from app_keys (the physical button)
        app_keys = self.config.get('app_keys', {})
        messages_uri = app_keys.get('MESSAGES') or app_keys.get('Messages')
        
        current_row = 0
        
        # Create MESSAGES button on top spanning 2 columns
        if messages_uri:
            tk.Button(af, text="MESSAGES", width=25, bg="#2c3e50", fg="white", font=("Segoe UI", 8, "bold"), 
                      relief="flat", activebackground="#1e1e1e",
                      command=lambda: self.press(messages_uri)).grid(row=current_row, column=0, columnspan=2, padx=3, pady=3)
            current_row = 1
        
        # Then add the rest of app keys in 2 columns below
        excluded = ["BACK", "VOL_UP", "VOL_DOWN", "MESSAGES"]
        app_items = [(l, u) for l, u in app_keys.items() if l.upper() not in excluded]
        
        for i, (l, u) in enumerate(app_items):
            col = i % 2
            row = current_row + (i // 2)
            tk.Button(af, text=l, width=12, bg="#2c3e50", fg="white", font=("Segoe UI", 8, "bold"), 
                      relief="flat", activebackground="#1e1e1e",
                      command=lambda x=u: self.press(x)).grid(row=row, column=col, padx=3, pady=3)

        # Navigation
        nf = tk.Frame(lower_f, bg="#121212")
        nf.grid(row=0, column=1, padx=20)
        nk = self.config.get('nav_keys', {})
        ak = self.config.get('app_keys', {})
        
        def nav_btn(parent, text, cmd, r, c, bg="#333", w=6, fg="white"):
            tk.Button(parent, text=text, width=w, bg=bg, fg=fg, relief="flat", font=("Segoe UI", 9, "bold"),
                      activebackground="#444", command=cmd).grid(row=r, column=c, padx=1, pady=1)

        nav_btn(nf, "▲", lambda: self.press(nk.get('Up')), 0, 1)
        nav_btn(nf, "◀", lambda: self.press(nk.get('Left')), 1, 0)
        nav_btn(nf, "OK", lambda: self.press(nk.get('Select')), 1, 1, bg="#2980b9")
        nav_btn(nf, "▶", lambda: self.press(nk.get('Right')), 1, 2)
        nav_btn(nf, "▼", lambda: self.press(nk.get('Down')), 2, 1)
        
        back_uri = ak.get('BACK') or ak.get('Back')
        if back_uri:
            tk.Button(nf, text="BACK", width=6, bg="#c0392b", fg="white", font=("Segoe UI", 7, "bold"),
                      relief="flat", activebackground="#a93226",
                      command=lambda: self.press(back_uri)).grid(row=2, column=0)

        # Keypad
        kf = tk.Frame(lower_f, bg="#121212")
        kf.grid(row=0, column=2, padx=20)
        kd = self.config.get('keypad', {})
        for r, row in enumerate([["1","2","3"], ["4","5","6"], ["7","8","9"], ["*","0","#"]]):
            for c, val in enumerate(row):
                tk.Button(kf, text=val, width=6, bg="#2a2a2a", fg="white", relief="flat", 
                          font=("Segoe UI", 10), activebackground="#444",
                          command=lambda u=kd.get(val): self.press(u)).grid(row=r, column=c, padx=2, pady=2)

        # Volume Cluster
        vf = tk.Frame(lower_f, bg="#121212")
        vf.grid(row=0, column=3, padx=10)
        tk.Button(vf, text="VOL +", width=14, bg="#555", fg="white", relief="flat", font=("Segoe UI", 8),
                  command=lambda: self.press(ak.get('VOL_UP'))).pack(pady=1)
        tk.Button(vf, text="VOL -", width=14, bg="#555", fg="white", relief="flat", font=("Segoe UI", 8),
                  command=lambda: self.press(ak.get('VOL_DOWN'))).pack(pady=1)

        # Footer
        ff = tk.Frame(self.main_container, bg="#1e1e1e")
        ff.pack(fill="x", side="bottom")
        tk.Button(ff, text="CONSOLE LOGS", bg="#121212", fg="#7f8c8d", font=("Segoe UI", 8, "bold"),
                  relief="flat", command=self.toggle_logs).pack(side="left", padx=10, pady=5)
        tk.Button(ff, text="RELOAD CONFIG", bg="#34495e", fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", command=self.reload_btn_config).pack(side="left", padx=5)
        self.countdown_label = tk.Label(ff, text="Next Refresh: 5s", bg="#1e1e1e", fg="#0F0", font=("Segoe UI", 9, "bold"))
        self.countdown_label.pack(side="left", padx=20)
        tk.Button(ff, text="REFRESH SCREEN", bg="#27ae60", fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", command=self.refresh_screen).pack(side="right", padx=10)