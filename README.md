# Aniccoli

**Aniccoli** is a desktop asset-organizing tool for 3D artists, students, developers, and small creative teams.

It scans project folders, categorizes assets, previews organization changes before moving files, detects exact duplicates, audits project health, exports inventory reports, and keeps recovery records for important file operations.

> **Current development direction:** Aniccoli keeps its existing Python core while introducing an experimental **PySide6 + QML** interface for a more modern desktop experience.

---

## Highlights

- Recursive project-folder scanning
- Automatic asset categorization
- Search, filtering, and sorting
- Asset selection and exclusion
- Preview-first file organization
- Date-based organization options
- Safe filename conflict handling
- Undo support for organization operations
- Exact-content duplicate detection
- Safe duplicate quarantine and restoration
- Project statistics
- Asset Health auditing
- JSON and CSV inventory reports
- Finder / file-manager integration
- Persistent preferences
- Keyboard shortcuts
- Multilingual UI support in the existing interface
- Mouse-wheel and trackpad scrolling support
- Experimental Qt / QML frontend

---

## UI Options

Aniccoli currently has two interface entry points.

### 1. Existing CustomTkinter interface

This is the current feature-complete desktop interface.

Run it with:

```bash
python main.py
