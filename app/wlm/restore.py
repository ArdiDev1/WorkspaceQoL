from __future__ import annotations

import win32gui

from .models import Layout


class LayoutRestoreService:
    def restore(self, layout: Layout) -> None:
        for slot in layout.windows:
            if slot.window_handle:
                win32gui.MoveWindow(slot.window_handle, slot.x, slot.y, slot.width, slot.height, True)
