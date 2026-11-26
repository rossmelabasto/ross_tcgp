"""Tiny wrapper around the ``adb`` command line tool.

Only three things are needed from the phone: take a screenshot, drag the list
and tap. Screenshots use ``adb exec-out screencap -p`` (PNG straight to
stdout, no temp file on the phone).

Drags use ``input motionevent`` (DOWN, a few MOVEs, a short pause, UP) instead
of ``input swipe``: a swipe ends while the finger is still moving, so the list
keeps scrolling by inertia ("fling") an unpredictable distance. Pausing before
lifting the finger stops the list right where the finger is.
"""

from __future__ import annotations

import io
import shutil
import struct
import subprocess

from PIL import Image

GAME_PACKAGE = "jp.pokemon.pokemontcgp"


class AdbError(RuntimeError):
    pass


class Device:
    def __init__(self, serial: str | None = None):
        if not shutil.which("adb"):
            raise AdbError("adb not found: install Android platform-tools")
        self.serial = serial or self._pick_device()

    def _base(self) -> list[str]:
        return ["adb", "-s", self.serial]

    @staticmethod
    def _pick_device() -> str:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
        devices = [ln.split()[0] for ln in out.splitlines()[1:] if ln.strip().endswith("device")]
        if not devices:
            raise AdbError("no device connected (check `adb devices` and USB debugging)")
        if len(devices) > 1:
            raise AdbError(f"several devices connected, pass --serial: {', '.join(devices)}")
        return devices[0]

    def shell(self, command: str) -> str:
        proc = subprocess.run(self._base() + ["shell", command], capture_output=True, text=True)
        if proc.returncode != 0:
            raise AdbError(proc.stderr.strip() or f"adb shell failed: {command}")
        return proc.stdout

    def screenshot(self) -> Image.Image:
        """Grab the screen as raw RGBA pixels.

        ``screencap -p`` makes the phone compress a PNG first (~2 s on a
        1080x2340 screen); the raw dump is ~10 MB but arrives in ~1 s over USB.
        The raw format is a small header (width, height, pixel format and,
        on Android 8+, a colour-space field) followed by the pixels.
        """
        proc = subprocess.run(self._base() + ["exec-out", "screencap"], capture_output=True)
        raw = proc.stdout
        if proc.returncode != 0 or len(raw) < 16:
            raise AdbError("screenshot failed (is the screen on and unlocked?)")
        width, height, fmt = struct.unpack_from("<3I", raw)
        header = len(raw) - width * height * 4
        if fmt != 1 or header not in (12, 16):  # 1 = RGBA_8888
            img = Image.open(io.BytesIO(self._png()))  # unusual device: fall back
            img.load()
            return img.convert("RGB")
        return Image.frombuffer("RGBA", (width, height), raw[header:], "raw", "RGBA", 0, 1).convert("RGB")

    def _png(self) -> bytes:
        proc = subprocess.run(self._base() + ["exec-out", "screencap", "-p"], capture_output=True)
        if proc.returncode != 0 or not proc.stdout.startswith(b"\x89PNG"):
            raise AdbError("screenshot failed (is the screen on and unlocked?)")
        return proc.stdout

    def foreground_package(self) -> str | None:
        out = self.shell("dumpsys window | grep mCurrentFocus")
        for token in out.replace("/", " ").replace("}", " ").split():
            if "." in token and not token.startswith("Window"):
                return token
        return None

    def tap(self, x: int, y: int) -> None:
        self.shell(f"input tap {x} {y}")

    def drag(self, x: int, y_from: int, y_to: int, steps: int = 8, hold: float = 0.35) -> None:
        """Drag vertically and hold still before lifting, so the list doesn't fling."""
        moves = "; ".join(
            f"input motionevent MOVE {x} {round(y_from + (y_to - y_from) * i / steps)}"
            for i in range(1, steps + 1)
        )
        self.shell(
            f"input motionevent DOWN {x} {y_from}; {moves}; sleep {hold}; "
            f"input motionevent UP {x} {y_to}"
        )
