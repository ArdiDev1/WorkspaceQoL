from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Layout


class LayoutStorageService:
    def __init__(self) -> None:
        self._directory = Path(os.environ["LOCALAPPDATA"]) / "WindowLayoutManager"
        self._file_path = self._directory / "layouts.json"
        self._directory.mkdir(parents=True, exist_ok=True)

    def load_layouts(self) -> list[Layout]:
        if not self._file_path.exists():
            return []

        raw = self._file_path.read_text(encoding="utf-8")
        if not raw.strip():
            return []

        return [Layout.from_dict(item) for item in json.loads(raw)]

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

    def delete_layout(self, name: str) -> None:
        layouts = [item for item in self.load_layouts() if item.name.lower() != name.lower()]
        self._write(layouts)

    def _write(self, layouts: list[Layout]) -> None:
        data = [layout.to_dict() for layout in layouts]
        self._file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
