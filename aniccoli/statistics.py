"""Asset statistics and project-summary tools for Aniccoli."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aniccoli.scanner import (
    AssetFile,
    calculate_total_size,
    format_file_size,
)


@dataclass(frozen=True)
class StatisticsGroup:
    """Store asset count and combined size for one group."""

    name: str
    asset_count: int
    total_size_bytes: int

    @property
    def total_size_text(self) -> str:
        """Return the group size in readable form."""
        return format_file_size(
            self.total_size_bytes
        )


@dataclass(frozen=True)
class AssetStatistics:
    """Store calculated statistics for scanned assets."""

    total_assets: int
    total_size_bytes: int
    average_size_bytes: int
    category_groups: tuple[StatisticsGroup, ...]
    extension_groups: tuple[StatisticsGroup, ...]
    folder_groups: tuple[StatisticsGroup, ...]
    largest_assets: tuple[AssetFile, ...]
    recently_modified_assets: tuple[AssetFile, ...]

    @property
    def total_size_text(self) -> str:
        """Return the combined asset size in readable form."""
        return format_file_size(
            self.total_size_bytes
        )

    @property
    def average_size_text(self) -> str:
        """Return the average asset size in readable form."""
        return format_file_size(
            self.average_size_bytes
        )

    @property
    def category_count(self) -> int:
        """Return the number of represented categories."""
        return len(
            self.category_groups
        )

    @property
    def extension_count(self) -> int:
        """Return the number of represented extensions."""
        return len(
            self.extension_groups
        )

    @property
    def folder_count(self) -> int:
        """Return the number of represented source folders."""
        return len(
            self.folder_groups
        )


def _folder_name(
    asset: AssetFile,
) -> str:
    """Return a readable source-folder name for an asset."""
    parent_folder = asset.relative_path.parent

    if parent_folder == Path("."):
        return "Project root"

    return str(
        parent_folder
    )


def _build_groups(
    assets: Iterable[AssetFile],
    *,
    group_name,
) -> tuple[StatisticsGroup, ...]:
    """Group assets by a selected text value."""
    grouped_counts: dict[str, int] = defaultdict(
        int
    )

    grouped_sizes: dict[str, int] = defaultdict(
        int
    )

    for asset in assets:
        name = str(
            group_name(
                asset
            )
        )

        grouped_counts[name] += 1
        grouped_sizes[name] += asset.size_bytes

    groups = (
        StatisticsGroup(
            name=name,
            asset_count=grouped_counts[name],
            total_size_bytes=grouped_sizes[name],
        )
        for name in grouped_counts
    )

    return tuple(
        sorted(
            groups,
            key=lambda group: (
                -group.asset_count,
                group.name.casefold(),
            ),
        )
    )


def _largest_assets(
    assets: Iterable[AssetFile],
    limit: int,
) -> tuple[AssetFile, ...]:
    """Return the largest scanned assets."""
    return tuple(
        sorted(
            assets,
            key=lambda asset: (
                -asset.size_bytes,
                str(
                    asset.relative_path
                ).casefold(),
            ),
        )[:limit]
    )


def _recently_modified_assets(
    assets: Iterable[AssetFile],
    limit: int,
) -> tuple[AssetFile, ...]:
    """Return the most recently modified scanned assets."""
    return tuple(
        sorted(
            assets,
            key=lambda asset: (
                -asset.modified_at.timestamp(),
                str(
                    asset.relative_path
                ).casefold(),
            ),
        )[:limit]
    )


def build_asset_statistics(
    assets: Iterable[AssetFile],
    *,
    largest_limit: int = 10,
    recent_limit: int = 10,
) -> AssetStatistics:
    """
    Calculate project statistics from scanned assets.

    The original asset collection is not modified.
    """
    if largest_limit < 0:
        raise ValueError(
            "Largest-asset limit cannot be negative."
        )

    if recent_limit < 0:
        raise ValueError(
            "Recent-asset limit cannot be negative."
        )

    asset_records = tuple(
        assets
    )

    total_assets = len(
        asset_records
    )

    total_size_bytes = calculate_total_size(
        asset_records
    )

    average_size_bytes = (
        total_size_bytes // total_assets
        if total_assets
        else 0
    )

    category_groups = _build_groups(
        asset_records,
        group_name=lambda asset: str(
            asset.category
        ),
    )

    extension_groups = _build_groups(
        asset_records,
        group_name=lambda asset: (
            asset.extension
            if asset.extension
            else "No extension"
        ),
    )

    folder_groups = _build_groups(
        asset_records,
        group_name=_folder_name,
    )

    return AssetStatistics(
        total_assets=total_assets,
        total_size_bytes=total_size_bytes,
        average_size_bytes=average_size_bytes,
        category_groups=category_groups,
        extension_groups=extension_groups,
        folder_groups=folder_groups,
        largest_assets=_largest_assets(
            asset_records,
            largest_limit,
        ),
        recently_modified_assets=(
            _recently_modified_assets(
                asset_records,
                recent_limit,
            )
        ),
    )