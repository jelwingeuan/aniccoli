"""Organization-planning, file-moving, and logging tools for Aniccoli."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from aniccoli.organization_options import (
    OrganizationOptions,
    build_destination_folder,
)
from aniccoli.scanner import AssetFile


HISTORY_DIRECTORY = Path(".aniccoli") / "history"
LOG_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PlannedMove:
    """Represent one planned file movement."""

    asset: AssetFile
    destination_path: Path
    renamed_for_conflict: bool

    @property
    def source_path(self) -> Path:
        """Return the current source path."""
        return self.asset.source_path

    @property
    def planned_file_name(self) -> str:
        """Return the filename that will be used after organization."""
        return self.destination_path.name


@dataclass(frozen=True)
class MoveFailure:
    """Store information about a file that could not be moved."""

    planned_move: PlannedMove
    error_message: str


@dataclass(frozen=True)
class OrganizationResult:
    """Store the result of an organization operation."""

    moved_files: tuple[PlannedMove, ...]
    failed_files: tuple[MoveFailure, ...]
    log_path: Path | None = None
    log_error: str | None = None

    @property
    def moved_count(self) -> int:
        """Return the number of files moved successfully."""
        return len(self.moved_files)

    @property
    def failed_count(self) -> int:
        """Return the number of files that failed to move."""
        return len(self.failed_files)

    @property
    def was_successful(self) -> bool:
        """Return True when every planned movement succeeded."""
        return self.failed_count == 0

    @property
    def log_was_saved(self) -> bool:
        """Return True when the activity log was saved successfully."""
        return (
            self.log_path is not None
            and self.log_error is None
        )


def _is_inside_folder(
    path: Path,
    root_folder: Path,
) -> bool:
    """Return True when a path is located inside the project folder."""
    try:
        path.relative_to(root_folder)
    except ValueError:
        return False

    return True


def _next_available_path(
    desired_path: Path,
    reserved_paths: set[Path],
) -> tuple[Path, bool]:
    """
    Find an available destination without overwriting another file.

    For example, when hero.fbx already exists, the function tries:

        hero_2.fbx
        hero_3.fbx
        hero_4.fbx
    """
    normalized_desired_path = desired_path.resolve()

    if (
        not normalized_desired_path.exists()
        and normalized_desired_path not in reserved_paths
    ):
        return normalized_desired_path, False

    parent_folder = normalized_desired_path.parent
    file_stem = normalized_desired_path.stem
    file_suffix = normalized_desired_path.suffix

    counter = 2

    while True:
        candidate_path = (
            parent_folder
            / f"{file_stem}_{counter}{file_suffix}"
        ).resolve()

        if (
            not candidate_path.exists()
            and candidate_path not in reserved_paths
        ):
            return candidate_path, True

        counter += 1


def build_organization_plan(
    project_folder: str | Path,
    assets: Iterable[AssetFile],
    *,
    options: OrganizationOptions | None = None,
) -> list[PlannedMove]:
    """
    Create a safe organization plan without moving any files.

    Files already located in their correct destination are skipped.
    Filename conflicts are resolved by creating a new filename.

    When no organization options are provided, Aniccoli keeps its
    existing category-only folder structure.
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

    active_options = (
        options
        if options is not None
        else OrganizationOptions()
    )

    planned_moves: list[PlannedMove] = []
    reserved_paths: set[Path] = set()

    for asset in assets:
        source_path = asset.source_path.resolve()

        relative_destination = build_destination_folder(
            asset=asset,
            options=active_options,
        )

        destination_directory = (
            root_folder
            / relative_destination
        ).resolve()

        desired_path = (
            destination_directory
            / asset.file_name
        ).resolve()

        if not _is_inside_folder(
            destination_directory,
            root_folder,
        ):
            raise ValueError(
                "A planned destination is outside the project folder."
            )

        if source_path == desired_path:
            continue

        available_path, renamed_for_conflict = (
            _next_available_path(
                desired_path=desired_path,
                reserved_paths=reserved_paths,
            )
        )

        reserved_paths.add(
            available_path
        )

        planned_moves.append(
            PlannedMove(
                asset=asset,
                destination_path=available_path,
                renamed_for_conflict=renamed_for_conflict,
            )
        )

    return sorted(
        planned_moves,
        key=lambda planned_move: str(
            planned_move.asset.relative_path
        ).lower(),
    )


def count_conflict_renames(
    planned_moves: Iterable[PlannedMove],
) -> int:
    """Count how many planned files require a safe rename."""
    return sum(
        1
        for planned_move in planned_moves
        if planned_move.renamed_for_conflict
    )


def _validate_move(
    planned_move: PlannedMove,
    root_folder: Path,
) -> tuple[Path, Path]:
    """Validate one movement before changing the filesystem."""
    source_path = (
        planned_move.source_path
        .expanduser()
        .resolve()
    )

    destination_path = (
        planned_move.destination_path
        .expanduser()
        .resolve()
    )

    if not source_path.exists():
        raise FileNotFoundError(
            f"The source file no longer exists: {source_path}"
        )

    if not source_path.is_file():
        raise ValueError(
            f"The source path is not a file: {source_path}"
        )

    if not _is_inside_folder(
        source_path,
        root_folder,
    ):
        raise ValueError(
            f"The source is outside the project folder: {source_path}"
        )

    if not _is_inside_folder(
        destination_path,
        root_folder,
    ):
        raise ValueError(
            "The destination is outside the project folder: "
            f"{destination_path}"
        )

    if source_path == destination_path:
        raise ValueError(
            "The source and destination paths are identical."
        )

    if destination_path.exists():
        raise FileExistsError(
            "The destination already exists: "
            f"{destination_path}"
        )

    return source_path, destination_path


def _relative_path_text(
    path: Path,
    root_folder: Path,
) -> str:
    """Return a path relative to the project when possible."""
    try:
        return str(
            path.resolve().relative_to(
                root_folder
            )
        )
    except ValueError:
        return str(
            path.resolve()
        )


def _create_log_path(
    root_folder: Path,
) -> Path:
    """Create and return a unique activity-log path."""
    history_folder = (
        root_folder
        / HISTORY_DIRECTORY
    )

    history_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return (
        history_folder
        / f"organization_{timestamp}.json"
    )


def _build_log_data(
    root_folder: Path,
    planned_moves: tuple[PlannedMove, ...],
    moved_files: tuple[PlannedMove, ...],
    failed_files: tuple[MoveFailure, ...],
) -> dict[str, object]:
    """Build JSON-compatible activity-log information."""
    moved_set = set(
        moved_files
    )

    failure_messages = {
        failure.planned_move: failure.error_message
        for failure in failed_files
    }

    movement_records: list[
        dict[str, object]
    ] = []

    for planned_move in planned_moves:
        if planned_move in moved_set:
            status = "moved"
            error_message = None
        elif planned_move in failure_messages:
            status = "failed"
            error_message = failure_messages[
                planned_move
            ]
        else:
            status = "not_processed"
            error_message = None

        movement_records.append(
            {
                "source": _relative_path_text(
                    planned_move.source_path,
                    root_folder,
                ),
                "destination": _relative_path_text(
                    planned_move.destination_path,
                    root_folder,
                ),
                "category": str(
                    planned_move.asset.category
                ),
                "renamed_for_conflict": (
                    planned_move.renamed_for_conflict
                ),
                "status": status,
                "error": error_message,
            }
        )

    return {
        "schema_version": LOG_SCHEMA_VERSION,
        "application": "Aniccoli",
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "project_folder": str(
            root_folder
        ),
        "summary": {
            "planned": len(
                planned_moves
            ),
            "moved": len(
                moved_files
            ),
            "failed": len(
                failed_files
            ),
        },
        "movements": movement_records,
    }


def _save_organization_log(
    root_folder: Path,
    planned_moves: tuple[PlannedMove, ...],
    moved_files: tuple[PlannedMove, ...],
    failed_files: tuple[MoveFailure, ...],
) -> Path:
    """Save one organization operation as a JSON activity log."""
    log_path = _create_log_path(
        root_folder
    )

    log_data = _build_log_data(
        root_folder=root_folder,
        planned_moves=planned_moves,
        moved_files=moved_files,
        failed_files=failed_files,
    )

    with log_path.open(
        mode="w",
        encoding="utf-8",
    ) as log_file:
        json.dump(
            log_data,
            log_file,
            indent=2,
            ensure_ascii=False,
        )

        log_file.write(
            "\n"
        )

    return log_path


def execute_organization_plan(
    project_folder: str | Path,
    planned_moves: Iterable[PlannedMove],
) -> OrganizationResult:
    """
    Execute a previously reviewed organization plan.

    Destination folders are created automatically. Existing destination
    files are never overwritten. Every operation is recorded in a JSON
    activity log inside the selected project folder.
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

    plan = tuple(
        planned_moves
    )

    moved_files: list[
        PlannedMove
    ] = []

    failed_files: list[
        MoveFailure
    ] = []

    for planned_move in plan:
        try:
            source_path, destination_path = _validate_move(
                planned_move=planned_move,
                root_folder=root_folder,
            )

            destination_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(source_path),
                str(destination_path),
            )
        except (
            FileNotFoundError,
            FileExistsError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            failed_files.append(
                MoveFailure(
                    planned_move=planned_move,
                    error_message=str(
                        error
                    ),
                )
            )
        else:
            moved_files.append(
                planned_move
            )

    moved_files_tuple = tuple(
        moved_files
    )

    failed_files_tuple = tuple(
        failed_files
    )

    log_path: Path | None = None
    log_error: str | None = None

    try:
        log_path = _save_organization_log(
            root_folder=root_folder,
            planned_moves=plan,
            moved_files=moved_files_tuple,
            failed_files=failed_files_tuple,
        )
    except (
        PermissionError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        log_error = str(
            error
        )

    return OrganizationResult(
        moved_files=moved_files_tuple,
        failed_files=failed_files_tuple,
        log_path=log_path,
        log_error=log_error,
    )