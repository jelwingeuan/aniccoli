# Aniccoli

**Aniccoli** is a desktop asset-organizing tool built for 3D artists, students, small creative teams, and developers who need a safer way to clean up large project folders.

It scans a project, categorizes assets, previews organization changes before moving files, detects exact duplicates, exports inventory reports, and keeps recovery records for important file operations.

> Current release: **v1.0.0**

---

## Why Aniccoli?

3D projects can quickly become difficult to manage:

- Models are mixed with textures and references
- Duplicate files occupy unnecessary storage
- Old or empty files remain unnoticed
- Assets are scattered across inconsistent folders
- Manual cleanup risks moving or overwriting the wrong files

Aniccoli brings those tasks into one clear desktop workspace while keeping file safety at the center of the workflow.

---

## Features

### Project scanning

- Choose any local project folder
- Recursively scan nested folders
- Display detected assets in a searchable table
- Show filenames, categories, sizes, source folders, and planned destinations
- Reveal any asset directly in Finder, File Explorer, or the Linux file manager

### Asset organization

- Automatically classify common 3D-production assets
- Preview the complete organization plan before moving anything
- Select or exclude individual assets
- Organize selected assets into structured folders
- Group organized files by year, month, or full date
- Protect existing files from accidental overwriting
- Undo the latest organization operation

### Search, filters, and sorting

- Search by filename or path
- Filter by category
- Filter by extension
- Filter by source folder
- Filter by file size
- Sort by filename, category, extension, size, creation date, or modification date
- Select all visible results
- Invert visible selections
- Clear the current selection

### Duplicate management

- Detect files with exactly matching content
- Review duplicate groups before taking action
- Reveal duplicate copies in the system file manager
- Select extra copies manually
- Keep at least one copy in every duplicate group
- Move selected duplicates into private quarantine
- Restore the latest duplicate cleanup
- Avoid permanent deletion during cleanup

### Project statistics

- Total asset count
- Combined project size
- Average asset size
- Category totals
- Extension totals
- Source-folder totals
- Largest assets
- Most recently modified assets

### Asset Health

Aniccoli can audit a project for:

- Empty files
- Very large files
- Duplicate filenames
- Files without extensions
- Assets that have not been modified for a long time

The audit is read-only and does not change project files.

### Reports and preferences

- Export selected assets as JSON
- Export selected assets as CSV
- Remember the last selected project folder
- Remember filter, sorting, and organization preferences
- Use built-in keyboard shortcuts
- Read workflow and safety guidance from the Help window
- Use natural trackpad and mouse-wheel scrolling

---

## Safety Design

Aniccoli follows a preview-first and recovery-friendly workflow.

- Organization begins with a reviewable preview
- Existing files are never silently overwritten
- Filename conflicts receive safe alternative names
- Organization operations create undo history
- Duplicate cleanup moves files into quarantine
- Duplicate restoration refuses to overwrite occupied locations
- Reports, filters, statistics, and audits are read-only

Aniccoli stores recovery information inside the selected project:

```text
.aniccoli/
```

Duplicate quarantine is stored inside:

```text
.aniccoli/duplicate_trash/
```

Do not remove the `.aniccoli` folder while you may still need undo or restoration features.

---

## Requirements

- Python 3.10 or newer
- CustomTkinter
- macOS, Windows, or Linux

Aniccoli v1.0.0 was primarily developed and tested on macOS.

---

## Installation

### 1. Open the project folder

Open Terminal inside the Aniccoli repository.

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the environment

macOS or Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install the dependency

```bash
python -m pip install customtkinter
```

### 5. Start Aniccoli

```bash
python main.py
```

---

## Basic Workflow

1. Launch Aniccoli.
2. Click **Choose Project**.
3. Select a 3D project folder.
4. Click **Scan Project**.
5. Review the detected assets.
6. Search, filter, sort, or exclude files.
7. Click **Preview Organization**.
8. Review every planned destination.
9. Confirm the operation only when the preview looks correct.
10. Use **Undo Organization** when restoration is needed.

---

## Duplicate Cleanup Workflow

1. Scan a project folder.
2. Click **Analyze Duplicates**.
3. Review each duplicate group.
4. Use **Reveal** when you need to inspect a file.
5. Select only the extra copies.
6. Click **Quarantine Selected**.
7. Use **Restore Last Cleanup** when restoration is needed.

Aniccoli prevents a cleanup operation from removing every copy in a duplicate group.

---

## Keyboard Shortcuts

### macOS

```text
Command + O          Choose project folder
Command + R          Scan selected folder
Command + F          Focus asset search
Command + Shift + A  Select visible assets
Command + Shift + C  Clear asset selection
F1                   Open Help
```

### Windows and Linux

Use `Ctrl` instead of `Command`.

---

## Project Structure

```text
Aniccoli/
├── main.py
├── README.md
└── aniccoli/
    ├── __init__.py
    ├── about_window.py
    ├── app.py
    ├── audit.py
    ├── audit_window.py
    ├── categories.py
    ├── duplicate_cleanup.py
    ├── duplicate_window.py
    ├── duplicates.py
    ├── file_actions.py
    ├── filters.py
    ├── history.py
    ├── organization_options.py
    ├── organizer.py
    ├── preferences.py
    ├── reports.py
    ├── scanner.py
    ├── selection.py
    ├── sorting.py
    ├── statistics.py
    └── statistics_window.py
```

---

## Development Checks

Compile all Python files:

```bash
python -m compileall main.py aniccoli
```

Test the application import:

```bash
python -c "from aniccoli.app import create_app; print('Aniccoli v1.0.0 import works!')"
```

Run the application:

```bash
python main.py
```

---

## Troubleshooting

### `ModuleNotFoundError`

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install CustomTkinter:

```bash
python -m pip install customtkinter
```

Confirm every Aniccoli module is inside the inner `aniccoli` folder.

### The app opens but the asset list is empty

- Confirm a project folder was selected
- Click **Scan Project**
- Clear active search and filter controls
- Confirm the selected folder contains files

### A file cannot be revealed

The asset may have been moved, renamed, organized, quarantined, or deleted outside Aniccoli. Scan the project again to refresh the interface.

### Undo or restoration is unavailable

Confirm the selected project still contains its hidden `.aniccoli` folder.

### Trackpad or mouse-wheel scrolling does not respond

- Fully close and reopen Aniccoli
- Place the pointer over the scrollable panel
- Confirm the latest `aniccoli/app.py` is installed
- Confirm Python is using the intended virtual environment

---

## v1.0.0 Release

Aniccoli v1.0.0 is the first stable release.

It includes:

- Complete project scanning and categorization
- Search, filtering, sorting, and asset selection
- Preview-first organization and undo history
- Exact duplicate detection
- Safe duplicate quarantine and restoration
- Project statistics
- Asset Health auditing
- JSON and CSV inventory reports
- Persistent preferences
- Finder and file-manager integration
- Keyboard shortcuts
- Redesigned desktop UI
- Trackpad and mouse-wheel scrolling support

---

## Known Limitations

- Aniccoli currently runs from Python rather than a signed installer
- Asset categorization is based on filenames and extensions
- Cloud storage conflicts are managed by the storage provider, not Aniccoli
- Undo and restoration require the hidden `.aniccoli` project records
- Very large projects may take longer to scan and hash for duplicate detection

---

## License

This repository does not currently include an open-source license. All rights are reserved unless a license is added later.
