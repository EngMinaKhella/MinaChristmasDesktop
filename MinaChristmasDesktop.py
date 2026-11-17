"""MinaChristmasDesktop - falling snow, Christmas lights and a flying Santa on your desktop.

Windows 10/11, Python 3.10+.
Run:  python MinaChristmasDesktop.py
"""
import json
import math
import os
import random
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from video_background import LoopingVideo

APP = "MinaChristmasDesktop"
KEY = "#010101"  # this exact colour becomes see-through
IS_WIN = sys.platform == "win32"
CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
CFG_FILE = os.path.join(CFG_DIR, "settings.json")
DEFAULTS = dict(snow=True, amount=150, speed=5.0, wind=0.0, var_wind=True,
                lights=False, santa=True, santa_every=8.0,
                show_message=False, message="Merry Christmas", autostart=False,
                wallpaper=True, restore_wp=True, music=True, volume=60.0,
                sparkle=True, tractor=True, pile=True, orig_wp="", custom_wp="", video_path="")
UI_KEYS = [k for k in DEFAULTS if k not in ("orig_wp", "custom_wp", "video_path")]
SPARK = ["#fff6c9", "#ffd54a", "#ffab40", "#ffffff"]
EMBER = ["#ff9d2e", "#ffd54a", "#ff7043"]
BULBS = ["#ff4d4d", "#ffd54a", "#4dd2ff", "#7dff7d", "#ff8ad8"]


def load_cfg():
    cfg = dict(DEFAULTS)
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            cfg.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


_u = None


def _user32():
    global _u
    if _u is None:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.GetAncestor.restype = wintypes.HWND
        u.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        u.GetWindowLongW.restype = ctypes.c_long
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetWindowLongW.restype = ctypes.c_long
        u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        _u = u
    return _u


def make_click_through(win):
    """Let mouse clicks pass through the overlay. Returns the window handle."""
    if not IS_WIN:
        return None
    u = _user32()
    win.update_idletasks()
    hwnd = u.GetAncestor(win.winfo_id(), 2)  # GA_ROOT
    style = u.GetWindowLongW(hwnd, -20)      # GWL_EXSTYLE
    # LAYERED | TRANSPARENT (click-through) | TOOLWINDOW | NOACTIVATE
    u.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000)
    return hwnd


def set_ex_transparent(hwnd, on):
    u = _user32()
    style = u.GetWindowLongW(hwnd, -20)
    u.SetWindowLongW(hwnd, -20, (style | 0x20) if on else (style & ~0x20))


def cursor_pos():
    import ctypes
    from ctypes import wintypes
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def work_bottom(default):
    """Y where the taskbar starts (bottom of the usable desktop area)."""
    if not IS_WIN:
        return default
    try:
        import ctypes
        from ctypes import wintypes
        r = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0):  # SPI_GETWORKAREA
            return r.bottom
    except Exception:
        pass
    return default


def set_autostart(on):
    if not IS_WIN:
        return
    import winreg
    path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}"'
                else:
                    py = sys.executable.replace("python.exe", "pythonw.exe")
                    cmd = f'"{py}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, APP)
                except FileNotFoundError:
                    pass
    except Exception:
        pass


def res(name):
    """Path of a bundled file (works from source and from the PyInstaller exe)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", name)


class Music:
    """Looping background music through Windows' built-in MCI (plays mp3, no packages)."""

    def __init__(self, path):
        self.alias, self.ok, self.playing = "minabg", False, False
        if IS_WIN and os.path.exists(path):
            self.ok = self.cmd(f'open "{path}" type mpegvideo alias {self.alias}') == 0

    def cmd(self, s, buf=None):
        import ctypes
        return ctypes.windll.winmm.mciSendStringW(s, buf, 32 if buf else 0, None)

    def set(self, on, volume):
        if not self.ok:
            return
        self.cmd(f"setaudio {self.alias} volume to {int(volume * 10)}")
        if on and not self.playing:
            self.cmd(f"play {self.alias} from 0 repeat")
            self.playing = True
        elif not on and self.playing:
            self.cmd(f"stop {self.alias}")
            self.playing = False

    def keepalive(self):
        if self.ok and self.playing:
            import ctypes
            buf = ctypes.create_unicode_buffer(32)
            self.cmd(f"status {self.alias} mode", buf)
            if buf.value == "stopped":
                self.cmd(f"play {self.alias} from 0 repeat")

    def close(self):
        if self.ok:
            self.cmd(f"close {self.alias}")


def get_wallpaper():
    import ctypes
    buf = ctypes.create_unicode_buffer(520)
    ctypes.windll.user32.SystemParametersInfoW(0x73, 520, buf, 0)  # SPI_GETDESKWALLPAPER
    return buf.value


def set_wallpaper(path):
    import ctypes
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "WallpaperStyle", 0, winreg.REG_SZ, "10")  # Fill
            winreg.SetValueEx(k, "TileWallpaper", 0, winreg.REG_SZ, "0")
    except Exception:
        pass
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)  # SPI_SETDESKWALLPAPER


class App:
    def __init__(self):
        if IS_WIN:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
        self.cfg = load_cfg()
        self.paused = False
        self.system_paused = False
        self._wndproc_callback = None
        self._old_wndproc = None
        self.tray = None
        self.tray_thread = None
        self.root = r = tk.Tk()
        r.title(APP)
        r.overrideredirect(True)
        self.W, self.H = r.winfo_screenwidth(), r.winfo_screenheight()
        r.geometry(f"{self.W}x{self.H}+0+0")
        r.configure(bg=KEY)
        r.attributes("-topmost", True)
        try:
            r.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass
        self.c = tk.Canvas(r, width=self.W, height=self.H, bg=KEY, highlightthickness=0)
        self.c.pack()
        self.video_item = self.c.create_image(0, 0, anchor="nw", tags="video_bg")
        self.video_player = None
        self.video_photo = None
        r.update()
        self.hwnd = make_click_through(r)
        self.ct = True
        self.install_power_notifications()

        self.flakes = []
        self.santa = None
        self.santa_at = time.time() + 6
        self.blink = 0
        self.n = 0
        self.wp_on = False
        self.last_hover = 0
        self.music = Music(res("holiday_ambiance.mp3"))
        self.start_saved_video()
        self.build_sparks()
        self.build_ground()
        self.build_lights()
        self.build_message()
        self.build_panel()
        self.apply(first=True)
        self.start_tray()
        self.tick()
        self.update_video_frame()
        self.blink_lights()

    # ---------- decorations ----------
    def build_lights(self):
        c, W = self.c, self.W
        pts = []
        swag = 260
        n = W // swag + 2
        for i in range(n):
            x0 = i * swag
            for j in range(0, 21):
                x = x0 + swag * j / 20
                pts += [x, 6 + 34 * math.sin(math.pi * j / 20)]
        c.create_line(*pts, fill="#0a3d1a", width=2, smooth=True, tags="lights")
        self.bulbs = []
        k = 0
        for i in range(n):
            for j in range(1, 9):
                t = j / 9
                x = i * swag + swag * t
                y = 6 + 34 * math.sin(math.pi * t) + 6
                col = BULBS[k % len(BULBS)]
                item = c.create_oval(x - 5, y - 3, x + 5, y + 9, fill=col, outline="", tags="lights")
                self.bulbs.append((item, col, k))
                k += 1

    def blink_lights(self):
        if not (self.paused or self.system_paused):
            self.blink ^= 1
            for item, col, k in self.bulbs:
                on = (k + self.blink) % 2 == 0
                self.c.itemconfigure(item, fill=col if on else "#3a3a3a")
        self.root.after(650, self.blink_lights)

    def build_message(self):
        mid = self.W // 2
        font = ("Segoe Script", max(26, self.H // 24), "bold")
        self.msg_shadow = self.c.create_text(mid + 2, 92, text="", font=font, fill="#0b3d1e", tags="msg")
        self.msg = self.c.create_text(mid, 90, text="", font=font, fill="#ffd54a", tags="msg")

    # ---------- snow ----------
    def sync_flakes(self):
        want = int(self.cfg["amount"]) if self.cfg["snow"] else 0
        while len(self.flakes) < want:
            r = random.uniform(1.5, 4.5)
            x, y = random.uniform(0, self.W), random.uniform(-self.H, self.H)
            col = random.choice(["#ffffff", "#ffffff", "#e3f4ff"])
            item = self.c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="")
            self.flakes.append([x, y, r, 0.6 + r * 0.45, random.uniform(0, 6.28), item])
        while len(self.flakes) > want:
            self.c.delete(self.flakes.pop()[5])

    # ---------- santa ----------
    def draw_santa(self, x, y, s):
        c = self.c

        def P(*pairs):
            return [v for px, py in pairs for v in (x + s * px, y + py)]

        def O(x1, y1, x2, y2, **kw):
            c.create_oval(x + s * x1, y + y1, x + s * x2, y + y2, tags="santa", **kw)

        def L(*pairs, **kw):
            c.create_line(*P(*pairs), tags="santa", **kw)

        c.create_polygon(*P((-75, 0), (35, 0), (22, 26), (-62, 26)), fill="#c62828", outline="#7f1414", tags="santa")
        L((-80, 34), (40, 34), fill="#ffd54a", width=3)
        L((40, 34), (50, 22), fill="#ffd54a", width=3)
        L((-55, 26), (-55, 34), fill="#ffd54a", width=2)
        L((10, 26), (10, 34), fill="#ffd54a", width=2)
        O(-72, -22, -44, 4, fill="#8d5524", outline="")          # gift sack
        O(-34, -22, -4, 4, fill="#e53935", outline="")           # Santa body
        O(-27, -38, -11, -22, fill="#ffd8b5", outline="")        # head
        c.create_polygon(*P((-30, -34), (-8, -34), (-20, -56)), fill="#e53935", tags="santa")
        O(-24, -62, -14, -52, fill="#ffffff", outline="")        # pompom
        O(-30, -36, -8, -30, fill="#ffffff", outline="")         # hat rim
        for ox in (90, 170):                                     # two reindeer
            L((ox - 40 if ox == 90 else 40, 12), (ox, 12), fill="#5d3a1a", width=2)
            O(ox, -2, ox + 42, 20, fill="#8d5524", outline="")
            O(ox + 36, -14, ox + 54, 4, fill="#8d5524", outline="")
            O(ox + 50, -8, ox + 58, 0, fill="#ff1744", outline="")
            L((ox + 42, -14), (ox + 46, -30), (ox + 52, -24), fill="#5d3a1a", width=2)
            L((ox + 6, 20), (ox - 2, 34), fill="#5d3a1a", width=3)
            L((ox + 34, 20), (ox + 42, 34), fill="#5d3a1a", width=3)

    def send_santa(self):
        if self.santa:
            return
        s = random.choice([1, -1])
        x = -260 if s == 1 else self.W + 260
        self.santa = dict(x=x, s=s, base=self.H * random.uniform(0.18, 0.4), t=0.0, y=0.0)
        self.santa["y"] = self.santa["base"]
        self.draw_santa(x, self.santa["y"], s)

    def move_santa(self):
        sa = self.santa
        sa["t"] += 1
        dx = 7 * sa["s"]
        ny = sa["base"] + 25 * math.sin(sa["t"] / 25)
        self.c.move("santa", dx, ny - sa["y"])
        sa["x"] += dx
        sa["y"] = ny
        if sa["x"] < -400 or sa["x"] > self.W + 400:
            self.c.delete("santa")
            self.santa = None
            self.santa_at = time.time() + self.cfg["santa_every"] * 60 * random.uniform(0.7, 1.3)

    # ---------- main loop ----------
    def tick(self):
        if self.paused or self.system_paused:
            self.root.after(250, self.tick)
            return
        now = time.time()
        cfg = self.cfg
        wind = cfg["wind"]
        if cfg["var_wind"]:
            wind += 2.2 * math.sin(now / 7) + 1.2 * math.sin(now / 3.1)
        sp = cfg["speed"] / 5.0
        W, H = self.W, self.H
        for f in self.flakes:
            f[1] += f[3] * sp
            f[0] += wind * (0.25 + f[2] / 6) * sp + math.sin(now * 1.4 + f[4]) * 0.5
            if f[1] > self.ground - 2:
                if cfg["pile"] and random.random() < 0.3:
                    self.add_snow(f[0])
                f[1], f[0] = -10, random.uniform(0, W)
            if f[0] > W + 10:
                f[0] = -10
            elif f[0] < -10:
                f[0] = W + 10
            r = f[2]
            self.c.coords(f[5], f[0] - r, f[1] - r, f[0] + r, f[1] + r)
        self.n += 1
        self.update_sparks()
        self.update_ground()
        if self.n % 150 == 0:
            self.music.keepalive()
        if self.santa:
            self.move_santa()
        elif cfg["santa"] and now >= self.santa_at:
            self.send_santa()
        self.root.after(33, self.tick)

    # ---------- taskbar snow + tractor ----------
    def build_ground(self):
        c, W, H = self.c, self.W, self.H
        # Scale taskbar decorations for HiDPI and 4K displays without letting them grow too large.
        self.k = max(0.8, min(2.0, H / 1080))
        self.ground = work_bottom(H - 48)       # top edge of the taskbar
        self.bw = 8
        self.nb = W // self.bw + 2
        self.snow_h = [0.0] * self.nb
        self.puffs = []
        self.pile = c.create_polygon(0, 0, 0, 0, 0, 0, fill="#f4fbff", outline="", smooth=True, tags="pile")
        self.tr = dict(x=W * 0.25, s=1, drag=False, off=0, by=0)
        self.draw_tractor()
        c.tag_bind("tractor", "<ButtonPress-1>", self.tr_down)
        c.bind("<B1-Motion>", self.tr_move)
        c.bind("<ButtonRelease-1>", self.tr_up)

    def add_snow(self, x):
        i = int(x // self.bw)
        for d, w in ((-2, 0.25), (-1, 0.6), (0, 1.0), (1, 0.6), (2, 0.25)):
            j = i + d
            if 0 <= j < self.nb:
                self.snow_h[j] = min(16.0, self.snow_h[j] + 0.8 * w)

    def draw_tractor(self):
        c, t, k = self.c, self.tr, self.k
        c.delete("tractor")
        x, y, s = t["x"], self.ground + t["by"], t["s"]

        def P(*pr):
            return [v for px, py in pr for v in (x + s * px * k, y + py * k)]

        def O(x1, y1, x2, y2, **kw):
            c.create_oval(x + s * x1 * k, y + y1 * k, x + s * x2 * k, y + y2 * k, tags="tractor", **kw)

        def Poly(*pr, **kw):
            c.create_polygon(*P(*pr), tags="tractor", **kw)

        O(-56, -50, -6, 0, fill="#1c1c1c", outline="#000000")      # rear wheel
        O(-43, -37, -19, -13, fill="#ffd54a", outline="")
        O(-35, -29, -27, -21, fill="#7f6a00", outline="")
        O(24, -30, 54, 0, fill="#1c1c1c", outline="#000000")       # front wheel
        O(33, -21, 45, -9, fill="#ffd54a", outline="")
        Poly((-20, -42), (14, -42), (58, -40), (62, -28), (62, -18), (-20, -18), fill="#d32f2f", outline="#7f1414")
        Poly((-46, -76), (-10, -76), (-10, -40), (-46, -40), fill="#bfe3ff", outline="#7f1414", width=2)
        Poly((-50, -82), (-6, -82), (-6, -76), (-50, -76), fill="#7f1414", outline="")
        Poly((-40, -82), (-16, -82), (-28, -104), fill="#e53935", outline="")   # Santa hat
        O(-33, -110, -23, -100, fill="#ffffff", outline="")
        c.create_line(*P((46, -40), (46, -62)), fill="#9e9e9e", width=max(2, int(4 * k)), tags="tractor")
        O(56, -36, 63, -29, fill="#fff176", outline="")            # headlight
        c.create_line(*P((60, -24), (70, -24)), fill="#78909c", width=3, tags="tractor")
        Poly((68, -40), (90, -34), (90, 0), (68, 0), fill="#b0bec5", outline="#607d8b")  # snow plow

    def move_tractor(self, nx):
        t = self.tr
        self.c.move("tractor", nx - t["x"], 0)
        t["x"] = nx

    def turn(self, s):
        self.tr["s"] = s
        self.draw_tractor()

    def tr_down(self, e):
        self.tr["drag"] = True
        self.tr["off"] = e.x - self.tr["x"]

    def tr_move(self, e):
        t = self.tr
        if not t["drag"]:
            return
        nx = min(max(e.x - t["off"], 110 * self.k), self.W - 110 * self.k)
        s = 1 if nx > t["x"] else (-1 if nx < t["x"] else t["s"])
        if s != t["s"]:
            self.turn(s)
        self.move_tractor(nx)

    def tr_up(self, _e):
        self.tr["drag"] = False

    def puff(self, x, y, vx, vy, g, r, grow, color, life):
        item = self.c.create_oval(0, 0, 0, 0, fill=color, outline="", tags="puff")
        self.puffs.append([item, x, y, vx, vy, g, r, grow, life])

    def update_ground(self):
        c, t, k, n = self.c, self.tr, self.k, self.n
        on = self.cfg["tractor"]
        # the overlay only catches the mouse while it is over the tractor
        want = True
        if on and IS_WIN:
            mx, my = cursor_pos()
            bb = c.bbox("tractor")
            if t["drag"] or (bb and bb[0] <= mx <= bb[2] and bb[1] <= my <= bb[3]):
                want = False
        if IS_WIN and want != self.ct:
            set_ex_transparent(self.hwnd, want)
            self.ct = want
        if on:
            if not t["drag"]:
                nx = t["x"] + 2.4 * t["s"] * k
                lo, hi = 110 * k, self.W - 110 * k
                if nx > hi:
                    nx = hi
                    self.turn(-1)
                elif nx < lo:
                    nx = lo
                    self.turn(1)
                self.move_tractor(nx)
            by = round(1.2 * math.sin(n / 3))
            if by != t["by"]:
                c.move("tractor", 0, by - t["by"])
                t["by"] = by
            fx = t["x"] + t["s"] * 80 * k  # the plow clears the snow in front of it
            removed = 0.0
            for j in range(int((fx - 16 * k) // self.bw), int((fx + 16 * k) // self.bw) + 1):
                if 0 <= j < self.nb and self.snow_h[j] > 0.2:
                    removed += self.snow_h[j]
                    self.snow_h[j] = 0.0
            if removed > 1 and len(self.puffs) < 150:
                for _ in range(2):
                    self.puff(fx, self.ground - 8 * k, t["s"] * random.uniform(0.4, 1.6),
                              -random.uniform(1.5, 3.5), 0.18, 2 * k, 0, "#ffffff", 26)
            if n % 7 == 0 and len(self.puffs) < 150:
                self.puff(t["x"] + t["s"] * 46 * k, self.ground - 62 * k, 0, -0.8, 0, 3 * k, 0.1, "#cfd8dc", 45)
        if self.cfg["pile"] and n % 5 == 0:
            g = self.ground
            pts = [0, g]
            for i, h in enumerate(self.snow_h):
                pts += [i * self.bw, g - h * k]
            pts += [self.nb * self.bw, g]
            c.coords(self.pile, *pts)
        keep = []
        for p in self.puffs:
            p[1] += p[3]
            p[2] += p[4]
            p[4] += p[5]
            p[6] += p[7]
            p[8] -= 1
            if p[8] <= 0:
                c.delete(p[0])
                continue
            c.coords(p[0], p[1] - p[6], p[2] - p[6], p[1] + p[6], p[2] + p[6])
            keep.append(p)
        self.puffs = keep

    # ---------- wallpaper scene effects ----------
    def build_sparks(self):
        W, H = self.W, self.H
        self.sc = max(W / 736, H / 414)  # same "fill" scaling Windows uses for the wallpaper
        self.ox, self.oy = (W - 736 * self.sc) / 2, (H - 414 * self.sc) / 2
        mk = lambda: self.c.create_oval(0, 0, 0, 0, outline="", tags="spark")
        self.sparks = [[mk(), 0, 0, 0, 1] for _ in range(45)]   # item, x, y, life left, life
        self.embers = [[mk(), 0, 0, 0, 1.0] for _ in range(28)]  # item, x, y, life left, speed
        self.flames = [[mk(), nx] for nx in (0.135, 0.157, 0.18)]
        self.wrects = [(0.605, 0.03, 0.99, 0.70), (0.375, 0.31, 0.465, 0.70)]  # window panes
        self.wsnow = [[mk(), random.randrange(2), random.random(), random.random(), random.uniform(0.6, 1.6)]
                      for _ in range(70)]

    def pt(self, nx, ny):
        return self.ox + nx * 736 * self.sc, self.oy + ny * 414 * self.sc

    def update_sparks(self):
        if not self.cfg["sparkle"]:
            return
        c, s = self.c, self.sc
        for sp in self.sparks:  # twinkling lights on the tree
            sp[3] -= 1
            if sp[3] <= 0:
                ny = random.uniform(0.2, 0.68)
                hw = 0.012 + (ny - 0.15) * 0.14
                sp[1], sp[2] = self.pt(0.555 + random.uniform(-hw, hw), ny)
                sp[3] = sp[4] = random.randint(10, 40)
                c.itemconfigure(sp[0], fill=random.choice(SPARK))
            r = max(0.1, 1.5 * s * math.sin(math.pi * sp[3] / sp[4]))
            c.coords(sp[0], sp[1] - r, sp[2] - r, sp[1] + r, sp[2] + r)
        for e in self.embers:  # embers rising from the fireplace
            e[3] -= 1
            e[2] -= e[4]
            e[1] += random.uniform(-0.6, 0.6) * s
            if e[3] <= 0:
                e[1], e[2] = self.pt(random.uniform(0.115, 0.2), random.uniform(0.64, 0.7))
                e[3] = random.randint(20, 60)
                e[4] = random.uniform(0.6, 1.6) * s
                c.itemconfigure(e[0], fill=random.choice(EMBER))
            r = max(0.1, 0.8 * s * min(1, e[3] / 20))
            c.coords(e[0], e[1] - r, e[2] - r, e[1] + r, e[2] + r)
        if self.n % 3 == 0:  # fireplace flames flicker
            for fl in self.flames:
                cx, by = self.pt(fl[1] + random.uniform(-0.002, 0.002), 0.71)
                w, h = 5.5 * s, random.uniform(0.03, 0.075) * 414 * s
                c.coords(fl[0], cx - w, by - h, cx + w, by)
                c.itemconfigure(fl[0], fill=random.choice(["#ff8a1f", "#ffc83a", "#ffe27a"]))
        for ws in self.wsnow:  # snow falling outside the windows
            x0, y0, x1, y1 = self.wrects[ws[1]]
            ws[3] += 0.0016 * ws[4]
            ws[2] += 0.0004 * math.sin(self.n / 20 + ws[4] * 5)
            if ws[3] > 1:
                ws[3], ws[2] = 0, random.random()
            X, Y = self.pt(x0 + ws[2] * (x1 - x0), y0 + ws[3] * (y1 - y0))
            r = 0.55 * s
            c.coords(ws[0], X - r, Y - r, X + r, Y + r)

    def start_saved_video(self):
        path = self.cfg.get("video_path", "")
        if path and os.path.isfile(path):
            try:
                self.video_player = LoopingVideo(path, width=self.W, height=self.H)
            except Exception:
                self.video_player = None

    def update_video_frame(self):
        player = self.video_player
        if player:
            frame = player.get_frame()
            if frame is not None:
                try:
                    frame = frame.resize((self.W, self.H), Image.Resampling.LANCZOS)
                    self.video_photo = ImageTk.PhotoImage(frame)
                    self.c.itemconfigure(self.video_item, image=self.video_photo)
                except Exception:
                    pass
            error = player.get_error()
            if error:
                self.stop_video(show_message=False)
                try:
                    messagebox.showwarning(APP, f"Video playback stopped: {error}")
                except Exception:
                    pass
        self.root.after(66, self.update_video_frame)

    def choose_video(self):
        path = filedialog.askopenfilename(title="Choose a looping desktop video",
            filetypes=[("Video files", "*.mp4 *.m4v *.mov *.mkv *.webm"), ("All files", "*.*")])
        if not path:
            return
        try:
            os.makedirs(CFG_DIR, exist_ok=True)
            ext = os.path.splitext(path)[1].lower() or ".mp4"
            target = os.path.join(CFG_DIR, "christmas_video" + ext)
            if os.path.normcase(os.path.abspath(path)) != os.path.normcase(os.path.abspath(target)):
                shutil.copy2(path, target)
            self.stop_video(show_message=False, save=False)
            self.cfg["video_path"] = target
            self.video_player = LoopingVideo(target, width=self.W, height=self.H)
            save_cfg(self.cfg)
        except Exception as exc:
            messagebox.showerror(APP, f"Could not start this video:\n{exc}")

    def stop_video(self, show_message=True, save=True):
        if self.video_player:
            self.video_player.stop()
            self.video_player = None
        self.video_photo = None
        self.c.itemconfigure(self.video_item, image="")
        if save:
            self.cfg["video_path"] = ""
            save_cfg(self.cfg)
        if show_message:
            messagebox.showinfo(APP, "Video background stopped.")

    def set_wp(self, on, force=False):
        """Apply the selected wallpaper while remembering the user's original one."""
        if not IS_WIN or (on == self.wp_on and not force):
            return
        try:
            if on:
                os.makedirs(CFG_DIR, exist_ok=True)
                custom = self.cfg.get("custom_wp", "")
                if custom and os.path.isfile(custom):
                    dst = custom
                else:
                    dst = os.path.join(CFG_DIR, "christmas_bg.jpg")
                    if not os.path.isfile(dst):
                        shutil.copyfile(res("christmas_bg.jpg"), dst)
                cur = get_wallpaper()
                # Snapshot the current wallpaper once per app run, even if it already matches the selected image.
                if cur and not self.cfg.get("orig_wp"):
                    self.cfg["orig_wp"] = cur
                set_wallpaper(dst)
                self.wp_on = True
            else:
                original = self.cfg.get("orig_wp")
                if original and os.path.isfile(original):
                    set_wallpaper(original)
                self.wp_on = False
            save_cfg(self.cfg)
        except Exception as exc:
            if IS_WIN:
                try:
                    messagebox.showwarning(APP, f"Could not change the wallpaper:\n{exc}")
                except Exception:
                    pass

    def choose_wallpaper(self):
        """Copy a user-selected image into AppData so it remains available after packaging."""
        path = filedialog.askopenfilename(
            title="Choose a desktop wallpaper",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            os.makedirs(CFG_DIR, exist_ok=True)
            ext = os.path.splitext(path)[1].lower() or ".jpg"
            target = os.path.join(CFG_DIR, "custom_wallpaper" + ext)
            if os.path.normcase(os.path.abspath(path)) != os.path.normcase(os.path.abspath(target)):
                shutil.copy2(path, target)
            self.cfg["custom_wp"] = target
            self.apply()
            if self.cfg.get("wallpaper"):
                self.set_wp(True, force=True)
            save_cfg(self.cfg)
        except Exception as exc:
            messagebox.showerror(APP, f"Could not use this image:\n{exc}")

    def use_default_wallpaper(self):
        self.cfg["custom_wp"] = ""
        self.apply()
        if self.cfg.get("wallpaper"):
            self.set_wp(True, force=True)
        save_cfg(self.cfg)

    def has_custom_wallpaper(self):
        path = self.cfg.get("custom_wp", "")
        return bool(path and os.path.isfile(path))

    # ---------- notification-area (system tray) ----------
    def install_power_notifications(self):
        """Pause effects on Windows lock/suspend and resume after unlock/wake."""
        if not IS_WIN:
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = self.hwnd or self.root.winfo_id()
            self._notification_hwnd = hwnd
            GWLP_WNDPROC = -4
            WM_POWERBROADCAST = 0x0218
            WM_WTSSESSION_CHANGE = 0x02B1
            PBT_APMSUSPEND = 0x0004
            PBT_APMRESUMEAUTOMATIC = 0x0012
            PBT_APMRESUMESUSPEND = 0x0007
            WTS_SESSION_LOCK = 0x7
            WTS_SESSION_UNLOCK = 0x8

            LRESULT = ctypes.c_ssize_t
            WPARAM = ctypes.c_size_t
            LPARAM = ctypes.c_ssize_t
            WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)

            set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            set_long.restype = ctypes.c_void_p
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            call_proc = user32.CallWindowProcW
            call_proc.restype = LRESULT
            call_proc.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

            def window_proc(window, msg, wparam, lparam):
                try:
                    if msg == WM_WTSSESSION_CHANGE:
                        if wparam == WTS_SESSION_LOCK:
                            self.root.after(0, self.set_system_paused, True)
                        elif wparam == WTS_SESSION_UNLOCK:
                            self.root.after(0, self.set_system_paused, False)
                    elif msg == WM_POWERBROADCAST:
                        if wparam == PBT_APMSUSPEND:
                            self.root.after(0, self.set_system_paused, True)
                        elif wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                            self.root.after(1000, self.set_system_paused, False)
                except Exception:
                    pass
                return call_proc(self._old_wndproc, window, msg, wparam, lparam)

            self._wndproc_callback = WNDPROC(window_proc)
            new_proc = ctypes.cast(self._wndproc_callback, ctypes.c_void_p)
            self._old_wndproc = set_long(hwnd, GWLP_WNDPROC, new_proc)
            if not self._old_wndproc:
                self._wndproc_callback = None
                self._old_wndproc = None
                return
            try:
                wts = ctypes.windll.wtsapi32
                wts.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
                wts.WTSRegisterSessionNotification.restype = wintypes.BOOL
                self._session_notifications = bool(wts.WTSRegisterSessionNotification(hwnd, 0))
            except Exception:
                self._session_notifications = False
        except Exception:
            # Lock-screen notifications are a convenience; desktop effects still work if unavailable.
            self._session_notifications = False

    def set_system_paused(self, value):
        self.system_paused = bool(value)
        self.music.set(self.cfg.get("music", False) and not self.paused and not self.system_paused,
                       self.cfg.get("volume", 60))
        if self.tray:
            suffix = " — Paused" if (self.paused or self.system_paused) else ""
            self.tray.title = "Mina Christmas Desktop" + suffix

    def _make_tray_image(self):
        from PIL import Image, ImageDraw
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Simple original Christmas-tree icon; drawn at high resolution for crisp tray scaling.
        draw.ellipse((8, 50, 56, 60), fill=(0, 0, 0, 55))
        draw.polygon([(32, 5), (12, 31), (23, 31), (8, 47), (56, 47), (41, 31), (52, 31)],
                     fill=(28, 125, 63, 255), outline=(10, 65, 32, 255))
        draw.rectangle((27, 45, 37, 57), fill=(125, 75, 42, 255))
        draw.ellipse((28, 20, 36, 28), fill=(255, 213, 74, 255))
        draw.ellipse((17, 36, 23, 42), fill=(255, 80, 80, 255))
        draw.ellipse((41, 36, 47, 42), fill=(80, 190, 255, 255))
        return image

    def start_tray(self):
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem("Open settings", self._tray_show, default=True),
                pystray.MenuItem(
                    lambda item: "Resume effects" if (self.paused or self.system_paused) else "Pause effects",
                    self._tray_pause,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit Mina Christmas Desktop", self._tray_quit),
            )
            self.tray = pystray.Icon(APP, self._make_tray_image(), "Mina Christmas Desktop", menu)
            self.tray_thread = threading.Thread(target=self.tray.run, name="MinaTray", daemon=True)
            self.tray_thread.start()
        except Exception as exc:
            # Keep the app usable even if the notification-area backend is unavailable.
            self.panel.deiconify()
            messagebox.showwarning(APP, f"The system-tray icon could not start.\n\n{exc}")

    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self.show_panel)

    def _tray_pause(self, icon=None, item=None):
        self.root.after(0, self.toggle_pause)

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self.quit)

    def show_panel(self):
        self.panel.deiconify()
        self.panel.lift()
        try:
            self.panel.focus_force()
        except tk.TclError:
            pass

    def hide_panel(self):
        self.panel.withdraw()

    def toggle_pause(self):
        self.paused = not self.paused
        self.music.set(self.cfg.get("music", False) and not self.paused and not self.system_paused,
                       self.cfg.get("volume", 60))
        if self.tray:
            suffix = " — Paused" if (self.paused or self.system_paused) else ""
            self.tray.title = "Mina Christmas Desktop" + suffix

    def bind_hover(self, w):
        for ch in w.winfo_children():
            if isinstance(ch, (ttk.Button, ttk.Checkbutton)):
                ch.bind("<Enter>", self.hover, add="+")
            self.bind_hover(ch)

    def hover(self, _=None):
        now = time.time()
        if IS_WIN and now - self.last_hover > 0.12:
            self.last_hover = now
            try:
                import winsound
                winsound.PlaySound(res("hover_sound.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    # ---------- control panel ----------
    def build_panel(self):
        p = self.panel = tk.Toplevel(self.root)
        p.title(APP)
        p.resizable(False, False)
        p.attributes("-topmost", True)
        p.protocol("WM_DELETE_WINDOW", self.hide_panel)
        p.geometry("+60+120")
        f = ttk.Frame(p, padding=14)
        f.grid()
        cfg = self.cfg
        self.V = {}
        for k in UI_KEYS:
            v = cfg[k]
            self.V[k] = (tk.BooleanVar if isinstance(v, bool) else
                         tk.StringVar if isinstance(v, str) else tk.DoubleVar)(value=v)
        ttk.Label(f, text="MinaChristmasDesktop", font=("Segoe UI", 14, "bold")).grid(columnspan=2, pady=(0, 8))
        row = [1]

        def check(text, key):
            ttk.Checkbutton(f, text=text, variable=self.V[key], command=self.apply).grid(
                row=row[0], columnspan=2, sticky="w", pady=2)
            row[0] += 1

        def scale(text, key, lo, hi):
            ttk.Label(f, text=text).grid(row=row[0], column=0, sticky="w")
            ttk.Scale(f, from_=lo, to=hi, variable=self.V[key], length=190,
                      command=lambda _=None: self.apply()).grid(row=row[0], column=1, pady=2)
            row[0] += 1

        check("Christmas wallpaper", "wallpaper")
        wallpaper_buttons = ttk.Frame(f)
        wallpaper_buttons.grid(row=row[0], columnspan=2, sticky="w", pady=(0, 4))
        ttk.Button(wallpaper_buttons, text="Choose image…", command=self.choose_wallpaper).pack(side="left", padx=(0, 5))
        ttk.Button(wallpaper_buttons, text="Use built-in", command=self.use_default_wallpaper).pack(side="left")
        row[0] += 1
        video_buttons = ttk.Frame(f)
        video_buttons.grid(row=row[0], columnspan=2, sticky="w", pady=(0, 6))
        ttk.Button(video_buttons, text="Choose video…", command=self.choose_video).pack(side="left", padx=(0, 5))
        ttk.Button(video_buttons, text="Stop video", command=self.stop_video).pack(side="left")
        row[0] += 1
        check("Restore my wallpaper on exit", "restore_wp")
        check("Music", "music")
        scale("Volume", "volume", 0, 100)
        check("Sparkle on tree & fireplace", "sparkle")
        check("Snow", "snow")
        check("Snow tractor on taskbar", "tractor")
        check("Snow piles on taskbar", "pile")
        scale("Amount", "amount", 10, 400)
        scale("Fall speed", "speed", 1, 12)
        scale("Wind (left / right)", "wind", -8, 8)
        check("Changing wind", "var_wind")
        check("Christmas lights", "lights")
        check("Santa flies by", "santa")
        scale("Santa every (min)", "santa_every", 1, 30)
        check("Show message", "show_message")
        e = ttk.Entry(f, textvariable=self.V["message"], width=32)
        e.grid(row=row[0], columnspan=2, pady=4)
        self.V["message"].trace_add("write", lambda *_: self.apply())
        row[0] += 1
        check("Start with Windows", "autostart")
        b = ttk.Frame(f)
        b.grid(row=row[0], columnspan=2, pady=(8, 0))
        ttk.Button(b, text="Send Santa now", command=self.send_santa).pack(side="left", padx=4)
        ttk.Button(b, text="Hide settings", command=self.hide_panel).pack(side="left", padx=4)
        ttk.Button(b, text="Quit", command=self.quit).pack(side="left", padx=4)
        ttk.Label(f, text="The app stays in the notification area beside the clock.",
                  foreground="#666666").grid(row=row[0] + 1, columnspan=2, pady=(8, 0))
        self.bind_hover(f)
        # Settings are opened from the tray icon; the desktop effects remain active.
        p.withdraw()

    def apply(self, first=False):
        old_auto = self.cfg["autostart"]
        for k, var in self.V.items():
            try:
                self.cfg[k] = var.get()
            except tk.TclError:
                pass
        self.cfg["amount"] = int(self.cfg["amount"])
        self.sync_flakes()
        self.c.itemconfigure("lights", state="normal" if self.cfg["lights"] else "hidden")
        text = self.cfg["message"] if self.cfg["show_message"] else ""
        self.c.itemconfigure(self.msg, text=text)
        self.c.itemconfigure(self.msg_shadow, text=text)
        self.music.set(self.cfg["music"], self.cfg["volume"])
        self.set_wp(self.cfg["wallpaper"])
        show_scene_sparkles = self.cfg["sparkle"] and not self.has_custom_wallpaper()
        self.c.itemconfigure("spark", state="normal" if show_scene_sparkles else "hidden")
        self.c.itemconfigure("tractor", state="normal" if self.cfg["tractor"] else "hidden")
        self.c.itemconfigure("pile", state="normal" if self.cfg["pile"] else "hidden")
        if first or self.cfg["autostart"] != old_auto:
            set_autostart(self.cfg["autostart"])
        save_cfg(self.cfg)

    def quit(self):
        if self.wp_on and self.cfg["restore_wp"]:
            self.set_wp(False)
        # Original wallpaper is per run; next launch captures the current Windows wallpaper.
        self.cfg["orig_wp"] = ""
        if self.video_player:
            self.video_player.stop()
            self.video_player = None
        self.music.close()
        save_cfg(self.cfg)
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        if IS_WIN and getattr(self, "_session_notifications", False):
            try:
                import ctypes
                from ctypes import wintypes
                wts = ctypes.windll.wtsapi32
                wts.WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
                wts.WTSUnRegisterSessionNotification.restype = wintypes.BOOL
                wts.WTSUnRegisterSessionNotification(getattr(self, "_notification_hwnd", self.root.winfo_id()))
            except Exception:
                pass
        if IS_WIN and self._old_wndproc and self._wndproc_callback:
            try:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
                set_long(getattr(self, "_notification_hwnd", self.root.winfo_id()), -4,
                         ctypes.c_void_p(self._old_wndproc))
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    App().root.mainloop()