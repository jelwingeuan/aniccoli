"""Duplicate-cleanup planning for Aniccoli; moves run through aniccoli.moves."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from aniccoli.moves import QUARANTINE_FOLDER, Move
from aniccoli.scanner import AssetFile


def _create_operation_id() -> str:
    """Create a unique, sortable cleanup-operation identifier."""
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return (
        f"{timestamp}_"
        f"{uuid4().hex[:8]}"
    )


def _normalize_relative_path(
    relative_path: Path,
) -> Path:
    """Validate and normalize a project-relative asset path."""
    path = Path(
        relative_path
    )

    if path.is_absolute():
        raise ValueError(
            "Duplicate cleanup requires project-relative asset paths."
        )

    normalized_parts = tuple(
        part
        for part in path.parts
        if part not in (
            "",
            ".",
        )
    )

    if not normalized_parts:
        raise ValueError(
            "A duplicate-cleanup path cannot be empty."
        )

    if ".." in normalized_parts:
        raise ValueError(
            "A duplicate-cleanup path cannot leave the project folder."
        )

    return Path(
        *normalized_parts
    )


def build_duplicate_cleanup_plan(
    project_folder: str | Path,
    assets_to_quarantine: Iterable[AssetFile],
) -> tuple[Move, ...]:
    """
    Plan quarantine moves for the selected copies without moving anything.

    The duplicate-results interface should pass only copies the user has
    explicitly selected for cleanup. This engine never permanently deletes
    files; it moves them into Aniccoli's private project quarantine.
    """
    root_folder = Path(
        project_folder
    ).expanduser().resolve()

    if not root_folder.exists():
        raise FileNotFoundError(
            f"The project folder does not exist: {root_folder}"
        )

    if not root_folder.is_dir():
        raise NotADirectoryError(
            f"The project path is not a folder: {root_folder}"
        )

    operation_id = _create_operation_id()

    quarantine_files_folder = (
        root_folder
        / QUARANTINE_FOLDER
        / operation_id
        / "files"
    ).resolve()

    moves: list[
        Move
    ] = []

    seen_source_paths: set[Path] = set()

    for asset in assets_to_quarantine:
        relative_path = _normalize_relative_path(
            asset.relative_path
        )

        original_path = (
            root_folder
            / relative_path
        ).resolve()

        if not original_path.is_relative_to(
            root_folder
        ):
            raise ValueError(
                "A selected duplicate is outside the project folder."
            )

        if not original_path.exists():
            raise FileNotFoundError(
                f"The selected duplicate no longer exists: {original_path}"
            )

        if not original_path.is_file():
            raise ValueError(
                f"The selected duplicate is not a file: {original_path}"
            )

        if original_path in seen_source_paths:
            continue

        quarantined_path = (
            quarantine_files_folder
            / relative_path
        ).resolve()

        if not quarantined_path.is_relative_to(
            quarantine_files_folder
        ):
            raise ValueError(
                "A quarantine destination is outside the operation folder."
            )

        seen_source_paths.add(
            original_path
        )

        moves.append(
            Move(
                source=original_path,
                destination=quarantined_path,
                details={
                    "file_name": asset.file_name,
                    "size_bytes": asset.size_bytes,
                },
            )
        )

    return tuple(
        sorted(
            moves,
            key=lambda move: str(
                move.source
            ).casefold(),
        )
    )
