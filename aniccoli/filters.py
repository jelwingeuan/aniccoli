"""Asset search, filtering and sorting for Aniccoli.

One AssetQuery describes everything the results list can narrow or order
by; query_assets applies all of it in one place.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from aniccoli.categories import AssetCategory
from aniccoli.scanner import AssetFile


class FolderMatchMode(str, Enum):
    """Control how assets are matched against a selected folder."""

    EXACT_FOLDER = "Selected folder only"
    INCLUDE_SUBFOLDERS = "Include subfolders"

    def __str__(self) -> str:
        """Return the readable option name."""
        return self.value


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
class AssetQuery:
    """Everything that narrows and orders the scanned assets."""

    search_text: str = ""

    categories: frozenset[AssetCategory] = field(
        default_factory=frozenset
    )

    extensions: frozenset[str] = field(
        default_factory=frozenset
    )

    minimum_size_bytes: int | None = None
    maximum_size_bytes: int | None = None

    modified_after: datetime | None = None
    modified_before: datetime | None = None

    folder: Path | None = None
    folder_match_mode: FolderMatchMode = (
        FolderMatchMode.INCLUDE_SUBFOLDERS
    )

    sort_field: SortField = SortField.NAME
    sort_direction: SortDirection = SortDirection.ASCENDING

    def __post_init__(self) -> None:
        """Normalize and validate the supplied query values."""
        object.__setattr__(
            self,
            "search_text",
            self.search_text.strip().lower(),
        )

        object.__setattr__(
            self,
            "categories",
            frozenset(self.categories),
        )

        object.__setattr__(
            self,
            "extensions",
            frozenset(
                _normalize_extension(extension)
                for extension in self.extensions
                if extension.strip()
            ),
        )

        if self.folder is not None:
            object.__setattr__(
                self,
                "folder",
                _normalize_relative_folder(
                    self.folder
                ),
            )

        self._validate_sizes()
        self._validate_dates()

    def _validate_sizes(self) -> None:
        """Validate minimum and maximum file-size filters."""
        if (
            self.minimum_size_bytes is not None
            and self.minimum_size_bytes < 0
        ):
            raise ValueError(
                "Minimum file size cannot be negative."
            )

        if (
            self.maximum_size_bytes is not None
            and self.maximum_size_bytes < 0
        ):
            raise ValueError(
                "Maximum file size cannot be negative."
            )

        if (
            self.minimum_size_bytes is not None
            and self.maximum_size_bytes is not None
            and self.minimum_size_bytes
            > self.maximum_size_bytes
        ):
            raise ValueError(
                "Minimum file size cannot be greater "
                "than maximum file size."
            )

    def _validate_dates(self) -> None:
        """Validate modification-date filters."""
        if (
            self.modified_after is not None
            and self.modified_before is not None
        ):
            try:
                invalid_date_range = (
                    self.modified_after
                    > self.modified_before
                )
            except TypeError as error:
                raise ValueError(
                    "Modification date filters must use "
                    "compatible datetime values."
                ) from error

            if invalid_date_range:
                raise ValueError(
                    "Modified-after date cannot be later "
                    "than modified-before date."
                )


@dataclass(frozen=True)
class QueryResult:
    """The assets that matched a query, in query order."""

    matched: tuple[AssetFile, ...]
    total_count: int


def query_assets(
    assets: Iterable[AssetFile],
    query: AssetQuery | None = None,
) -> QueryResult:
    """Return the assets that match every criterion, sorted as asked."""
    active_query = (
        query
        if query is not None
        else AssetQuery()
    )

    asset_list = list(
        assets
    )

    matched = [
        asset
        for asset in asset_list
        if _matches(
            asset,
            active_query,
        )
    ]

    matched.sort(
        key=_SORT_KEYS[active_query.sort_field],
        reverse=(
            active_query.sort_direction
            is SortDirection.DESCENDING
        ),
    )

    return QueryResult(
        matched=tuple(matched),
        total_count=len(asset_list),
    )


def collect_available_categories(
    assets: Iterable[AssetFile],
) -> tuple[AssetCategory, ...]:
    """Return categories currently present in the scanned assets."""
    categories = {
        asset.category
        for asset in assets
    }

    return tuple(
        sorted(
            categories,
            key=lambda category: (
                category.value.lower()
            ),
        )
    )


def collect_available_extensions(
    assets: Iterable[AssetFile],
) -> tuple[str, ...]:
    """Return file extensions currently present in scanned assets."""
    extensions = {
        asset.extension.lower()
        for asset in assets
        if asset.extension
    }

    return tuple(
        sorted(extensions)
    )


def collect_available_folders(
    assets: Iterable[AssetFile],
) -> tuple[Path, ...]:
    """Return every unique parent folder found in scanned assets."""
    available_folders = {
        _normalize_relative_folder(
            asset.relative_path.parent
        )
        for asset in assets
    }

    return tuple(
        sorted(
            available_folders,
            key=lambda folder: (
                folder != Path("."),
                str(folder).casefold(),
            ),
        )
    )


def _matches(
    asset: AssetFile,
    query: AssetQuery,
) -> bool:
    """Return True when an asset passes every criterion of the query."""
    if query.search_text:
        searchable_text = " ".join(
            (
                asset.file_name,
                str(asset.relative_path),
                asset.extension,
                str(asset.category),
                str(asset.destination),
            )
        ).lower()

        if not all(
            word in searchable_text
            for word in query.search_text.split()
        ):
            return False

    if (
        query.categories
        and asset.category not in query.categories
    ):
        return False

    if (
        query.extensions
        and asset.extension.lower() not in query.extensions
    ):
        return False

    if (
        query.minimum_size_bytes is not None
        and asset.size_bytes < query.minimum_size_bytes
    ):
        return False

    if (
        query.maximum_size_bytes is not None
        and asset.size_bytes > query.maximum_size_bytes
    ):
        return False

    try:
        if (
            query.modified_after is not None
            and asset.modified_at < query.modified_after
        ):
            return False

        if (
            query.modified_before is not None
            and asset.modified_at > query.modified_before
        ):
            return False
    except TypeError as error:
        raise ValueError(
            "Asset and filter dates must use compatible "
            "datetime values."
        ) from error

    if query.folder is not None:
        asset_folder = _normalize_relative_folder(
            asset.relative_path.parent
        )

        if query.folder_match_mode is FolderMatchMode.EXACT_FOLDER:
            return asset_folder == query.folder

        return (
            query.folder == Path(".")
            or asset_folder.is_relative_to(query.folder)
        )

    return True


def _normalize_extension(extension: str) -> str:
    """Convert an extension into lowercase dot-prefixed form."""
    normalized_extension = (
        extension
        .strip()
        .lower()
    )

    if not normalized_extension:
        return ""

    if not normalized_extension.startswith("."):
        normalized_extension = (
            f".{normalized_extension}"
        )

    return normalized_extension


def _normalize_relative_folder(
    folder: str | Path,
) -> Path:
    """Return a safe project-relative folder path."""
    normalized_folder = Path(
        folder
    )

    if normalized_folder.is_absolute():
        raise ValueError(
            "The folder filter must be relative to the project."
        )

    normalized_parts = tuple(
        part
        for part in normalized_folder.parts
        if part not in (
            "",
            ".",
        )
    )

    if ".." in normalized_parts:
        raise ValueError(
            "The folder filter cannot leave the project folder."
        )

    if not normalized_parts:
        return Path(".")

    return Path(
        *normalized_parts
    )


def _path_key(asset: AssetFile) -> str:
    """Return the tie-breaking key shared by every sort order."""
    return str(asset.relative_path).casefold()


_SORT_KEYS: dict[SortField, Callable[[AssetFile], object]] = {
    SortField.NAME: lambda asset: (
        asset.file_name.casefold(),
        _path_key(asset),
    ),
    SortField.CATEGORY: lambda asset: (
        str(asset.category).casefold(),
        _path_key(asset),
    ),
    SortField.EXTENSION: lambda asset: (
        asset.extension.casefold(),
        _path_key(asset),
    ),
    SortField.SIZE: lambda asset: (
        asset.size_bytes,
        _path_key(asset),
    ),
    SortField.CREATED: lambda asset: (
        asset.created_at.timestamp(),
        _path_key(asset),
    ),
    SortField.MODIFIED: lambda asset: (
        asset.modified_at.timestamp(),
        _path_key(asset),
    ),
}
