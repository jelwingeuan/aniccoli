"""Asset search and filtering tools for Aniccoli."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from aniccoli.categories import AssetCategory
from aniccoli.scanner import AssetFile


@dataclass(frozen=True)
class AssetFilter:
    """Store the active search and filtering options."""

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

    def __post_init__(self) -> None:
        """Normalize and validate the supplied filter values."""
        normalized_search_text = (
            self.search_text
            .strip()
            .lower()
        )

        normalized_categories = frozenset(
            self.categories
        )

        normalized_extensions = frozenset(
            _normalize_extension(extension)
            for extension in self.extensions
            if extension.strip()
        )

        object.__setattr__(
            self,
            "search_text",
            normalized_search_text,
        )

        object.__setattr__(
            self,
            "categories",
            normalized_categories,
        )

        object.__setattr__(
            self,
            "extensions",
            normalized_extensions,
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

    @property
    def has_active_filters(self) -> bool:
        """Return True when at least one filter is active."""
        return any(
            (
                bool(self.search_text),
                bool(self.categories),
                bool(self.extensions),
                self.minimum_size_bytes is not None,
                self.maximum_size_bytes is not None,
                self.modified_after is not None,
                self.modified_before is not None,
            )
        )


@dataclass(frozen=True)
class AssetFilterResult:
    """Store the result of filtering scanned assets."""

    matched_assets: tuple[AssetFile, ...]
    total_count: int

    @property
    def matched_count(self) -> int:
        """Return the number of assets matching the filters."""
        return len(self.matched_assets)

    @property
    def hidden_count(self) -> int:
        """Return the number of assets hidden by the filters."""
        return self.total_count - self.matched_count

    @property
    def has_matches(self) -> bool:
        """Return True when at least one asset matched."""
        return self.matched_count > 0


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


def _build_searchable_text(
    asset: AssetFile,
) -> str:
    """Build searchable text from an asset's information."""
    searchable_parts = (
        asset.file_name,
        str(asset.relative_path),
        asset.extension,
        str(asset.category),
        str(asset.destination),
    )

    return " ".join(
        searchable_parts
    ).lower()


def _matches_search_text(
    asset: AssetFile,
    search_text: str,
) -> bool:
    """Return True when every search word matches the asset."""
    if not search_text:
        return True

    searchable_text = _build_searchable_text(
        asset
    )

    search_words = (
        word
        for word in search_text.split()
        if word
    )

    return all(
        word in searchable_text
        for word in search_words
    )


def _matches_categories(
    asset: AssetFile,
    categories: frozenset[AssetCategory],
) -> bool:
    """Return True when the asset matches the category filter."""
    if not categories:
        return True

    return asset.category in categories


def _matches_extensions(
    asset: AssetFile,
    extensions: frozenset[str],
) -> bool:
    """Return True when the asset matches the extension filter."""
    if not extensions:
        return True

    return asset.extension.lower() in extensions


def _matches_file_size(
    asset: AssetFile,
    minimum_size_bytes: int | None,
    maximum_size_bytes: int | None,
) -> bool:
    """Return True when the asset is within the selected size range."""
    if (
        minimum_size_bytes is not None
        and asset.size_bytes < minimum_size_bytes
    ):
        return False

    if (
        maximum_size_bytes is not None
        and asset.size_bytes > maximum_size_bytes
    ):
        return False

    return True


def _matches_modified_date(
    asset: AssetFile,
    modified_after: datetime | None,
    modified_before: datetime | None,
) -> bool:
    """Return True when the modification date matches the range."""
    try:
        if (
            modified_after is not None
            and asset.modified_at < modified_after
        ):
            return False

        if (
            modified_before is not None
            and asset.modified_at > modified_before
        ):
            return False
    except TypeError as error:
        raise ValueError(
            "Asset and filter dates must use compatible "
            "datetime values."
        ) from error

    return True


def asset_matches_filter(
    asset: AssetFile,
    asset_filter: AssetFilter,
) -> bool:
    """Return True when an asset passes every active filter."""
    return all(
        (
            _matches_search_text(
                asset,
                asset_filter.search_text,
            ),
            _matches_categories(
                asset,
                asset_filter.categories,
            ),
            _matches_extensions(
                asset,
                asset_filter.extensions,
            ),
            _matches_file_size(
                asset,
                asset_filter.minimum_size_bytes,
                asset_filter.maximum_size_bytes,
            ),
            _matches_modified_date(
                asset,
                asset_filter.modified_after,
                asset_filter.modified_before,
            ),
        )
    )


def filter_assets(
    assets: Iterable[AssetFile],
    asset_filter: AssetFilter | None = None,
) -> AssetFilterResult:
    """
    Filter scanned assets while preserving their existing order.

    When no filter is supplied, every asset is returned.
    """
    asset_list = list(
        assets
    )

    active_filter = (
        asset_filter
        if asset_filter is not None
        else AssetFilter()
    )

    matched_assets = tuple(
        asset
        for asset in asset_list
        if asset_matches_filter(
            asset,
            active_filter,
        )
    )

    return AssetFilterResult(
        matched_assets=matched_assets,
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


from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from aniccoli.categories import AssetCategory
from aniccoli.scanner import AssetFile


@dataclass(frozen=True)
class AssetFilter:
    """Store the active search and filtering options."""

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

    def __post_init__(self) -> None:
        """Normalize and validate the supplied filter values."""
        normalized_search_text = (
            self.search_text
            .strip()
            .lower()
        )

        normalized_categories = frozenset(
            self.categories
        )

        normalized_extensions = frozenset(
            _normalize_extension(extension)
            for extension in self.extensions
            if extension.strip()
        )

        object.__setattr__(
            self,
            "search_text",
            normalized_search_text,
        )

        object.__setattr__(
            self,
            "categories",
            normalized_categories,
        )

        object.__setattr__(
            self,
            "extensions",
            normalized_extensions,
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

    @property
    def has_active_filters(self) -> bool:
        """Return True when at least one filter is active."""
        return any(
            (
                bool(self.search_text),
                bool(self.categories),
                bool(self.extensions),
                self.minimum_size_bytes is not None,
                self.maximum_size_bytes is not None,
                self.modified_after is not None,
                self.modified_before is not None,
            )
        )


@dataclass(frozen=True)
class AssetFilterResult:
    """Store the result of filtering scanned assets."""

    matched_assets: tuple[AssetFile, ...]
    total_count: int

    @property
    def matched_count(self) -> int:
        """Return the number of assets matching the filters."""
        return len(self.matched_assets)

    @property
    def hidden_count(self) -> int:
        """Return the number of assets hidden by the filters."""
        return self.total_count - self.matched_count

    @property
    def has_matches(self) -> bool:
        """Return True when at least one asset matched."""
        return self.matched_count > 0


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


def _build_searchable_text(
    asset: AssetFile,
) -> str:
    """Build searchable text from an asset's information."""
    searchable_parts = (
        asset.file_name,
        str(asset.relative_path),
        asset.extension,
        str(asset.category),
        str(asset.destination),
    )

    return " ".join(
        searchable_parts
    ).lower()


def _matches_search_text(
    asset: AssetFile,
    search_text: str,
) -> bool:
    """Return True when every search word matches the asset."""
    if not search_text:
        return True

    searchable_text = _build_searchable_text(
        asset
    )

    search_words = (
        word
        for word in search_text.split()
        if word
    )

    return all(
        word in searchable_text
        for word in search_words
    )


def _matches_categories(
    asset: AssetFile,
    categories: frozenset[AssetCategory],
) -> bool:
    """Return True when the asset matches the category filter."""
    if not categories:
        return True

    return asset.category in categories


def _matches_extensions(
    asset: AssetFile,
    extensions: frozenset[str],
) -> bool:
    """Return True when the asset matches the extension filter."""
    if not extensions:
        return True

    return asset.extension.lower() in extensions


def _matches_file_size(
    asset: AssetFile,
    minimum_size_bytes: int | None,
    maximum_size_bytes: int | None,
) -> bool:
    """Return True when the asset is within the selected size range."""
    if (
        minimum_size_bytes is not None
        and asset.size_bytes < minimum_size_bytes
    ):
        return False

    if (
        maximum_size_bytes is not None
        and asset.size_bytes > maximum_size_bytes
    ):
        return False

    return True


def _matches_modified_date(
    asset: AssetFile,
    modified_after: datetime | None,
    modified_before: datetime | None,
) -> bool:
    """Return True when the modification date matches the range."""
    try:
        if (
            modified_after is not None
            and asset.modified_at < modified_after
        ):
            return False

        if (
            modified_before is not None
            and asset.modified_at > modified_before
        ):
            return False
    except TypeError as error:
        raise ValueError(
            "Asset and filter dates must use compatible "
            "datetime values."
        ) from error

    return True


def asset_matches_filter(
    asset: AssetFile,
    asset_filter: AssetFilter,
) -> bool:
    """Return True when an asset passes every active filter."""
    return all(
        (
            _matches_search_text(
                asset,
                asset_filter.search_text,
            ),
            _matches_categories(
                asset,
                asset_filter.categories,
            ),
            _matches_extensions(
                asset,
                asset_filter.extensions,
            ),
            _matches_file_size(
                asset,
                asset_filter.minimum_size_bytes,
                asset_filter.maximum_size_bytes,
            ),
            _matches_modified_date(
                asset,
                asset_filter.modified_after,
                asset_filter.modified_before,
            ),
        )
    )


def filter_assets(
    assets: Iterable[AssetFile],
    asset_filter: AssetFilter | None = None,
) -> AssetFilterResult:
    """
    Filter scanned assets while preserving their existing order.

    When no filter is supplied, every asset is returned.
    """
    asset_list = list(
        assets
    )

    active_filter = (
        asset_filter
        if asset_filter is not None
        else AssetFilter()
    )

    matched_assets = tuple(
        asset
        for asset in asset_list
        if asset_matches_filter(
            asset,
            active_filter,
        )
    )

    return AssetFilterResult(
        matched_assets=matched_assets,
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