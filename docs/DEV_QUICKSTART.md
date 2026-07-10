# Dev Quickstart

This is a plain Python app (no build step) — Tkinter for the UI, `pywin32` for the
Win32 calls (window enumeration, moving windows, global hotkeys), `psutil` for
looking up process names.

## 1. Set up the environment

From the `app/` folder:

```powershell
cd app
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

`requirements-dev.txt` pulls in `requirements.txt` (the runtime deps: `pywin32`,
`psutil`) plus `pytest` for testing. If you only want to run the app and not
touch tests, `pip install -r requirements.txt` is enough.

## 2. Run the app

```powershell
python main.py
```

Opens the "Window Layout Manager" window. See the "manual test checklist" below
for what to click through.

## 3. Run the automated tests

```powershell
python -m pytest
```

`test_storage.py` and `test_hotkeys.py` cover the two pieces of logic that
don't require a live desktop or GUI: layout persistence and hotkey-string
parsing. `window_enum.py`, `restore.py`, `hotkeys.py`'s Win32 listener, and
`app.py`'s UI wiring all call into real Win32 APIs / Tkinter, so they're
exercised manually instead (see checklist below) rather than mocked.

### The test config: `pytest.ini` + `tests/conftest.py`

- **`pytest.ini`** just points pytest at the `tests/` folder (`testpaths = tests`).
- **`tests/conftest.py`** does two things:
  1. Inserts `app/` onto `sys.path` so `import wlm` resolves regardless of
     where `pytest` is invoked from.
  2. Defines an `autouse` fixture, `isolated_local_appdata`, that uses
     `monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))` to redirect
     `LayoutStorageService` at a throwaway per-test temp directory instead of
     your real `%LOCALAPPDATA%\WindowLayoutManager\layouts.json`. Because it's
     `autouse=True`, every test gets this isolation for free — no test can
     accidentally read or clobber your actual saved layouts.

Every test in `test_storage.py` relies on that fixture implicitly: it
constructs a fresh `LayoutStorageService()` per test, and since `LOCALAPPDATA`
is patched before the test body runs, each test starts from an empty,
private `layouts.json`.

## 4. Manual test checklist (things pytest can't cover)

1. **Save**: type a name, click "Save Current Layout" — it appears in the
   list. Check `%LOCALAPPDATA%\WindowLayoutManager\layouts.json` was written.
2. **Restore**: move/resize some windows, select the saved layout, click
   "Restore" — windows snap back.
3. **Hotkey**: select a layout, type a combo (e.g. `Ctrl+Alt+K`), click
   "Set Hotkey". Focus a *different* app and press the combo — the layout
   restores even without the app window focused (proves it's a real global
   hotkey, not just a Tkinter key binding).
4. **Rebind**: set a second hotkey — the first one should stop triggering
   (only one binding is active at a time by design).
5. **Delete**: select a layout, click "Delete" — it disappears from the list
   and from `layouts.json`.
6. **Clean close**: close the window — it should exit immediately, not hang
   (confirms the hotkey listener thread shuts down).

## Project layout

```
app/
  requirements.txt       # runtime deps: pywin32, psutil
  requirements-dev.txt    # + pytest
  pytest.ini               # points pytest at tests/
  main.py                   # entry point
  wlm/
    models.py                # Layout, WindowSlot dataclasses
    storage.py                 # JSON persistence
    window_enum.py               # enumerate visible windows (Win32)
    restore.py                     # move windows back into place (Win32)
    hotkeys.py                       # real global hotkey registration
    app.py                             # Tkinter UI, wires it all together
  tests/
    conftest.py                        # sys.path fix-up + LOCALAPPDATA isolation
    test_storage.py                      # LayoutStorageService round-trip tests
    test_hotkeys.py                        # parse_hotkey tests
```

See `CODE_WALKTHROUGH.md` for a line-by-line explanation of every source file.
