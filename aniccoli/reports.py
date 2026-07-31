"""Asset inventory report-export tools for Aniccoli."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable

from aniccoli.organization_options import (
    OrganizationOptions,
    build_destination_folder,
)
from aniccoli.scanner import (
    AssetFile,
    calculate_total_size,
    format_file_size,
)


class ReportFormat(str, Enum):
    """Supported asset-report file formats."""

    JSON = "json"
    CSV = "csv"

    @property
    def file_extension(self) -> str:
        """Return the expected filename extension."""
        return f".{self.value}"

    def __str__(self) -> str:
        """Return the readable format name."""
        return self.value.upper()


@dataclass(frozen=True)
class AssetReportResult:
    """Store information about a completed report export."""

    report_path: Path
    report_format: ReportFormat
    asset_count: int
    total_size_bytes: int

    @property
    def total_size_text(self) -> str:
        """Return the exported asset size in readable form."""
        return format_file_size(
            self.total_size_bytes
        )


def _resolve_report_format(
    output_path: Path,
    report_format: ReportFormat | None,
) -> ReportFormat:
    """Determine the required report format."""
    if report_format is not None:
        return report_format

    suffix = output_path.suffix.lower()

    if suffix == ".json":
        return ReportFormat.JSON

    if suffix == ".csv":
        return ReportFormat.CSV

    raise ValueError(
        "The report filename must end with .json or .csv."
    )


def _apply_report_extension(
    output_path: Path,
    report_format: ReportFormat,
) -> Path:
    """Ensure the report path uses the correct extension."""
    expected_extension = report_format.file_extension

    if output_path.suffix.lower() == expected_extension:
        return output_path

    if output_path.suffix:
        return output_path.with_suffix(
            expected_extension
        )

    return output_path.with_name(
        f"{output_path.name}{expected_extension}"
    )


def _next_available_report_path(
    desired_path: Path,
) -> Path:
    """
    Find an unused report path without overwriting an existing file.

    Examples:
        asset_report.json
        asset_report_2.json
        asset_report_3.json
    """
    if not desired_path.exists():
        return desired_path

    parent_folder = desired_path.parent
    file_stem = desired_path.stem
    file_suffix = desired_path.suffix

    counter = 2

    while True:
        candidate_path = (
            parent_folder
            / f"{file_stem}_{counter}{file_suffix}"
        )

        if not candidate_path.exists():
            return candidate_path

        counter += 1


def _asset_record(
    asset: AssetFile,
    options: OrganizationOptions,
) -> dict[str, object]:
    """Convert one scanned asset into report-compatible data."""
    planned_destination = build_destination_folder(
        asset=asset,
        options=options,
    )

    return {
        "relative_path": str(
            asset.relative_path
        ),
        "file_name": asset.file_name,
        "extension": asset.extension,
        "category": str(
            asset.category
        ),
        "size_bytes": asset.size_bytes,
        "size_text": asset.size_text,
        "created_at": asset.created_at.isoformat(),
        "modified_at": asset.modified_at.isoformat(),
        "planned_destination": str(
            planned_destination
        ),
    }


def _category_summary(
    assets: Iterable[AssetFile],
) -> dict[str, int]:
    """Count exported assets by category."""
    category_counts = Counter(
        str(asset.category)
        for asset in assets
    )

    return dict(
        sorted(
            category_counts.items(),
            key=lambda item: item[0].lower(),
        )
    )


def _build_json_report(
    assets: tuple[AssetFile, ...],
    project_folder: Path | None,
    options: OrganizationOptions,
) -> dict[str, object]:
    """Build the complete JSON report structure."""
    total_size_bytes = calculate_total_size(
        assets
    )

    return {
        "schema_version": 1,
        "application": "Aniccoli",
        "report_type": "asset_inventory",
        "exported_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "project_folder": (
            str(project_folder)
            if project_folder is not None
            else None
        ),
        "organization_options": {
            "date_grouping": str(
                options.date_grouping
            ),
            "date_source": str(
                options.date_source
            ),
        },
        "summary": {
            "asset_count": len(
                assets
            ),
            "total_size_bytes": total_size_bytes,
            "total_size_text": format_file_size(
                total_size_bytes
            ),
            "category_count": len(
                _category_summary(
                    assets
                )
            ),
            "categories": _category_summary(
                assets
            ),
        },
        "assets": [
            _asset_record(
                asset=asset,
                options=options,
            )
            for asset in assets
        ],
    }


def _write_json_report(
    report_path: Path,
    assets: tuple[AssetFile, ...],
    project_folder: Path | None,
    options: OrganizationOptions,
) -> None:
    """Write an asset inventory report in JSON format."""
    report_data = _build_json_report(
        assets=assets,
        project_folder=project_folder,
        options=options,
    )

    with report_path.open(
        mode="w",
        encoding="utf-8",
    ) as report_file:
        json.dump(
            report_data,
            report_file,
            indent=2,
            ensure_ascii=False,
        )

        report_file.write(
            "\n"
        )


def _write_csv_report(
    report_path: Path,
    assets: tuple[AssetFile, ...],
    options: OrganizationOptions,
) -> None:
    """Write an asset inventory report in CSV format."""
    field_names = (
        "relative_path",
        "file_name",
        "extension",
        "category",
        "size_bytes",
        "size_text",
        "created_at",
        "modified_at",
        "planned_destination",
    )

    with report_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as report_file:
        writer = csv.DictWriter(
            report_file,
            fieldnames=field_names,
        )

        writer.writeheader()

        for asset in assets:
            writer.writerow(
                _asset_record(
                    asset=asset,
                    options=options,
                )
            )


def export_asset_report(
    output_path: str | Path,
    assets: Iterable[AssetFile],
    *,
    project_folder: str | Path | None = None,
    options: OrganizationOptions | None = None,
    report_format: ReportFormat | None = None,
    overwrite: bool = False,
) -> AssetReportResult:
    """
    Export scanned assets as a JSON or CSV inventory report.

    Args:
        output_path:
            Desired report filename.

        assets:
            Scanned asset records to include.

        project_folder:
            Optional project location included in JSON metadata.

        options:
            Organization rules used to calculate planned destinations.

        report_format:
            Explicit JSON or CSV format. When omitted, the format is
            inferred from the output filename extension.

        overwrite:
            When False, an existing report will not be overwritten.
            A numbered filename is created instead.

    Returns:
        Information about the generated report.
    """
    asset_records = tuple(
        assets
    )

    active_options = (
        options
        if options is not None
        else OrganizationOptions()
    )

    requested_path = Path(
        output_path
    ).expanduser()

    resolved_format = _resolve_report_format(
        output_path=requested_path,
        report_format=report_format,
    )

    report_path = _apply_report_extension(
        output_path=requested_path,
        report_format=resolved_format,
    ).resolve()

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if report_path.exists() and not overwrite:
        report_path = _next_available_report_path(
            report_path
        )

    resolved_project_folder = (
        Path(
            project_folder
        ).expanduser().resolve()
        if project_folder is not None
        else None
    )

    if resolved_format is ReportFormat.JSON:
        _write_json_report(
            report_path=report_path,
            assets=asset_records,
            project_folder=resolved_project_folder,
            options=active_options,
        )
    elif resolved_format is ReportFormat.CSV:
        _write_csv_report(
            report_path=report_path,
            assets=asset_records,
            options=active_options,
        )
    else:
        raise ValueError(
            f"Unsupported report format: {resolved_format}"
        )

    return AssetReportResult(
        report_path=report_path,
        report_format=resolved_format,
        asset_count=len(
            asset_records
        ),
        total_size_bytes=calculate_total_size(
            asset_records
        ),
    )