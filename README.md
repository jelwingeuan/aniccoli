# 🥦 Animated Broccoli

**Keep your 3D projects fresh, clean, and organized.**

Animated Broccoli is a beginner-friendly Python desktop application designed to help 3D artists, animators, students, and game developers organize messy production folders.

The application scans a selected folder, detects different asset types, and sorts Blender, Maya, Unity, texture, reference, render, audio, document, and archive files into a clean project structure.

## About the Project

3D projects can quickly become difficult to manage when models, textures, references, renders, and project files are stored in the same folder.

Animated Broccoli helps solve this problem by automatically identifying files and organizing them into suitable folders based on:

* File extension
* Software type
* Asset category
* Texture type
* Creation or modification date

The goal is to reduce the time spent searching for files and help users maintain a cleaner and more consistent production workflow.

## Main Features

* Select and scan a project folder
* Detect supported 3D production files
* Organize Blender and Maya project files
* Organize Unity scenes, prefabs, materials, animations, and scripts
* Sort 3D model formats such as FBX, OBJ, GLTF, GLB, and STL
* Detect texture types using file names
* Organize references, renders, audio, documents, videos, and archives
* Preview planned file movements before applying changes
* Search and filter assets
* Detect duplicate files using file hashes
* Save organization activity logs
* Undo recent file movements
* Display project statistics
* Group files by creation or modification date

## Supported File Types

### Blender and Maya

* `.blend`
* `.ma`
* `.mb`

### 3D Models

* `.fbx`
* `.obj`
* `.gltf`
* `.glb`
* `.stl`

### Unity Assets

* `.unity`
* `.prefab`
* `.mat`
* `.asset`
* `.anim`
* `.controller`
* `.cs`

### Textures and Images

* `.png`
* `.jpg`
* `.jpeg`
* `.tga`
* `.exr`
* `.hdr`
* `.psd`
* `.tif`
* `.tiff`

### Documents and References

* `.pdf`
* `.doc`
* `.docx`
* `.txt`
* `.md`

### Audio

* `.mp3`
* `.wav`
* `.ogg`
* `.flac`

### Video

* `.mp4`
* `.mov`
* `.avi`
* `.mkv`

### Archives

* `.zip`
* `.rar`
* `.7z`

## Texture Detection

Animated Broccoli can identify common texture maps by checking file names.

For example:

```text
robot_basecolor.png
robot_normal.png
robot_roughness.png
robot_metallic.png
robot_height.png
robot_ao.png
```

These files can automatically be organized into folders such as:

```text
Textures/
├── Base_Color/
├── Normal/
├── Roughness/
├── Metallic/
├── Height/
├── Ambient_Occlusion/
└── Other/
```

## Example Folder Structure

```text
Project_Name/
├── 3D_Models/
│   ├── Blender/
│   ├── Maya/
│   ├── FBX/
│   ├── OBJ/
│   ├── GLTF/
│   └── STL/
├── Unity/
│   ├── Scenes/
│   ├── Prefabs/
│   ├── Materials/
│   ├── Animations/
│   ├── Scripts/
│   └── Other/
├── Textures/
│   ├── Base_Color/
│   ├── Normal/
│   ├── Roughness/
│   ├── Metallic/
│   ├── Height/
│   ├── Ambient_Occlusion/
│   └── Other/
├── References/
├── Renders/
├── Audio/
├── Videos/
├── Documents/
├── Archives/
└── Unknown/
```

## How It Works

1. Open Animated Broccoli.
2. Select a folder containing your project assets.
3. Allow the application to scan the folder.
4. Review the detected files and categories.
5. Preview the proposed file movements.
6. Confirm the organization process.
7. Browse the newly organized project folders.
8. Use the undo feature when necessary.

## Safe Organization

Animated Broccoli is designed to avoid moving files without the user’s knowledge.

Before any changes are made, the application shows a preview containing:

* Original file location
* New file location
* Detected file category
* Possible naming conflicts

Example:

```text
File: character_final.blend

Current location:
Downloads/character_final.blend

New location:
My_Project/3D_Models/Blender/character_final.blend
```

The user must confirm the operation before files are moved.

## Duplicate Detection

The application can identify possible duplicate assets using:

* File names
* File sizes
* File hashes

Users can then decide whether to:

* Keep both files
* Rename one file
* Move duplicates into a separate folder
* Remove unnecessary duplicates

## Search and Filtering

Assets can be searched or filtered by:

* File name
* File extension
* Asset category
* Software type
* Creation date
* Modification date
* File size

Example filters include:

* Blender files only
* Maya files only
* Unity assets only
* Textures only
* Recently modified files
* Large files
* Duplicate files

## Project Dashboard

The dashboard may display:

* Total number of files
* Total project size
* Number of 3D models
* Number of textures
* Number of Blender files
* Number of Maya files
* Number of Unity assets
* Number of references
* Number of duplicates
* Recently modified files

## Technologies Used

* Python
* CustomTkinter
* pathlib
* shutil
* hashlib
* Pillow
* SQLite
* JSON
* datetime

## Planned Interface

The application is planned to include a clean sidebar with the following sections:

* Dashboard
* Scan Folder
* All Assets
* 3D Models
* Blender Files
* Maya Files
* Unity Files
* Textures
* References
* Duplicates
* Activity Log
* Settings

## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/animated-broccoli.git
```

Move into the project folder:

```bash
cd animated-broccoli
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment on Windows:

```bash
.venv\Scripts\activate
```

Activate the virtual environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

## Beginner Version

The first version of Animated Broccoli will focus on:

* Selecting a folder
* Scanning files
* Detecting file extensions
* Categorizing files
* Previewing file movements
* Moving files safely
* Saving an activity log
* Undoing the latest organization operation

## Future Improvements

Planned future features include:

* Drag-and-drop file importing
* Image and texture previews
* 3D model thumbnails
* Blender integration
* Maya integration
* Unity project detection
* Missing texture detection
* Automatic texture-set matching
* Asset tagging
* Custom folder rules
* Batch asset renaming
* Cloud backup
* Team project sharing
* Version tracking
* AI-assisted asset naming
* CSV asset-list exporting
* PDF project reports
* Dark and light interface modes

## Project Status

Animated Broccoli is currently under development.

The project is being built step by step with small and meaningful Git commits so that beginners can understand how each feature works.

## Contributing

Contributions, suggestions, and bug reports are welcome.

To contribute:

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Commit your changes.
5. Push the branch.
6. Open a pull request.

Example:

```bash
git checkout -b feature/new-feature
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

## License

This project is intended for educational and portfolio purposes.

A formal open-source license may be added later.

## Author

Created as a Python learning project for organizing 3D art, animation, and game-development assets.

---

🥦 **Animated Broccoli**

Helping artists keep their digital workspace fresh.
