# Window Layout Manager

## Goal
Window Layout Manager is a Windows desktop utility for saving and restoring window layouts with global hotkeys. The initial v1 release focuses on local JSON-backed persistence and a WPF tray interface.

## Roadmap
1. v1 Local MVP
   - Save named layouts to JSON
   - Enumerate visible windows and store positions on disk
   - Restore saved window placements by matching title/process metadata
   - Register global hotkeys for save/restore actions
2. v2 SQLite-backed persistence
   - Replace JSON files with a local SQLite database
   - Add schema migration support and storing layout snapshots with metadata
3. v3 Go API layer
   - Expose a REST API for layout CRUD and synchronization
   - Use Go, net/http, and SQLite/Postgres persistence
4. v4 Cloud sync and collaboration
   - Sync layouts across devices using a hosted backend
   - Add authentication, cloud backup, and conflict resolution

## Current known limitations
- Window matching is heuristic and may not reliably identify every application instance.
- Only local persistence is implemented in v1.
- Restore behavior depends on the target windows being open and visible.
- Global hotkey registration can be impacted by other applications occupying the same hotkeys.
