from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .hotkeys import HotkeyService, parse_hotkey
from .models import Layout
from .restore import LayoutRestoreService
from .storage import LayoutStorageService
from .window_enum import WindowEnumerationService

APP_TITLE = "Window Layout Manager"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.storage = LayoutStorageService()
        self.window_enum = WindowEnumerationService()
        self.restore_service = LayoutRestoreService()
        self.hotkeys = HotkeyService()

        self._layouts: list[Layout] = []

        root.title(APP_TITLE)
        root.geometry("720x450")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_widgets()
        self._refresh_layouts()

        self.hotkeys.start()
        self.root.after(50, self._poll_hotkey_queue)

    def _build_widgets(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=(12, 0))

        self.name_entry = tk.Entry(top, width=40)
        self.name_entry.pack(side="left", padx=(0, 8))

        tk.Button(top, text="Save Current Layout", command=self._on_save).pack(side="left")

        self.layouts_listbox = tk.Listbox(self.root)
        self.layouts_listbox.pack(fill="both", expand=True, padx=12, pady=12)

        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(bottom, text="Restore", command=self._on_restore).pack(side="left", padx=(0, 8))
        tk.Button(bottom, text="Delete", command=self._on_delete).pack(side="left", padx=(0, 8))

        self.hotkey_entry = tk.Entry(bottom, width=16)
        self.hotkey_entry.insert(0, "Ctrl+Alt+L")
        self.hotkey_entry.pack(side="left", padx=(0, 8))

        tk.Button(bottom, text="Set Hotkey", command=self._on_set_hotkey).pack(side="left")

    def _refresh_layouts(self) -> None:
        self._layouts = self.storage.load_layouts()
        self.layouts_listbox.delete(0, tk.END)
        for layout in self._layouts:
            self.layouts_listbox.insert(tk.END, layout.name)

    def _selected_layout(self) -> Layout | None:
        selection = self.layouts_listbox.curselection()
        if not selection:
            return None
        return self._layouts[selection[0]]

    def _on_save(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showinfo(APP_TITLE, "Please enter a layout name.")
            return

        layout = Layout(name=name, windows=self.window_enum.enumerate_windows())
        self.storage.save_layout(layout)
        self._refresh_layouts()

    def _on_restore(self) -> None:
        layout = self._selected_layout()
        if layout is not None:
            self.restore_service.restore(layout)

    def _on_delete(self) -> None:
        layout = self._selected_layout()
        if layout is not None:
            self.storage.delete_layout(layout.name)
            self._refresh_layouts()

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

    def _restore_by_name(self, name: str) -> None:
        for layout in self.storage.load_layouts():
            if layout.name.lower() == name.lower():
                self.restore_service.restore(layout)
                return

    def _poll_hotkey_queue(self) -> None:
        callback = self.hotkeys.poll()
        while callback is not None:
            callback()
            callback = self.hotkeys.poll()
        self.root.after(50, self._poll_hotkey_queue)

    def _on_close(self) -> None:
        self.hotkeys.stop()
        self.root.destroy()
