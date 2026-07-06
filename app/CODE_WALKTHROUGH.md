# Code Walkthrough

A line-by-line explanation of every source file in `app/`. Blank lines and
standalone closing brackets are skipped since they carry no behavior; every
statement that does something is covered.

---

## `wlm/models.py`

```python
from __future__ import annotations
```
Line 1. Lets type hints like `list[WindowSlot]` and `Layout | None` work on
older Python versions by treating all annotations as strings instead of
evaluating them immediately. Not strictly required on 3.13, but harmless and
keeps the file portable.

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
```
Lines 3–4. `dataclass`/`field` build the two plain data containers below;
`asdict` recursively converts a dataclass (and nested dataclasses) into a
plain `dict` for JSON serialization. `datetime`/`timezone` are used to stamp
a layout with its creation time in UTC.

```python
@dataclass
class WindowSlot:
    title: str = ""
    process_name: str = ""
    process_id: int = 0
    window_handle: int = 0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    is_visible: bool = True
```
Lines 8–17. One `WindowSlot` = one captured window: its title, owning
process name/PID, raw Win32 window handle (`HWND`, represented as a plain
`int` in Python — pywin32 hands these back as ints), its screen rectangle
(`x, y, width, height`), and whether it was visible when captured. Every
field has a default so `WindowSlot()` alone is valid — used by tests to build
minimal slots without specifying every field.

```python
    @staticmethod
    def from_dict(data: dict) -> "WindowSlot":
        return WindowSlot(
            title=data.get("title", ""),
            ...
        )
```
Lines 19–31. Rebuilds a `WindowSlot` from a plain dict (i.e. what
`json.loads` hands back). Uses `.get(key, default)` for every field rather
than `data[key]` so that loading an older or hand-edited `layouts.json`
missing a field doesn't crash — it just falls back to the field's default.

```python
@dataclass
class Layout:
    name: str = ""
    windows: list[WindowSlot] = field(default_factory=list)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```
Lines 34–38. A `Layout` is a named group of `WindowSlot`s plus a creation
timestamp. `windows` uses `field(default_factory=list)` instead of `= []`
because a bare mutable default would be *shared* across every `Layout`
instance (the classic Python mutable-default-argument trap) — `dataclasses`
enforces this by raising an error if you try `= []` directly. `created_at_utc`
similarly uses a `default_factory` lambda so the timestamp is evaluated fresh
each time a `Layout` is constructed, not once at class-definition time.

```python
    def to_dict(self) -> dict:
        data = asdict(self)
        return data
```
Lines 40–42. Converts the whole `Layout` (including its list of
`WindowSlot`s) into nested plain dicts/lists, ready for `json.dumps`.

```python
    @staticmethod
    def from_dict(data: dict) -> "Layout":
        return Layout(
            name=data.get("name", ""),
            windows=[WindowSlot.from_dict(w) for w in data.get("windows", [])],
            created_at_utc=data.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
        )
```
Lines 44–50. The inverse of `to_dict`: rebuilds a `Layout` from a plain dict,
mapping each raw window dict back through `WindowSlot.from_dict`.

```python
    def __str__(self) -> str:
        return self.name
```
Lines 52–53. Makes `str(layout)` return just its name — convenient anywhere
a `Layout` needs to render as text (not currently relied on by `app.py`,
which reads `.name` directly, but harmless to have).

---

## `wlm/storage.py`

```python
import json
import os
from pathlib import Path

from .models import Layout
```
Lines 3–7. `json` for (de)serializing to/from `layouts.json`. `os` to read
the `LOCALAPPDATA` environment variable. `Path` for filesystem paths (nicer
API than string concatenation). `Layout` is the model this service persists.

```python
class LayoutStorageService:
    def __init__(self) -> None:
        self._directory = Path(os.environ["LOCALAPPDATA"]) / "WindowLayoutManager"
        self._file_path = self._directory / "layouts.json"
        self._directory.mkdir(parents=True, exist_ok=True)
```
Lines 11–14. On construction, computes the storage directory as
`%LOCALAPPDATA%\WindowLayoutManager` (the standard per-user, non-roaming data
location on Windows) and the JSON file inside it, then creates that
directory if it doesn't already exist (`exist_ok=True` avoids an error if it
does). Reading `os.environ["LOCALAPPDATA"]` with `[]` rather than `.get(...)`
is deliberate: if that variable is ever missing, we want a loud `KeyError`
immediately, not a service that silently writes somewhere unexpected. This
is also the line the test suite's `isolated_local_appdata` fixture hooks
into — it patches `LOCALAPPDATA` before this constructor runs, so tests get
an isolated temp directory instead of the real one.

```python
    def load_layouts(self) -> list[Layout]:
        if not self._file_path.exists():
            return []

        raw = self._file_path.read_text(encoding="utf-8")
        if not raw.strip():
            return []

        return [Layout.from_dict(item) for item in json.loads(raw)]
```
Lines 16–24. Returns every saved layout. Two early-out guards: if the file
was never created yet (fresh install / fresh temp dir in tests), or if it
exists but is empty/whitespace-only (e.g. left over from a previous crash
mid-write), return an empty list rather than letting `json.loads` raise on
empty input. Otherwise parses the JSON array and maps each element through
`Layout.from_dict`.

```python
    def save_layout(self, layout: Layout) -> None:
        layouts = self.load_layouts()
        existing_index = next(
            (i for i, item in enumerate(layouts) if item.name.lower() == layout.name.lower()),
            None,
        )

        if existing_index is not None:
            layouts[existing_index] = layout
        else:
            layouts.append(layout)

        self._write(layouts)
```
Lines 26–38. An upsert: loads everything currently saved, searches for a
layout with the same name (case-insensitively, so "Office" and "office" are
the same layout), and either replaces that entry in place or appends a new
one, then writes the whole list back out. `next(generator, None)` is a
concise way to get "the first matching index, or `None` if nothing
matched" without a manual loop-and-break.

```python
    def delete_layout(self, name: str) -> None:
        layouts = [item for item in self.load_layouts() if item.name.lower() != name.lower()]
        self._write(layouts)
```
Lines 40–42. Loads everything, keeps every layout whose name doesn't match
(case-insensitive) the one being deleted, writes the filtered list back.
Deleting a name that doesn't exist is a no-op (nothing gets filtered out) —
covered by `test_delete_missing_layout_is_a_no_op`.

```python
    def _write(self, layouts: list[Layout]) -> None:
        data = [layout.to_dict() for layout in layouts]
        self._file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
```
Lines 44–46. The single place that actually touches disk: converts every
`Layout` to a plain dict, serializes the whole list as pretty-printed
(`indent=2`) JSON, and overwrites `layouts.json` in one shot. Both
`save_layout` and `delete_layout` funnel through here so there's exactly one
write path to keep in sync with the on-disk format.

---

## `wlm/window_enum.py`

```python
import psutil
import win32gui
import win32process

from .models import WindowSlot
```
Lines 3–7. `win32gui` wraps the Win32 `user32.dll` calls used here
(`EnumWindows`, `IsWindowVisible`, `GetWindowText`, `GetWindowRect`).
`win32process` gives access to `GetWindowThreadProcessId`. `psutil` is used
instead of raw Win32 to resolve a process ID into a human-readable process
name — it's simpler and safer than manually opening a process handle and
querying its module filename.

```python
class WindowEnumerationService:
    def enumerate_windows(self) -> list[WindowSlot]:
        windows: list[WindowSlot] = []

        def on_window(hwnd: int, _lparam) -> bool:
```
Lines 10–14. `enumerate_windows` builds up a `windows` list by defining a
callback, `on_window`, and handing it to `win32gui.EnumWindows` (below).
Win32's `EnumWindows` API calls this callback once per top-level window on
the desktop; `_lparam` is a user-data pointer parameter required by the
Win32 callback signature but unused here (the leading underscore signals
"intentionally ignored").

```python
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
```
Line 15. Filters out windows we don't care about: `IsWindowVisible` skips
hidden windows, and `GetWindowText(hwnd)` being truthy (non-empty) skips
titleless windows — mostly invisible helper/utility windows that Windows
creates internally and that a user would never think of as "a window" to
save/restore.

```python
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
```
Lines 16–17. `GetWindowRect` returns the window's bounding rectangle in
screen coordinates as `(left, top, right, bottom)`. `GetWindowThreadProcessId`
returns a `(thread_id, process_id)` pair; the thread ID isn't needed here so
it's discarded into `_`.

```python
                try:
                    process_name = psutil.Process(process_id).name()
                except psutil.NoSuchProcess:
                    return True
```
Lines 19–22. Looks up the owning process's name (e.g. `"firefox.exe"`).
Guarded because a window's process can exit in the split second between
`EnumWindows` handing us the `hwnd` and this lookup running — without the
guard, `psutil.Process(pid)` would raise and crash the *entire* enumeration
over one disappearing window. On that race, this window is simply skipped
(`return True` tells `EnumWindows` to keep enumerating the rest).

```python
                windows.append(
                    WindowSlot(
                        title=win32gui.GetWindowText(hwnd),
                        process_name=process_name,
                        process_id=process_id,
                        window_handle=hwnd,
                        x=left,
                        y=top,
                        width=right - left,
                        height=bottom - top,
                        is_visible=True,
                    )
                )
```
Lines 24–36. Builds a `WindowSlot` from everything gathered above and adds
it to the results. Note `width`/`height` are *derived* from the rectangle
(`right - left`, `bottom - top`) since Win32 gives corners, not a
width/height pair directly. `is_visible=True` is hardcoded here because we
already filtered to only visible windows on line 15 — every slot that makes
it this far is visible by construction.

```python
            return True

        win32gui.EnumWindows(on_window, None)
        return windows
```
Lines 38, 40–41. `return True` at the end of `on_window` tells `EnumWindows`
to continue to the next window (returning `False` from a Win32 enum callback
stops enumeration early — not needed here since we want every window
inspected). `win32gui.EnumWindows(on_window, None)` is the actual call that
drives the whole callback loop (the `None` is the unused `lparam` passed
through to every `on_window` call). Once it returns, every visible, titled
window has been visited, and the accumulated `windows` list is returned.

---

## `wlm/restore.py`

```python
import win32gui

from .models import Layout


class LayoutRestoreService:
    def restore(self, layout: Layout) -> None:
        for slot in layout.windows:
            if slot.window_handle:
                win32gui.MoveWindow(slot.window_handle, slot.x, slot.y, slot.width, slot.height, True)
```
The whole file. For every `WindowSlot` in the layout, if it has a non-zero
`window_handle` (a handle of `0` means "not a real window," e.g. a slot
built by hand without one — see the tests), calls `MoveWindow` to move/resize
that window back to its saved rectangle. The final `True` argument is
Win32's `bRepaint` flag, telling Windows to immediately repaint the window
in its new position/size rather than leaving that until the next natural
repaint.

**Known limitation** (inherited by design from the original app, not a bug):
this matches purely on the *raw* handle captured at save time. Window
handles are only valid for the lifetime of that specific window instance —
if the target app was closed and reopened (or the machine rebooted) since
the layout was saved, its handle has changed and `MoveWindow` silently does
nothing for that slot. Matching by title/process as a fallback is a
documented future improvement, not implemented yet.

---

## `wlm/hotkeys.py`

This file is the one genuinely new piece of behavior versus a straight
port — it registers a real, OS-level global hotkey (works even when the
app isn't focused), which requires a small dedicated Win32 message loop.

```python
import queue
import threading
from typing import Callable, Optional

import win32api
import win32con
import win32gui
```
Lines 3–9. `queue.Queue` is the thread-safe hand-off between the background
Win32 listener thread and Tkinter's main thread (Tkinter is not thread-safe —
you can't call into it from another thread). `threading` runs that listener
in the background. `win32api`/`win32gui` provide the window/message-loop
primitives; `win32con` supplies Win32 constants (`MOD_CONTROL`, `WM_HOTKEY`,
etc.).

```python
_MODIFIER_MAP = {
    "ctrl": win32con.MOD_CONTROL,
    "control": win32con.MOD_CONTROL,
    "alt": win32con.MOD_ALT,
    "shift": win32con.MOD_SHIFT,
    "win": win32con.MOD_WIN,
}
```
Lines 11–17. Maps the human-typed modifier names (as they'd appear in
`"Ctrl+Alt+L"`) to the Win32 `RegisterHotKey` modifier bit flags. Both
`"ctrl"` and `"control"` are accepted since either is a natural thing to
type.

```python
_MOD_NOREPEAT = 0x4000
```
Line 19. `MOD_NOREPEAT` isn't exposed as a named constant in `win32con`, so
it's hardcoded here (this is its actual documented Win32 value). Registering
a hotkey with this flag means holding the key combo down doesn't fire the
callback repeatedly via OS key-repeat — one press, one trigger.

```python
_HOTKEY_ID = 1
_WM_APP_REGISTER = win32con.WM_APP + 1
_WM_APP_UNREGISTER = win32con.WM_APP + 2
```
Lines 21–23. `_HOTKEY_ID` is the identifier Win32 uses to refer to "the"
hotkey — since this app only supports one active binding at a time, it's a
constant rather than something generated per-registration.
`WM_APP`-based values are the standard way to define your own custom window
messages (the `WM_APP` range is reserved by Windows for exactly this).
`_WM_APP_REGISTER` is actually used (see `_wnd_proc` below);
`_WM_APP_UNREGISTER` is defined for symmetry/future use but isn't currently
sent anywhere — unregistering happens implicitly whenever a new hotkey is
registered, or on `stop()`.

```python
def parse_hotkey(text: str) -> tuple[int, int]:
    parts = [p.strip() for p in text.split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError("Hotkey must include at least one modifier and a key, e.g. Ctrl+Alt+L")
```
Lines 26–29. Splits input like `"Ctrl+Alt+L"` on `+`, trims whitespace
around each piece, and drops any empty pieces (guards against stray `+`s or
trailing/leading `+`). Requires at least two parts — one modifier and one
key — otherwise a bare key like `"L"` would register as a system-wide,
un-modified hotkey that could interfere with normal typing.

```python
    *modifier_parts, key_part = parts
    modifiers = 0
    for part in modifier_parts:
        mod = _MODIFIER_MAP.get(part.lower())
        if mod is None:
            raise ValueError(f"Unknown modifier: {part}")
        modifiers |= mod
```
Lines 31–37. Unpacks everything but the last piece as modifiers, and the
last piece as the key itself (so `"Ctrl+Alt+L"` → modifiers
`["Ctrl", "Alt"]`, key `"L"`). Looks up each modifier case-insensitively in
`_MODIFIER_MAP`; an unrecognized modifier (e.g. a typo) raises immediately
with the offending text so the UI can show a clear error. `modifiers |= mod`
OR-combines the bit flags — `RegisterHotKey` expects a single integer with
all applicable modifier bits set.

```python
    if len(key_part) != 1 or not key_part.isalnum():
        raise ValueError("The key must be a single letter or digit, e.g. Ctrl+Alt+L")

    return modifiers | _MOD_NOREPEAT, ord(key_part.upper())
```
Lines 39–42. Restricts the key itself to a single alphanumeric character —
keeps `parse_hotkey` simple by not having to map named keys like "Enter" or
"F5" to their virtual-key codes. `ord(key_part.upper())` works because, for
Windows, virtual-key codes for `'0'`–`'9'` and `'A'`–`'Z'` are numerically
identical to their ASCII codes — `ord('L')` is exactly the VK code
`RegisterHotKey` expects. `_MOD_NOREPEAT` is OR'd in here so every hotkey
this function produces automatically gets the no-repeat behavior.

```python
class HotkeyService:
    def __init__(self) -> None:
        self._callback_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._callback: Optional[Callable[[], None]] = None
        self._hwnd = 0
        self._registered = False
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
```
Lines 46–52. `_callback_queue` is where a triggered hotkey's callback lands,
waiting to be picked up by Tkinter's main-thread polling loop (in `app.py`).
`_callback` holds the *currently bound* callback (only one at a time,
matching the single-hotkey-binding design). `_hwnd` is the handle of the
hidden listener window, `0` until `_run` creates it. `_registered` tracks
whether a hotkey is currently registered with Windows (so a second
`register()` call knows to unregister the old one first). `_thread` is the
background listener thread, created in `start()`. `_ready` is a
`threading.Event` used to block `start()` until the background thread has
actually created its window and is ready to receive messages — without it,
`register()` could be called before `_hwnd` exists.

```python
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)
```
Lines 54–57. Spawns `_run` (below) on a background thread and blocks (up to
5 seconds, as a safety cap) until that thread signals `_ready`. `daemon=True`
means this thread won't by itself prevent the Python process from exiting —
though in practice `stop()` shuts it down explicitly before app exit anyway.

```python
    def register(self, modifiers: int, vk: int, callback: Callable[[], None]) -> None:
        self._callback = callback
        win32api.PostMessage(self._hwnd, _WM_APP_REGISTER, modifiers, vk)
```
Lines 59–61. Stores the callback to invoke when the hotkey fires, then
*posts* (asynchronously, doesn't block) a custom message to the listener
window asking it to actually register the hotkey. This indirection exists
because `RegisterHotKey`/`UnregisterHotKey` must be called from the same
thread that owns the window/message queue — since `register()` is called
from the Tkinter main thread but the window lives on the background thread,
it can't call `RegisterHotKey` directly; it has to ask that thread to do it,
via a message, which `_wnd_proc` (below) handles when it's received on the
correct thread.

```python
    def poll(self) -> Optional[Callable[[], None]]:
        try:
            return self._callback_queue.get_nowait()
        except queue.Empty:
            return None
```
Lines 63–67. Non-blocking check: returns the next pending triggered
callback, or `None` if nothing's waiting. Called repeatedly from Tkinter's
`root.after` loop in `app.py` rather than blocking, since blocking here
would freeze the UI.

```python
    def stop(self) -> None:
        if self._hwnd:
            win32api.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)
```
Lines 69–73. Shutdown: posts a standard `WM_CLOSE` to the listener window
(handled below to clean up and quit its message loop), then waits (up to 2
seconds) for the background thread to actually finish, so the app doesn't
exit while that thread is mid-cleanup.

```python
    def _run(self) -> None:
        class_name = "WindowLayoutManagerHotkeyWindow"
        h_instance = win32api.GetModuleHandle(None)

        wnd_class = win32gui.WNDCLASS()
        wnd_class.lpfnWndProc = self._wnd_proc
        wnd_class.lpszClassName = class_name
        wnd_class.hInstance = h_instance
        class_atom = win32gui.RegisterClass(wnd_class)
```
Lines 75–83. The background thread's entry point. To receive any Win32
messages (including `WM_HOTKEY`) a thread needs a window, and creating a
window first requires registering a *window class* describing it.
`GetModuleHandle(None)` gets a handle to the current process's module (a
required field on the class struct). `wnd_class.lpfnWndProc = self._wnd_proc`
is the key line: it tells Windows to call `self._wnd_proc` (below) for every
message sent to windows of this class. `RegisterClass` registers it with
Windows and returns an atom (a lightweight class identifier) used to create
windows of this class.

```python
        self._hwnd = win32gui.CreateWindow(
            class_atom, class_name, 0, 0, 0, 0, 0, 0, 0, h_instance, None
        )
        self._ready.set()
        win32gui.PumpMessages()
```
Lines 85–89. Creates an actual window of that class. Its style/position/size
arguments are all `0` because this window is never shown — it exists purely
as a message target, not a visible UI element. Once created, `_ready.set()`
unblocks `start()` (the window/`hwnd` now exists and is safe to post
messages to), and `PumpMessages()` starts this thread's Win32 message loop,
which blocks here, dispatching incoming messages to `_wnd_proc` until the
loop is told to quit (see `WM_DESTROY` below).

```python
    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int):
        if msg == _WM_APP_REGISTER:
            if self._registered:
                win32gui.UnregisterHotKey(hwnd, _HOTKEY_ID)
            win32gui.RegisterHotKey(hwnd, _HOTKEY_ID, wparam, lparam)
            self._registered = True
            return 0
```
Lines 91–97. The message handler, invoked by `PumpMessages()` on the
listener thread for every message the window receives. Handles the custom
`_WM_APP_REGISTER` message posted by `register()`: `modifiers`/`vk` arrive
packed into `wparam`/`lparam` (Win32's generic "two extra integers" message
parameters). If a hotkey is already registered, unregisters it first
(`RegisterHotKey` errors if you try to register the same ID twice without
unregistering) — this is what makes "setting a new hotkey replaces the old
one" work. `return 0` tells Windows the message was handled.

```python
        if msg == win32con.WM_HOTKEY:
            if self._callback is not None:
                self._callback_queue.put(self._callback)
            return 0
```
Lines 99–102. The actual payoff: Windows sends `WM_HOTKEY` to this window
whenever the registered global combo is pressed, from *any* application.
Rather than calling `self._callback()` directly here — which would run it on
the background thread, unsafe for Tkinter — it's pushed onto the
thread-safe queue for `app.py`'s polling loop to pick up and run on the main
thread.

```python
        if msg == win32con.WM_CLOSE:
            if self._registered:
                win32gui.UnregisterHotKey(hwnd, _HOTKEY_ID)
            win32gui.DestroyWindow(hwnd)
            return 0

        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
```
Lines 104–112. Two-step shutdown, triggered by `stop()`'s `WM_CLOSE` post:
first unregister the hotkey (so it doesn't linger as a system-wide binding
after the app closes) and destroy the window, which in turn generates a
`WM_DESTROY` message; handling *that* by calling `PostQuitMessage(0)` is
what makes `PumpMessages()` in `_run` actually return, ending the background
thread's message loop (and the thread itself, since `_run` has nothing left
to do after that call returns).

```python
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
```
Line 114. For every message not explicitly handled above, defers to
Windows' default window procedure — required so the window still behaves
correctly for the many housekeeping messages it wasn't written to care
about.

---

## `wlm/app.py`

```python
import tkinter as tk
from tkinter import messagebox

from .hotkeys import HotkeyService, parse_hotkey
from .models import Layout
from .restore import LayoutRestoreService
from .storage import LayoutStorageService
from .window_enum import WindowEnumerationService

APP_TITLE = "Window Layout Manager"
```
Lines 3–12. Standard library Tkinter for widgets and `messagebox` for popup
dialogs (info/error). Imports every service the UI wires together.
`APP_TITLE` is a single shared constant reused as both the window title and
every dialog box's title, so renaming the app means changing one line.

```python
class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.storage = LayoutStorageService()
        self.window_enum = WindowEnumerationService()
        self.restore_service = LayoutRestoreService()
        self.hotkeys = HotkeyService()

        self._layouts: list[Layout] = []
```
Lines 16–23. Takes the already-created Tk root window (built in `main.py`)
and instantiates one of each service. `self._layouts` mirrors, in memory,
whatever's currently shown in the listbox — kept in sync by
`_refresh_layouts` — so that clicking an item by its listbox index can be
mapped straight back to the corresponding `Layout` object without re-reading
the file on every click.

```python
        root.title(APP_TITLE)
        root.geometry("720x450")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
```
Lines 25–27. Sets the window's title bar text and initial size in pixels.
`root.protocol("WM_DELETE_WINDOW", ...)` intercepts the window's close
button (the OS-level "X") so `_on_close` (below) can run its own cleanup —
stopping the hotkey thread — instead of Tkinter just tearing the window down
directly.

```python
        self._build_widgets()
        self._refresh_layouts()

        self.hotkeys.start()
        self.root.after(50, self._poll_hotkey_queue)
```
Lines 29–33. Lays out all the widgets, then populates the listbox from
whatever's already saved on disk. Starts the background hotkey listener
thread. Schedules the first run of `_poll_hotkey_queue` 50ms from now —
`root.after` is Tkinter's non-blocking "call this later, on the UI thread"
primitive; this kicks off a recurring poll (each call reschedules itself,
see below) that checks for triggered hotkeys roughly 20 times a second.

```python
    def _build_widgets(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=(12, 0))

        self.name_entry = tk.Entry(top, width=40)
        self.name_entry.pack(side="left", padx=(0, 8))

        tk.Button(top, text="Save Current Layout", command=self._on_save).pack(side="left")
```
Lines 35–42. Builds the top row: a `Frame` container that stretches to fill
the window's width (`fill="x"`), holding a text entry (for the new layout's
name) and a button that calls `_on_save` when clicked. `pack(side="left", ...)`
lays widgets out left-to-right within their frame; the `padx`/`pady` tuples
are (before, after) pixel spacing.

```python
        self.layouts_listbox = tk.Listbox(self.root)
        self.layouts_listbox.pack(fill="both", expand=True, padx=12, pady=12)
```
Lines 44–45. The main list of saved layouts, packed to both fill and expand
into any extra space (so resizing the window grows the list, not just the
frames around it).

```python
        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(bottom, text="Restore", command=self._on_restore).pack(side="left", padx=(0, 8))
        tk.Button(bottom, text="Delete", command=self._on_delete).pack(side="left", padx=(0, 8))

        self.hotkey_entry = tk.Entry(bottom, width=16)
        self.hotkey_entry.insert(0, "Ctrl+Alt+L")
        self.hotkey_entry.pack(side="left", padx=(0, 8))

        tk.Button(bottom, text="Set Hotkey", command=self._on_set_hotkey).pack(side="left")
```
Lines 47–57. The bottom row: Restore/Delete buttons acting on whatever's
currently selected in the listbox, a text entry pre-filled
(`.insert(0, ...)`, inserting at character position 0) with a sensible
default hotkey string, and the "Set Hotkey" button that reads that entry
when clicked.

```python
    def _refresh_layouts(self) -> None:
        self._layouts = self.storage.load_layouts()
        self.layouts_listbox.delete(0, tk.END)
        for layout in self._layouts:
            self.layouts_listbox.insert(tk.END, layout.name)
```
Lines 59–63. Re-reads every layout from disk into `self._layouts`, clears
the listbox entirely (`delete(0, tk.END)` — from the first item to the
last), and re-populates it with just the names, in the same order as
`self._layouts` — that parallel ordering is what lets `_selected_layout`
(below) map a listbox click back to an object by index. Called after every
save/delete so the UI always reflects what's actually on disk.

```python
    def _selected_layout(self) -> Layout | None:
        selection = self.layouts_listbox.curselection()
        if not selection:
            return None
        return self._layouts[selection[0]]
```
Lines 65–69. `curselection()` returns a tuple of selected indices (empty if
nothing's selected, since this listbox doesn't enable multi-select — it'll
have zero or one entries in practice). Returns `None` if nothing's selected,
otherwise indexes into `self._layouts` using the first (only) selected
index to get the actual `Layout` object.

```python
    def _on_save(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showinfo(APP_TITLE, "Please enter a layout name.")
            return

        layout = Layout(name=name, windows=self.window_enum.enumerate_windows())
        self.storage.save_layout(layout)
        self._refresh_layouts()
```
Lines 71–79. Handler for "Save Current Layout". Reads and trims the name
field; if it's empty, shows an info dialog and bails out rather than saving
an unnamed layout. Otherwise builds a new `Layout`, capturing the *current*
window positions right now via `enumerate_windows()`, persists it (which
upserts by name — saving under an existing name overwrites it), and
refreshes the listbox to show the result.

```python
    def _on_restore(self) -> None:
        layout = self._selected_layout()
        if layout is not None:
            self.restore_service.restore(layout)
```
Lines 81–84. Handler for "Restore". If something's selected, hands it
straight to `LayoutRestoreService.restore`. Silently does nothing if
nothing's selected (no error dialog) — clicking Restore with no selection
just isn't an action, rather than something worth interrupting the user
about.

```python
    def _on_delete(self) -> None:
        layout = self._selected_layout()
        if layout is not None:
            self.storage.delete_layout(layout.name)
            self._refresh_layouts()
```
Lines 86–90. Handler for "Delete". Same guard pattern; deletes by name from
storage, then refreshes the list so the deleted entry visibly disappears.

```python
    def _on_set_hotkey(self) -> None:
        layout = self._selected_layout()
        if layout is None:
            messagebox.showinfo(APP_TITLE, "Select a layout first, then set a hotkey to restore it.")
            return

        try:
            modifiers, vk = parse_hotkey(self.hotkey_entry.get().strip())
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        layout_name = layout.name
        self.hotkeys.register(modifiers, vk, lambda: self._restore_by_name(layout_name))
        messagebox.showinfo(APP_TITLE, f"Hotkey set to restore '{layout_name}'.")
```
Lines 92–106. Handler for "Set Hotkey". Requires a layout to be selected
(unlike Restore/Delete, this one *does* need an explicit dialog telling the
user why nothing happened, since silently doing nothing here would be
confusing given the button appears actionable). Parses the hotkey text box;
any `ValueError` from `parse_hotkey` (bad format, unknown modifier, etc.) is
shown to the user as an error dialog rather than crashing. `layout_name` is
captured into its own local variable specifically so the `lambda` closes
over a plain string rather than the `Layout` object or the loop/selection
state — by the time the hotkey is actually pressed later, `layout` (and
whatever's selected in the listbox) may have changed, but the name captured
at bind-time is what should be restored. Registers the hotkey bound to a
callback that restores by that captured name, then confirms via dialog.

```python
    def _restore_by_name(self, name: str) -> None:
        for layout in self.storage.load_layouts():
            if layout.name.lower() == name.lower():
                self.restore_service.restore(layout)
                return
```
Lines 108–112. The actual callback invoked when the bound hotkey fires.
Deliberately re-reads layouts from storage (rather than closing over the
`Layout` object that existed at bind-time) so that if the layout was
re-saved with updated window positions after the hotkey was set, pressing
the hotkey restores the *latest* version, not a stale in-memory snapshot.
Returns as soon as a case-insensitive name match is found and restored; if
the named layout was deleted since the hotkey was bound, this is a silent
no-op — pressing a hotkey for a deleted layout does nothing rather than
erroring (there's no good UI to show an error into at that moment, since the
hotkey works even when the app isn't focused).

```python
    def _poll_hotkey_queue(self) -> None:
        callback = self.hotkeys.poll()
        while callback is not None:
            callback()
            callback = self.hotkeys.poll()
        self.root.after(50, self._poll_hotkey_queue)
```
Lines 114–119. Runs on the Tkinter main thread every ~50ms (rescheduling
itself via `root.after` each time, forming the recurring loop). Drains
*every* pending callback currently in the queue (the `while`, not just an
`if`) before rescheduling — in case multiple hotkey presses queued up
between polls, all get processed in one pass rather than one per tick.

```python
    def _on_close(self) -> None:
        self.hotkeys.stop()
        self.root.destroy()
```
Lines 121–123. Bound to the window's close button via
`root.protocol("WM_DELETE_WINDOW", ...)` in `__init__`. Stops the hotkey
listener thread cleanly (unregistering the hotkey, joining the thread)
*before* tearing down the Tkinter window — ordering it the other way could
leave the background thread's `PostMessage` calls targeting a window that
Tkinter has already destroyed.

---

## `main.py`

```python
import tkinter as tk

from wlm.app import App


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```
The entry point. `tk.Tk()` creates the actual root window (nothing is shown
yet). `App(root)` runs all the setup in `App.__init__` — building widgets,
loading saved layouts, starting the hotkey listener. `root.mainloop()` then
blocks, running Tkinter's event loop (processing clicks, redraws, and the
scheduled `root.after` callbacks) until the window is closed. The
`if __name__ == "__main__":` guard means `main()` only runs when this file
is executed directly (`python main.py`), not if it were ever imported as a
module elsewhere.

---

## `tests/conftest.py`

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
Makes `import wlm` work inside test files regardless of the directory
`pytest` is invoked from. `Path(__file__).resolve().parent.parent` walks up
from `tests/conftest.py` → `tests/` → `app/` (the directory containing the
`wlm` package), and inserting it at the front of `sys.path` ensures it's
found before any same-named package that might exist elsewhere.

```python
import pytest


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path, monkeypatch):
    """Point LOCALAPPDATA at a throwaway temp dir so tests never touch the real layouts.json."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
```
A pytest fixture. `tmp_path` is a built-in pytest fixture providing a fresh,
unique temporary directory per test function (auto-cleaned up afterward).
`monkeypatch` is pytest's fixture for reversibly patching things (env vars,
attributes, dict entries) that auto-undoes the patch after the test, even if
the test fails. `autouse=True` means every test in the whole `tests/`
folder gets this fixture applied automatically, without needing to name it
as a parameter — so it's impossible to accidentally write a test against
this codebase that touches your real `%LOCALAPPDATA%\WindowLayoutManager\layouts.json`.

---

## `tests/test_storage.py`

Each test constructs its own `LayoutStorageService()` — thanks to the
`autouse` fixture above, `LOCALAPPDATA` is already patched by the time that
constructor runs, so every test starts from a fresh, empty, private
directory with no `layouts.json` yet.

- `test_load_layouts_when_file_missing_returns_empty` — exercises
  `storage.py` lines 17–18 (the file-doesn't-exist guard).
- `test_save_creates_new_layout` — saves one layout, reloads, checks both
  the name and a nested field round-tripped correctly through
  `to_dict`/`from_dict`.
- `test_save_upserts_by_case_insensitive_name` — saves `"Office"`, then
  saves `"office"` with different contents, and asserts there's still only
  one layout and it has the *second* save's data — this is what proves
  `save_layout`'s case-insensitive match-and-replace (not match-and-append)
  actually works.
- `test_delete_removes_layout_case_insensitively` — saves `"temp"`, deletes
  `"TEMP"`, confirms it's gone — proves deletion isn't case-sensitive
  either.
- `test_delete_missing_layout_is_a_no_op` — deletes a name that was never
  saved and confirms the one real layout survives untouched, proving
  `delete_layout` doesn't error or clear everything when the name isn't
  found.

## `tests/test_hotkeys.py`

All tests call `parse_hotkey` directly — no Win32/window state involved, so
no special fixture needed beyond what `conftest.py` already provides.

- `test_parse_simple_combo` — checks `"Ctrl+Alt+L"` sets both the
  `MOD_CONTROL` and `MOD_ALT` bits and resolves the key to `ord('L')`.
- `test_parse_is_case_insensitive_on_modifiers` — same, but with mixed-case
  input (`"ctrl+ALT+k"`), proving the `.lower()` lookup in `_MODIFIER_MAP`
  actually normalizes case rather than being coincidentally correct in the
  first test.
- `test_parse_accepts_digit_key` — confirms digit keys (`"1"`) work, not
  just letters, since `parse_hotkey`'s guard checks `.isalnum()`, not
  `.isalpha()`.
- `test_parse_rejects_missing_modifier` / `test_parse_rejects_unknown_modifier`
  / `test_parse_rejects_multi_char_key` / `test_parse_rejects_empty_string` —
  each feeds an invalid combo and asserts `parse_hotkey` raises `ValueError`,
  covering all four validation branches in the function (too few parts,
  unrecognized modifier name, key longer than one character, and the
  degenerate empty-string case which falls into the "too few parts"
  branch).
