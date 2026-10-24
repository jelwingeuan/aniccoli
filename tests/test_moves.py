"""Safe moves, journals and reversal, tested on real temporary folders."""

import json
import shutil
from pathlib import Path

import pytest

from aniccoli.moves import (
    JOURNAL_FOLDER,
    QUARANTINE_FOLDER,
    JournalKind,
    Move,
    NothingToReverseError,
    apply_moves,
    latest_journal,
    reverse_latest,
)


FIXTURES = Path(__file__).parent / "fixtures"
ORGANIZE = JournalKind.ORGANIZE
QUARANTINE = JournalKind.QUARANTINE


def write(path: Path, text: str = "data") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    folder = tmp_path / "project"
    folder.mkdir()
    return folder


def test_apply_moves_files_and_writes_a_journal(project: Path) -> None:
    write(project / "hero.fbx", "mesh")

    result = apply_moves(
        project,
        [Move(project / "hero.fbx", project / "Models/hero.fbx", {"category": "FBX Model"})],
        ORGANIZE,
    )

    assert (project / "Models/hero.fbx").read_text() == "mesh"
    assert not (project / "hero.fbx").exists()
    assert len(result.done) == 1 and not result.failed and not result.journal_error
    assert json.loads(result.journal_path.read_text())["movements"] == [
        {
            "source": "hero.fbx",
            "destination": "Models/hero.fbx",
            "category": "FBX Model",
            "status": "moved",
            "error": None,
        }
    ]
    assert latest_journal(project, ORGANIZE) == result.journal_path
    assert latest_journal(project, QUARANTINE) is None


def test_refused_moves_fail_alone_and_touch_nothing(project: Path) -> None:
    write(project / "keep.png", "new")
    write(project / "taken.png", "old")
    write(project / "fine.txt")
    (project / "folder").mkdir()
    outside = project.parent / "outside.txt"
    write(outside, "outside")

    result = apply_moves(
        project,
        [
            Move(project / "keep.png", project / "taken.png"),
            Move(project / "fine.txt", outside.with_name("escaped.txt")),
            Move(outside, project / "pulled_in.txt"),
            Move(project / "folder", project / "moved_folder"),
            Move(project / "missing.png", project / "anywhere.png"),
            Move(project / "fine.txt", project / "Docs/fine.txt"),
        ],
        ORGANIZE,
    )

    assert [move.destination.name for move in result.done] == ["fine.txt"]
    assert len(result.failed) == 5
    assert (project / "taken.png").read_text() == "old"
    assert (project / "keep.png").read_text() == "new"
    assert outside.read_text() == "outside"
    assert not outside.with_name("escaped.txt").exists()
    assert (project / "folder").is_dir()
    statuses = [entry["status"] for entry in json.loads(result.journal_path.read_text())["movements"]]
    assert statuses == ["failed"] * 5 + ["moved"]


def test_reverse_round_trip(project: Path) -> None:
    write(project / "a.fbx", "a")
    write(project / "maps/b.png", "b")
    apply_moves(
        project,
        [
            Move(project / "a.fbx", project / "Models/a.fbx"),
            Move(project / "maps/b.png", project / "Textures/b.png"),
        ],
        ORGANIZE,
    )

    result = reverse_latest(project, ORGANIZE)

    assert len(result.done) == 2 and not result.failed
    assert (project / "a.fbx").read_text() == "a"
    assert (project / "maps/b.png").read_text() == "b"
    assert json.loads(result.journal_path.read_text())["undo_status"] == "complete"
    assert latest_journal(project, ORGANIZE) is None
    with pytest.raises(NothingToReverseError):
        reverse_latest(project, ORGANIZE)


def test_reverse_skips_restored_files_and_resumes_after_a_failure(project: Path) -> None:
    write(project / "a.fbx", "a")
    write(project / "b.fbx", "b")
    apply_moves(
        project,
        [
            Move(project / "a.fbx", project / "Models/a.fbx"),
            Move(project / "b.fbx", project / "Models/b.fbx"),
        ],
        ORGANIZE,
    )
    shutil.move(project / "Models/a.fbx", project / "a.fbx")
    write(project / "b.fbx", "someone else's file")

    first = reverse_latest(project, ORGANIZE)

    assert [move.destination.name for move in first.skipped] == ["a.fbx"]
    assert len(first.failed) == 1 and not first.done
    assert (project / "b.fbx").read_text() == "someone else's file"
    assert (project / "Models/b.fbx").read_text() == "b"
    assert latest_journal(project, ORGANIZE) == first.journal_path

    (project / "b.fbx").unlink()
    second = reverse_latest(project, ORGANIZE)

    assert [move.destination.name for move in second.done] == ["b.fbx"]
    assert (project / "b.fbx").read_text() == "b"
    assert latest_journal(project, ORGANIZE) is None


def test_quarantine_stays_inside_the_quarantine_folder(project: Path) -> None:
    write(project / "copy.png")
    trash = project / QUARANTINE_FOLDER / "op1/files"

    refused = apply_moves(project, [Move(project / "copy.png", project / "elsewhere.png")], QUARANTINE)
    assert len(refused.failed) == 1 and (project / "copy.png").exists()

    moved = apply_moves(project, [Move(project / "copy.png", trash / "copy.png")], QUARANTINE)
    assert len(moved.done) == 1

    journal = json.loads(moved.journal_path.read_text())
    journal["movements"][0]["destination"] = "elsewhere.png"
    moved.journal_path.write_text(json.dumps(journal))
    write(project / "elsewhere.png")

    result = reverse_latest(project, QUARANTINE)
    assert len(result.failed) == 1 and not result.done
    assert (project / "elsewhere.png").exists() and not (project / "copy.png").exists()


def install_legacy_organize_log(project: Path) -> Path:
    log = json.loads((FIXTURES / "legacy_organization_log.json").read_text())
    for movement in log["movements"]:
        write(project / movement["destination"], movement["source"])
    path = project / JOURNAL_FOLDER / "organization_20261025_073417_544591.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(log))
    return path


def test_legacy_organize_log_can_be_undone(project: Path) -> None:
    log_path = install_legacy_organize_log(project)

    assert latest_journal(project, ORGANIZE) == log_path
    result = reverse_latest(project, ORGANIZE)

    assert len(result.done) == 4 and not result.failed
    for source in ("hero.fbx", "notes.txt", "maps/hero_normal.png", "dupes/rock.png"):
        assert (project / source).read_text() == source
    assert latest_journal(project, ORGANIZE) is None


def test_legacy_organize_log_already_undone_is_not_reversible(project: Path) -> None:
    log_path = install_legacy_organize_log(project)
    log = json.loads(log_path.read_text())
    log["undo_status"] = "complete"
    log_path.write_text(json.dumps(log))

    assert latest_journal(project, ORGANIZE) is None


def install_legacy_manifest(project: Path) -> Path:
    manifest = json.loads((FIXTURES / "legacy_duplicate_manifest.json").read_text())
    write(project / manifest["files"][0]["quarantined_path"], "rock")
    path = project / QUARANTINE_FOLDER / manifest["operation_id"] / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_legacy_duplicate_manifest_can_be_restored_after_a_partial_attempt(project: Path) -> None:
    manifest_path = install_legacy_manifest(project)
    write(project / "dupes/old/rock.png", "occupied")

    assert latest_journal(project, QUARANTINE) == manifest_path
    first = reverse_latest(project, QUARANTINE)
    assert len(first.failed) == 1

    (project / "dupes/old/rock.png").unlink()
    second = reverse_latest(project, QUARANTINE)

    assert len(second.done) == 1
    assert (project / "dupes/old/rock.png").read_text() == "rock"
    assert latest_journal(project, QUARANTINE) is None


def test_newest_quarantine_is_restored_first(project: Path) -> None:
    install_legacy_manifest(project)
    write(project / "copy.png", "new copy")
    newer = apply_moves(
        project,
        [Move(project / "copy.png", project / QUARANTINE_FOLDER / "op2/files/copy.png")],
        QUARANTINE,
    )

    assert latest_journal(project, QUARANTINE) == newer.journal_path
    reverse_latest(project, QUARANTINE)

    assert (project / "copy.png").read_text() == "new copy"
    assert not (project / "dupes/old/rock.png").exists()


def test_missing_project_folder_is_refused(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        apply_moves(tmp_path / "missing", [], ORGANIZE)
    with pytest.raises(FileNotFoundError):
        latest_journal(tmp_path / "missing", ORGANIZE)
