"""Organization planning for Aniccoli; moves run through aniccoli.moves."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aniccoli.moves import Move
from aniccoli.organization_options import (
    OrganizationOptions,
    build_destination_folder,
)
from aniccoli.scanner import AssetFile


@dataclass(frozen=True)
class PlannedMove:
    """Represent one planned file movement."""

    asset: AssetFile
    destination_path: Path
    renamed_for_conflict: bool

    @property
    def source_path(self) -> Path:
        """Return the current source path."""
        return self.asset.source_path

    @property
    def planned_file_name(self) -> str:
        """Return the filename that will be used after organization."""
        return self.destination_path.name

    def as_move(self) -> Move:
        """Return this planned movement for aniccoli.moves.apply_moves."""
        return Move(
            source=self.source_path,
            destination=self.destination_path,
            details={
                "category": str(self.asset.category),
                "renamed_for_conflict": self.renamed_for_conflict,
            },
        )


def _next_available_path(
    desired_path: Path,
    reserved_paths: set[Path],
) -> tuple[Path, bool]:
    """
    Find an available destination without overwriting another file.

    For example, when hero.fbx already exists, the function tries:

        hero_2.fbx
        hero_3.fbx
        hero_4.fbx
    """
    normalized_desired_path = desired_path.resolve()

    if (
        not normalized_desired_path.exists()
        and normalized_desired_path not in reserved_paths
    ):
        return normalized_desired_path, False

    parent_folder = normalized_desired_path.parent
    file_stem = normalized_desired_path.stem
    file_suffix = normalized_desired_path.suffix

    counter = 2

    while True:
        candidate_path = (
            parent_folder
            / f"{file_stem}_{counter}{file_suffix}"
        ).resolve()

        if (
            not candidate_path.exists()
            and candidate_path not in reserved_paths
        ):
            return candidate_path, True

        counter += 1


def build_organization_plan(
    project_folder: str | Path,
    assets: Iterable[AssetFile],
    *,
    options: OrganizationOptions | None = None,
) -> list[PlannedMove]:
    """
    Create a safe organization plan without moving any files.

    Files already located in their correct destination are skipped.
    Filename conflicts are resolved by creating a new filename.

    When no organization options are provided, Aniccoli keeps its
    existing category-only folder structure.
    """
    root_folder = Path(
        project_folder
    ).expanduser().resolve()

    if not root_folder.exists():
        raise FileNotFoundError(
            f"The project folder does not exist: {root_folder}"
        )

    if not root_folder.is_dir():
        raise NotADirectoryError(
            f"The project path is not a folder: {root_folder}"
        )

    active_options = (
        options
        if options is not None
        else OrganizationOptions()
    )

    planned_moves: list[PlannedMove] = []
    reserved_paths: set[Path] = set()

    for asset in assets:
        source_path = asset.source_path.resolve()

        relative_destination = build_destination_folder(
            asset=asset,
            options=active_options,
        )

        destination_directory = (
            root_folder
            / relative_destination
        ).resolve()

        desired_path = (
            destination_directory
            / asset.file_name
        ).resolve()

        if not destination_directory.is_relative_to(
            root_folder
        ):
            raise ValueError(
                "A planned destination is outside the project folder."
            )

        if source_path == desired_path:
            continue

        available_path, renamed_for_conflict = (
            _next_available_path(
                desired_path=desired_path,
                reserved_paths=reserved_paths,
            )
        )

        reserved_paths.add(
            available_path
        )

        planned_moves.append(
            PlannedMove(
                asset=asset,
                destination_path=available_path,
                renamed_for_conflict=renamed_for_conflict,
            )
        )

    return sorted(
        planned_moves,
        key=lambda planned_move: str(
            planned_move.asset.relative_path
        ).lower(),
    )


def count_conflict_renames(
    planned_moves: Iterable[PlannedMove],
) -> int:
    """Count how many planned files require a safe rename."""
    return sum(
        1
        for planned_move in planned_moves
        if planned_move.renamed_for_conflict
    )
