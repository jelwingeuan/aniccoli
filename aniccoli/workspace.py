"""One project's scan, selection and organize-undo workflow, without any UI.

The window asks the Workspace to act and redraws from its state, so the
whole workflow can be exercised in tests on real temporary folders.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from aniccoli.duplicates import (
    DuplicateGroup,
    find_duplicate_groups,
)
from aniccoli.filters import (
    AssetQuery,
    QueryResult,
    query_assets,
)
from aniccoli.moves import (
    JournalKind,
    MoveResult,
    apply_moves,
    latest_journal,
    reverse_latest,
)
from aniccoli.organization_options import OrganizationOptions
from aniccoli.organizer import (
    PlannedMove,
    build_organization_plan,
)
from aniccoli.reports import (
    AssetReportResult,
    ReportFormat,
    export_asset_report,
)
from aniccoli.scanner import (
    AssetFile,
    scan_folder,
)
from aniccoli.selection import (
    AssetSelection,
    SelectionSummary,
    select_all_assets,
    selected_assets,
    summarize_selection,
)


class WorkspaceError(RuntimeError):
    """A step was asked for before the workspace was ready for it."""

    def __init__(
        self,
        key: str,
    ) -> None:
        """Store the translation key that tells the user what to do first."""
        super().__init__(key)
        self.key = key


class Workspace:
    """The selected project folder and everything Aniccoli knows about it."""

    def __init__(
        self,
        project: Path | None = None,
    ) -> None:
        """Start with a project folder, or none, and nothing scanned."""
        self.project = project
        self.assets: tuple[AssetFile, ...] = ()
        self.selection = AssetSelection()
        self.plan: tuple[PlannedMove, ...] = ()
        self._recursive = True

    def open(
        self,
        project: Path | None,
    ) -> None:
        """Switch to another project folder and forget the previous scan."""
        self.project = project
        self.assets = ()
        self.selection = AssetSelection()
        self.plan = ()

    def scan(
        self,
        *,
        recursive: bool,
    ) -> None:
        """Scan the project, select every asset and drop any earlier plan."""
        project = self._require_project()
        self._recursive = recursive
        self.plan = ()

        try:
            self.assets = tuple(
                scan_folder(
                    project,
                    recursive=recursive,
                    include_hidden=False,
                )
            )
        except OSError:
            self.assets = ()
            self.selection = AssetSelection()
            raise

        self.selection = select_all_assets(
            self.assets
        )

    def query(
        self,
        query: AssetQuery,
    ) -> QueryResult:
        """Return the scanned assets that match a query."""
        return query_assets(
            self.assets,
            query,
        )

    def set_selected(
        self,
        assets: Iterable[AssetFile],
        selected: bool,
    ) -> None:
        """Select or deselect the given assets."""
        paths = select_all_assets(
            assets
        ).selected_paths

        self.selection = AssetSelection(
            selected_paths=(
                self.selection.selected_paths | paths
                if selected
                else self.selection.selected_paths - paths
            )
        )

    def invert_selection(
        self,
        assets: Iterable[AssetFile],
    ) -> None:
        """Flip the selection of the given assets only."""
        self.selection = AssetSelection(
            selected_paths=(
                self.selection.selected_paths
                ^ select_all_assets(assets).selected_paths
            )
        )

    def selected_assets(self) -> tuple[AssetFile, ...]:
        """Return the selected assets in scan order."""
        return selected_assets(
            self.assets,
            self.selection,
        )

    def selection_summary(self) -> SelectionSummary:
        """Return how many scanned assets are selected."""
        return summarize_selection(
            self.assets,
            self.selection,
        )

    def plan_organization(
        self,
        options: OrganizationOptions,
    ) -> tuple[PlannedMove, ...]:
        """Plan where the selected assets would move, without moving them."""
        project = self._require_scan(
            "scan_before_preview"
        )

        chosen = self.selected_assets()

        if not chosen:
            raise WorkspaceError(
                "select_before_preview"
            )

        self.plan = tuple(
            build_organization_plan(
                project_folder=project,
                assets=chosen,
                options=options,
            )
        )

        return self.plan

    def organize(self) -> MoveResult:
        """Move the planned files, then rescan so the assets match the disk."""
        project = self._require_project()

        if not self.plan:
            raise WorkspaceError(
                "preview_nothing"
            )

        result = apply_moves(
            project,
            [
                planned_move.as_move()
                for planned_move in self.plan
            ],
            JournalKind.ORGANIZE,
        )

        self._rescan_after_moves()
        return result

    def undo(self) -> MoveResult:
        """Reverse the latest organization, then rescan."""
        result = reverse_latest(
            self._require_project(),
            JournalKind.ORGANIZE,
        )

        self._rescan_after_moves()
        return result

    def latest_undo(self) -> Path | None:
        """Return the journal that undo would reverse, if there is one."""
        if self.project is None:
            return None

        try:
            return latest_journal(
                self.project,
                JournalKind.ORGANIZE,
            )
        except OSError:
            return None

    def find_duplicates(self) -> list[DuplicateGroup]:
        """Return groups of scanned files with exactly the same content."""
        self._require_scan(
            "duplicate_before"
        )

        return find_duplicate_groups(
            self.assets,
            include_empty=False,
        )

    def export_report(
        self,
        output_path: Path,
        report_format: ReportFormat,
        options: OrganizationOptions,
    ) -> AssetReportResult:
        """Write an inventory of the selected assets."""
        project = self._require_scan(
            "scan_before_export"
        )

        chosen = self.selected_assets()

        if not chosen:
            raise WorkspaceError(
                "select_before_export"
            )

        return export_asset_report(
            output_path=output_path,
            assets=chosen,
            project_folder=project,
            options=options,
            report_format=report_format,
            overwrite=False,
        )

    def _rescan_after_moves(self) -> None:
        """Refresh the assets after files moved, keeping the move result."""
        try:
            self.scan(
                recursive=self._recursive,
            )
        except OSError:
            # The moves already happened and are journaled; the next scan
            # reports why the folder can no longer be read.
            pass

    def _require_project(self) -> Path:
        """Return the project folder, or explain that one is needed."""
        if self.project is None:
            raise WorkspaceError(
                "choose_first"
            )

        return self.project

    def _require_scan(
        self,
        key: str,
    ) -> Path:
        """Return the project folder once it has been scanned."""
        project = self._require_project()

        if not self.assets:
            raise WorkspaceError(key)

        return project
