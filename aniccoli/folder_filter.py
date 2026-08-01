"""Parent-folder filtering tools for Aniccoli."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

from aniccoli.scanner import AssetFile


class FolderMatchMode(str, Enum):
    """Control how assets are matched against a selected folder."""

    EXACT_FOLDER = "Selected folder only"
    INCLUDE_SUBFOLDERS = "Include subfolders"

    def __str__(self) -> str:
        """Return the readable option name."""
        return self.value


@dataclass(frozen=True)
class FolderFilterOptions:
    """Store the selected parent-folder filtering options."""

    folder: Path | None = None
    match_mode: FolderMatchMode = (
        FolderMatchMode.INCLUDE_SUBFOLDERS
    )

    def __post_init__(self) -> None:
        """Validate and normalize the selected relative folder."""
        if self.folder is None:
            return

        normalized_folder = normalize_relative_folder(
            self.folder
        )

        object.__setattr__(
            self,
            "folder",
            normalized_folder,
        )

    @property
    def has_active_filter(self) -> bool:
        """Return True when a parent folder was selected."""
        return self.folder is not None


def normalize_relative_folder(
    folder: str | Path,
) -> Path:
    """Return a safe project-relative folder path."""
    normalized_folder = Path(
        folder
    )

    if normalized_folder.is_absolute():
        raise ValueError(
            "The folder filter must be relative to the project."
        )

    normalized_parts = tuple(
        part
        for part in normalized_folder.parts
        if part not in (
            "",
            ".",
        )
    )

    if ".." in normalized_parts:
        raise ValueError(
            "The folder filter cannot leave the project folder."
        )

    if not normalized_parts:
        return Path(".")

    return Path(
        *normalized_parts
    )


def _is_inside_folder(
    asset_parent: Path,
    selected_folder: Path,
) -> bool:
    """Return True when an asset folder is inside another folder."""
    if selected_folder == Path("."):
        return True

    try:
        asset_parent.relative_to(
            selected_folder
        )
    except ValueError:
        return False

    return True


def asset_matches_folder(
    asset: AssetFile,
    options: FolderFilterOptions,
) -> bool:
    """Return True when an asset matches the folder options."""
    if not options.has_active_filter:
        return True

    selected_folder = options.folder

    if selected_folder is None:
        return True

    asset_parent = normalize_relative_folder(
        asset.relative_path.parent
    )

    if (
        options.match_mode
        is FolderMatchMode.EXACT_FOLDER
    ):
        return asset_parent == selected_folder

    if (
        options.match_mode
        is FolderMatchMode.INCLUDE_SUBFOLDERS
    ):
        return _is_inside_folder(
            asset_parent=asset_parent,
            selected_folder=selected_folder,
        )

    raise ValueError(
        "Unsupported folder match mode: "
        f"{options.match_mode}"
    )


def filter_assets_by_folder(
    assets: Iterable[AssetFile],
    options: FolderFilterOptions | None = None,
) -> tuple[AssetFile, ...]:
    """
    Return assets matching the selected parent folder.

    The original asset collection is not changed.
    """
    active_options = (
        options
        if options is not None
        else FolderFilterOptions()
    )

    return tuple(
        asset
        for asset in assets
        if asset_matches_folder(
            asset=asset,
            options=active_options,
        )
    )


def collect_available_folders(
    assets: Iterable[AssetFile],
) -> tuple[Path, ...]:
    """Return every unique parent folder found in scanned assets."""
    available_folders = {
        normalize_relative_folder(
            asset.relative_path.parent
        )
        for asset in assets
    }

    return tuple(
        sorted(
            available_folders,
            key=lambda folder: (
                folder != Path("."),
                str(folder).casefold(),
            ),
        )
    )


def folder_display_name(
    folder: Path,
) -> str:
    """Return a readable name for a project-relative folder."""
    normalized_folder = normalize_relative_folder(
        folder
    )

    if normalized_folder == Path("."):
        return "Project root"

    return str(
        normalized_folder
    )