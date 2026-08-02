"""Asset selection and exclusion tools for Aniccoli."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aniccoli.scanner import AssetFile


def _normalize_asset_path(
    path: str | Path,
) -> Path:
    """Return a safe project-relative asset path."""
    normalized_path = Path(path)

    if normalized_path.is_absolute():
        raise ValueError(
            "Asset selections must use project-relative paths."
        )

    normalized_parts = tuple(
        part
        for part in normalized_path.parts
        if part not in ("", ".")
    )

    if not normalized_parts:
        raise ValueError(
            "An asset selection cannot use an empty path."
        )

    if ".." in normalized_parts:
        raise ValueError(
            "An asset selection cannot leave the project folder."
        )

    return Path(*normalized_parts)


@dataclass(frozen=True)
class AssetSelection:
    """Store the project-relative paths of selected assets."""

    selected_paths: frozenset[Path] = frozenset()

    def __post_init__(self) -> None:
        """Normalize and validate every selected path."""
        normalized_paths = frozenset(
            _normalize_asset_path(path)
            for path in self.selected_paths
        )

        object.__setattr__(
            self,
            "selected_paths",
            normalized_paths,
        )

    @property
    def selected_count(self) -> int:
        """Return the number of selected asset paths."""
        return len(self.selected_paths)

    @property
    def is_empty(self) -> bool:
        """Return True when no assets are selected."""
        return not self.selected_paths

    def contains(self, asset: AssetFile) -> bool:
        """Return True when an asset is selected."""
        return (
            _normalize_asset_path(asset.relative_path)
            in self.selected_paths
        )

    def select(self, asset: AssetFile) -> AssetSelection:
        """Return a new selection that includes an asset."""
        selected_path = _normalize_asset_path(
            asset.relative_path
        )

        return AssetSelection(
            selected_paths=(
                self.selected_paths
                | {selected_path}
            )
        )

    def deselect(self, asset: AssetFile) -> AssetSelection:
        """Return a new selection without an asset."""
        selected_path = _normalize_asset_path(
            asset.relative_path
        )

        return AssetSelection(
            selected_paths=(
                self.selected_paths
                - {selected_path}
            )
        )

    def toggle(self, asset: AssetFile) -> AssetSelection:
        """Return a new selection with an asset toggled."""
        if self.contains(asset):
            return self.deselect(asset)

        return self.select(asset)


def select_all_assets(
    assets: Iterable[AssetFile],
) -> AssetSelection:
    """Return a selection containing every supplied asset."""
    return AssetSelection(
        selected_paths=frozenset(
            _normalize_asset_path(
                asset.relative_path
            )
            for asset in assets
        )
    )


def clear_asset_selection() -> AssetSelection:
    """Return an empty asset selection."""
    return AssetSelection()


def invert_asset_selection(
    assets: Iterable[AssetFile],
    selection: AssetSelection,
) -> AssetSelection:
    """Invert a selection within a supplied asset collection."""
    available_paths = {
        _normalize_asset_path(asset.relative_path)
        for asset in assets
    }

    return AssetSelection(
        selected_paths=frozenset(
            available_paths
            - selection.selected_paths
        )
    )


def retain_available_selections(
    assets: Iterable[AssetFile],
    selection: AssetSelection,
) -> AssetSelection:
    """Remove selections that no longer exist in a scan."""
    available_paths = {
        _normalize_asset_path(asset.relative_path)
        for asset in assets
    }

    return AssetSelection(
        selected_paths=frozenset(
            selection.selected_paths
            & available_paths
        )
    )


def selected_assets(
    assets: Iterable[AssetFile],
    selection: AssetSelection,
) -> tuple[AssetFile, ...]:
    """Return only selected assets while preserving input order."""
    return tuple(
        asset
        for asset in assets
        if selection.contains(asset)
    )


def excluded_assets(
    assets: Iterable[AssetFile],
    selection: AssetSelection,
) -> tuple[AssetFile, ...]:
    """Return assets that are not selected while preserving input order."""
    return tuple(
        asset
        for asset in assets
        if not selection.contains(asset)
    )


@dataclass(frozen=True)
class SelectionSummary:
    """Store counts for a selection against an asset collection."""

    total_assets: int
    selected_assets: int
    excluded_assets: int

    @property
    def has_selection(self) -> bool:
        """Return True when at least one asset is selected."""
        return self.selected_assets > 0

    @property
    def all_selected(self) -> bool:
        """Return True when every available asset is selected."""
        return (
            self.total_assets > 0
            and self.selected_assets
            == self.total_assets
        )


def summarize_selection(
    assets: Iterable[AssetFile],
    selection: AssetSelection,
) -> SelectionSummary:
    """Calculate selection counts for an asset collection."""
    asset_records = tuple(assets)

    selected_count = len(
        selected_assets(
            asset_records,
            selection,
        )
    )

    return SelectionSummary(
        total_assets=len(asset_records),
        selected_assets=selected_count,
        excluded_assets=(
            len(asset_records)
            - selected_count
        ),
    )