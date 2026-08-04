"""Safe duplicate-cleanup and restoration tools for Aniccoli."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from aniccoli.scanner import AssetFile


DUPLICATE_TRASH_DIRECTORY = (
    Path(".aniccoli")
    / "duplicate_trash"
)

MANIFEST_FILE_NAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DuplicateCleanupMove:
    """Represent one selected duplicate copy to quarantine."""

    asset: AssetFile
    original_path: Path
    quarantined_path: Path

    @property
    def relative_path(self) -> Path:
        """Return the original project-relative path."""
        return self.asset.relative_path


@dataclass(frozen=True)
class DuplicateCleanupPlan:
    """Store a reviewed duplicate-cleanup operation."""

    project_folder: Path
    operation_id: str
    moves: tuple[DuplicateCleanupMove, ...]

    @property
    def operation_folder(self) -> Path:
        """Return the private folder used for this cleanup."""
        return (
            self.project_folder
            / DUPLICATE_TRASH_DIRECTORY
            / self.operation_id
        )

    @property
    def manifest_path(self) -> Path:
        """Return the JSON manifest path for this cleanup."""
        return (
            self.operation_folder
            / MANIFEST_FILE_NAME
        )

    @property
    def selected_count(self) -> int:
        """Return the number of selected duplicate copies."""
        return len(
            self.moves
        )


@dataclass(frozen=True)
class DuplicateCleanupFailure:
    """Store information about an item that could not be processed."""

    source_path: Path
    destination_path: Path
    error_message: str


@dataclass(frozen=True)
class DuplicateCleanupResult:
    """Store the result of quarantining selected duplicate copies."""

    operation_id: str
    quarantined_moves: tuple[DuplicateCleanupMove, ...]
    failed_moves: tuple[DuplicateCleanupFailure, ...]
    manifest_path: Path | None
    manifest_error: str | None = None

    @property
    def quarantined_count(self) -> int:
        """Return the number of files moved to private quarantine."""
        return len(
            self.quarantined_moves
        )

    @property
    def failed_count(self) -> int:
        """Return the number of files that could not be moved."""
        return len(
            self.failed_moves
        )

    @property
    def was_successful(self) -> bool:
        """Return True when every selected item was quarantined."""
        return self.failed_count == 0

    @property
    def manifest_was_saved(self) -> bool:
        """Return True when the cleanup manifest was saved."""
        return (
            self.manifest_path is not None
            and self.manifest_error is None
        )


@dataclass(frozen=True)
class DuplicateRestoreMove:
    """Represent one quarantined duplicate copy to restore."""

    quarantined_path: Path
    original_path: Path


@dataclass(frozen=True)
class DuplicateRestoreResult:
    """Store the result of restoring a duplicate-cleanup operation."""

    manifest_path: Path
    restored_moves: tuple[DuplicateRestoreMove, ...]
    failed_moves: tuple[DuplicateCleanupFailure, ...]

    @property
    def restored_count(self) -> int:
        """Return the number of files restored successfully."""
        return len(
            self.restored_moves
        )

    @property
    def failed_count(self) -> int:
        """Return the number of files that could not be restored."""
        return len(
            self.failed_moves
        )

    @property
    def was_successful(self) -> bool:
        """Return True when every quarantined file was restored."""
        return self.failed_count == 0


class NoDuplicateCleanupHistoryError(RuntimeError):
    """Raised when there is no restorable duplicate-cleanup history."""


def _is_inside_folder(
    path: Path,
    folder: Path,
) -> bool:
    """Return True when a path is inside a folder."""
    try:
        path.relative_to(
            folder
        )
    except ValueError:
        return False

    return True


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
) -> DuplicateCleanupPlan:
    """
    Build a safe cleanup plan without moving or deleting files.

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
        / DUPLICATE_TRASH_DIRECTORY
        / operation_id
        / "files"
    ).resolve()

    moves: list[
        DuplicateCleanupMove
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

        if not _is_inside_folder(
            original_path,
            root_folder,
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

        if not _is_inside_folder(
            quarantined_path,
            quarantine_files_folder,
        ):
            raise ValueError(
                "A quarantine destination is outside the operation folder."
            )

        seen_source_paths.add(
            original_path
        )

        moves.append(
            DuplicateCleanupMove(
                asset=asset,
                original_path=original_path,
                quarantined_path=quarantined_path,
            )
        )

    return DuplicateCleanupPlan(
        project_folder=root_folder,
        operation_id=operation_id,
        moves=tuple(
            sorted(
                moves,
                key=lambda move: str(
                    move.relative_path
                ).casefold(),
            )
        ),
    )


def _relative_to_project(
    path: Path,
    project_folder: Path,
) -> str:
    """Return a path as project-relative text."""
    return str(
        path.resolve().relative_to(
            project_folder
        )
    )


def _build_manifest_data(
    plan: DuplicateCleanupPlan,
    quarantined_moves: tuple[DuplicateCleanupMove, ...],
    failed_moves: tuple[DuplicateCleanupFailure, ...],
) -> dict[str, object]:
    """Build JSON-compatible cleanup-manifest data."""
    quarantined_sources = {
        move.original_path
        for move in quarantined_moves
    }

    failure_messages = {
        failure.source_path: failure.error_message
        for failure in failed_moves
    }

    records: list[
        dict[str, object]
    ] = []

    for move in plan.moves:
        if move.original_path in quarantined_sources:
            status = "quarantined"
            error_message = None
        else:
            status = "failed"
            error_message = failure_messages.get(
                move.original_path,
                "The file was not quarantined.",
            )

        records.append(
            {
                "original_path": _relative_to_project(
                    move.original_path,
                    plan.project_folder,
                ),
                "quarantined_path": _relative_to_project(
                    move.quarantined_path,
                    plan.project_folder,
                ),
                "file_name": move.asset.file_name,
                "size_bytes": move.asset.size_bytes,
                "status": status,
                "error": error_message,
            }
        )

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "application": "Aniccoli",
        "operation_type": "duplicate_cleanup",
        "operation_id": plan.operation_id,
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "project_folder": str(
            plan.project_folder
        ),
        "status": (
            "quarantined"
            if not failed_moves
            else "partially_quarantined"
        ),
        "summary": {
            "selected": plan.selected_count,
            "quarantined": len(
                quarantined_moves
            ),
            "failed": len(
                failed_moves
            ),
        },
        "files": records,
    }


def _save_manifest(
    plan: DuplicateCleanupPlan,
    quarantined_moves: tuple[DuplicateCleanupMove, ...],
    failed_moves: tuple[DuplicateCleanupFailure, ...],
) -> Path:
    """Save a duplicate-cleanup manifest."""
    plan.operation_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_data = _build_manifest_data(
        plan=plan,
        quarantined_moves=quarantined_moves,
        failed_moves=failed_moves,
    )

    with plan.manifest_path.open(
        mode="w",
        encoding="utf-8",
    ) as manifest_file:
        json.dump(
            manifest_data,
            manifest_file,
            indent=2,
            ensure_ascii=False,
        )

        manifest_file.write(
            "\n"
        )

    return plan.manifest_path


def execute_duplicate_cleanup(
    plan: DuplicateCleanupPlan,
) -> DuplicateCleanupResult:
    """
    Move selected duplicate copies into Aniccoli's private quarantine.

    Existing files are never overwritten. No permanent deletion occurs.
    """
    quarantined_moves: list[
        DuplicateCleanupMove
    ] = []

    failed_moves: list[
        DuplicateCleanupFailure
    ] = []

    for move in plan.moves:
        try:
            if not move.original_path.exists():
                raise FileNotFoundError(
                    "The selected duplicate no longer exists: "
                    f"{move.original_path}"
                )

            if move.quarantined_path.exists():
                raise FileExistsError(
                    "The quarantine destination already exists: "
                    f"{move.quarantined_path}"
                )

            move.quarantined_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(
                    move.original_path
                ),
                str(
                    move.quarantined_path
                ),
            )
        except (
            FileNotFoundError,
            FileExistsError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            failed_moves.append(
                DuplicateCleanupFailure(
                    source_path=move.original_path,
                    destination_path=move.quarantined_path,
                    error_message=str(
                        error
                    ),
                )
            )
        else:
            quarantined_moves.append(
                move
            )

    quarantined_tuple = tuple(
        quarantined_moves
    )

    failed_tuple = tuple(
        failed_moves
    )

    manifest_path: Path | None = None
    manifest_error: str | None = None

    try:
        manifest_path = _save_manifest(
            plan=plan,
            quarantined_moves=quarantined_tuple,
            failed_moves=failed_tuple,
        )
    except (
        PermissionError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        manifest_error = str(
            error
        )

    return DuplicateCleanupResult(
        operation_id=plan.operation_id,
        quarantined_moves=quarantined_tuple,
        failed_moves=failed_tuple,
        manifest_path=manifest_path,
        manifest_error=manifest_error,
    )


def _load_manifest(
    manifest_path: Path,
) -> dict[str, object]:
    """Load and validate a duplicate-cleanup manifest."""
    try:
        with manifest_path.open(
            mode="r",
            encoding="utf-8",
        ) as manifest_file:
            data = json.load(
                manifest_file
            )
    except json.JSONDecodeError as error:
        raise ValueError(
            f"The cleanup manifest is damaged: {manifest_path}"
        ) from error

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            f"The cleanup manifest is invalid: {manifest_path}"
        )

    if data.get(
        "operation_type"
    ) != "duplicate_cleanup":
        raise ValueError(
            f"The file is not a duplicate-cleanup manifest: {manifest_path}"
        )

    files = data.get(
        "files"
    )

    if not isinstance(
        files,
        list,
    ):
        raise ValueError(
            f"The cleanup manifest has no valid file list: {manifest_path}"
        )

    return data


def find_latest_restorable_duplicate_cleanup(
    project_folder: str | Path,
) -> Path | None:
    """Return the latest cleanup manifest containing quarantined files."""
    root_folder = Path(
        project_folder
    ).expanduser().resolve()

    trash_folder = (
        root_folder
        / DUPLICATE_TRASH_DIRECTORY
    )

    if not trash_folder.exists():
        return None

    manifest_paths = sorted(
        trash_folder.glob(
            f"*/{MANIFEST_FILE_NAME}"
        ),
        reverse=True,
    )

    for manifest_path in manifest_paths:
        try:
            data = _load_manifest(
                manifest_path
            )
        except (
            PermissionError,
            OSError,
            ValueError,
        ):
            continue

        files = data.get(
            "files",
            [],
        )

        if any(
            isinstance(
                record,
                dict,
            )
            and record.get(
                "status"
            ) == "quarantined"
            for record in files
        ):
            return manifest_path

    return None


def _save_updated_manifest(
    manifest_path: Path,
    data: dict[str, object],
) -> None:
    """Save an updated restoration status to a cleanup manifest."""
    with manifest_path.open(
        mode="w",
        encoding="utf-8",
    ) as manifest_file:
        json.dump(
            data,
            manifest_file,
            indent=2,
            ensure_ascii=False,
        )

        manifest_file.write(
            "\n"
        )


def restore_duplicate_cleanup(
    project_folder: str | Path,
    manifest_path: str | Path | None = None,
) -> DuplicateRestoreResult:
    """
    Restore files from a duplicate-cleanup quarantine operation.

    Existing files at original locations are never overwritten.
    """
    root_folder = Path(
        project_folder
    ).expanduser().resolve()

    selected_manifest = (
        Path(
            manifest_path
        ).expanduser().resolve()
        if manifest_path is not None
        else find_latest_restorable_duplicate_cleanup(
            root_folder
        )
    )

    if selected_manifest is None:
        raise NoDuplicateCleanupHistoryError(
            "There is no duplicate-cleanup operation available to restore."
        )

    expected_history_folder = (
        root_folder
        / DUPLICATE_TRASH_DIRECTORY
    ).resolve()

    if not _is_inside_folder(
        selected_manifest,
        expected_history_folder,
    ):
        raise ValueError(
            "The cleanup manifest is outside this project."
        )

    data = _load_manifest(
        selected_manifest
    )

    file_records = data[
        "files"
    ]

    restored_moves: list[
        DuplicateRestoreMove
    ] = []

    failed_moves: list[
        DuplicateCleanupFailure
    ] = []

    for record in file_records:
        if not isinstance(
            record,
            dict,
        ):
            continue

        if record.get(
            "status"
        ) != "quarantined":
            continue

        original_value = record.get(
            "original_path"
        )

        quarantined_value = record.get(
            "quarantined_path"
        )

        if not isinstance(
            original_value,
            str,
        ) or not isinstance(
            quarantined_value,
            str,
        ):
            continue

        original_path = (
            root_folder
            / _normalize_relative_path(
                Path(
                    original_value
                )
            )
        ).resolve()

        quarantined_path = (
            root_folder
            / _normalize_relative_path(
                Path(
                    quarantined_value
                )
            )
        ).resolve()

        try:
            if not _is_inside_folder(
                original_path,
                root_folder,
            ):
                raise ValueError(
                    "The original restoration path is outside the project."
                )

            if not _is_inside_folder(
                quarantined_path,
                expected_history_folder,
            ):
                raise ValueError(
                    "The quarantined file is outside cleanup history."
                )

            if not quarantined_path.exists():
                raise FileNotFoundError(
                    "The quarantined file no longer exists: "
                    f"{quarantined_path}"
                )

            if original_path.exists():
                raise FileExistsError(
                    "The original location is occupied and will not "
                    f"be overwritten: {original_path}"
                )

            original_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(
                    quarantined_path
                ),
                str(
                    original_path
                ),
            )
        except (
            FileNotFoundError,
            FileExistsError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            failed_moves.append(
                DuplicateCleanupFailure(
                    source_path=quarantined_path,
                    destination_path=original_path,
                    error_message=str(
                        error
                    ),
                )
            )

            record[
                "restore_error"
            ] = str(
                error
            )
        else:
            restored_moves.append(
                DuplicateRestoreMove(
                    quarantined_path=quarantined_path,
                    original_path=original_path,
                )
            )

            record[
                "status"
            ] = "restored"

            record[
                "restored_at"
            ] = (
                datetime.now()
                .astimezone()
                .isoformat()
            )

            record[
                "restore_error"
            ] = None

    data[
        "status"
    ] = (
        "restored"
        if not failed_moves
        else "partially_restored"
    )

    data[
        "last_restore_attempt_at"
    ] = (
        datetime.now()
        .astimezone()
        .isoformat()
    )

    _save_updated_manifest(
        manifest_path=selected_manifest,
        data=data,
    )

    return DuplicateRestoreResult(
        manifest_path=selected_manifest,
        restored_moves=tuple(
            restored_moves
        ),
        failed_moves=tuple(
            failed_moves
        ),
    )
