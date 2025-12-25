import tkinter as tk
from cisco_core import CiscoBasePhone

class Cisco7911Phone(CiscoBasePhone):
    def set_screen_dims(self):
        self.screen_w, self.screen_h = 192, 64

    def build_ui(self):
        top_f = tk.Frame(self.main_container, bg="#121212"); top_f.pack(pady=10)
        
        # Screen
        sf = tk.Frame(top_f, bg="#121212", bd=2, relief="sunken"); sf.grid(row=0, column=0, padx=5)
        self.screen_canvas = tk.Canvas(sf, width=self.screen_w, height=self.screen_h, bg="black", highlightthickness=0); self.screen_canvas.pack()
        
        # Dial/Control Section
        mid_f = tk.Frame(self.main_container, bg="#121212"); mid_f.pack(pady=10)
        ak = self.config.get('app_keys', {})
        
        # Apps & Hold
        cf = tk.Frame(mid_f, bg="#121212"); cf.grid(row=0, column=0, padx=10)
        tk.Button(cf, text="HOLD", width=10, bg="#d35400", fg="white", command=lambda: self.press(ak.get('HOLD'))).pack(pady=5)
        tk.Button(cf, text="MENU", width=10, bg="#2c3e50", fg="white", command=lambda: self.press(ak.get('MENU'))).pack(pady=5)

        # Nav (Up/Down only for 7911)
        nf = tk.Frame(mid_f, bg="#121212"); nf.grid(row=0, column=1, padx=10)
        nk = self.config.get('nav_keys', {})
        tk.Button(nf, text="▲", width=5, command=lambda: self.press(nk.get('Up'))).pack()
        tk.Button(nf, text="Select", width=5, bg="#2980b9", fg="white", command=lambda: self.press(nk.get('Select'))).pack(pady=2)
        tk.Button(nf, text="▼", width=5, command=lambda: self.press(nk.get('Down'))).pack()

        # Volume
        vf = tk.Frame(mid_f, bg="#121212"); vf.grid(row=0, column=2, padx=10)
        tk.Button(vf, text="VOL +", width=8, bg="#555", fg="white", command=lambda: self.press(ak.get('VOL_UP'))).pack(pady=5)
        tk.Button(vf, text="VOL -", width=8, bg="#555", fg="white", command=lambda: self.press(ak.get('VOL_DOWN'))).pack(pady=5)

        # Keypad
        kf = tk.Frame(self.main_container, bg="#121212"); kf.pack(pady=10)
        kd = self.config.get('keypad', {})
        for r, row in enumerate([["1","2","3"], ["4","5","6"], ["7","8","9"], ["*","0","#"]]):
            for c, val in enumerate(row):
                tk.Button(kf, text=val, width=5, command=lambda u=kd.get(val): self.press(u)).grid(row=r, column=c, padx=1, pady=1)

        # Footer
        ff = tk.Frame(self.main_container, bg="#1e1e1e"); ff.pack(fill="x", side="bottom")
        tk.Button(ff, text="CONSOLE LOGS", command=self.toggle_logs).pack(side="left", padx=10, pady=5)
        tk.Button(ff, text="RELOAD CONFIG", bg="#34495e", fg="white", font=("Arial", 8),
                  command=self.reload_btn_config).pack(side="left", padx=5)
        self.countdown_label = tk.Label(ff, text="Next Refresh: 5s", bg="#1e1e1e", fg="#0F0", font=("Arial", 9, "bold"))
        self.countdown_label.pack(side="left", padx=20)
        tk.Button(ff, text="REFRESH SCREEN", bg="#27ae60", fg="white", command=self.refresh_screen).pack(side="right", padx=10)
