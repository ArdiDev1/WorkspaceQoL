from __future__ import annotations

import queue
import threading
from typing import Callable, Optional

import win32api
import win32con
import win32gui

_MODIFIER_MAP = {
    "ctrl": win32con.MOD_CONTROL,
    "control": win32con.MOD_CONTROL,
    "alt": win32con.MOD_ALT,
    "shift": win32con.MOD_SHIFT,
    "win": win32con.MOD_WIN,
}

_MOD_NOREPEAT = 0x4000

_HOTKEY_ID = 1
_WM_APP_REGISTER = win32con.WM_APP + 1
_WM_APP_UNREGISTER = win32con.WM_APP + 2


def parse_hotkey(text: str) -> tuple[int, int]:
    parts = [p.strip() for p in text.split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError("Hotkey must include at least one modifier and a key, e.g. Ctrl+Alt+L")

    *modifier_parts, key_part = parts
    modifiers = 0
    for part in modifier_parts:
        mod = _MODIFIER_MAP.get(part.lower())
        if mod is None:
            raise ValueError(f"Unknown modifier: {part}")
        modifiers |= mod

    if len(key_part) != 1 or not key_part.isalnum():
        raise ValueError("The key must be a single letter or digit, e.g. Ctrl+Alt+L")

    return modifiers | _MOD_NOREPEAT, ord(key_part.upper())


class HotkeyService:
    def __init__(self) -> None:
        self._callback_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._callback: Optional[Callable[[], None]] = None
        self._hwnd = 0
        self._registered = False
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def register(self, modifiers: int, vk: int, callback: Callable[[], None]) -> None:
        self._callback = callback
        win32api.PostMessage(self._hwnd, _WM_APP_REGISTER, modifiers, vk)

    def poll(self) -> Optional[Callable[[], None]]:
        try:
            return self._callback_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        if self._hwnd:
            win32api.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        class_name = "WindowLayoutManagerHotkeyWindow"
        h_instance = win32api.GetModuleHandle(None)

        wnd_class = win32gui.WNDCLASS()
        wnd_class.lpfnWndProc = self._wnd_proc
        wnd_class.lpszClassName = class_name
        wnd_class.hInstance = h_instance
        class_atom = win32gui.RegisterClass(wnd_class)

        self._hwnd = win32gui.CreateWindow(
            class_atom, class_name, 0, 0, 0, 0, 0, 0, 0, h_instance, None
        )
        self._ready.set()
        win32gui.PumpMessages()

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int):
        if msg == _WM_APP_REGISTER:
            if self._registered:
                win32gui.UnregisterHotKey(hwnd, _HOTKEY_ID)
            win32gui.RegisterHotKey(hwnd, _HOTKEY_ID, wparam, lparam)
            self._registered = True
            return 0

        if msg == win32con.WM_HOTKEY:
            if self._callback is not None:
                self._callback_queue.put(self._callback)
            return 0

        if msg == win32con.WM_CLOSE:
            if self._registered:
                win32gui.UnregisterHotKey(hwnd, _HOTKEY_ID)
            win32gui.DestroyWindow(hwnd)
            return 0

        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
