"""Asset health auditing tools for Aniccoli."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable

from aniccoli.scanner import (
    AssetFile,
    format_file_size,
)


class AuditSeverity(str, Enum):
    """Available severity levels for asset audit issues."""

    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"

    def __str__(self) -> str:
        """Return the readable severity name."""
        return self.value


class AuditIssueType(str, Enum):
    """Types of asset problems detected by Aniccoli."""

    EMPTY_FILE = "Empty file"
    LARGE_FILE = "Large file"
    DUPLICATE_NAME = "Duplicate filename"
    MISSING_EXTENSION = "Missing extension"
    STALE_FILE = "Stale file"

    def __str__(self) -> str:
        """Return the readable issue name."""
        return self.value


@dataclass(frozen=True)
class AssetAuditIssue:
    """Describe one problem found during an asset audit."""

    issue_type: AuditIssueType
    severity: AuditSeverity
    asset: AssetFile
    message: str
    related_paths: tuple[Path, ...] = ()

    @property
    def relative_path(self) -> Path:
        """Return the affected asset's project-relative path."""
        return self.asset.relative_path


@dataclass(frozen=True)
class AssetAuditReport:
    """Store the result of a complete asset health audit."""

    scanned_asset_count: int
    issues: tuple[AssetAuditIssue, ...]

    @property
    def issue_count(self) -> int:
        """Return the total number of detected issues."""
        return len(
            self.issues
        )

    @property
    def error_count(self) -> int:
        """Return the number of error-level issues."""
        return sum(
            1
            for issue in self.issues
            if issue.severity is AuditSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Return the number of warning-level issues."""
        return sum(
            1
            for issue in self.issues
            if issue.severity is AuditSeverity.WARNING
        )

    @property
    def info_count(self) -> int:
        """Return the number of informational issues."""
        return sum(
            1
            for issue in self.issues
            if issue.severity is AuditSeverity.INFO
        )

    @property
    def healthy_asset_count(self) -> int:
        """Return the number of assets with no detected problems."""
        affected_paths = {
            issue.asset.relative_path
            for issue in self.issues
        }

        return max(
            0,
            self.scanned_asset_count
            - len(
                affected_paths
            ),
        )

    @property
    def is_healthy(self) -> bool:
        """Return True when no issues were detected."""
        return not self.issues

    def issues_for_asset(
        self,
        asset: AssetFile,
    ) -> tuple[AssetAuditIssue, ...]:
        """Return all audit issues belonging to one asset."""
        return tuple(
            issue
            for issue in self.issues
            if issue.asset.relative_path
            == asset.relative_path
        )


def _severity_rank(
    severity: AuditSeverity,
) -> int:
    """Return a sorting rank for an audit severity."""
    ranks = {
        AuditSeverity.ERROR: 0,
        AuditSeverity.WARNING: 1,
        AuditSeverity.INFO: 2,
    }

    return ranks[
        severity
    ]


def _find_duplicate_filename_issues(
    assets: tuple[AssetFile, ...],
) -> list[AssetAuditIssue]:
    """Find assets that share the same filename."""
    grouped_assets: dict[
        str,
        list[AssetFile],
    ] = defaultdict(
        list
    )

    for asset in assets:
        grouped_assets[
            asset.file_name.casefold()
        ].append(
            asset
        )

    issues: list[
        AssetAuditIssue
    ] = []

    for matching_assets in grouped_assets.values():
        if len(
            matching_assets
        ) < 2:
            continue

        sorted_matches = sorted(
            matching_assets,
            key=lambda asset: str(
                asset.relative_path
            ).casefold(),
        )

        for asset in sorted_matches:
            related_paths = tuple(
                matching_asset.relative_path
                for matching_asset in sorted_matches
                if matching_asset.relative_path
                != asset.relative_path
            )

            issues.append(
                AssetAuditIssue(
                    issue_type=(
                        AuditIssueType.DUPLICATE_NAME
                    ),
                    severity=AuditSeverity.WARNING,
                    asset=asset,
                    message=(
                        f'The filename "{asset.file_name}" '
                        "is also used by another asset."
                    ),
                    related_paths=related_paths,
                )
            )

    return issues


def _find_individual_asset_issues(
    asset: AssetFile,
    *,
    large_file_threshold_bytes: int,
    stale_cutoff: datetime | None,
) -> list[AssetAuditIssue]:
    """Find health issues affecting one asset."""
    issues: list[
        AssetAuditIssue
    ] = []

    if asset.size_bytes == 0:
        issues.append(
            AssetAuditIssue(
                issue_type=AuditIssueType.EMPTY_FILE,
                severity=AuditSeverity.ERROR,
                asset=asset,
                message=(
                    "The file is empty and may be damaged "
                    "or incomplete."
                ),
            )
        )

    if (
        large_file_threshold_bytes > 0
        and asset.size_bytes
        >= large_file_threshold_bytes
    ):
        issues.append(
            AssetAuditIssue(
                issue_type=AuditIssueType.LARGE_FILE,
                severity=AuditSeverity.WARNING,
                asset=asset,
                message=(
                    f"The file is {asset.size_text}, which "
                    "meets or exceeds the audit threshold of "
                    f"{format_file_size(large_file_threshold_bytes)}."
                ),
            )
        )

    if not asset.extension:
        issues.append(
            AssetAuditIssue(
                issue_type=(
                    AuditIssueType.MISSING_EXTENSION
                ),
                severity=AuditSeverity.WARNING,
                asset=asset,
                message=(
                    "The file has no extension, so its type "
                    "may be difficult to identify."
                ),
            )
        )

    if (
        stale_cutoff is not None
        and asset.modified_at.timestamp()
        < stale_cutoff.timestamp()
    ):
        issues.append(
            AssetAuditIssue(
                issue_type=AuditIssueType.STALE_FILE,
                severity=AuditSeverity.WARNING,
                asset=asset,
                message=(
                    "The asset has not been modified since "
                    f"{asset.modified_at:%Y-%m-%d}."
                ),
            )
        )

    return issues


def audit_assets(
    assets: Iterable[AssetFile],
    *,
    large_file_threshold_bytes: int = (
        500 * 1024**2
    ),
    stale_after_days: int | None = 365,
    reference_time: datetime | None = None,
) -> AssetAuditReport:
    """
    Audit scanned assets and return detected health issues.

    Args:
        assets:
            Scanned assets to inspect.

        large_file_threshold_bytes:
            Files at or above this size receive a large-file warning.
            Set the value to zero to disable the check.

        stale_after_days:
            Files older than this number of days receive a stale-file
            warning. Set it to None to disable the check.

        reference_time:
            Time used to calculate stale files. The current time is used
            when this value is omitted.
    """
    if large_file_threshold_bytes < 0:
        raise ValueError(
            "Large-file threshold cannot be negative."
        )

    if (
        stale_after_days is not None
        and stale_after_days < 0
    ):
        raise ValueError(
            "Stale-file age cannot be negative."
        )

    asset_records = tuple(
        assets
    )

    active_reference_time = (
        reference_time
        if reference_time is not None
        else datetime.now()
    )

    stale_cutoff = (
        active_reference_time
        - timedelta(
            days=stale_after_days,
        )
        if stale_after_days is not None
        else None
    )

    issues: list[
        AssetAuditIssue
    ] = []

    for asset in asset_records:
        issues.extend(
            _find_individual_asset_issues(
                asset=asset,
                large_file_threshold_bytes=(
                    large_file_threshold_bytes
                ),
                stale_cutoff=stale_cutoff,
            )
        )

    issues.extend(
        _find_duplicate_filename_issues(
            asset_records
        )
    )

    sorted_issues = tuple(
        sorted(
            issues,
            key=lambda issue: (
                _severity_rank(
                    issue.severity
                ),
                str(
                    issue.issue_type
                ).casefold(),
                str(
                    issue.asset.relative_path
                ).casefold(),
            ),
        )
    )

    return AssetAuditReport(
        scanned_asset_count=len(
            asset_records
        ),
        issues=sorted_issues,
    )