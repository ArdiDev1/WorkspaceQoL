from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


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

    @staticmethod
    def from_dict(data: dict) -> "WindowSlot":
        return WindowSlot(
            title=data.get("title", ""),
            process_name=data.get("process_name", ""),
            process_id=data.get("process_id", 0),
            window_handle=data.get("window_handle", 0),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 0),
            height=data.get("height", 0),
            is_visible=data.get("is_visible", True),
        )


@dataclass
class Layout:
    name: str = ""
    windows: list[WindowSlot] = field(default_factory=list)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        data = asdict(self)
        return data

    @staticmethod
    def from_dict(data: dict) -> "Layout":
        return Layout(
            name=data.get("name", ""),
            windows=[WindowSlot.from_dict(w) for w in data.get("windows", [])],
            created_at_utc=data.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
        )

    def __str__(self) -> str:
        return self.name
