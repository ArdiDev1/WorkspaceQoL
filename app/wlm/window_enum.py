from __future__ import annotations

import psutil
import win32gui
import win32process

from .models import WindowSlot


class WindowEnumerationService:
    def enumerate_windows(self) -> list[WindowSlot]:
        windows: list[WindowSlot] = []

        def on_window(hwnd: int, _lparam) -> bool:
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)

                try:
                    process_name = psutil.Process(process_id).name()
                except psutil.NoSuchProcess:
                    return True

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

            return True

        win32gui.EnumWindows(on_window, None)
        return windows
