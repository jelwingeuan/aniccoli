"""Searching, filtering and sorting through the single AssetQuery."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from aniccoli.categories import AssetCategory
from aniccoli.filters import (
    AssetQuery,
    FolderMatchMode,
    SortDirection,
    SortField,
    collect_available_folders,
    query_assets,
)
from aniccoli.scanner import AssetFile


NOW = datetime(2026, 10, 25, 12, 0)


def asset(relative: str, category: AssetCategory, size: int, days_old: int) -> AssetFile:
    path = Path(relative)
    return AssetFile(
        source_path=Path("/project") / path,
        relative_path=path,
        file_name=path.name,
        extension=path.suffix.lower(),
        category=category,
        destination=Path("Sorted") / path.name,
        size_bytes=size,
        created_at=NOW - timedelta(days=days_old + 1),
        modified_at=NOW - timedelta(days=days_old),
    )


ASSETS = [
    asset("hero.fbx", AssetCategory.FBX, 3_000, 2),
    asset("characters/hero_normal.png", AssetCategory.TEXTURE_NORMAL, 1_000, 10),
    asset("characters/villain/villain.fbx", AssetCategory.FBX, 5_000, 40),
    asset("Audio/forest.WAV", AssetCategory.AUDIO, 9_000, 1),
]


def names(query: AssetQuery) -> list[str]:
    return [found.file_name for found in query_assets(ASSETS, query).matched]


def test_empty_query_returns_everything_sorted_by_name() -> None:
    result = query_assets(ASSETS)
    assert [found.file_name for found in result.matched] == [
        "forest.WAV", "hero.fbx", "hero_normal.png", "villain.fbx",
    ]
    assert result.total_count == 4


def test_each_criterion_on_its_own() -> None:
    assert names(AssetQuery(search_text="  HERO ")) == ["hero.fbx", "hero_normal.png"]
    assert names(AssetQuery(search_text="characters fbx")) == ["villain.fbx"]
    assert names(AssetQuery(categories=frozenset({AssetCategory.FBX}))) == ["hero.fbx", "villain.fbx"]
    assert names(AssetQuery(extensions=frozenset({"WAV"}))) == ["forest.WAV"]
    assert names(AssetQuery(minimum_size_bytes=3_000, maximum_size_bytes=5_000)) == ["hero.fbx", "villain.fbx"]
    assert names(AssetQuery(modified_after=NOW - timedelta(days=5))) == ["forest.WAV", "hero.fbx"]
    assert names(AssetQuery(modified_before=NOW - timedelta(days=5))) == ["hero_normal.png", "villain.fbx"]


def test_criteria_combine_and_total_counts_everything() -> None:
    result = query_assets(
        ASSETS,
        AssetQuery(
            categories=frozenset({AssetCategory.FBX}),
            folder=Path("characters"),
            sort_field=SortField.SIZE,
        ),
    )
    assert [found.file_name for found in result.matched] == ["villain.fbx"]
    assert result.total_count == 4


def test_folder_modes() -> None:
    assert names(AssetQuery(folder=Path("characters"))) == ["hero_normal.png", "villain.fbx"]
    assert names(AssetQuery(folder=Path("characters"), folder_match_mode=FolderMatchMode.EXACT_FOLDER)) == ["hero_normal.png"]
    assert names(AssetQuery(folder=Path("."), folder_match_mode=FolderMatchMode.EXACT_FOLDER)) == ["hero.fbx"]
    assert len(names(AssetQuery(folder=Path(".")))) == 4
    assert collect_available_folders(ASSETS) == (
        Path("."), Path("Audio"), Path("characters"), Path("characters/villain"),
    )


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (SortField.NAME, ["forest.WAV", "hero.fbx", "hero_normal.png", "villain.fbx"]),
        # Ties break on the relative path, so characters/villain/ comes first.
        (SortField.CATEGORY, ["forest.WAV", "villain.fbx", "hero.fbx", "hero_normal.png"]),
        (SortField.EXTENSION, ["villain.fbx", "hero.fbx", "hero_normal.png", "forest.WAV"]),
        (SortField.SIZE, ["hero_normal.png", "hero.fbx", "villain.fbx", "forest.WAV"]),
        (SortField.CREATED, ["villain.fbx", "hero_normal.png", "hero.fbx", "forest.WAV"]),
        (SortField.MODIFIED, ["villain.fbx", "hero_normal.png", "hero.fbx", "forest.WAV"]),
    ],
)
def test_sort_fields_and_directions(field: SortField, expected: list[str]) -> None:
    assert names(AssetQuery(sort_field=field)) == expected
    assert names(AssetQuery(sort_field=field, sort_direction=SortDirection.DESCENDING)) == expected[::-1]


@pytest.mark.parametrize(
    "bad_query",
    [
        dict(minimum_size_bytes=-1),
        dict(maximum_size_bytes=-1),
        dict(minimum_size_bytes=10, maximum_size_bytes=5),
        dict(modified_after=NOW, modified_before=NOW - timedelta(days=1)),
        dict(folder=Path("/absolute")),
        dict(folder=Path("../outside")),
    ],
)
def test_invalid_queries_raise(bad_query: dict) -> None:
    with pytest.raises(ValueError):
        AssetQuery(**bad_query)
