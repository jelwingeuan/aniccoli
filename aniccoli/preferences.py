"""Persistent application preferences for Aniccoli."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aniccoli.organization_options import (
    DateGrouping,
    DateSource,
)


PREFERENCES_SCHEMA_VERSION = 1

DEFAULT_PREFERENCES_DIRECTORY = (
    Path.home()
    / ".aniccoli"
)

DEFAULT_PREFERENCES_PATH = (
    DEFAULT_PREFERENCES_DIRECTORY
    / "preferences.json"
)


@dataclass(frozen=True)
class AppPreferences:
    """Store settings that should remain between app sessions."""

    recursive_scan: bool = True
    date_grouping: DateGrouping = DateGrouping.NONE
    date_source: DateSource = DateSource.MODIFIED
    last_project_folder: str | None = None

    @property
    def last_project_path(self) -> Path | None:
        """Return the saved project folder as a Path."""
        if not self.last_project_folder:
            return None

        return Path(
            self.last_project_folder
        ).expanduser()


def _preferences_to_data(
    preferences: AppPreferences,
) -> dict[str, Any]:
    """Convert application preferences into JSON-compatible data."""
    data = asdict(
        preferences
    )

    data["schema_version"] = (
        PREFERENCES_SCHEMA_VERSION
    )

    data["date_grouping"] = (
        preferences.date_grouping.value
    )

    data["date_source"] = (
        preferences.date_source.value
    )

    return data


def save_preferences(
    preferences: AppPreferences,
    preferences_path: str | Path = DEFAULT_PREFERENCES_PATH,
) -> Path:
    """Save application preferences to a JSON file."""
    output_path = Path(
        preferences_path
    ).expanduser().resolve()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = output_path.with_suffix(
        f"{output_path.suffix}.tmp"
    )

    preference_data = _preferences_to_data(
        preferences
    )

    try:
        with temporary_path.open(
            mode="w",
            encoding="utf-8",
        ) as preferences_file:
            json.dump(
                preference_data,
                preferences_file,
                indent=2,
                ensure_ascii=False,
            )

            preferences_file.write(
                "\n"
            )

        temporary_path.replace(
            output_path
        )
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return output_path


def _read_boolean(
    data: dict[str, Any],
    key: str,
    default: bool,
) -> bool:
    """Read a strict Boolean preference."""
    value = data.get(
        key,
        default,
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    return default


def _read_date_grouping(
    data: dict[str, Any],
) -> DateGrouping:
    """Read and validate the saved date-grouping option."""
    value = data.get(
        "date_grouping",
        DateGrouping.NONE.value,
    )

    try:
        return DateGrouping(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return DateGrouping.NONE


def _read_date_source(
    data: dict[str, Any],
) -> DateSource:
    """Read and validate the saved date-source option."""
    value = data.get(
        "date_source",
        DateSource.MODIFIED.value,
    )

    try:
        return DateSource(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return DateSource.MODIFIED


def _read_last_project_folder(
    data: dict[str, Any],
) -> str | None:
    """Read and normalize the saved project-folder value."""
    value = data.get(
        "last_project_folder"
    )

    if not isinstance(
        value,
        str,
    ):
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    return cleaned_value


def load_preferences(
    preferences_path: str | Path = DEFAULT_PREFERENCES_PATH,
) -> AppPreferences:
    """
    Load saved application preferences.

    Missing, damaged, or unsupported preference files safely return the
    default settings instead of preventing Aniccoli from opening.
    """
    input_path = Path(
        preferences_path
    ).expanduser().resolve()

    if not input_path.exists():
        return AppPreferences()

    if not input_path.is_file():
        return AppPreferences()

    try:
        with input_path.open(
            mode="r",
            encoding="utf-8",
        ) as preferences_file:
            data = json.load(
                preferences_file
            )
    except (
        json.JSONDecodeError,
        PermissionError,
        OSError,
    ):
        return AppPreferences()

    if not isinstance(
        data,
        dict,
    ):
        return AppPreferences()

    return AppPreferences(
        recursive_scan=_read_boolean(
            data=data,
            key="recursive_scan",
            default=True,
        ),
        date_grouping=_read_date_grouping(
            data
        ),
        date_source=_read_date_source(
            data
        ),
        last_project_folder=(
            _read_last_project_folder(
                data
            )
        ),
    )


def update_preferences(
    current_preferences: AppPreferences,
    *,
    recursive_scan: bool | None = None,
    date_grouping: DateGrouping | None = None,
    date_source: DateSource | None = None,
    last_project_folder: str | Path | None = None,
    clear_last_project_folder: bool = False,
) -> AppPreferences:
    """Create updated preferences without changing the original object."""
    if clear_last_project_folder:
        resolved_last_project_folder = None
    elif last_project_folder is not None:
        resolved_last_project_folder = str(
            Path(
                last_project_folder
            ).expanduser().resolve()
        )
    else:
        resolved_last_project_folder = (
            current_preferences.last_project_folder
        )

    return AppPreferences(
        recursive_scan=(
            recursive_scan
            if recursive_scan is not None
            else current_preferences.recursive_scan
        ),
        date_grouping=(
            date_grouping
            if date_grouping is not None
            else current_preferences.date_grouping
        ),
        date_source=(
            date_source
            if date_source is not None
            else current_preferences.date_source
        ),
        last_project_folder=(
            resolved_last_project_folder
        ),
    )