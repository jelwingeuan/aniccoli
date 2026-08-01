"""Asset sorting tools for Aniccoli."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

from aniccoli.scanner import AssetFile


class SortField(str, Enum):
    """Available asset properties used for sorting."""

    NAME = "File name"
    CATEGORY = "Category"
    EXTENSION = "Extension"
    SIZE = "File size"
    CREATED = "Creation date"
    MODIFIED = "Modification date"

    def __str__(self) -> str:
        """Return the readable option name."""
        return self.value


class SortDirection(str, Enum):
    """Available sorting directions."""

    ASCENDING = "Ascending"
    DESCENDING = "Descending"

    def __str__(self) -> str:
        """Return the readable option name."""
        return self.value


@dataclass(frozen=True)
class AssetSortOptions:
    """Store the selected field and direction for asset sorting."""

    field: SortField = SortField.NAME
    direction: SortDirection = SortDirection.ASCENDING

    @property
    def reverse(self) -> bool:
        """Return True when sorting should use descending order."""
        return self.direction is SortDirection.DESCENDING


SortKey = Callable[[AssetFile], object]


def _name_key(asset: AssetFile) -> tuple[str, str]:
    """Return a case-insensitive filename sorting key."""
    return (
        asset.file_name.casefold(),
        str(asset.relative_path).casefold(),
    )


def _category_key(asset: AssetFile) -> tuple[str, str]:
    """Return a category sorting key."""
    return (
        str(asset.category).casefold(),
        str(asset.relative_path).casefold(),
    )


def _extension_key(asset: AssetFile) -> tuple[str, str]:
    """Return an extension sorting key."""
    return (
        asset.extension.casefold(),
        str(asset.relative_path).casefold(),
    )


def _size_key(asset: AssetFile) -> tuple[int, str]:
    """Return a file-size sorting key."""
    return (
        asset.size_bytes,
        str(asset.relative_path).casefold(),
    )


def _created_key(asset: AssetFile) -> tuple[float, str]:
    """Return a creation-date sorting key."""
    return (
        asset.created_at.timestamp(),
        str(asset.relative_path).casefold(),
    )


def _modified_key(asset: AssetFile) -> tuple[float, str]:
    """Return a modification-date sorting key."""
    return (
        asset.modified_at.timestamp(),
        str(asset.relative_path).casefold(),
    )


def _select_sort_key(field: SortField) -> SortKey:
    """Return the correct sorting function for a selected field."""
    sort_keys: dict[SortField, SortKey] = {
        SortField.NAME: _name_key,
        SortField.CATEGORY: _category_key,
        SortField.EXTENSION: _extension_key,
        SortField.SIZE: _size_key,
        SortField.CREATED: _created_key,
        SortField.MODIFIED: _modified_key,
    }

    try:
        return sort_keys[field]
    except KeyError as error:
        raise ValueError(
            f"Unsupported asset sort field: {field}"
        ) from error


def sort_assets(
    assets: Iterable[AssetFile],
    options: AssetSortOptions | None = None,
) -> tuple[AssetFile, ...]:
    """
    Return assets sorted according to the selected options.

    The original collection is not changed. When no options are supplied,
    assets are sorted by filename in ascending order.
    """
    active_options = (
        options
        if options is not None
        else AssetSortOptions()
    )

    sort_key = _select_sort_key(
        active_options.field
    )

    return tuple(
        sorted(
            assets,
            key=sort_key,
            reverse=active_options.reverse,
        )
    )


def collect_parent_folders(
    assets: Iterable[AssetFile],
) -> tuple[Path, ...]:
    """Return the unique parent folders present in scanned assets."""
    parent_folders = {
        asset.relative_path.parent
        for asset in assets
    }

    return tuple(
        sorted(
            parent_folders,
            key=lambda folder: str(folder).casefold(),
        )
    )