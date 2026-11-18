"""Animated winter-cabin wallpaper for Mina Christmas Desktop.

The background is generated locally with Pillow and displayed in a click-through
WorkerW child window behind desktop icons and application windows.
"""
import base64
import math
import os
import random
import tkinter as tk
import ctypes
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


def _create_cabin_scene(path):
    """Create an original, wide winter cabin illustration without network assets."""
    width, height = 1280, 720
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    # Deep blue winter sky with a soft dusk gradient.
    top = (5, 16, 35)
    bottom = (37, 82, 116)
    for y in range(height):
        t = y / height
        blend = t ** 1.35
        color = tuple(int(top[i] * (1 - blend) + bottom[i] * blend) for i in range(3))
        draw.line((0, y, width, y), fill=color)

    # Moon glow and moon disc.
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((90, 45, 310, 265), fill=(153, 207, 245, 48))
    glow = glow.filter(ImageFilter.GaussianBlur(48))
    image = Image.alpha_composite(image.convert("RGBA"), glow)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((145, 82, 245, 182), fill=(244, 246, 237, 255))
    draw.ellipse((165, 95, 237, 174), fill=(231, 237, 235, 255))
    for _ in range(95):
        x, y = random.Random(_ + 8).randint(0, width), random.Random(_ + 91).randint(0, 330)
        r = random.Random(_ + 14).choice((1, 1, 2))
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(213, 235, 249, random.randint(95, 190)))

    # Layered alpine peaks and their snowy ridges.
    draw.polygon([(0, 420), (115, 280), (205, 365), (330, 210), (455, 390),
                  (590, 230), (725, 410), (860, 235), (1005, 410), (1140, 205),
                  (1280, 400), (1280, 560), (0, 560)], fill=(20, 48, 75, 255))
    draw.polygon([(0, 450), (160, 320), (260, 410), (425, 245), (540, 435),
                  (670, 292), (820, 455), (960, 280), (1100, 440), (1220, 295),
                  (1280, 365), (1280, 570), (0, 570)], fill=(28, 64, 91, 255))
    snow_caps = [
        [(115, 280), (145, 314), (170, 307), (205, 365), (182, 350), (160, 358)],
        [(330, 210), (357, 264), (388, 251), (455, 390), (414, 354), (388, 370), (366, 332)],
        [(590, 230), (620, 278), (645, 263), (725, 410), (684, 372), (660, 386), (634, 332)],
        [(860, 235), (892, 280), (922, 263), (1005, 410), (966, 368), (940, 386), (914, 336)],
        [(1140, 205), (1171, 254), (1201, 239), (1280, 400), (1248, 363), (1215, 380), (1188, 324)],
    ]
    for cap in snow_caps:
        draw.polygon(cap, fill=(226, 240, 248, 255))
        draw.line(cap[:3], fill=(255, 255, 255, 255), width=4)

    # Frozen lake and snowy valley.
    draw.polygon([(0, 440), (250, 420), (430, 460), (570, 430), (730, 475),
                  (900, 430), (1080, 475), (1280, 425), (1280, 720), (0, 720)],
                 fill=(174, 207, 224, 255))
    draw.polygon([(0, 500), (260, 450), (460, 498), (665, 464), (840, 510),
                  (1050, 470), (1280, 510), (1280, 720), (0, 720)],
                 fill=(224, 238, 245, 255))
    for i in range(34):
        x = (i * 83) % width
        y = 475 + (i * 29) % 170
        draw.line((x, y, x + 26 + i % 17, y - 2), fill=(246, 251, 253, 155), width=2)

    # Pine tree helper: layered, snow-lipped firs.
    def pine(cx, base, scale, color):
        trunk_w = max(3, int(7 * scale))
        draw.rectangle((cx - trunk_w//2, base - 12*scale, cx + trunk_w//2, base),
                       fill=(75, 55, 43, 255))
        for layer in range(4):
            y = base - (95 - layer * 23) * scale
            half = (30 + layer * 15) * scale
            tip = y - 40 * scale
            draw.polygon([(cx, tip), (cx - half, y + 8*scale),
                          (cx + half, y + 8*scale)], fill=color)
            draw.line((cx-half*0.72, y+4*scale, cx, tip+9*scale,
                       cx+half*0.72, y+4*scale), fill=(220, 238, 246, 210),
                      width=max(1, int(2*scale)), joint="curve")

    for x, base, scale in [
        (22, 525, 1.45), (92, 510, 1.12), (172, 525, .88), (265, 502, .72),
        (475, 518, .70), (555, 520, .82), (1188, 514, 1.18), (1255, 535, 1.48)
    ]:
        pine(x, base, scale, (13, 52, 52, 255))

    # Cabin body, timber textures and warm window light.
    draw.polygon([(600, 360), (865, 205), (1195, 360), (1180, 590), (620, 590)],
                 fill=(74, 48, 34, 255), outline=(34, 28, 28, 255))
    draw.polygon([(620, 364), (865, 235), (1170, 365), (1160, 565), (630, 565)],
                 fill=(111, 70, 45, 255))
    for y in range(390, 560, 22):
        draw.line((632, y, 1159, y), fill=(73, 44, 32, 170), width=3)
        draw.line((642, y+4, 1148, y+4), fill=(167, 111, 69, 65), width=1)

    # Roof and chimney.
    draw.rectangle((1038, 150, 1113, 300), fill=(56, 58, 63, 255))
    draw.rectangle((1048, 143, 1104, 160), fill=(36, 42, 51, 255))
    draw.polygon([(560, 366), (859, 170), (1210, 355), (1183, 383),
                  (860, 240), (601, 395)], fill=(34, 42, 51, 255))
    draw.polygon([(555, 350), (855, 150), (1214, 338), (1194, 356),
                  (859, 194), (576, 373)], fill=(235, 244, 248, 255))
    draw.line((572, 352, 855, 163, 1204, 342), fill=(255, 255, 255, 255), width=12)
    draw.ellipse((1048, 128, 1106, 154), fill=(239, 247, 251, 255))

    # Porch and timber posts.
    draw.rectangle((604, 535, 1190, 575), fill=(55, 38, 30, 255))
    draw.rectangle((600, 570, 1200, 584), fill=(111, 74, 50, 255))
    for x in (635, 790, 1135, 1180):
        draw.rectangle((x, 360, x+13, 574), fill=(72, 45, 32, 255))
        draw.line((x+3, 367, x+3, 570), fill=(159, 107, 66, 190), width=2)
    draw.line((620, 536, 1180, 536), fill=(195, 151, 105, 255), width=7)
    for x in range(640, 1160, 54):
        draw.line((x, 540, x, 570), fill=(198, 158, 116, 255), width=4)

    # Large warm window: decorated room, tree, gifts and fireplace.
    draw.rounded_rectangle((805, 337, 1085, 510), radius=5,
                           fill=(255, 180, 82, 255), outline=(39, 35, 31, 255), width=12)
    draw.rectangle((818, 350, 1072, 497), fill=(255, 197, 107, 255))
    draw.rectangle((818, 350, 1072, 497), fill=(255, 222, 154, 55))
    # Interior wall and floor.
    draw.rectangle((820, 352, 1070, 493), fill=(129, 72, 43, 90))
    draw.rectangle((820, 467, 1070, 494), fill=(89, 52, 36, 210))

    # Indoor Christmas tree.
    tx, ty = 925, 471
    draw.rectangle((tx-5, ty-10, tx+6, ty+3), fill=(91, 55, 32, 255))
    draw.polygon([(tx, 371), (tx-34, 418), (tx+34, 418)], fill=(17, 91, 56, 255))
    draw.polygon([(tx, 395), (tx-42, 447), (tx+42, 447)], fill=(18, 103, 61, 255))
    draw.polygon([(tx, 420), (tx-51, 469), (tx+51, 469)], fill=(20, 112, 64, 255))
    draw.ellipse((tx-6, 362, tx+6, 374), fill=(255, 220, 91, 255))
    for x, y, col in [
        (tx-17, 418, (225, 56, 52, 255)), (tx+15, 427, (255, 211, 77, 255)),
        (tx-26, 446, (255, 235, 169, 255)), (tx+28, 452, (222, 55, 54, 255)),
        (tx-10, 459, (83, 188, 232, 255)), (tx+8, 440, (255, 255, 220, 255))
    ]:
        draw.ellipse((x-4, y-4, x+4, y+4), fill=col)

    # Fireplace in the right side of the window.
    draw.rectangle((991, 399, 1058, 480), fill=(72, 48, 39, 255))
    draw.rectangle((1000, 409, 1049, 468), fill=(30, 26, 30, 255))
    draw.polygon([(1026, 465), (1006, 451), (1018, 432), (1025, 447),
                  (1035, 426), (1045, 454)], fill=(255, 143, 40, 255))
    draw.polygon([(1026, 464), (1018, 452), (1028, 439), (1036, 456)],
                 fill=(255, 220, 104, 255))
    draw.rectangle((987, 477, 1063, 487), fill=(80, 51, 39, 255))
    # Mullions and indoor garland.
    draw.rectangle((928, 350, 936, 497), fill=(54, 39, 34, 255))
    draw.rectangle((818, 423, 1072, 430), fill=(54, 39, 34, 255))
    draw.arc((824, 343, 1070, 407), 0, 180, fill=(36, 95, 57, 255), width=7)
    for x in range(840, 1060, 28):
        draw.ellipse((x-3, 389, x+3, 395), fill=(255, 208, 90, 255))

    # Front door and lantern.
    draw.rectangle((665, 395, 770, 558), fill=(61, 40, 31, 255), outline=(35, 31, 31, 255), width=8)
    draw.rectangle((677, 407, 758, 540), fill=(116, 72, 45, 255))
    draw.rectangle((689, 420, 746, 474), fill=(255, 190, 96, 255), outline=(48, 38, 32, 255), width=5)
    draw.ellipse((741, 490, 749, 498), fill=(245, 204, 102, 255))
    draw.rectangle((612, 392, 626, 440), fill=(45, 43, 40, 255))
    draw.polygon([(604, 393), (633, 393), (628, 405), (609, 405)], fill=(255, 197, 92, 255))
    draw.ellipse((604, 404, 634, 440), fill=(255, 171, 75, 45))

    # Presents and snow-covered path.
    for x, y, color in [(835, 490, (182, 37, 44, 255)), (860, 485, (36, 106, 71, 255)),
                        (954, 488, (194, 145, 54, 255))]:
        draw.rectangle((x, y, x+22, y+18), fill=color, outline=(245, 218, 164, 255), width=2)
        draw.rectangle((x+9, y, x+13, y+18), fill=(255, 220, 120, 255))
        draw.arc((x+3, y-7, x+12, y+5), 180, 360, fill=(255, 223, 138, 255), width=2)
    draw.polygon([(0, 575), (260, 544), (475, 576), (680, 550), (900, 582),
                  (1130, 552), (1280, 578), (1280, 720), (0, 720)],
                 fill=(242, 249, 252, 255))
    draw.polygon([(505, 720), (640, 575), (780, 720)], fill=(221, 237, 246, 255))
    draw.line((620, 590, 645, 620, 680, 650, 720, 680), fill=(205, 225, 238, 255), width=5)

    # Snowy foreground firs, fence and a glowing path lantern.
    for x, base, scale in [(48, 680, 1.45), (132, 655, 1.02), (300, 650, .75),
                           (475, 635, .65), (1190, 660, 1.12), (1260, 690, 1.45)]:
        pine(x, base, scale, (13, 62, 54, 255))
    draw.line((0, 620, 410, 620), fill=(84, 61, 44, 255), width=8)
    for x in range(18, 410, 70):
        draw.line((x, 592, x, 675), fill=(83, 58, 42, 255), width=7)
    draw.rectangle((370, 500, 385, 566), fill=(59, 47, 39, 255))
    draw.polygon([(359, 504), (393, 504), (387, 514), (365, 514)], fill=(54, 54, 55, 255))
    draw.rectangle((365, 514, 387, 542), fill=(255, 196, 100, 190), outline=(45, 48, 51, 255), width=3)
    draw.ellipse((350, 524, 400, 574), fill=(255, 184, 87, 35))

    # Snow caps, sparkling foreground flakes and tiny warm porch lights.
    for i in range(160):
        rng = random.Random(1000 + i)
        x, y = rng.randrange(width), rng.randrange(380, height)
        r = rng.choice((1, 1, 2, 2, 3))
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 255, 255, rng.randrange(100, 210)))
    for i, x in enumerate(range(635, 1175, 42)):
        y = 357 + int(4 * math.sin(i * .7))
        draw.ellipse((x-4, y-4, x+4, y+4), fill=(255, 218, 119, 255))

    image.convert("RGB").save(path, "JPEG", quality=91, optimize=True)
    return path


def bundled_scene_path(resource, app_dir):
    """Decode the supplied original cabin artwork into a cached local JPEG."""
    os.makedirs(app_dir, exist_ok=True)
    target = os.path.join(app_dir, "winter_cabin_scene.jpg")
    if os.path.isfile(target) and os.path.getsize(target) > 30_000:
        return target
    try:
        encoded = []
        for part_name in _ASSET_PARTS:
            with open(resource(part_name), "r", encoding="ascii") as stream:
                encoded.append(stream.read().strip())
        data = base64.b64decode("".join(encoded), validate=True)
        temp = target + ".tmp"
        with open(temp, "wb") as stream:
            stream.write(data)
        os.replace(temp, target)
    except Exception:
        # Keep the app usable when running from an incomplete source checkout.
        _create_cabin_scene(target)
    return target


def _desktop_worker_window():
    """Find the WorkerW window behind Explorer's desktop icon view."""
    user32 = ctypes.windll.user32
    progman = user32.FindWindowW("Progman", None)
    if progman:
        result = ctypes.c_ulong()
        try:
            user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0, 0x0002, 1000, ctypes.byref(result))
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
    """Low-frequency, low-interference animated image behind desktop icons."""

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
                source.convert("RGB"), (self.width, self.height),
                method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
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
            root = user32.GetAncestor(hwnd, 2)
            return root or hwnd
        except Exception:
            return hwnd

    def _attach_behind_icons(self):
        user32 = ctypes.windll.user32
        parent = _desktop_worker_window()
        if not parent:
            return False
        try:
            user32.SetParent(self.hwnd, parent)
            get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)

            style = int(get_long(self.hwnd, -16))
            style = (style | 0x40000000 | 0x10000000) & ~0x80000000
            set_long(self.hwnd, -16, style)

            ex_style = int(get_long(self.hwnd, -20))
            ex_style |= 0x00000020 | 0x00080000 | 0x00000080 | 0x08000000
            set_long(self.hwnd, -20, ex_style)

            flags = 0x0004 | 0x0010 | 0x0020 | 0x0040
            user32.SetWindowPos(self.hwnd, None, 0, 0, self.width, self.height, flags)
            return True
        except Exception:
            return False

    def _render(self):
        image = self.base.copy().convert("RGBA")
        t = self.frame_number / 9.0

        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        cx, cy = int(self.width * 0.80), int(self.height * 0.66)
        pulse = 0.5 + 0.5 * math.sin(t * 2.1)
        radius_x = max(45, int(self.width * 0.06))
        radius_y = max(30, int(self.height * 0.065))
        alpha = int(18 + pulse * 23)
        glow_draw.ellipse((cx-radius_x, cy-radius_y, cx+radius_x, cy+radius_y),
                          fill=(255, 139, 48, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(max(8, int(self.width * 0.012))))
        image = Image.alpha_composite(image, glow)
        draw = ImageDraw.Draw(image, "RGBA")

        for x0, y0, radius, speed, drift, phase in self.snow:
            x = (x0 + drift * t) % self.width
            y = (y0 + speed * t) % self.height
            shimmer = 0.72 + 0.28 * math.sin(t * 1.6 + phase)
            opacity = int(105 + 100 * shimmer)
            r = max(1, int(radius))
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(244, 250, 255, opacity))

        for i in range(8):
            phase = t * 1.8 + i * 1.37
            x = int(self.width * (0.72 + 0.045 * ((i % 4) / 3)))
            y = int(self.height * (0.59 + 0.07 * (i // 4)) + 3 * math.sin(phase))
            alpha = int(75 + 130 * (0.5 + 0.5 * math.sin(phase)))
            r = 2 if self.width < 1500 else 3
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 218, 110, alpha))

        # A few soft chimney wisps drift upward and fade naturally.
        smoke_x = int(self.width * 0.84)
        smoke_y = int(self.height * 0.18)
        for i in range(4):
            phase = t * 0.55 + i * 1.35
            drift = int(7 * math.sin(phase))
            rise = int((t * 7 + i * 14) % max(40, int(self.height * 0.09)))
            radius = max(4, int(self.width * (0.004 + i * 0.001)))
            alpha = max(8, 34 - i * 6)
            draw.ellipse(
                (smoke_x + drift - radius, smoke_y - rise - radius,
                 smoke_x + drift + radius, smoke_y - rise + radius),
                fill=(215, 226, 238, alpha),
            )

        return image.convert("RGB")

    def set_paused(self, paused):
        """Pause the animated WorkerW layer while another app is in front."""
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
            self.after_id = self.root.after(110, self._tick)
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
