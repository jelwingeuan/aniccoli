"""Folder-scanning tools for the Aniccoli asset organizer."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from aniccoli.categories import (
    AssetCategory,
    classify_file,
    destination_folder,
)


IGNORED_DIRECTORY_NAMES = {
    "__pycache__",
    "node_modules",
}


@dataclass(frozen=True)
class AssetFile:
    """Store information about one file discovered during a scan."""

    source_path: Path
    relative_path: Path
    file_name: str
    extension: str
    category: AssetCategory
    destination: Path
    size_bytes: int
    created_at: datetime
    modified_at: datetime

    @property
    def size_text(self) -> str:
        """Return the file size in a readable format."""
        return format_file_size(self.size_bytes)


def format_file_size(size_bytes: int) -> str:
    """Convert a file size in bytes into a readable value."""
    if size_bytes < 0:
        raise ValueError("File size cannot be negative.")

    units = ("B", "KB", "MB", "GB", "TB")
    size = float(size_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"

            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size_bytes} B"


def _is_hidden(
    path: Path,
    root_folder: Path,
) -> bool:
    """Return True when a file or folder is hidden."""
    try:
        relative_path = path.relative_to(root_folder)
    except ValueError:
        relative_path = path

    return any(
        part.startswith(".")
        for part in relative_path.parts
    )


def _created_timestamp(file_path: Path) -> float:
    """Return the best available creation timestamp."""
    file_stat = file_path.stat()

    return getattr(
        file_stat,
        "st_birthtime",
        file_stat.st_ctime,
    )


def _create_asset_record(
    file_path: Path,
    root_folder: Path,
) -> AssetFile:
    """Create an AssetFile record for a discovered file."""
    file_stat = file_path.stat()
    category = classify_file(file_path)

    return AssetFile(
        source_path=file_path,
        relative_path=file_path.relative_to(root_folder),
        file_name=file_path.name,
        extension=file_path.suffix.lower(),
        category=category,
        destination=destination_folder(category),
        size_bytes=file_stat.st_size,
        created_at=datetime.fromtimestamp(
            _created_timestamp(file_path)
        ),
        modified_at=datetime.fromtimestamp(
            file_stat.st_mtime
        ),
    )


def _iter_recursive_files(
    root_folder: Path,
    include_hidden: bool,
) -> Iterable[Path]:
    """Yield files from the folder and all its subfolders."""
    for current_path in root_folder.rglob("*"):
        if not include_hidden and _is_hidden(
            current_path,
            root_folder,
        ):
            continue

        if current_path.is_dir():
            continue

        if any(
            parent.name in IGNORED_DIRECTORY_NAMES
            for parent in current_path.parents
        ):
            continue

        if current_path.is_file():
            yield current_path


def _iter_top_level_files(
    root_folder: Path,
    include_hidden: bool,
) -> Iterable[Path]:
    """Yield files located directly inside the selected folder."""
    for current_path in root_folder.iterdir():
        if not include_hidden and _is_hidden(
            current_path,
            root_folder,
        ):
            continue

        if current_path.is_file():
            yield current_path


def scan_folder(
    folder_path: str | Path,
    *,
    recursive: bool = True,
    include_hidden: bool = False,
) -> list[AssetFile]:
    """Scan a folder and return information about discovered files."""
    root_folder = Path(
        folder_path
    ).expanduser().resolve()

    if not root_folder.exists():
        raise FileNotFoundError(
            f"The selected folder does not exist: {root_folder}"
        )

    if not root_folder.is_dir():
        raise NotADirectoryError(
            f"The selected path is not a folder: {root_folder}"
        )

    try:
        if recursive:
            discovered_files = _iter_recursive_files(
                root_folder,
                include_hidden,
            )
        else:
            discovered_files = _iter_top_level_files(
                root_folder,
                include_hidden,
            )

        assets = [
            _create_asset_record(
                file_path=file_path,
                root_folder=root_folder,
            )
            for file_path in discovered_files
        ]

    except PermissionError as error:
        raise PermissionError(
            f"Aniccoli cannot read this folder: {root_folder}"
        ) from error

    return sorted(
        assets,
        key=lambda asset: str(
            asset.relative_path
        ).lower(),
    )


def summarize_assets(
    assets: Iterable[AssetFile],
) -> dict[AssetCategory, int]:
    """Count how many files belong to each category."""
    category_counts = Counter(
        asset.category
        for asset in assets
    )

    return dict(
        sorted(
            category_counts.items(),
            key=lambda item: item[0].value.lower(),
        )
    )


def calculate_total_size(
    assets: Iterable[AssetFile],
) -> int:
    """Return the combined size of all scanned files."""
    return sum(
        asset.size_bytes
        for asset in assets
    )