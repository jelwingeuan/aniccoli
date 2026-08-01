"""Project statistics window for Aniccoli."""

from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from aniccoli.scanner import AssetFile
from aniccoli.statistics import (
    AssetStatistics,
    StatisticsGroup,
)


class AssetStatisticsWindow(ctk.CTkToplevel):
    """Display calculated statistics for scanned project assets."""

    def __init__(
        self,
        master: ctk.CTk,
        statistics: AssetStatistics,
    ) -> None:
        """Create the project-statistics window."""
        super().__init__(master)

        self.statistics = statistics

        self.title("Aniccoli Project Statistics")
        self.geometry("1080x740")
        self.minsize(900, 620)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(
            0,
            weight=1,
        )

        self.grid_rowconfigure(
            2,
            weight=1,
        )

        self._create_header()
        self._create_summary_cards()
        self._create_statistics_tabs()
        self._create_close_button()

    def _create_header(self) -> None:
        """Create the statistics-window heading."""
        header_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )

        header_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=25,
            pady=(25, 15),
        )

        header_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        title_label = ctk.CTkLabel(
            master=header_frame,
            text="Project Statistics",
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
            master=header_frame,
            text=(
                "A read-only overview of every asset in the latest scan."
            ),
            font=ctk.CTkFont(
                size=13,
            ),
            anchor="w",
        )

        description_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 0),
        )

    def _create_summary_cards(self) -> None:
        """Create the main project-statistics cards."""
        summary_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )

        summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 15),
        )

        for column in range(5):
            summary_frame.grid_columnconfigure(
                column,
                weight=1,
                uniform="statistics-summary",
            )

        summary_values = (
            (
                "Assets",
                str(self.statistics.total_assets),
            ),
            (
                "Combined size",
                self.statistics.total_size_text,
            ),
            (
                "Average size",
                self.statistics.average_size_text,
            ),
            (
                "Categories",
                str(self.statistics.category_count),
            ),
            (
                "Source folders",
                str(self.statistics.folder_count),
            ),
        )

        for column, (heading, value) in enumerate(
            summary_values
        ):
            self._create_summary_card(
                parent=summary_frame,
                column=column,
                heading=heading,
                value=value,
            )

    def _create_summary_card(
        self,
        parent: ctk.CTkFrame,
        column: int,
        heading: str,
        value: str,
    ) -> None:
        """Create one project-statistics summary card."""
        card = ctk.CTkFrame(
            master=parent,
            corner_radius=12,
        )

        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(
                0 if column == 0 else 5,
                0 if column == 4 else 5,
            ),
        )

        value_label = ctk.CTkLabel(
            master=card,
            text=value,
            font=ctk.CTkFont(
                size=22,
                weight="bold",
            ),
        )

        value_label.pack(
            padx=15,
            pady=(15, 2),
        )

        heading_label = ctk.CTkLabel(
            master=card,
            text=heading,
            font=ctk.CTkFont(
                size=12,
            ),
        )

        heading_label.pack(
            padx=15,
            pady=(0, 15),
        )

    def _create_statistics_tabs(self) -> None:
        """Create category, extension, folder, and asset tabs."""
        tab_view = ctk.CTkTabview(
            master=self,
            corner_radius=12,
        )

        tab_view.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=25,
            pady=(0, 15),
        )

        tab_names = (
            "Categories",
            "Extensions",
            "Folders",
            "Largest Assets",
            "Recently Modified",
        )

        for tab_name in tab_names:
            tab_view.add(
                tab_name
            )

            tab_view.tab(
                tab_name
            ).grid_columnconfigure(
                0,
                weight=1,
            )

            tab_view.tab(
                tab_name
            ).grid_rowconfigure(
                0,
                weight=1,
            )

        self._populate_group_tab(
            parent=tab_view.tab("Categories"),
            groups=self.statistics.category_groups,
            empty_message="No asset categories are available.",
        )

        self._populate_group_tab(
            parent=tab_view.tab("Extensions"),
            groups=self.statistics.extension_groups,
            empty_message="No file extensions are available.",
        )

        self._populate_group_tab(
            parent=tab_view.tab("Folders"),
            groups=self.statistics.folder_groups,
            empty_message="No source folders are available.",
        )

        self._populate_asset_tab(
            parent=tab_view.tab("Largest Assets"),
            assets=self.statistics.largest_assets,
            empty_message="No assets are available.",
        )

        self._populate_asset_tab(
            parent=tab_view.tab("Recently Modified"),
            assets=self.statistics.recently_modified_assets,
            empty_message="No assets are available.",
        )

    def _populate_group_tab(
        self,
        parent: ctk.CTkFrame,
        groups: tuple[StatisticsGroup, ...],
        empty_message: str,
    ) -> None:
        """Populate a statistics tab containing grouped totals."""
        scroll_frame = ctk.CTkScrollableFrame(
            master=parent,
            corner_radius=8,
        )

        scroll_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=8,
            pady=8,
        )

        scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        if not groups:
            self._create_empty_label(
                parent=scroll_frame,
                message=empty_message,
            )
            return

        for row_number, group in enumerate(
            groups
        ):
            row_frame = ctk.CTkFrame(
                master=scroll_frame,
                corner_radius=8,
            )

            row_frame.grid(
                row=row_number,
                column=0,
                sticky="ew",
                pady=(0, 6),
            )

            row_frame.grid_columnconfigure(
                0,
                weight=1,
            )

            name_label = ctk.CTkLabel(
                master=row_frame,
                text=group.name,
                font=ctk.CTkFont(
                    size=13,
                    weight="bold",
                ),
                anchor="w",
            )

            name_label.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=14,
                pady=12,
            )

            count_label = ctk.CTkLabel(
                master=row_frame,
                text=(
                    f"{group.asset_count} asset"
                    f"{'' if group.asset_count == 1 else 's'}"
                ),
                font=ctk.CTkFont(
                    size=12,
                ),
                width=110,
            )

            count_label.grid(
                row=0,
                column=1,
                padx=14,
                pady=12,
            )

            size_label = ctk.CTkLabel(
                master=row_frame,
                text=group.total_size_text,
                font=ctk.CTkFont(
                    size=12,
                ),
                width=120,
                anchor="e",
            )

            size_label.grid(
                row=0,
                column=2,
                padx=14,
                pady=12,
            )

    def _populate_asset_tab(
        self,
        parent: ctk.CTkFrame,
        assets: tuple[AssetFile, ...],
        empty_message: str,
    ) -> None:
        """Populate a statistics tab containing individual assets."""
        scroll_frame = ctk.CTkScrollableFrame(
            master=parent,
            corner_radius=8,
        )

        scroll_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=8,
            pady=8,
        )

        scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        if not assets:
            self._create_empty_label(
                parent=scroll_frame,
                message=empty_message,
            )
            return

        for row_number, asset in enumerate(
            assets
        ):
            self._create_asset_row(
                parent=scroll_frame,
                asset=asset,
                row_number=row_number,
            )

    def _create_asset_row(
        self,
        parent: ctk.CTkScrollableFrame,
        asset: AssetFile,
        row_number: int,
    ) -> None:
        """Create one asset row in a statistics tab."""
        row_frame = ctk.CTkFrame(
            master=parent,
            corner_radius=8,
        )

        row_frame.grid(
            row=row_number,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )

        row_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        path_label = ctk.CTkLabel(
            master=row_frame,
            text=str(
                asset.relative_path
            ),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            anchor="w",
            justify="left",
        )

        path_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=12,
        )

        category_label = ctk.CTkLabel(
            master=row_frame,
            text=str(
                asset.category
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            width=150,
            anchor="w",
        )

        category_label.grid(
            row=0,
            column=1,
            padx=14,
            pady=12,
        )

        size_label = ctk.CTkLabel(
            master=row_frame,
            text=asset.size_text,
            font=ctk.CTkFont(
                size=12,
            ),
            width=100,
            anchor="e",
        )

        size_label.grid(
            row=0,
            column=2,
            padx=14,
            pady=12,
        )

        modified_label = ctk.CTkLabel(
            master=row_frame,
            text=self._format_datetime(
                asset.modified_at
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            width=145,
            anchor="e",
        )

        modified_label.grid(
            row=0,
            column=3,
            padx=14,
            pady=12,
        )

    def _create_empty_label(
        self,
        parent: ctk.CTkScrollableFrame,
        message: str,
    ) -> None:
        """Create an empty-state message inside a tab."""
        empty_label = ctk.CTkLabel(
            master=parent,
            text=message,
            font=ctk.CTkFont(
                size=14,
            ),
        )

        empty_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=70,
        )

    def _create_close_button(self) -> None:
        """Create the close button."""
        close_button = ctk.CTkButton(
            master=self,
            text="Close",
            command=self.destroy,
            width=120,
            height=40,
        )

        close_button.grid(
            row=3,
            column=0,
            sticky="e",
            padx=25,
            pady=(0, 25),
        )

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Return a compact readable date and time."""
        return value.strftime(
            "%Y-%m-%d %H:%M"
        )