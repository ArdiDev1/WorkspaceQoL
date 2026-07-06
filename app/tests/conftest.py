import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path, monkeypatch):
    """Point LOCALAPPDATA at a throwaway temp dir so tests never touch the real layouts.json."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
