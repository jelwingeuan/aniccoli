"""Duplicate-file detection tools for Aniccoli."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aniccoli.scanner import AssetFile, format_file_size


DEFAULT_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class DuplicateGroup:
    """Represent a group of files with identical content."""

    content_hash: str
    files: tuple[AssetFile, ...]
    size_bytes: int

    @property
    def file_count(self) -> int:
        """Return the total number of identical files."""
        return len(self.files)

    @property
    def duplicate_copy_count(self) -> int:
        """
        Return the number of unnecessary duplicate copies.

        One file is treated as the original. Every additional identical
        file is counted as a duplicate copy.
        """
        return max(
            0,
            self.file_count - 1,
        )

    @property
    def reclaimable_bytes(self) -> int:
        """
        Estimate storage that could be recovered.

        This assumes one file is kept and every additional identical
        copy is removed.
        """
        return (
            self.size_bytes
            * self.duplicate_copy_count
        )

    @property
    def size_text(self) -> str:
        """Return the size of one file in a readable format."""
        return format_file_size(
            self.size_bytes
        )

    @property
    def reclaimable_size_text(self) -> str:
        """Return reclaimable storage in a readable format."""
        return format_file_size(
            self.reclaimable_bytes
        )


def calculate_sha256(
    file_path: str | Path,
    *,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE,
) -> str:
    """
    Calculate the SHA-256 hash of one file.

    The file is read in chunks instead of loading its entire contents
    into memory. This allows Aniccoli to process large 3D files safely.

    Args:
        file_path:
            The file whose content should be hashed.

        chunk_size:
            Number of bytes read during each operation.

    Raises:
        ValueError:
            The chunk size is invalid or the path is not a file.

        FileNotFoundError:
            The selected file no longer exists.

        PermissionError:
            The file cannot be read.

    Returns:
        The hexadecimal SHA-256 hash of the file.
    """
    path = Path(
        file_path
    ).expanduser().resolve()

    if chunk_size <= 0:
        raise ValueError(
            "Hash chunk size must be greater than zero."
        )

    if not path.exists():
        raise FileNotFoundError(
            f"The file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"The selected path is not a file: {path}"
        )

    file_hash = hashlib.sha256()

    with path.open(
        mode="rb",
    ) as source_file:
        while True:
            file_chunk = source_file.read(
                chunk_size
            )

            if not file_chunk:
                break

            file_hash.update(
                file_chunk
            )

    return file_hash.hexdigest()


def _group_assets_by_size(
    assets: Iterable[AssetFile],
    *,
    include_empty: bool,
) -> dict[int, list[AssetFile]]:
    """
    Group files by size before calculating hashes.

    Files with different sizes cannot have identical content, so only
    groups containing at least two same-sized files need hashing.
    """
    size_groups: dict[
        int,
        list[AssetFile],
    ] = defaultdict(list)

    for asset in assets:
        if (
            asset.size_bytes == 0
            and not include_empty
        ):
            continue

        size_groups[
            asset.size_bytes
        ].append(asset)

    return {
        file_size: same_size_assets
        for file_size, same_size_assets in size_groups.items()
        if len(same_size_assets) > 1
    }


def find_duplicate_groups(
    assets: Iterable[AssetFile],
    *,
    include_empty: bool = False,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE,
) -> list[DuplicateGroup]:
    """
    Find files that contain exactly the same data.

    The process contains two stages:

    1. Group files with matching sizes.
    2. Calculate SHA-256 hashes only for those possible matches.

    Args:
        assets:
            Scanned asset records from Aniccoli's folder scanner.

        include_empty:
            When False, zero-byte files are ignored. Empty files contain
            no useful asset data and are often temporary placeholders.

        chunk_size:
            Number of bytes read at one time while hashing.

    Returns:
        Duplicate groups sorted by reclaimable storage.
    """
    if chunk_size <= 0:
        raise ValueError(
            "Hash chunk size must be greater than zero."
        )

    size_groups = _group_assets_by_size(
        assets,
        include_empty=include_empty,
    )

    hash_groups: dict[
        tuple[int, str],
        list[AssetFile],
    ] = defaultdict(list)

    for file_size, possible_duplicates in (
        size_groups.items()
    ):
        for asset in possible_duplicates:
            content_hash = calculate_sha256(
                asset.source_path,
                chunk_size=chunk_size,
            )

            group_key = (
                file_size,
                content_hash,
            )

            hash_groups[
                group_key
            ].append(asset)

    duplicate_groups: list[
        DuplicateGroup
    ] = []

    for (
        file_size,
        content_hash,
    ), matching_files in hash_groups.items():
        if len(matching_files) < 2:
            continue

        sorted_files = tuple(
            sorted(
                matching_files,
                key=lambda asset: str(
                    asset.relative_path
                ).lower(),
            )
        )

        duplicate_groups.append(
            DuplicateGroup(
                content_hash=content_hash,
                files=sorted_files,
                size_bytes=file_size,
            )
        )

    return sorted(
        duplicate_groups,
        key=lambda group: (
            -group.reclaimable_bytes,
            -group.file_count,
            group.content_hash,
        ),
    )


def count_duplicate_files(
    duplicate_groups: Iterable[DuplicateGroup],
) -> int:
    """Return the total number of files inside duplicate groups."""
    return sum(
        group.file_count
        for group in duplicate_groups
    )


def count_duplicate_copies(
    duplicate_groups: Iterable[DuplicateGroup],
) -> int:
    """Return the number of additional duplicate copies."""
    return sum(
        group.duplicate_copy_count
        for group in duplicate_groups
    )


def calculate_reclaimable_bytes(
    duplicate_groups: Iterable[DuplicateGroup],
) -> int:
    """Return the estimated recoverable storage in bytes."""
    return sum(
        group.reclaimable_bytes
        for group in duplicate_groups
    )