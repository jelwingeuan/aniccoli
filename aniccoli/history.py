"""Organization-history and undo tools for Aniccoli."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from aniccoli.organizer import HISTORY_DIRECTORY


class NoUndoHistoryError(RuntimeError):
    """Raised when no organization operation is available to undo."""


@dataclass(frozen=True)
class UndoMove:
    """Represent one planned reverse movement."""

    current_path: Path
    original_path: Path
    category: str

    @property
    def current_file_name(self) -> str:
        """Return the file's current name."""
        return self.current_path.name

    @property
    def original_file_name(self) -> str:
        """Return the file's original name."""
        return self.original_path.name


@dataclass(frozen=True)
class UndoFailure:
    """Store information about a file that could not be restored."""

    undo_move: UndoMove
    error_message: str


@dataclass(frozen=True)
class UndoResult:
    """Store the result of an undo operation."""

    organization_log_path: Path
    restored_files: tuple[UndoMove, ...]
    already_restored_files: tuple[UndoMove, ...]
    failed_files: tuple[UndoFailure, ...]
    undo_log_path: Path | None = None
    log_error: str | None = None

    @property
    def restored_count(self) -> int:
        """Return the number of files restored during this operation."""
        return len(self.restored_files)

    @property
    def already_restored_count(self) -> int:
        """Return the number of files already in their original locations."""
        return len(self.already_restored_files)

    @property
    def failed_count(self) -> int:
        """Return the number of files that could not be restored."""
        return len(self.failed_files)

    @property
    def was_successful(self) -> bool:
        """Return True when no undo movements failed."""
        return self.failed_count == 0

    @property
    def log_was_saved(self) -> bool:
        """Return True when the undo log was saved successfully."""
        return (
            self.undo_log_path is not None
            and self.log_error is None
        )


def _is_inside_folder(
    path: Path,
    root_folder: Path,
) -> bool:
    """Return True when a path is inside the selected project folder."""
    try:
        path.relative_to(root_folder)
    except ValueError:
        return False

    return True


def _validate_project_folder(
    project_folder: str | Path,
) -> Path:
    """Validate and return the resolved project folder."""
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

    return root_folder


def _load_json_file(
    file_path: Path,
) -> dict[str, object]:
    """Load a JSON file and verify that it contains an object."""
    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as json_file:
        data = json.load(json_file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid Aniccoli history file: {file_path}"
        )

    return data


def _save_json_file(
    file_path: Path,
    data: dict[str, object],
) -> None:
    """Save a dictionary as a formatted JSON file."""
    with file_path.open(
        mode="w",
        encoding="utf-8",
    ) as json_file:
        json.dump(
            data,
            json_file,
            indent=2,
            ensure_ascii=False,
        )

        json_file.write("\n")


def _is_undoable_log(
    log_data: dict[str, object],
) -> bool:
    """Return True when an organization log can still be undone."""
    if log_data.get("application") != "Aniccoli":
        return False

    if log_data.get("undo_status") == "complete":
        return False

    movements = log_data.get("movements")

    if not isinstance(movements, list):
        return False

    return any(
        isinstance(movement, dict)
        and movement.get("status") == "moved"
        for movement in movements
    )


def find_latest_undoable_log(
    project_folder: str | Path,
) -> Path | None:
    """Find the newest organization log that has not been fully undone."""
    root_folder = _validate_project_folder(
        project_folder
    )

    history_folder = (
        root_folder / HISTORY_DIRECTORY
    )

    if not history_folder.exists():
        return None

    organization_logs = sorted(
        history_folder.glob(
            "organization_*.json"
        ),
        reverse=True,
    )

    for log_path in organization_logs:
        try:
            log_data = _load_json_file(
                log_path
            )
        except (
            json.JSONDecodeError,
            OSError,
            ValueError,
        ):
            continue

        if _is_undoable_log(log_data):
            return log_path

    return None


def _resolve_logged_path(
    root_folder: Path,
    logged_path: object,
) -> Path:
    """Convert a logged relative path into a safe absolute path."""
    if not isinstance(logged_path, str):
        raise ValueError(
            "The history log contains an invalid file path."
        )

    resolved_path = (
        root_folder / logged_path
    ).resolve()

    if not _is_inside_folder(
        resolved_path,
        root_folder,
    ):
        raise ValueError(
            "The history log contains a path outside "
            "the selected project folder."
        )

    return resolved_path


def build_undo_plan(
    project_folder: str | Path,
    organization_log_path: str | Path,
) -> list[UndoMove]:
    """Build a reverse-movement plan from an organization log."""
    root_folder = _validate_project_folder(
        project_folder
    )

    log_path = Path(
        organization_log_path
    ).expanduser().resolve()

    if not log_path.exists():
        raise FileNotFoundError(
            f"The organization log does not exist: {log_path}"
        )

    if not log_path.is_file():
        raise ValueError(
            f"The organization log is not a file: {log_path}"
        )

    if not _is_inside_folder(
        log_path,
        root_folder,
    ):
        raise ValueError(
            "The organization log is outside "
            "the selected project folder."
        )

    log_data = _load_json_file(
        log_path
    )

    logged_project = log_data.get(
        "project_folder"
    )

    if not isinstance(
        logged_project,
        str,
    ):
        raise ValueError(
            "The organization log has no valid project folder."
        )

    if Path(
        logged_project
    ).expanduser().resolve() != root_folder:
        raise ValueError(
            "The organization log belongs to another project."
        )

    movements = log_data.get(
        "movements"
    )

    if not isinstance(movements, list):
        raise ValueError(
            "The organization log has no valid movement records."
        )

    undo_plan: list[UndoMove] = []

    for movement in reversed(
        movements
    ):
        if not isinstance(
            movement,
            dict,
        ):
            continue

        if movement.get("status") != "moved":
            continue

        current_path = _resolve_logged_path(
            root_folder=root_folder,
            logged_path=movement.get(
                "destination"
            ),
        )

        original_path = _resolve_logged_path(
            root_folder=root_folder,
            logged_path=movement.get(
                "source"
            ),
        )

        category = movement.get(
            "category",
            "Unknown",
        )

        undo_plan.append(
            UndoMove(
                current_path=current_path,
                original_path=original_path,
                category=str(category),
            )
        )

    return undo_plan


def _create_undo_log_path(
    root_folder: Path,
) -> Path:
    """Create a unique path for an undo activity log."""
    history_folder = (
        root_folder / HISTORY_DIRECTORY
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
        / f"undo_{timestamp}.json"
    )


def _relative_path_text(
    path: Path,
    root_folder: Path,
) -> str:
    """Return a path relative to the project folder."""
    return str(
        path.resolve().relative_to(
            root_folder
        )
    )


def _build_undo_log_data(
    root_folder: Path,
    organization_log_path: Path,
    undo_plan: tuple[UndoMove, ...],
    restored_files: tuple[UndoMove, ...],
    already_restored_files: tuple[UndoMove, ...],
    failed_files: tuple[UndoFailure, ...],
) -> dict[str, object]:
    """Build JSON-compatible information for an undo operation."""
    restored_set = set(
        restored_files
    )

    already_restored_set = set(
        already_restored_files
    )

    failure_messages = {
        failure.undo_move: failure.error_message
        for failure in failed_files
    }

    movement_records: list[
        dict[str, object]
    ] = []

    for undo_move in undo_plan:
        if undo_move in restored_set:
            status = "restored"
            error_message = None
        elif undo_move in already_restored_set:
            status = "already_restored"
            error_message = None
        else:
            status = "failed"
            error_message = failure_messages.get(
                undo_move
            )

        movement_records.append(
            {
                "current_path": _relative_path_text(
                    undo_move.current_path,
                    root_folder,
                ),
                "original_path": _relative_path_text(
                    undo_move.original_path,
                    root_folder,
                ),
                "category": undo_move.category,
                "status": status,
                "error": error_message,
            }
        )

    return {
        "schema_version": 1,
        "application": "Aniccoli",
        "operation": "undo",
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "project_folder": str(
            root_folder
        ),
        "organization_log": (
            _relative_path_text(
                organization_log_path,
                root_folder,
            )
        ),
        "summary": {
            "planned": len(undo_plan),
            "restored": len(
                restored_files
            ),
            "already_restored": len(
                already_restored_files
            ),
            "failed": len(
                failed_files
            ),
        },
        "movements": movement_records,
    }


def _update_organization_log(
    organization_log_path: Path,
    undo_log_path: Path | None,
    failed_count: int,
) -> None:
    """Record the latest undo status inside the organization log."""
    organization_data = _load_json_file(
        organization_log_path
    )

    organization_data[
        "undo_status"
    ] = (
        "complete"
        if failed_count == 0
        else "partial"
    )

    organization_data[
        "undo_updated_at"
    ] = (
        datetime.now()
        .astimezone()
        .isoformat()
    )

    if undo_log_path is not None:
        organization_data[
            "undo_log"
        ] = undo_log_path.name

    _save_json_file(
        organization_log_path,
        organization_data,
    )


def execute_undo_plan(
    project_folder: str | Path,
    organization_log_path: str | Path,
    undo_moves: Iterable[UndoMove],
) -> UndoResult:
    """Restore files using a previously reviewed undo plan."""
    root_folder = _validate_project_folder(
        project_folder
    )

    log_path = Path(
        organization_log_path
    ).expanduser().resolve()

    plan = tuple(
        undo_moves
    )

    restored_files: list[
        UndoMove
    ] = []

    already_restored_files: list[
        UndoMove
    ] = []

    failed_files: list[
        UndoFailure
    ] = []

    for undo_move in plan:
        current_path = (
            undo_move.current_path
            .expanduser()
            .resolve()
        )

        original_path = (
            undo_move.original_path
            .expanduser()
            .resolve()
        )

        try:
            if not _is_inside_folder(
                current_path,
                root_folder,
            ):
                raise ValueError(
                    "The current file is outside "
                    "the selected project folder."
                )

            if not _is_inside_folder(
                original_path,
                root_folder,
            ):
                raise ValueError(
                    "The original location is outside "
                    "the selected project folder."
                )

            current_exists = (
                current_path.exists()
            )

            original_exists = (
                original_path.exists()
            )

            if (
                not current_exists
                and original_exists
            ):
                already_restored_files.append(
                    undo_move
                )
                continue

            if (
                current_exists
                and original_exists
            ):
                raise FileExistsError(
                    "The original location already contains a file: "
                    f"{original_path}"
                )

            if (
                not current_exists
                and not original_exists
            ):
                raise FileNotFoundError(
                    "Neither the organized file nor its original "
                    f"file exists: {current_path}"
                )

            if not current_path.is_file():
                raise ValueError(
                    f"The organized path is not a file: {current_path}"
                )

            original_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(current_path),
                str(original_path),
            )
        except (
            FileNotFoundError,
            FileExistsError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            failed_files.append(
                UndoFailure(
                    undo_move=undo_move,
                    error_message=str(
                        error
                    ),
                )
            )
        else:
            restored_files.append(
                undo_move
            )

    restored_tuple = tuple(
        restored_files
    )

    already_restored_tuple = tuple(
        already_restored_files
    )

    failed_tuple = tuple(
        failed_files
    )

    undo_log_path: Path | None = None
    log_errors: list[str] = []

    try:
        undo_log_path = (
            _create_undo_log_path(
                root_folder
            )
        )

        undo_log_data = (
            _build_undo_log_data(
                root_folder=root_folder,
                organization_log_path=log_path,
                undo_plan=plan,
                restored_files=restored_tuple,
                already_restored_files=(
                    already_restored_tuple
                ),
                failed_files=failed_tuple,
            )
        )

        _save_json_file(
            undo_log_path,
            undo_log_data,
        )
    except (
        PermissionError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        undo_log_path = None
        log_errors.append(
            str(error)
        )

    try:
        _update_organization_log(
            organization_log_path=log_path,
            undo_log_path=undo_log_path,
            failed_count=len(
                failed_tuple
            ),
        )
    except (
        json.JSONDecodeError,
        PermissionError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        log_errors.append(
            str(error)
        )

    log_error = (
        " | ".join(log_errors)
        if log_errors
        else None
    )

    return UndoResult(
        organization_log_path=log_path,
        restored_files=restored_tuple,
        already_restored_files=(
            already_restored_tuple
        ),
        failed_files=failed_tuple,
        undo_log_path=undo_log_path,
        log_error=log_error,
    )


def undo_latest_organization(
    project_folder: str | Path,
) -> UndoResult:
    """Find and undo the latest available organization operation."""
    root_folder = _validate_project_folder(
        project_folder
    )

    organization_log_path = (
        find_latest_undoable_log(
            root_folder
        )
    )

    if organization_log_path is None:
        raise NoUndoHistoryError(
            "No organization operation is available to undo."
        )

    undo_plan = build_undo_plan(
        project_folder=root_folder,
        organization_log_path=organization_log_path,
    )

    if not undo_plan:
        raise NoUndoHistoryError(
            "The latest organization log contains "
            "no moved files to restore."
        )

    return execute_undo_plan(
        project_folder=root_folder,
        organization_log_path=organization_log_path,
        undo_moves=undo_plan,
    )