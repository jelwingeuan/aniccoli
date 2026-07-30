"""Duplicate-results window for Aniccoli."""

from __future__ import annotations

from collections.abc import Sequence

import customtkinter as ctk

from aniccoli.duplicates import (
    DuplicateGroup,
    calculate_reclaimable_bytes,
    count_duplicate_copies,
)
from aniccoli.scanner import format_file_size


class DuplicateResultsWindow(ctk.CTkToplevel):
    """Display duplicate-file groups without modifying any files."""

    def __init__(
        self,
        master: ctk.CTk,
        duplicate_groups: Sequence[DuplicateGroup],
    ) -> None:
        """Create the duplicate-results window."""
        super().__init__(master)

        self.duplicate_groups = list(duplicate_groups)

        self._configure_window()
        self._create_interface()

    def _configure_window(self) -> None:
        """Configure the duplicate-results window."""
        self.title("Aniccoli Duplicate Analysis")
        self.geometry("1100x700")
        self.minsize(850, 550)

        self.transient(self.master)
        self.grab_set()

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _create_interface(self) -> None:
        """Create all duplicate-analysis interface elements."""
        self._create_heading()
        self._create_summary()
        self._create_results_area()
        self._create_close_button()

    def _create_heading(self) -> None:
        """Create the window title and explanation."""
        heading_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )
        heading_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=25,
            pady=(25, 15),
        )

        heading_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            master=heading_frame,
            text="Duplicate Analysis",
            font=ctk.CTkFont(
                size=28,
                weight="bold",
            ),
            anchor="w",
        )
        title_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        description_label = ctk.CTkLabel(
            master=heading_frame,
            text=(
                "Files shown in the same group have identical content. "
                "Aniccoli has not deleted or modified anything."
            ),
            font=ctk.CTkFont(size=14),
            anchor="w",
            justify="left",
            wraplength=950,
        )
        description_label.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 0),
        )

    def _create_summary(self) -> None:
        """Create duplicate summary cards."""
        summary_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )
        summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 18),
        )

        summary_frame.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="duplicate_summary",
        )

        group_count = len(self.duplicate_groups)

        duplicate_copy_count = count_duplicate_copies(
            self.duplicate_groups
        )

        reclaimable_bytes = calculate_reclaimable_bytes(
            self.duplicate_groups
        )

        self._create_summary_card(
            parent=summary_frame,
            column=0,
            value=str(group_count),
            heading="Duplicate groups",
        )

        self._create_summary_card(
            parent=summary_frame,
            column=1,
            value=str(duplicate_copy_count),
            heading="Extra copies",
        )

        self._create_summary_card(
            parent=summary_frame,
            column=2,
            value=format_file_size(reclaimable_bytes),
            heading="Potentially reclaimable",
        )

    def _create_summary_card(
        self,
        parent: ctk.CTkFrame,
        column: int,
        value: str,
        heading: str,
    ) -> None:
        """Create one duplicate-summary card."""
        card = ctk.CTkFrame(
            master=parent,
            corner_radius=12,
        )
        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=(
                0 if column == 0 else 6,
                0 if column == 2 else 6,
            ),
        )

        value_label = ctk.CTkLabel(
            master=card,
            text=value,
            font=ctk.CTkFont(
                size=25,
                weight="bold",
            ),
        )
        value_label.pack(
            padx=20,
            pady=(16, 2),
        )

        heading_label = ctk.CTkLabel(
            master=card,
            text=heading,
            font=ctk.CTkFont(size=13),
        )
        heading_label.pack(
            padx=20,
            pady=(0, 16),
        )

    def _create_results_area(self) -> None:
        """Create the scrollable list of duplicate groups."""
        results_frame = ctk.CTkScrollableFrame(
            master=self,
            corner_radius=12,
        )
        results_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=25,
            pady=(0, 15),
        )

        results_frame.grid_columnconfigure(0, weight=1)

        if not self.duplicate_groups:
            empty_label = ctk.CTkLabel(
                master=results_frame,
                text=(
                    "No exact-content duplicate files were found.\n\n"
                    "Files with different content are not considered "
                    "duplicates, even when their names are similar."
                ),
                font=ctk.CTkFont(size=15),
                justify="center",
                wraplength=650,
            )
            empty_label.grid(
                row=0,
                column=0,
                padx=30,
                pady=80,
            )
            return

        for group_number, duplicate_group in enumerate(
            self.duplicate_groups,
            start=1,
        ):
            self._create_duplicate_group(
                parent=results_frame,
                duplicate_group=duplicate_group,
                group_number=group_number,
            )

    def _create_duplicate_group(
        self,
        parent: ctk.CTkScrollableFrame,
        duplicate_group: DuplicateGroup,
        group_number: int,
    ) -> None:
        """Create one card containing identical files."""
        group_card = ctk.CTkFrame(
            master=parent,
            corner_radius=10,
        )
        group_card.grid(
            row=group_number - 1,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )

        group_card.grid_columnconfigure(0, weight=1)

        heading_label = ctk.CTkLabel(
            master=group_card,
            text=(
                f"Duplicate Group {group_number} — "
                f"{duplicate_group.file_count} identical files"
            ),
            font=ctk.CTkFont(
                size=17,
                weight="bold",
            ),
            anchor="w",
        )
        heading_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(16, 4),
        )

        details_label = ctk.CTkLabel(
            master=group_card,
            text=(
                f"Size per file: {duplicate_group.size_text}    •    "
                f"Extra copies: {duplicate_group.duplicate_copy_count}    •    "
                f"Potentially reclaimable: "
                f"{duplicate_group.reclaimable_size_text}"
            ),
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        details_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 3),
        )

        hash_label = ctk.CTkLabel(
            master=group_card,
            text=(
                "SHA-256: "
                f"{duplicate_group.content_hash[:24]}..."
            ),
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        hash_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12),
        )

        files_frame = ctk.CTkFrame(
            master=group_card,
            corner_radius=8,
        )
        files_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 18),
        )

        files_frame.grid_columnconfigure(0, weight=1)

        for file_number, asset in enumerate(
            duplicate_group.files,
            start=1,
        ):
            role_text = (
                "Reference copy"
                if file_number == 1
                else "Matching copy"
            )

            file_row = ctk.CTkFrame(
                master=files_frame,
                fg_color="transparent",
            )
            file_row.grid(
                row=file_number - 1,
                column=0,
                sticky="ew",
                padx=10,
                pady=(
                    (8, 4)
                    if file_number == 1
                    else (4, 8)
                    if file_number == duplicate_group.file_count
                    else 4
                ),
            )

            file_row.grid_columnconfigure(0, weight=1)

            path_label = ctk.CTkLabel(
                master=file_row,
                text=str(asset.relative_path),
                font=ctk.CTkFont(size=13),
                anchor="w",
                justify="left",
            )
            path_label.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=(5, 10),
            )

            category_label = ctk.CTkLabel(
                master=file_row,
                text=str(asset.category),
                font=ctk.CTkFont(size=12),
            )
            category_label.grid(
                row=0,
                column=1,
                padx=10,
            )

            role_label = ctk.CTkLabel(
                master=file_row,
                text=role_text,
                font=ctk.CTkFont(
                    size=12,
                    weight="bold",
                ),
                width=120,
            )
            role_label.grid(
                row=0,
                column=2,
                padx=(10, 5),
            )

    def _create_close_button(self) -> None:
        """Create the close button."""
        close_button = ctk.CTkButton(
            master=self,
            text="Close",
            command=self.destroy,
            width=140,
            height=40,
        )
        close_button.grid(
            row=3,
            column=0,
            sticky="e",
            padx=25,
            pady=(0, 25),
        )