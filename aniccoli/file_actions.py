"""Operating-system file actions for Aniccoli."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def reveal_in_file_manager(
    path: str | Path,
) -> Path:
    """
    Reveal a file or folder in the operating system's file manager.

    macOS:
        Reveals the selected item in Finder.

    Windows:
        Selects the item in File Explorer.

    Linux:
        Opens the containing folder with the default file manager.

    Returns:
        The resolved path that was revealed.
    """
    resolved_path = Path(
        path
    ).expanduser().resolve()

    if not resolved_path.exists():
        raise FileNotFoundError(
            f"The file or folder no longer exists: {resolved_path}"
        )

    if sys.platform == "darwin":
        command = [
            "open",
            "-R",
            str(resolved_path),
        ]
    elif sys.platform.startswith(
        "win"
    ):
        if resolved_path.is_dir():
            command = [
                "explorer",
                str(resolved_path),
            ]
        else:
            command = [
                "explorer",
                f"/select,{resolved_path}",
            ]
    elif sys.platform.startswith(
        "linux"
    ):
        target_folder = (
            resolved_path
            if resolved_path.is_dir()
            else resolved_path.parent
        )

        command = [
            "xdg-open",
            str(target_folder),
        ]
    else:
        raise OSError(
            "Opening the system file manager is not supported "
            f"on this platform: {sys.platform}"
        )

    try:
        subprocess.run(
            command,
            check=True,
        )
    except FileNotFoundError as error:
        raise OSError(
            "The operating system file manager command "
            "could not be found."
        ) from error
    except subprocess.CalledProcessError as error:
        raise OSError(
            "The operating system could not reveal the selected item."
        ) from error

    return resolved_path
