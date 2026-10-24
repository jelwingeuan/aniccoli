"""Safe, journaled file moves inside a project folder, and their reversal.

Organizing and duplicate quarantine both go through apply_moves, and undo
and restore both go through reverse_latest, so every file operation gets
the same safety rules: paths stay inside the project, nothing is ever
overwritten, each file succeeds or fails on its own, and every operation
is recorded in a JSON journal that can be reversed later.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


JOURNAL_FOLDER = Path(".aniccoli") / "history"
QUARANTINE_FOLDER = Path(".aniccoli") / "duplicate_trash"
JOURNAL_SCHEMA_VERSION = 2


class JournalKind(str, Enum):
    """The kinds of reversible operation, used as journal name prefixes."""

    ORGANIZE = "organization"
    QUARANTINE = "quarantine"

    def __str__(self) -> str:
        """Return the journal name prefix."""
        return self.value


class NothingToReverseError(RuntimeError):
    """Raised when a project has no journal of a kind left to reverse."""


@dataclass(frozen=True)
class Move:
    """One file movement from source to destination."""

    source: Path
    destination: Path
    details: Mapping[str, object] = field(
        default_factory=dict,
        compare=False,
    )


@dataclass(frozen=True)
class MoveFailure:
    """A movement that was refused or failed, with the reason."""

    move: Move
    error: str


@dataclass(frozen=True)
class MoveResult:
    """The outcome of applying or reversing a group of movements."""

    done: tuple[Move, ...]
    skipped: tuple[Move, ...]
    failed: tuple[MoveFailure, ...]
    journal_path: Path | None
    journal_error: str | None = None


def apply_moves(
    project: str | Path,
    moves: Iterable[Move],
    kind: JournalKind,
) -> MoveResult:
    """Move files inside the project and record the operation in a journal."""
    root = _project_root(
        project
    )

    done: list[Move] = []
    failed: list[MoveFailure] = []
    entries: list[dict[str, object]] = []

    for move in moves:
        error_message: str | None = None

        try:
            if kind is JournalKind.QUARANTINE:
                _check_in_quarantine(
                    root,
                    move.destination,
                )

            _move_file(
                root,
                move.source,
                move.destination,
            )
        except (OSError, ValueError) as error:
            error_message = str(error)
            failed.append(
                MoveFailure(
                    move=move,
                    error=error_message,
                )
            )
        else:
            done.append(move)

        entries.append(
            {
                "source": _relative_text(
                    root,
                    move.source,
                ),
                "destination": _relative_text(
                    root,
                    move.destination,
                ),
                **move.details,
                "status": (
                    "failed"
                    if error_message
                    else "moved"
                ),
                "error": error_message,
            }
        )

    journal = {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "application": "Aniccoli",
        "operation": kind.value,
        "created_at": _now(),
        "project_folder": str(root),
        "summary": {
            "planned": len(entries),
            "moved": len(done),
            "failed": len(failed),
        },
        "movements": entries,
    }

    journal_path: Path | None = None
    journal_error: str | None = None

    try:
        journal_folder = root / JOURNAL_FOLDER
        journal_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        journal_path = journal_folder / (
            f"{kind.value}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        )

        _save_json(
            journal_path,
            journal,
        )
    except (OSError, TypeError, ValueError) as error:
        journal_path = None
        journal_error = str(error)

    return MoveResult(
        done=tuple(done),
        skipped=(),
        failed=tuple(failed),
        journal_path=journal_path,
        journal_error=journal_error,
    )


def latest_journal(
    project: str | Path,
    kind: JournalKind,
) -> Path | None:
    """Return the newest journal of this kind that can still be reversed."""
    newest = next(
        _reversible_journals(
            _project_root(project),
            kind,
        ),
        None,
    )

    return (
        newest[0]
        if newest is not None
        else None
    )


def reverse_latest(
    project: str | Path,
    kind: JournalKind,
) -> MoveResult:
    """Move the files of the newest reversible journal back where they were."""
    root = _project_root(
        project
    )

    newest = next(
        _reversible_journals(
            root,
            kind,
        ),
        None,
    )

    if newest is None:
        raise NothingToReverseError(
            "There is no earlier operation left to reverse in this project."
        )

    journal_path, journal = newest

    return _reverse_journal(
        root,
        kind,
        journal_path,
        journal,
    )


def _reverse_journal(
    root: Path,
    kind: JournalKind,
    journal_path: Path,
    journal: dict[str, object],
) -> MoveResult:
    """Reverse every still-moved entry of one journal and save its status."""
    done: list[Move] = []
    skipped: list[Move] = []
    failed: list[MoveFailure] = []

    for entry in journal["movements"]:
        if entry.get("status") != "moved":
            continue

        current_text = entry.get("destination")
        original_text = entry.get("source")

        if not (
            isinstance(current_text, str)
            and isinstance(original_text, str)
        ):
            # A malformed entry names no file that could be moved safely.
            continue

        move = Move(
            source=root / current_text,
            destination=root / original_text,
            details={
                key: value
                for key, value in entry.items()
                if key not in ("source", "destination", "status", "error")
            },
        )

        try:
            current_path = _inside_project(
                root,
                move.source,
            )

            if kind is JournalKind.QUARANTINE:
                _check_in_quarantine(
                    root,
                    current_path,
                )

            original_path = _inside_project(
                root,
                move.destination,
            )

            if (
                not current_path.exists()
                and original_path.exists()
            ):
                skipped.append(move)
            else:
                _move_file(
                    root,
                    current_path,
                    original_path,
                )
                done.append(move)
        except (OSError, ValueError) as error:
            failed.append(
                MoveFailure(
                    move=move,
                    error=str(error),
                )
            )
            entry["reverse_error"] = str(error)
        else:
            entry["status"] = "reversed"
            entry.pop("reverse_error", None)

    journal["schema_version"] = JOURNAL_SCHEMA_VERSION
    journal["undo_status"] = (
        "partial"
        if failed
        else "complete"
    )
    journal["undone_at"] = _now()

    journal_error: str | None = None

    try:
        _save_json(
            journal_path,
            journal,
        )
    except (OSError, TypeError, ValueError) as error:
        journal_error = str(error)

    return MoveResult(
        done=tuple(done),
        skipped=tuple(skipped),
        failed=tuple(failed),
        journal_path=journal_path,
        journal_error=journal_error,
    )


def _reversible_journals(
    root: Path,
    kind: JournalKind,
) -> Iterator[tuple[Path, dict[str, object]]]:
    """Yield journals of this kind with entries left to reverse, newest first."""
    candidates = list(
        (root / JOURNAL_FOLDER).glob(f"{kind.value}_*.json")
    )

    if kind is JournalKind.QUARANTINE:
        # Duplicate cleanups made before journals were shared kept a
        # manifest inside each quarantine folder.
        candidates += (root / QUARANTINE_FOLDER).glob("*/manifest.json")

    journals: list[tuple[datetime, Path, dict[str, object]]] = []

    for journal_path in candidates:
        try:
            journal = _load_journal(journal_path)

            if journal is None or not any(
                entry.get("status") == "moved"
                for entry in journal["movements"]
            ):
                continue

            journals.append(
                (
                    _created_at(journal, journal_path),
                    journal_path,
                    journal,
                )
            )
        except (OSError, ValueError):
            # An unreadable journal must not block undo for the others.
            continue

    journals.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    for _created, journal_path, journal in journals:
        yield journal_path, journal


def _load_journal(
    journal_path: Path,
) -> dict[str, object] | None:
    """Read a journal in the current or a legacy format, or return None."""
    with journal_path.open(encoding="utf-8") as journal_file:
        data = json.load(journal_file)

    if (
        not isinstance(data, dict)
        or data.get("application") != "Aniccoli"
    ):
        return None

    if data.get("operation_type") == "duplicate_cleanup":
        files = data.get("files")

        if not isinstance(files, list):
            return None

        status_names = {
            "quarantined": "moved",
            "restored": "reversed",
        }

        data["movements"] = [
            {
                "source": record.get("original_path"),
                "destination": record.get("quarantined_path"),
                "file_name": record.get("file_name"),
                "size_bytes": record.get("size_bytes"),
                "status": status_names.get(
                    record.get("status"),
                    record.get("status"),
                ),
                "error": record.get("error"),
            }
            for record in files
            if isinstance(record, dict)
        ]

        # Saved back in the current format, so a partial restore can resume.
        del data["files"]
        del data["operation_type"]
        data["operation"] = JournalKind.QUARANTINE.value
        return data

    movements = data.get("movements")

    if not isinstance(movements, list):
        return None

    data["movements"] = [
        entry
        for entry in movements
        if isinstance(entry, dict)
    ]

    # Legacy organize logs marked a finished undo only at the top level.
    if data.get("undo_status") == "complete":
        for entry in data["movements"]:
            if entry.get("status") == "moved":
                entry["status"] = "reversed"

    return data


def _created_at(
    journal: dict[str, object],
    journal_path: Path,
) -> datetime:
    """Return when a journal was written, for newest-first ordering."""
    try:
        return datetime.fromisoformat(
            str(journal.get("created_at"))
        ).astimezone()
    except ValueError:
        return datetime.fromtimestamp(
            journal_path.stat().st_mtime
        ).astimezone()


def _move_file(
    root: Path,
    source: Path,
    destination: Path,
) -> None:
    """Move one file inside the project without overwriting anything."""
    source_path = _inside_project(
        root,
        source,
    )

    destination_path = _inside_project(
        root,
        destination,
    )

    if source_path == destination_path:
        raise ValueError(
            "The source and destination paths are identical."
        )

    if not source_path.exists():
        raise FileNotFoundError(
            f"The source file no longer exists: {source_path}"
        )

    if not source_path.is_file():
        raise ValueError(
            f"The source path is not a file: {source_path}"
        )

    if destination_path.exists():
        raise FileExistsError(
            "The destination already exists and will not be "
            f"overwritten: {destination_path}"
        )

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.move(
        source_path,
        destination_path,
    )


def _inside_project(
    root: Path,
    path: Path,
) -> Path:
    """Resolve a path and refuse it unless it is inside the project."""
    resolved_path = (
        root / path.expanduser()
    ).resolve()

    if not resolved_path.is_relative_to(root):
        raise ValueError(
            f"The path is outside the project folder: {resolved_path}"
        )

    return resolved_path


def _check_in_quarantine(
    root: Path,
    path: Path,
) -> None:
    """Refuse a quarantined-file path outside the quarantine folder."""
    resolved_path = _inside_project(
        root,
        path,
    )

    if not resolved_path.is_relative_to(
        (root / QUARANTINE_FOLDER).resolve()
    ):
        raise ValueError(
            "The quarantined file is outside the quarantine folder: "
            f"{resolved_path}"
        )


def _project_root(
    project: str | Path,
) -> Path:
    """Resolve and validate the project folder."""
    root = Path(
        project
    ).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"The project folder does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"The project path is not a folder: {root}"
        )

    return root


def _relative_text(
    root: Path,
    path: Path,
) -> str:
    """Return a path relative to the project, or absolute if outside it."""
    resolved_path = (
        root / path.expanduser()
    ).resolve()

    if resolved_path.is_relative_to(root):
        return resolved_path.relative_to(root).as_posix()

    return str(resolved_path)


def _save_json(
    path: Path,
    data: dict[str, object],
) -> None:
    """Write a dictionary as formatted UTF-8 JSON."""
    with path.open(
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


def _now() -> str:
    """Return the current local time as an ISO 8601 string."""
    return datetime.now().astimezone().isoformat()
