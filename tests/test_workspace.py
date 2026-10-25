"""The whole scan, select, plan, organize and undo workflow, without a window."""

from pathlib import Path

import pytest

from aniccoli.filters import AssetQuery
from aniccoli.moves import NothingToReverseError
from aniccoli.organization_options import OrganizationOptions
from aniccoli.reports import ReportFormat
from aniccoli.workspace import Workspace, WorkspaceError


def make_project(root: Path) -> Path:
    files = {
        "hero.fbx": "mesh",
        "maps/hero_normal.png": "normal",
        "notes.txt": "todo",
        "rock.png": "rock",
        "old/rock.png": "rock",
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def layout(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text()
        for path in root.rglob("*")
        if path.is_file() and ".aniccoli" not in path.relative_to(root).parts
    }


def test_scan_select_plan_organize_undo_round_trip(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    before = layout(project)
    workspace = Workspace(project)

    workspace.scan(recursive=True)
    assert len(workspace.assets) == 5
    assert workspace.selection_summary().selected_assets == 5

    textures = workspace.query(AssetQuery(search_text="png")).matched
    workspace.set_selected(workspace.assets, False)
    workspace.set_selected(textures, True)
    assert {asset.file_name for asset in workspace.selected_assets()} == {"hero_normal.png", "rock.png"}

    plan = workspace.plan_organization(OrganizationOptions())
    assert len(plan) == 3
    assert any(move.renamed_for_conflict for move in plan)

    result = workspace.organize()
    assert len(result.done) == 3 and not result.failed
    assert sorted(layout(project).values()) == sorted(before.values())
    assert "hero.fbx" in layout(project) and "notes.txt" in layout(project)
    assert workspace.plan == ()
    assert len(workspace.assets) == 5, "organize rescans the project"
    assert workspace.latest_undo() is not None

    undone = workspace.undo()
    assert len(undone.done) == 3
    assert layout(project) == before
    assert workspace.latest_undo() is None
    with pytest.raises(NothingToReverseError):
        workspace.undo()


def test_invert_selection_only_touches_the_given_assets(tmp_path: Path) -> None:
    workspace = Workspace(make_project(tmp_path))
    workspace.scan(recursive=True)
    fbx = workspace.query(AssetQuery(search_text="fbx")).matched

    workspace.invert_selection(fbx)

    assert workspace.selection_summary().selected_assets == 4
    assert all(asset.file_name != "hero.fbx" for asset in workspace.selected_assets())


def test_steps_out_of_order_are_refused(tmp_path: Path) -> None:
    empty = Workspace()
    with pytest.raises(WorkspaceError) as error:
        empty.scan(recursive=True)
    assert error.value.key == "choose_first"

    workspace = Workspace(make_project(tmp_path / "project"))
    for step, key in (
        (lambda: workspace.plan_organization(OrganizationOptions()), "scan_before_preview"),
        (workspace.find_duplicates, "duplicate_before"),
        (workspace.organize, "preview_nothing"),
    ):
        with pytest.raises(WorkspaceError) as error:
            step()
        assert error.value.key == key

    workspace.scan(recursive=True)
    workspace.set_selected(workspace.assets, False)
    with pytest.raises(WorkspaceError) as error:
        workspace.plan_organization(OrganizationOptions())
    assert error.value.key == "select_before_preview"
    with pytest.raises(WorkspaceError) as error:
        workspace.export_report(tmp_path / "report.json", ReportFormat.JSON, OrganizationOptions())
    assert error.value.key == "select_before_export"


def test_scanning_a_missing_folder_clears_the_old_scan(tmp_path: Path) -> None:
    project = make_project(tmp_path / "project")
    workspace = Workspace(project)
    workspace.scan(recursive=True)

    workspace.open(tmp_path / "gone")
    with pytest.raises(OSError):
        workspace.scan(recursive=True)
    assert workspace.assets == () and workspace.selection_summary().selected_assets == 0


def test_duplicates_and_report(tmp_path: Path) -> None:
    project = make_project(tmp_path / "project")
    workspace = Workspace(project)
    workspace.scan(recursive=False)
    assert {asset.file_name for asset in workspace.assets} == {"hero.fbx", "notes.txt", "rock.png"}

    workspace.scan(recursive=True)
    groups = workspace.find_duplicates()
    assert [sorted(asset.relative_path.as_posix() for asset in group.files) for group in groups] == [
        ["old/rock.png", "rock.png"],
    ]

    report = workspace.export_report(tmp_path / "report.json", ReportFormat.JSON, OrganizationOptions())
    assert report.asset_count == 5 and report.report_path.exists()
