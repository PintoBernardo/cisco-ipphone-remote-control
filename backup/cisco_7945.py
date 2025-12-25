import tkinter as tk
from cisco_core import CiscoBasePhone

class Cisco7945Phone(CiscoBasePhone):
    def set_screen_dims(self):
        self.screen_w, self.screen_h = 320, 222

    def build_ui(self):
        top_f = tk.Frame(self.main_container, bg="#121212"); top_f.pack(pady=10)
        
        # Screen
        sf = tk.Frame(top_f, bg="#121212", bd=2, relief="sunken"); sf.grid(row=0, column=0, padx=5)
        self.screen_canvas = tk.Canvas(sf, width=self.screen_w, height=self.screen_h, bg="black", highlightthickness=0); self.screen_canvas.pack()

        # Line Keys (Right side)
        lk_f = tk.Frame(top_f, bg="#121212"); lk_f.grid(row=0, column=1, padx=5)
        for l, u in self.config.get('line_keys', {}).items():
            tk.Button(lk_f, text="●", width=3, bg="#2a2a2a", fg="#27ae60", relief="flat", activebackground="#333",
                      command=lambda x=u: self.press(x), pady=7).pack(pady=15)
        
        # Softkeys (Limited to 2)
        skf = tk.Frame(self.main_container, bg="#121212"); skf.pack(pady=10)
        soft_keys = list(self.config.get('softkeys', {}).items())[:2]
        for l, u in soft_keys:
            tk.Button(skf, text=l.upper(), width=14, bg="#34495e", fg="#00d2ff", relief="flat", 
                      font=("Segoe UI", 8, "bold"), activebackground="#2c3e50", 
                      command=lambda x=u: self.press(x)).pack(side="left", padx=5)

        # Control Section
        mid_f = tk.Frame(self.main_container, bg="#121212"); mid_f.pack(pady=10)
        
        # App Cluster (Right)
        akf = tk.Frame(mid_f, bg="#121212"); akf.grid(row=0, column=1, padx=20)
        ak = self.config.get('app_keys', {})
        for label in ["MESSAGES", "DIRECTORIES", "SERVICES", "SETTINGS", "HELP"]:
            if label in ak:
                tk.Button(akf, text=label, width=14, bg="#2c3e50", fg="white", font=("Segoe UI", 8, "bold"),
                          relief="flat", activebackground="#1e1e1e",
                          command=lambda u=ak[label]: self.press(u)).pack(pady=2)

        # Navigation (Left)
        nf = tk.Frame(mid_f, bg="#121212"); nf.grid(row=0, column=0, padx=20)
        nk = self.config.get('nav_keys', {})
        def nav_btn(parent, text, cmd, r, c, bg="#333", w=6, fg="white"):
            tk.Button(parent, text=text, width=w, bg=bg, fg=fg, relief="flat", font=("Segoe UI", 9, "bold"),
                      activebackground="#444", command=cmd).grid(row=r, column=c, padx=1, pady=1)

        nav_btn(nf, "▲", lambda: self.press(nk.get('Up')), 0, 1)
        nav_btn(nf, "◀", lambda: self.press(nk.get('Left')), 1, 0)
        nav_btn(nf, "OK", lambda: self.press(nk.get('Select')), 1, 1, bg="#2980b9")
        nav_btn(nf, "▶", lambda: self.press(nk.get('Right')), 1, 2)
        nav_btn(nf, "▼", lambda: self.press(nk.get('Down')), 2, 1)

        # Bottom Grid (Keypad + Mute)
        bot_f = tk.Frame(self.main_container, bg="#121212"); bot_f.pack(pady=10)
        
        # Keypad
        kf = tk.Frame(bot_f, bg="#121212"); kf.grid(row=0, column=0, padx=20)
        kd = self.config.get('keypad', {})
        for r, row in enumerate([["1","2","3"], ["4","5","6"], ["7","8","9"], ["*","0","#"]]):
            for c, val in enumerate(row):
                tk.Button(kf, text=val, width=6, bg="#2a2a2a", fg="white", relief="flat", 
                          font=("Segoe UI", 10), activebackground="#444",
                          command=lambda u=kd.get(val): self.press(u)).grid(row=r, column=c, padx=2, pady=2)

        # Mute & Volume (Right of keypad)
        vf = tk.Frame(bot_f, bg="#121212"); vf.grid(row=0, column=1, padx=10)
        tk.Button(vf, text="MUTE", width=14, bg="#c0392b", fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  command=lambda: self.press(ak.get('MUTE'))).pack(pady=5)
        
        # Volume buttons side-by-side
        v_sub = tk.Frame(vf, bg="#121212")
        v_sub.pack()
        tk.Button(v_sub, text="VOL +", width=6, bg="#555", fg="white", relief="flat", 
                  font=("Segoe UI", 8), command=lambda: self.press(ak.get('VOL_UP'))).pack(side="left", padx=1)
        tk.Button(v_sub, text="VOL -", width=6, bg="#555", fg="white", relief="flat", 
                  font=("Segoe UI", 8), command=lambda: self.press(ak.get('VOL_DOWN'))).pack(side="left", padx=1)

        # Footer
        ff = tk.Frame(self.main_container, bg="#1e1e1e"); ff.pack(fill="x", side="bottom")
        tk.Button(ff, text="CONSOLE LOGS", command=self.toggle_logs).pack(side="left", padx=10, pady=5)
        tk.Button(ff, text="RELOAD CONFIG", bg="#34495e", fg="white", font=("Arial", 8),
                  command=self.reload_btn_config).pack(side="left", padx=5)
        self.countdown_label = tk.Label(ff, text="Next Refresh: 5s", bg="#1e1e1e", fg="#0F0", font=("Arial", 9, "bold"))
        self.countdown_label.pack(side="left", padx=20)
        tk.Button(ff, text="REFRESH SCREEN", bg="#27ae60", fg="white", command=self.refresh_screen).pack(side="right", padx=10)
