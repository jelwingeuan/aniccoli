# Aniccoli

Aniccoli is a beginner-friendly desktop application for organizing 3D project assets.

It scans a project folder, identifies common asset types, previews a safe organization plan, detects duplicate files, exports reports, and keeps restoration history for file-moving operations.

## Version

Current development version:

```text
1.0.0
```

## Main Features

- Choose and scan a project folder
- Recursively discover project assets
- Categorize 3D models, textures, references, audio, video, and other files
- Search scanned assets
- Filter by category, extension, size, and source folder
- Sort by name, category, size, extension, creation date, or modification date
- Select or exclude individual assets
- Preview organization before moving files
- Organize assets into categorized folders
- Group organized assets by year, month, or full date
- Avoid overwriting filename conflicts
- Undo the latest organization operation
- Detect exact-content duplicate files
- Safely quarantine selected duplicate copies
- Restore the latest duplicate cleanup
- Reveal files in Finder, File Explorer, or the Linux file manager
- Review project statistics
- Run an asset health audit
- Export asset inventory reports as JSON or CSV
- Remember interface preferences
- Use keyboard shortcuts
- Read built-in workflow and safety guidance

## Safety

Aniccoli is designed around preview-first and restoration-friendly workflows.

- Organization starts with a preview.
- Existing files are not overwritten.
- Filename conflicts receive safe alternative names.
- Organization operations write undo history.
- Duplicate cleanup does not permanently delete files.
- Duplicate copies are moved into private quarantine.
- Restoration refuses to overwrite occupied locations.
- Reports, statistics, filtering, and audits are read-only.

Aniccoli stores operation records inside a hidden project folder:

```text
.aniccoli/
```

Duplicate-cleanup quarantine is stored inside:

```text
.aniccoli/duplicate_trash/
```

Keep the `.aniccoli` folder while you may still need undo or restoration features.

## Requirements

- Python 3.10 or newer
- CustomTkinter
- macOS, Windows, or Linux

The project has primarily been developed and tested on macOS.

## Project Structure

```text
Aniccoli/
├── main.py
├── README.md
├── aniccoli/
│   ├── __init__.py
│   ├── about_window.py
│   ├── app.py
│   ├── audit.py
│   ├── audit_window.py
│   ├── categories.py
│   ├── duplicate_cleanup.py
│   ├── duplicate_window.py
│   ├── duplicates.py
│   ├── file_actions.py
│   ├── filters.py
│   ├── history.py
│   ├── organization_options.py
│   ├── organizer.py
│   ├── preferences.py
│   ├── reports.py
│   ├── scanner.py
│   ├── selection.py
│   ├── sorting.py
│   ├── statistics.py
│   └── statistics_window.py
└── .venv/
```

The exact list may change as development continues.

## Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd Aniccoli
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install CustomTkinter:

```bash
python -m pip install customtkinter
```

## Run Aniccoli

With the virtual environment activated:

```bash
python main.py
```

## Basic Workflow

1. Open Aniccoli.
2. Click **Choose Folder**.
3. Select a 3D project folder.
4. Click **Scan Folder**.
5. Review the detected files.
6. Search, filter, sort, or exclude assets.
7. Click **Preview Organization**.
8. Review every planned destination.
9. Confirm organization only when the plan looks correct.
10. Use **Undo Last Organization** when restoration is needed.

## Duplicate Cleanup Workflow

1. Scan a project folder.
2. Click **Analyze Duplicates**.
3. Review each exact-content duplicate group.
4. Click **Reveal** to inspect files in the system file manager.
5. Select only the extra copies.
6. Click **Quarantine Selected**.
7. Use **Restore Last Cleanup** when restoration is needed.

Aniccoli prevents cleanup when every copy in a duplicate group is selected.

## Asset Health Audit

The **Asset Health** window checks for:

- Empty files
- Very large files
- Duplicate filenames
- Files without extensions
- Files that have not been modified for a long time

The audit does not modify project files.

## Project Statistics

The **Project Statistics** window shows:

- Total asset count
- Combined file size
- Average file size
- Category totals
- Extension totals
- Source-folder totals
- Largest assets
- Most recently modified assets

## Reports

Aniccoli can export selected assets as:

- JSON
- CSV

Reports contain inventory information and do not move or modify files.

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

## Development Checks

Compile the project:

```bash
python -m compileall main.py aniccoli
```

Test the main application import:

```bash
python -c "from aniccoli.app import create_app; print('Aniccoli import works!')"
```

Run the application:

```bash
python main.py
```

## Troubleshooting

### `ModuleNotFoundError`

Confirm the virtual environment is active:

```bash
source .venv/bin/activate
```

Then install the dependency:

```bash
python -m pip install customtkinter
```

Also confirm that each Python file is inside the inner `aniccoli` folder.

### The app opens but no files appear

- Confirm a project folder has been selected.
- Click **Scan Folder**.
- Clear active search and filter controls.
- Confirm the folder contains supported files.

### A file cannot be revealed

The file may have been moved, renamed, organized, quarantined, or deleted outside Aniccoli. Scan the project again to refresh the interface.

### Undo or restoration history is unavailable

Confirm the project still contains its hidden `.aniccoli` folder.

## Planned Release Work

Before the final packaged release:

- Complete final interface testing
- Add application screenshots
- Add automated smoke tests
- Package the macOS application
- Prepare the `v1.0.0` GitHub release

## License

A license has not yet been selected.
