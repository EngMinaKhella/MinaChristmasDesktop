"""Low-overhead looping video frames for Mina Christmas Desktop.

Uses the FFmpeg binary distributed by imageio-ffmpeg. Decoding runs off the
Tk event thread and a one-frame queue keeps memory use bounded.
"""
import queue
import subprocess
import threading

import imageio_ffmpeg
from PIL import Image


class LoopingVideo:
    def __init__(self, path, width=1280, height=720, fps=15):
        self.path = path
        self.width = min(1280, max(640, int(width)))
        self.height = max(360, int(round(self.width * 9 / 16)))
        self.fps = max(10, min(20, int(fps)))
        self.frames = queue.Queue(maxsize=1)
        self.error = None
        self.closed = threading.Event()
        self.process = None
        self.thread = threading.Thread(target=self._decode, name="MinaVideoDecoder", daemon=True)
        self.thread.start()

    def _decode(self):
        frame_size = self.width * self.height * 3
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
            "-re", "-stream_loop", "-1", "-i", self.path, "-an", "-sn", "-dn",
            "-vf", f"fps={self.fps},scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ]
        try:
            self.process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, bufsize=frame_size * 2
            )
            while not self.closed.is_set():
                raw = self.process.stdout.read(frame_size)
                if len(raw) != frame_size:
                    if self.closed.is_set():
                        break
                    raise RuntimeError("Video decoding failed. Try an MP4 encoded with H.264.")
                frame = Image.frombytes("RGB", (self.width, self.height), raw)
                try:
                    self.frames.put_nowait(frame)
                except queue.Full:
                    try:
                        self.frames.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self.frames.put_nowait(frame)
                    except queue.Full:
                        pass
        except Exception as exc:
            if not self.closed.is_set():
                self.error = str(exc)
        finally:
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.wait()

    def get_frame(self):
        newest = None
        while True:
            try:
                newest = self.frames.get_nowait()
            except queue.Empty:
                return newest

    def get_error(self):
        return self.error

    def stop(self):
        self.closed.set()
        if self.process and self.process.poll() is None:
            self.process.kill()
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
