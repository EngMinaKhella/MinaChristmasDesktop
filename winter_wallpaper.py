"""Animated Windows wallpaper layer for Mina Christmas Desktop.

The image is hosted as a click-through child of the desktop WorkerW, behind
desktop icons and normal application windows. Motion is rendered with Pillow.
"""
import base64
import ctypes
import os
import random
import tkinter as tk
from ctypes import wintypes

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageTk


_ASSET_PARTS = (
    "winter_cabin_scene.jpg.b64.01",
    "winter_cabin_scene.jpg.b64.02",
    "winter_cabin_scene.jpg.b64.03",
    "winter_cabin_scene.jpg.b64.04",
    "winter_cabin_scene.jpg.b64.05",
    "winter_cabin_scene.jpg.b64.06",
    "winter_cabin_scene.jpg.b64.07",
    "winter_cabin_scene.jpg.b64.08",
    "winter_cabin_scene.jpg.b64.09",
    "winter_cabin_scene.jpg.b64.10",
    "winter_cabin_scene.jpg.b64.11",
    "winter_cabin_scene.jpg.b64.12",
)


def bundled_scene_path(resource, app_dir):
    """Decode the bundled text-safe JPEG chunks into the user's app-data folder."""
    os.makedirs(app_dir, exist_ok=True)
    target = os.path.join(app_dir, "winter_cabin_scene.jpg")
    if os.path.isfile(target) and os.path.getsize(target) > 20_000:
        return target

    encoded = []
    for part_name in _ASSET_PARTS:
        with open(resource(part_name), "r", encoding="ascii") as stream:
            encoded.append(stream.read().strip())
    data = base64.b64decode("".join(encoded), validate=True)
    temp = target + ".tmp"
    with open(temp, "wb") as stream:
        stream.write(data)
    os.replace(temp, target)
    return target


def _desktop_worker_window():
    """Find the WorkerW window behind Explorer's desktop icon view."""
    user32 = ctypes.windll.user32
    progman = user32.FindWindowW("Progman", None)
    if progman:
        result = ctypes.c_ulong()
        try:
            user32.SendMessageTimeoutW(
                progman, 0x052C, 0xD, 0, 0x0002, 1000, ctypes.byref(result)
            )
        except Exception:
            pass

    candidates = []

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _):
        view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if view:
            worker = user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if worker:
                candidates.append(worker)
            return False
        return True

    callback = enum_proc(visit)
    user32.EnumWindows(callback, 0)
    return candidates[0] if candidates else progman


class AnimatedWallpaper:
    """Low-frequency, low-interference animated image behind Windows desktop icons."""

    def __init__(self, root, image_path, width, height):
        if os.name != "nt":
            raise RuntimeError("The animated desktop wallpaper layer requires Windows.")

        self.root = root
        self.width = max(640, int(width))
        self.height = max(360, int(height))
        self.frame_number = 0
        self.after_id = None
        self.paused = False
        self.photo = None
        self.closed = False
        self._random = random.Random(2026)

        with Image.open(image_path) as source:
            self.base = ImageOps.fit(
                source.convert("RGB"),
                (self.width, self.height),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

        self.snow = []
        for _ in range(max(70, min(190, self.width // 8))):
            self.snow.append((
                self._random.uniform(0, self.width),
                self._random.uniform(0, self.height),
                self._random.uniform(0.7, 2.5),
                self._random.uniform(10.0, 34.0),
                self._random.uniform(-5.0, 5.0),
                self._random.uniform(0, 6.28),
            ))

        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", False)
        self.window.geometry(f"{self.width}x{self.height}+0+0")
        self.window.configure(bg="#06142a")
        self.label = tk.Label(self.window, bd=0, highlightthickness=0, bg="#06142a")
        self.label.pack(fill="both", expand=True)
        self.window.update_idletasks()
        self.window.update()

        self.hwnd = self._root_hwnd()
        if not self._attach_behind_icons():
            self.window.destroy()
            raise RuntimeError("Could not attach the animated scene behind desktop icons.")

        self._tick()

    def _root_hwnd(self):
        user32 = ctypes.windll.user32
        hwnd = self.window.winfo_id()
        try:
            root = user32.GetAncestor(hwnd, 2)  # GA_ROOT
            return root or hwnd
        except Exception:
            return hwnd

    def _attach_behind_icons(self):
        user32 = ctypes.windll.user32
        parent = _desktop_worker_window()
        if not parent:
            return False

        try:
            user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
            user32.SetParent.restype = wintypes.HWND
            user32.SetParent(self.hwnd, parent)

            get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            get_long.argtypes = [wintypes.HWND, ctypes.c_int]
            get_long.restype = ctypes.c_ssize_t
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
            set_long.restype = ctypes.c_ssize_t
            user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
            user32.SetWindowPos.restype = wintypes.BOOL

            style = int(get_long(self.hwnd, -16))
            style = (style | 0x40000000 | 0x10000000) & ~0x80000000  # CHILD + VISIBLE, not POPUP
            set_long(self.hwnd, -16, style)

            ex_style = int(get_long(self.hwnd, -20))
            ex_style |= 0x00000020 | 0x00080000 | 0x00000080 | 0x08000000
            set_long(self.hwnd, -20, ex_style)  # transparent, layered, tool-window, no-activate

            flags = 0x0004 | 0x0010 | 0x0020 | 0x0040  # NOACTIVATE, SHOW, FRAMECHANGED, NOZORDER
            user32.SetWindowPos(
                self.hwnd, None, 0, 0, self.width, self.height, flags
            )
            return True
        except Exception:
            return False

    def _render(self):
        image = self.base.copy().convert("RGBA")
        t = self.frame_number / 9.0

        # A soft amber pulse around the visible fireplace, not a full-screen flash.
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        cx, cy = int(self.width * 0.49), int(self.height * 0.62)
        pulse = 0.5 + 0.5 * __import__("math").sin(t * 2.1)
        radius_x = max(45, int(self.width * 0.075))
        radius_y = max(30, int(self.height * 0.075))
        alpha = int(18 + pulse * 23)
        glow_draw.ellipse(
            (cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y),
            fill=(255, 139, 48, alpha),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(max(8, int(self.width * 0.012))))
        image = Image.alpha_composite(image, glow)
        draw = ImageDraw.Draw(image, "RGBA")

        # Quiet drifting snow in the mountain view and across the foreground.
        for x0, y0, radius, speed, drift, phase in self.snow:
            x = (x0 + drift * t) % self.width
            y = (y0 + speed * t) % self.height
            shimmer = 0.72 + 0.28 * __import__("math").sin(t * 1.6 + phase)
            opacity = int(105 + 100 * shimmer)
            r = max(1, int(radius))
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(244, 250, 255, opacity))

        # Tiny warm twinkles around the Christmas tree visible through the window.
        for i in range(8):
            phase = t * 1.8 + i * 1.37
            x = int(self.width * (0.16 + 0.12 * ((i % 4) / 3)))
            y = int(self.height * (0.27 + 0.12 * (i // 4)) + 4 * __import__("math").sin(phase))
            alpha = int(75 + 130 * (0.5 + 0.5 * __import__("math").sin(phase)))
            r = 2 if self.width < 1500 else 3
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 218, 110, alpha))

        # A small drifting chimney wisp adds motion to the snowy roofline.
        smoke_x = int(self.width * 0.32)
        smoke_y = int(self.height * 0.14)
        for i in range(4):
            drift = int(7 * __import__("math").sin(t * 0.7 + i))
            lift = int((t * 5 + i * 12) % 44)
            r = max(5, int(self.width * (0.006 + i * 0.001)))
            draw.ellipse(
                (smoke_x + drift-r, smoke_y-lift-r,
                 smoke_x + drift+r, smoke_y-lift+r),
                fill=(210, 222, 235, max(8, 32 - i * 5)),
            )

        return image.convert("RGB")

    def set_paused(self, paused):
        """Pause the animated WorkerW layer while another app is in front or Windows is locked."""
        if self.closed:
            return
        paused = bool(paused)
        if paused == self.paused:
            return
        self.paused = paused
        if paused and self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
        elif not paused and self.after_id is None:
            self._tick()

    def _tick(self):
        if self.closed or self.paused:
            self.after_id = None
            return
        try:
            frame = self._render()
            self.photo = ImageTk.PhotoImage(frame)
            self.label.configure(image=self.photo)
            self.frame_number += 1
            self.after_id = self.root.after(110, self._tick)  # about 9 FPS
        except Exception:
            self.stop()

    def stop(self):
        if self.closed:
            return
        self.closed = True
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
        try:
            self.window.destroy()
        except Exception:
            pass
        self.photo = None
