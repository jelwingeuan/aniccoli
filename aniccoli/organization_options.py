"""Configurable organization rules for Aniccoli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable

from aniccoli.scanner import AssetFile


class DateGrouping(str, Enum):
    """Available date-based folder structures."""

    NONE = "No date grouping"
    YEAR = "Year"
    YEAR_MONTH = "Year and month"

    def __str__(self) -> str:
        """Return the readable option name."""
        return self.value


class DateSource(str, Enum):
    """File date used when creating date folders."""

    CREATED = "Creation date"
    MODIFIED = "Modification date"

    def __str__(self) -> str:
        """Return the readable option name."""
        return self.value


@dataclass(frozen=True)
class OrganizationOptions:
    """Store configurable rules used when organizing assets."""

    date_grouping: DateGrouping = DateGrouping.NONE
    date_source: DateSource = DateSource.MODIFIED

    @property
    def uses_date_grouping(self) -> bool:
        """Return True when files should be grouped by date."""
        return self.date_grouping is not DateGrouping.NONE


@dataclass(frozen=True)
class DestinationPreview:
    """Store one asset and its calculated destination folder."""

    asset: AssetFile
    destination_folder: Path


def select_asset_datetime(
    asset: AssetFile,
    date_source: DateSource,
) -> datetime:
    """Return the selected date value from an asset record."""
    if date_source is DateSource.CREATED:
        return asset.created_at

    if date_source is DateSource.MODIFIED:
        return asset.modified_at

    raise ValueError(
        f"Unsupported date source: {date_source}"
    )


def build_date_subfolder(
    asset: AssetFile,
    options: OrganizationOptions,
) -> Path:
    """
    Build the optional date portion of an asset destination.

    Examples:
        No date grouping:
            Path("")

        Year:
            Path("2026")

        Year and month:
            Path("2026") / "07_July"
    """
    if options.date_grouping is DateGrouping.NONE:
        return Path()

    asset_date = select_asset_datetime(
        asset=asset,
        date_source=options.date_source,
    )

    year_folder = str(
        asset_date.year
    )

    if options.date_grouping is DateGrouping.YEAR:
        return Path(
            year_folder
        )

    if options.date_grouping is DateGrouping.YEAR_MONTH:
        month_folder = (
            f"{asset_date.month:02d}_"
            f"{asset_date.strftime('%B')}"
        )

        return (
            Path(year_folder)
            / month_folder
        )

    raise ValueError(
        "Unsupported date-grouping option: "
        f"{options.date_grouping}"
    )


def build_destination_folder(
    asset: AssetFile,
    options: OrganizationOptions,
) -> Path:
    """
    Calculate the final relative destination folder for an asset.

    The existing category destination is always preserved. Date folders
    are appended only when date grouping is enabled.
    """
    base_destination = asset.destination

    if not options.uses_date_grouping:
        return base_destination

    date_subfolder = build_date_subfolder(
        asset=asset,
        options=options,
    )

    return (
        base_destination
        / date_subfolder
    )


def build_destination_previews(
    assets: Iterable[AssetFile],
    options: OrganizationOptions,
) -> tuple[DestinationPreview, ...]:
    """Calculate destination folders for multiple scanned assets."""
    previews = (
        DestinationPreview(
            asset=asset,
            destination_folder=build_destination_folder(
                asset=asset,
                options=options,
            ),
        )
        for asset in assets
    )

    return tuple(
        sorted(
            previews,
            key=lambda preview: str(
                preview.asset.relative_path
            ).lower(),
        )
    )