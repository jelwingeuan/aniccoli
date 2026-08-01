"""Main desktop window for Aniccoli."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from aniccoli.categories import AssetCategory
from aniccoli.duplicate_window import DuplicateResultsWindow
from aniccoli.duplicates import (
    DuplicateGroup,
    count_duplicate_copies,
    find_duplicate_groups,
)
from aniccoli.filters import (
    AssetFilter,
    collect_available_categories,
    collect_available_extensions,
    filter_assets,
)
from aniccoli.folder_filter import (
    FolderFilterOptions,
    FolderMatchMode,
    collect_available_folders,
    filter_assets_by_folder,
    folder_display_name,
)
from aniccoli.history import (
    NoUndoHistoryError,
    find_latest_undoable_log,
    undo_latest_organization,
)
from aniccoli.organization_options import (
    DateGrouping,
    DateSource,
    OrganizationOptions,
    build_destination_folder,
)
from aniccoli.organizer import (
    PlannedMove,
    build_organization_plan,
    count_conflict_renames,
    execute_organization_plan,
)
from aniccoli.reports import (
    ReportFormat,
    export_asset_report,
)
from aniccoli.scanner import (
    AssetFile,
    calculate_total_size,
    format_file_size,
    scan_folder,
    summarize_assets,
)
from aniccoli.sorting import (
    AssetSortOptions,
    SortDirection,
    SortField,
    sort_assets,
)


ALL_CATEGORIES = "All categories"
ALL_EXTENSIONS = "All extensions"
ALL_FOLDERS = "All folders"
ANY_SIZE = "Any size"
ANY_TIME = "Any time"


SIZE_FILTER_OPTIONS: dict[
    str,
    tuple[int | None, int | None],
] = {
    ANY_SIZE: (None, None),
    "Up to 1 MB": (
        None,
        1024**2,
    ),
    "1 MB to 10 MB": (
        1024**2,
        10 * 1024**2,
    ),
    "10 MB to 100 MB": (
        10 * 1024**2,
        100 * 1024**2,
    ),
    "100 MB and above": (
        100 * 1024**2,
        None,
    ),
}


MODIFIED_FILTER_OPTIONS: dict[str, int | None] = {
    ANY_TIME: None,
    "Last 24 hours": 1,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
}


class AniccoliApp(ctk.CTk):
    """Main application window for Aniccoli."""

    def __init__(self) -> None:
        """Create and configure the application window."""
        super().__init__()

        self.selected_folder: Optional[Path] = None

        self.scanned_assets: list[AssetFile] = []
        self.filtered_assets: list[AssetFile] = []
        self.organization_plan: list[PlannedMove] = []
        self.duplicate_groups: list[DuplicateGroup] = []

        self.available_categories: tuple[
            AssetCategory,
            ...,
        ] = ()

        self.available_extensions: tuple[
            str,
            ...,
        ] = ()

        self.available_folders: tuple[
            Path,
            ...,
        ] = ()

        self.folder_display_lookup: dict[
            str,
            Path,
        ] = {}

        self.recursive_scan_var = ctk.BooleanVar(
            value=True,
        )

        self.search_var = ctk.StringVar(
            value="",
        )

        self.category_filter_var = ctk.StringVar(
            value=ALL_CATEGORIES,
        )

        self.extension_filter_var = ctk.StringVar(
            value=ALL_EXTENSIONS,
        )

        self.size_filter_var = ctk.StringVar(
            value=ANY_SIZE,
        )

        self.modified_filter_var = ctk.StringVar(
            value=ANY_TIME,
        )

        self.folder_filter_var = ctk.StringVar(
            value=ALL_FOLDERS,
        )

        self.folder_match_mode_var = ctk.StringVar(
            value=str(
                FolderMatchMode.INCLUDE_SUBFOLDERS
            ),
        )

        self.sort_field_var = ctk.StringVar(
            value=str(
                SortField.NAME
            ),
        )

        self.sort_direction_var = ctk.StringVar(
            value=str(
                SortDirection.ASCENDING
            ),
        )

        self.date_grouping_var = ctk.StringVar(
            value=str(
                DateGrouping.NONE
            ),
        )

        self.date_source_var = ctk.StringVar(
            value=str(
                DateSource.MODIFIED
            ),
        )

        self._configure_window()
        self._create_interface()

    def _configure_window(self) -> None:
        """Configure the main application window."""
        self.title("Aniccoli")
        self.geometry("1440x900")
        self.minsize(1120, 760)

        self.grid_rowconfigure(
            0,
            weight=1,
        )

        self.grid_columnconfigure(
            0,
            weight=1,
        )

    def _create_interface(self) -> None:
        """Create the complete application interface."""
        self.main_container = ctk.CTkFrame(
            master=self,
            corner_radius=0,
            fg_color="transparent",
        )

        self.main_container.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=30,
            pady=25,
        )

        self.main_container.grid_columnconfigure(
            0,
            weight=1,
        )

        self.main_container.grid_rowconfigure(
            3,
            weight=1,
        )

        self._create_header()
        self._create_folder_controls()
        self._create_summary_section()
        self._create_results_section()

    def _create_header(self) -> None:
        """Create the application heading."""
        header_frame = ctk.CTkFrame(
            master=self.main_container,
            fg_color="transparent",
        )

        header_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 20),
        )

        header_frame.grid_columnconfigure(
            1,
            weight=1,
        )

        logo_label = ctk.CTkLabel(
            master=header_frame,
            text="🥦",
            font=ctk.CTkFont(
                size=48,
            ),
        )

        logo_label.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(0, 15),
        )

        title_label = ctk.CTkLabel(
            master=header_frame,
            text="Aniccoli",
            font=ctk.CTkFont(
                size=32,
                weight="bold",
            ),
            anchor="w",
        )

        title_label.grid(
            row=0,
            column=1,
            sticky="w",
        )

        description_label = ctk.CTkLabel(
            master=header_frame,
            text=(
                "Scan, search, analyze, organize, and restore "
                "your 3D production assets."
            ),
            font=ctk.CTkFont(
                size=14,
            ),
            anchor="w",
        )

        description_label.grid(
            row=1,
            column=1,
            sticky="w",
        )

    def _create_folder_controls(self) -> None:
        """Create folder, organization, and undo controls."""
        folder_card = ctk.CTkFrame(
            master=self.main_container,
            corner_radius=15,
        )

        folder_card.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 18),
        )

        folder_card.grid_columnconfigure(
            0,
            weight=1,
        )

        heading_label = ctk.CTkLabel(
            master=folder_card,
            text="Project folder",
            font=ctk.CTkFont(
                size=18,
                weight="bold",
            ),
            anchor="w",
        )

        heading_label.grid(
            row=0,
            column=0,
            columnspan=6,
            sticky="w",
            padx=25,
            pady=(20, 5),
        )

        self.selected_folder_label = ctk.CTkLabel(
            master=folder_card,
            text="No folder selected",
            font=ctk.CTkFont(
                size=13,
            ),
            anchor="w",
            justify="left",
            wraplength=1200,
        )

        self.selected_folder_label.grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="ew",
            padx=25,
            pady=(0, 15),
        )

        choose_folder_button = ctk.CTkButton(
            master=folder_card,
            text="Choose Project Folder",
            command=self._select_folder,
            width=180,
            height=40,
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        choose_folder_button.grid(
            row=2,
            column=0,
            sticky="w",
            padx=(25, 8),
            pady=(0, 20),
        )

        recursive_checkbox = ctk.CTkCheckBox(
            master=folder_card,
            text="Scan subfolders",
            variable=self.recursive_scan_var,
            onvalue=True,
            offvalue=False,
            font=ctk.CTkFont(
                size=14,
            ),
        )

        recursive_checkbox.grid(
            row=2,
            column=1,
            sticky="w",
            padx=8,
            pady=(0, 20),
        )

        self.scan_button = ctk.CTkButton(
            master=folder_card,
            text="Scan Folder",
            command=self._scan_selected_folder,
            width=125,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.scan_button.grid(
            row=2,
            column=2,
            padx=8,
            pady=(0, 20),
        )

        self.duplicate_button = ctk.CTkButton(
            master=folder_card,
            text="Analyze Duplicates",
            command=self._analyze_duplicates,
            width=155,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.duplicate_button.grid(
            row=2,
            column=3,
            padx=8,
            pady=(0, 20),
        )

        self.preview_button = ctk.CTkButton(
            master=folder_card,
            text="Preview Organization",
            command=self._preview_organization,
            width=170,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.preview_button.grid(
            row=2,
            column=4,
            padx=8,
            pady=(0, 20),
        )

        self.undo_button = ctk.CTkButton(
            master=folder_card,
            text="Undo Last Organization",
            command=self._undo_last_organization,
            width=180,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.undo_button.grid(
            row=2,
            column=5,
            sticky="e",
            padx=(8, 25),
            pady=(0, 20),
        )

        organization_settings_frame = ctk.CTkFrame(
            master=folder_card,
            corner_radius=10,
        )

        organization_settings_frame.grid(
            row=3,
            column=0,
            columnspan=6,
            sticky="ew",
            padx=25,
            pady=(0, 12),
        )

        organization_settings_frame.grid_columnconfigure(
            4,
            weight=1,
        )

        organization_settings_label = ctk.CTkLabel(
            master=organization_settings_frame,
            text="Organization settings",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        organization_settings_label.grid(
            row=0,
            column=0,
            padx=(15, 10),
            pady=12,
        )

        date_grouping_label = ctk.CTkLabel(
            master=organization_settings_frame,
            text="Date grouping:",
            font=ctk.CTkFont(
                size=13,
            ),
        )

        date_grouping_label.grid(
            row=0,
            column=1,
            padx=(10, 5),
            pady=12,
        )

        self.date_grouping_menu = ctk.CTkOptionMenu(
            master=organization_settings_frame,
            variable=self.date_grouping_var,
            values=[
                str(option)
                for option in DateGrouping
            ],
            command=lambda _value: (
                self._on_organization_options_changed()
            ),
            width=170,
            height=36,
        )

        self.date_grouping_menu.grid(
            row=0,
            column=2,
            padx=(5, 15),
            pady=12,
        )

        date_source_label = ctk.CTkLabel(
            master=organization_settings_frame,
            text="Use:",
            font=ctk.CTkFont(
                size=13,
            ),
        )

        date_source_label.grid(
            row=0,
            column=3,
            padx=(10, 5),
            pady=12,
        )

        self.date_source_menu = ctk.CTkOptionMenu(
            master=organization_settings_frame,
            variable=self.date_source_var,
            values=[
                str(option)
                for option in DateSource
            ],
            command=lambda _value: (
                self._on_organization_options_changed()
            ),
            width=170,
            height=36,
            state="disabled",
        )

        self.date_source_menu.grid(
            row=0,
            column=4,
            sticky="w",
            padx=(5, 15),
            pady=12,
        )

        settings_description = ctk.CTkLabel(
            master=organization_settings_frame,
            text=(
                "Optional: place files inside year or "
                "year-and-month folders."
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="e",
        )

        settings_description.grid(
            row=0,
            column=5,
            sticky="e",
            padx=(10, 15),
            pady=12,
        )

        self.export_button = ctk.CTkButton(
            master=organization_settings_frame,
            text="Export Report",
            command=self._export_inventory_report,
            width=135,
            height=36,
            state="disabled",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        self.export_button.grid(
            row=0,
            column=6,
            padx=(0, 15),
            pady=12,
        )

        self.status_label = ctk.CTkLabel(
            master=folder_card,
            text="Choose a folder to begin.",
            font=ctk.CTkFont(
                size=13,
            ),
            anchor="w",
        )

        self.status_label.grid(
            row=4,
            column=0,
            columnspan=6,
            sticky="ew",
            padx=25,
            pady=(0, 20),
        )

    def _create_summary_section(self) -> None:
        """Create the scan-summary cards."""
        summary_frame = ctk.CTkFrame(
            master=self.main_container,
            fg_color="transparent",
        )

        summary_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 18),
        )

        summary_frame.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="summary",
        )

        self.files_count_label = (
            self._create_summary_card(
                parent=summary_frame,
                column=0,
                heading="Files found",
                starting_value="0",
            )
        )

        self.total_size_label = (
            self._create_summary_card(
                parent=summary_frame,
                column=1,
                heading="Combined size",
                starting_value="0 B",
            )
        )

        self.categories_count_label = (
            self._create_summary_card(
                parent=summary_frame,
                column=2,
                heading="Categories",
                starting_value="0",
            )
        )

    def _create_summary_card(
        self,
        parent: ctk.CTkFrame,
        column: int,
        heading: str,
        starting_value: str,
    ) -> ctk.CTkLabel:
        """Create a summary card and return its value label."""
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
            text=starting_value,
            font=ctk.CTkFont(
                size=26,
                weight="bold",
            ),
        )

        value_label.pack(
            padx=20,
            pady=(17, 2),
        )

        heading_label = ctk.CTkLabel(
            master=card,
            text=heading,
            font=ctk.CTkFont(
                size=13,
            ),
        )

        heading_label.pack(
            padx=20,
            pady=(0, 17),
        )

        return value_label

    def _create_results_section(self) -> None:
        """Create filters and the scrollable results section."""
        results_card = ctk.CTkFrame(
            master=self.main_container,
            corner_radius=15,
        )

        results_card.grid(
            row=3,
            column=0,
            sticky="nsew",
        )

        results_card.grid_columnconfigure(
            0,
            weight=1,
        )

        results_card.grid_rowconfigure(
            3,
            weight=1,
        )

        heading_frame = ctk.CTkFrame(
            master=results_card,
            fg_color="transparent",
        )

        heading_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 12),
        )

        heading_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        results_heading = ctk.CTkLabel(
            master=heading_frame,
            text="Scanned assets",
            font=ctk.CTkFont(
                size=18,
                weight="bold",
            ),
            anchor="w",
        )

        results_heading.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.filter_count_label = ctk.CTkLabel(
            master=heading_frame,
            text="Showing 0 of 0 files",
            font=ctk.CTkFont(
                size=13,
            ),
            anchor="e",
        )

        self.filter_count_label.grid(
            row=0,
            column=1,
            sticky="e",
        )

        self._create_filter_controls(
            results_card
        )

        results_header = ctk.CTkFrame(
            master=results_card,
            corner_radius=8,
        )

        results_header.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 5),
        )

        results_header.grid_columnconfigure(
            0,
            weight=3,
        )

        results_header.grid_columnconfigure(
            1,
            weight=2,
        )

        results_header.grid_columnconfigure(
            2,
            weight=1,
        )

        results_header.grid_columnconfigure(
            3,
            weight=2,
        )

        headings = (
            "File",
            "Category",
            "Size",
            "Planned folder",
        )

        for column, heading in enumerate(
            headings
        ):
            self._create_column_heading(
                parent=results_header,
                text=heading,
                column=column,
            )

        self.results_scroll_frame = (
            ctk.CTkScrollableFrame(
                master=results_card,
                corner_radius=8,
            )
        )

        self.results_scroll_frame.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=15,
            pady=(0, 15),
        )

        self.results_scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        self._show_empty_results_message(
            "No scan results yet.\n"
            "Select a project folder and click Scan Folder."
        )

    def _create_filter_controls(
        self,
        parent: ctk.CTkFrame,
    ) -> None:
        """Create search and filtering controls."""
        filter_frame = ctk.CTkFrame(
            master=parent,
            corner_radius=10,
        )

        filter_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10),
        )

        filter_frame.grid_columnconfigure(
            0,
            weight=3,
        )

        filter_frame.grid_columnconfigure(
            (1, 2, 3, 4),
            weight=1,
        )

        self.search_entry = ctk.CTkEntry(
            master=filter_frame,
            textvariable=self.search_var,
            placeholder_text=(
                "Search file name, path, category, or folder..."
            ),
            height=38,
        )

        self.search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(12, 6),
            pady=12,
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda _event: self._apply_filters(),
        )

        self.category_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.category_filter_var,
            values=[
                ALL_CATEGORIES,
            ],
            command=lambda _value: (
                self._apply_filters()
            ),
            height=38,
        )

        self.category_filter_menu.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=12,
        )

        self.extension_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.extension_filter_var,
            values=[
                ALL_EXTENSIONS,
            ],
            command=lambda _value: (
                self._apply_filters()
            ),
            height=38,
        )

        self.extension_filter_menu.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=6,
            pady=12,
        )

        self.size_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.size_filter_var,
            values=list(
                SIZE_FILTER_OPTIONS,
            ),
            command=lambda _value: (
                self._apply_filters()
            ),
            height=38,
        )

        self.size_filter_menu.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=6,
            pady=12,
        )

        self.modified_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.modified_filter_var,
            values=list(
                MODIFIED_FILTER_OPTIONS,
            ),
            command=lambda _value: (
                self._apply_filters()
            ),
            height=38,
        )

        self.modified_filter_menu.grid(
            row=0,
            column=4,
            sticky="ew",
            padx=6,
            pady=12,
        )

        folder_controls_frame = ctk.CTkFrame(
            master=filter_frame,
            fg_color="transparent",
        )

        folder_controls_frame.grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )

        folder_controls_frame.grid_columnconfigure(
            1,
            weight=1,
        )

        folder_filter_label = ctk.CTkLabel(
            master=folder_controls_frame,
            text="Parent folder:",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        folder_filter_label.grid(
            row=0,
            column=0,
            padx=(0, 8),
        )

        self.folder_filter_menu = ctk.CTkOptionMenu(
            master=folder_controls_frame,
            variable=self.folder_filter_var,
            values=[
                ALL_FOLDERS,
            ],
            command=lambda _value: (
                self._on_folder_filter_changed()
            ),
            height=36,
        )

        self.folder_filter_menu.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
        )

        folder_match_label = ctk.CTkLabel(
            master=folder_controls_frame,
            text="Match:",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        folder_match_label.grid(
            row=0,
            column=2,
            padx=(0, 8),
        )

        self.folder_match_mode_menu = ctk.CTkOptionMenu(
            master=folder_controls_frame,
            variable=self.folder_match_mode_var,
            values=[
                str(option)
                for option in FolderMatchMode
            ],
            command=lambda _value: (
                self._apply_filters()
            ),
            width=190,
            height=36,
            state="disabled",
        )

        self.folder_match_mode_menu.grid(
            row=0,
            column=3,
            padx=(0, 12),
        )

        folder_filter_hint = ctk.CTkLabel(
            master=folder_controls_frame,
            text=(
                "Filter the table by the asset's current "
                "project folder."
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
        )

        folder_filter_hint.grid(
            row=0,
            column=4,
            sticky="w",
        )

        sort_field_label = ctk.CTkLabel(
            master=folder_controls_frame,
            text="Sort by:",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        sort_field_label.grid(
            row=1,
            column=0,
            padx=(0, 8),
            pady=(10, 0),
        )

        self.sort_field_menu = ctk.CTkOptionMenu(
            master=folder_controls_frame,
            variable=self.sort_field_var,
            values=[
                str(option)
                for option in SortField
            ],
            command=lambda _value: (
                self._apply_filters()
            ),
            height=36,
        )

        self.sort_field_menu.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=(10, 0),
        )

        sort_direction_label = ctk.CTkLabel(
            master=folder_controls_frame,
            text="Direction:",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        sort_direction_label.grid(
            row=1,
            column=2,
            padx=(0, 8),
            pady=(10, 0),
        )

        self.sort_direction_menu = ctk.CTkOptionMenu(
            master=folder_controls_frame,
            variable=self.sort_direction_var,
            values=[
                str(option)
                for option in SortDirection
            ],
            command=lambda _value: (
                self._apply_filters()
            ),
            width=190,
            height=36,
        )

        self.sort_direction_menu.grid(
            row=1,
            column=3,
            padx=(0, 12),
            pady=(10, 0),
        )

        reset_sort_button = ctk.CTkButton(
            master=folder_controls_frame,
            text="Reset Sort",
            command=self._reset_sort,
            width=115,
            height=36,
        )

        reset_sort_button.grid(
            row=1,
            column=4,
            sticky="w",
            pady=(10, 0),
        )

        clear_button = ctk.CTkButton(
            master=filter_frame,
            text="Clear Filters",
            command=self._clear_filters,
            width=115,
            height=38,
        )

        clear_button.grid(
            row=0,
            column=5,
            padx=(6, 12),
            pady=12,
        )

    def _create_column_heading(
        self,
        parent: ctk.CTkFrame,
        text: str,
        column: int,
    ) -> None:
        """Create one heading in the results table."""
        label = ctk.CTkLabel(
            master=parent,
            text=text,
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            anchor="w",
        )

        label.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=12,
            pady=10,
        )

    def _build_organization_options(
        self,
    ) -> OrganizationOptions:
        """Build organization rules from the selected controls."""
        date_grouping = DateGrouping(
            self.date_grouping_var.get()
        )

        date_source = DateSource(
            self.date_source_var.get()
        )

        return OrganizationOptions(
            date_grouping=date_grouping,
            date_source=date_source,
        )

    def _on_organization_options_changed(
        self,
    ) -> None:
        """Refresh destinations when organization settings change."""
        options = self._build_organization_options()

        self.date_source_menu.configure(
            state=(
                "normal"
                if options.uses_date_grouping
                else "disabled"
            ),
        )

        self.organization_plan = []

        if self.scanned_assets:
            self._display_assets()

            self.status_label.configure(
                text=(
                    "Organization settings updated. "
                    "Open Preview Organization to review "
                    "the new destinations."
                ),
            )

    def _select_folder(self) -> None:
        """Open the folder picker and store the selected folder."""
        selected_path = filedialog.askdirectory(
            parent=self,
            title="Select a 3D project folder",
            mustexist=True,
        )

        if not selected_path:
            return

        self.selected_folder = Path(
            selected_path
        ).expanduser().resolve()

        self.selected_folder_label.configure(
            text=str(
                self.selected_folder
            ),
        )

        self.status_label.configure(
            text=(
                "Folder selected. Click Scan Folder "
                "to inspect its assets."
            ),
        )

        self.scan_button.configure(
            state="normal",
        )

        self._reset_scan_results()
        self._refresh_undo_button()

    def _scan_selected_folder(self) -> None:
        """Scan the selected folder and display its assets."""
        if self.selected_folder is None:
            self.status_label.configure(
                text="Please choose a project folder first.",
            )
            return

        self.scan_button.configure(
            state="disabled",
            text="Scanning...",
        )

        self.preview_button.configure(
            state="disabled",
        )

        self.duplicate_button.configure(
            state="disabled",
        )

        self.export_button.configure(
            state="disabled",
        )

        self.status_label.configure(
            text="Scanning the selected folder...",
        )

        self.update_idletasks()

        try:
            self.scanned_assets = scan_folder(
                self.selected_folder,
                recursive=self.recursive_scan_var.get(),
                include_hidden=False,
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
        ) as error:
            self.scanned_assets = []
            self.filtered_assets = []
            self.organization_plan = []
            self.duplicate_groups = []

            self.status_label.configure(
                text=f"Scan failed: {error}",
            )

            self._refresh_filter_options()
            self._display_assets()
        else:
            self.organization_plan = []
            self.duplicate_groups = []

            self._refresh_filter_options()
            self._reset_filter_controls()
            self._display_assets()

            file_count = len(
                self.scanned_assets
            )

            self.status_label.configure(
                text=(
                    f"Scan complete. "
                    f"{file_count} file"
                    f"{'' if file_count == 1 else 's'} found."
                ),
            )

            if self.scanned_assets:
                self.preview_button.configure(
                    state="normal",
                )

                self.duplicate_button.configure(
                    state="normal",
                )

                self.export_button.configure(
                    state="normal",
                )
        finally:
            self.scan_button.configure(
                state="normal",
                text="Scan Folder",
            )

            self._refresh_undo_button()

    def _refresh_filter_options(self) -> None:
        """Refresh category, extension, and folder choices."""
        self.available_categories = (
            collect_available_categories(
                self.scanned_assets
            )
        )

        self.available_extensions = (
            collect_available_extensions(
                self.scanned_assets
            )
        )

        self.available_folders = (
            collect_available_folders(
                self.scanned_assets
            )
        )

        category_values = [
            ALL_CATEGORIES,
        ] + [
            str(category)
            for category in self.available_categories
        ]

        extension_values = [
            ALL_EXTENSIONS,
        ] + list(
            self.available_extensions
        )

        self.folder_display_lookup = {
            folder_display_name(
                folder
            ): folder
            for folder in self.available_folders
        }

        folder_values = [
            ALL_FOLDERS,
        ] + list(
            self.folder_display_lookup
        )

        self.category_filter_menu.configure(
            values=category_values,
        )

        self.extension_filter_menu.configure(
            values=extension_values,
        )

        self.folder_filter_menu.configure(
            values=folder_values,
        )

        if (
            self.category_filter_var.get()
            not in category_values
        ):
            self.category_filter_var.set(
                ALL_CATEGORIES,
            )

        if (
            self.extension_filter_var.get()
            not in extension_values
        ):
            self.extension_filter_var.set(
                ALL_EXTENSIONS,
            )

        if (
            self.folder_filter_var.get()
            not in folder_values
        ):
            self.folder_filter_var.set(
                ALL_FOLDERS,
            )

        self.folder_match_mode_menu.configure(
            state=(
                "normal"
                if self.folder_filter_var.get()
                != ALL_FOLDERS
                else "disabled"
            ),
        )

    def _reset_filter_controls(self) -> None:
        """Reset all filter controls."""
        self.search_var.set(
            "",
        )

        self.category_filter_var.set(
            ALL_CATEGORIES,
        )

        self.extension_filter_var.set(
            ALL_EXTENSIONS,
        )

        self.size_filter_var.set(
            ANY_SIZE,
        )

        self.modified_filter_var.set(
            ANY_TIME,
        )

        self.folder_filter_var.set(
            ALL_FOLDERS,
        )

        self.folder_match_mode_var.set(
            str(
                FolderMatchMode.INCLUDE_SUBFOLDERS
            ),
        )

        self.folder_match_mode_menu.configure(
            state="disabled",
        )

    def _clear_filters(self) -> None:
        """Clear all active filters."""
        self._reset_filter_controls()
        self._apply_filters()

    def _on_folder_filter_changed(
        self,
    ) -> None:
        """Enable folder matching options and refresh visible assets."""
        self.folder_match_mode_menu.configure(
            state=(
                "normal"
                if self.folder_filter_var.get()
                != ALL_FOLDERS
                else "disabled"
            ),
        )

        self._apply_filters()

    def _build_folder_filter(
        self,
    ) -> FolderFilterOptions:
        """Build parent-folder filtering options from the controls."""
        selected_display_name = (
            self.folder_filter_var.get()
        )

        selected_folder = (
            self.folder_display_lookup.get(
                selected_display_name
            )
        )

        return FolderFilterOptions(
            folder=selected_folder,
            match_mode=FolderMatchMode(
                self.folder_match_mode_var.get()
            ),
        )

    def _reset_sort(self) -> None:
        """Restore filename sorting in ascending order."""
        self.sort_field_var.set(
            str(
                SortField.NAME
            ),
        )

        self.sort_direction_var.set(
            str(
                SortDirection.ASCENDING
            ),
        )

        self._apply_filters()

    def _build_sort_options(
        self,
    ) -> AssetSortOptions:
        """Build asset-sorting options from the controls."""
        return AssetSortOptions(
            field=SortField(
                self.sort_field_var.get()
            ),
            direction=SortDirection(
                self.sort_direction_var.get()
            ),
        )

    def _build_asset_filter(self) -> AssetFilter:
        """Build an AssetFilter from the interface controls."""
        selected_category_text = (
            self.category_filter_var.get()
        )

        selected_categories = frozenset(
            category
            for category in self.available_categories
            if str(category) == selected_category_text
        )

        selected_extension = (
            self.extension_filter_var.get()
        )

        selected_extensions = (
            frozenset(
                {
                    selected_extension,
                }
            )
            if selected_extension != ALL_EXTENSIONS
            else frozenset()
        )

        minimum_size, maximum_size = (
            SIZE_FILTER_OPTIONS.get(
                self.size_filter_var.get(),
                (
                    None,
                    None,
                ),
            )
        )

        modified_days = (
            MODIFIED_FILTER_OPTIONS.get(
                self.modified_filter_var.get()
            )
        )

        modified_after = (
            datetime.now()
            - timedelta(
                days=modified_days,
            )
            if modified_days is not None
            else None
        )

        return AssetFilter(
            search_text=self.search_var.get(),
            categories=selected_categories,
            extensions=selected_extensions,
            minimum_size_bytes=minimum_size,
            maximum_size_bytes=maximum_size,
            modified_after=modified_after,
        )

    def _apply_filters(self) -> None:
        """Filter scanned assets and refresh the visible rows."""
        if not self.scanned_assets:
            self.filtered_assets = []

            self.filter_count_label.configure(
                text="Showing 0 of 0 files",
            )
            return

        try:
            result = filter_assets(
                self.scanned_assets,
                self._build_asset_filter(),
            )

            folder_filtered_assets = (
                filter_assets_by_folder(
                    result.matched_assets,
                    self._build_folder_filter(),
                )
            )

            sorted_assets = sort_assets(
                folder_filtered_assets,
                self._build_sort_options(),
            )
        except ValueError as error:
            self.status_label.configure(
                text=f"Filter error: {error}",
            )
            return

        self.filtered_assets = list(
            sorted_assets
        )

        visible_count = len(
            self.filtered_assets
        )

        self.filter_count_label.configure(
            text=(
                f"Showing {visible_count} "
                f"of {result.total_count} files"
            ),
        )

        self._clear_result_rows()

        if not self.filtered_assets:
            self._show_empty_results_message(
                "No assets match the current filters."
            )
            return

        for row_number, asset in enumerate(
            self.filtered_assets
        ):
            self._create_asset_row(
                asset=asset,
                row_number=row_number,
            )

    def _reset_scan_results(self) -> None:
        """Clear results when another folder is selected."""
        self.scanned_assets = []
        self.filtered_assets = []
        self.organization_plan = []
        self.duplicate_groups = []

        self.files_count_label.configure(
            text="0",
        )

        self.total_size_label.configure(
            text="0 B",
        )

        self.categories_count_label.configure(
            text="0",
        )

        self.filter_count_label.configure(
            text="Showing 0 of 0 files",
        )

        self.preview_button.configure(
            state="disabled",
        )

        self.duplicate_button.configure(
            state="disabled",
        )

        self.export_button.configure(
            state="disabled",
        )

        self.available_categories = ()
        self.available_extensions = ()
        self.available_folders = ()
        self.folder_display_lookup = {}

        self.category_filter_menu.configure(
            values=[
                ALL_CATEGORIES,
            ],
        )

        self.extension_filter_menu.configure(
            values=[
                ALL_EXTENSIONS,
            ],
        )

        self.folder_filter_menu.configure(
            values=[
                ALL_FOLDERS,
            ],
        )

        self._reset_filter_controls()
        self._clear_result_rows()

        self._show_empty_results_message(
            "Folder selected.\n"
            "Click Scan Folder to inspect its assets."
        )

    def _display_assets(self) -> None:
        """Update the summary cards and apply active filters."""
        total_size = calculate_total_size(
            self.scanned_assets
        )

        category_summary = summarize_assets(
            self.scanned_assets
        )

        self.files_count_label.configure(
            text=str(
                len(self.scanned_assets)
            ),
        )

        self.total_size_label.configure(
            text=format_file_size(
                total_size
            ),
        )

        self.categories_count_label.configure(
            text=str(
                len(category_summary)
            ),
        )

        self._clear_result_rows()

        if not self.scanned_assets:
            self.filtered_assets = []

            self.filter_count_label.configure(
                text="Showing 0 of 0 files",
            )

            self._show_empty_results_message(
                "No supported or visible files were found."
            )
            return

        self._apply_filters()

    def _show_empty_results_message(
        self,
        message: str,
    ) -> None:
        """Display a message in the results area."""
        empty_label = ctk.CTkLabel(
            master=self.results_scroll_frame,
            text=message,
            font=ctk.CTkFont(
                size=14,
            ),
            justify="center",
        )

        empty_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=60,
        )

    def _clear_result_rows(self) -> None:
        """Remove every widget from the results area."""
        for child_widget in (
            self.results_scroll_frame.winfo_children()
        ):
            child_widget.destroy()

    def _create_asset_row(
        self,
        asset: AssetFile,
        row_number: int,
    ) -> None:
        """Create one row representing a scanned asset."""
        row_frame = ctk.CTkFrame(
            master=self.results_scroll_frame,
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
            weight=3,
        )

        row_frame.grid_columnconfigure(
            1,
            weight=2,
        )

        row_frame.grid_columnconfigure(
            2,
            weight=1,
        )

        row_frame.grid_columnconfigure(
            3,
            weight=2,
        )

        planned_destination = (
            build_destination_folder(
                asset=asset,
                options=(
                    self._build_organization_options()
                ),
            )
        )

        values = (
            str(
                asset.relative_path
            ),
            str(
                asset.category
            ),
            asset.size_text,
            str(
                planned_destination
            ),
        )

        for column, value in enumerate(
            values
        ):
            value_label = ctk.CTkLabel(
                master=row_frame,
                text=value,
                font=ctk.CTkFont(
                    size=12,
                ),
                anchor="w",
                justify="left",
            )

            value_label.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=12,
                pady=10,
            )

    def _export_inventory_report(self) -> None:
        """Export all scanned assets as a JSON or CSV inventory report."""
        if (
            self.selected_folder is None
            or not self.scanned_assets
        ):
            self.status_label.configure(
                text="Scan a folder before exporting a report.",
            )
            return

        selected_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Aniccoli Asset Inventory",
            initialdir=str(
                self.selected_folder
            ),
            initialfile="aniccoli_asset_inventory.json",
            defaultextension=".json",
            filetypes=(
                (
                    "JSON report",
                    "*.json",
                ),
                (
                    "CSV report",
                    "*.csv",
                ),
            ),
        )

        if not selected_path:
            return

        output_path = Path(
            selected_path
        ).expanduser()

        report_format = (
            ReportFormat.CSV
            if output_path.suffix.lower() == ".csv"
            else ReportFormat.JSON
        )

        self.export_button.configure(
            state="disabled",
            text="Exporting...",
        )

        self.status_label.configure(
            text="Exporting the asset inventory report...",
        )

        self.update_idletasks()

        try:
            result = export_asset_report(
                output_path=output_path,
                assets=self.scanned_assets,
                project_folder=self.selected_folder,
                options=self._build_organization_options(),
                report_format=report_format,
                overwrite=False,
            )
        except (
            PermissionError,
            OSError,
            TypeError,
            ValueError,
        ) as error:
            messagebox.showerror(
                title="Report Export Failed",
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=f"Report export failed: {error}",
            )
            return
        finally:
            self.export_button.configure(
                state=(
                    "normal"
                    if self.scanned_assets
                    else "disabled"
                ),
                text="Export Report",
            )

        messagebox.showinfo(
            title="Report Exported",
            message=(
                f"Format: {result.report_format}\n"
                f"Assets exported: {result.asset_count}\n"
                f"Combined size: {result.total_size_text}\n\n"
                f"Saved to:\n{result.report_path}"
            ),
            parent=self,
        )

        self.status_label.configure(
            text=(
                "Asset report exported successfully: "
                f"{result.report_path.name}"
            ),
        )

    def _analyze_duplicates(self) -> None:
        """Analyze and display exact-content duplicates."""
        if not self.scanned_assets:
            self.status_label.configure(
                text=(
                    "Scan a folder before "
                    "analyzing duplicates."
                ),
            )
            return

        self.duplicate_button.configure(
            state="disabled",
            text="Analyzing...",
        )

        self.status_label.configure(
            text=(
                "Analyzing possible duplicates. "
                "Large files may take a moment..."
            ),
        )

        self.update_idletasks()

        try:
            self.duplicate_groups = (
                find_duplicate_groups(
                    self.scanned_assets,
                    include_empty=False,
                )
            )
        except (
            FileNotFoundError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            self.duplicate_groups = []

            messagebox.showerror(
                title="Duplicate Analysis Failed",
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=(
                    f"Duplicate analysis failed: {error}"
                ),
            )
            return
        finally:
            self.duplicate_button.configure(
                state="normal",
                text="Analyze Duplicates",
            )

        duplicate_copy_count = (
            count_duplicate_copies(
                self.duplicate_groups
            )
        )

        if self.duplicate_groups:
            group_count = len(
                self.duplicate_groups
            )

            self.status_label.configure(
                text=(
                    f"Duplicate analysis complete. "
                    f"{group_count} group"
                    f"{'' if group_count == 1 else 's'} "
                    f"and {duplicate_copy_count} extra cop"
                    f"{'y' if duplicate_copy_count == 1 else 'ies'} "
                    "found."
                ),
            )
        else:
            self.status_label.configure(
                text=(
                    "Duplicate analysis complete. "
                    "No duplicates found."
                ),
            )

        DuplicateResultsWindow(
            master=self,
            duplicate_groups=self.duplicate_groups,
        )

    def _preview_organization(self) -> None:
        """Build and display the organization preview."""
        if (
            self.selected_folder is None
            or not self.scanned_assets
        ):
            self.status_label.configure(
                text=(
                    "Scan a folder before "
                    "creating a preview."
                ),
            )
            return

        try:
            self.organization_plan = (
                build_organization_plan(
                    project_folder=self.selected_folder,
                    assets=self.scanned_assets,
                    options=(
                        self._build_organization_options()
                    ),
                )
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            OSError,
            ValueError,
        ) as error:
            self.status_label.configure(
                text=f"Preview failed: {error}",
            )
            return

        if not self.organization_plan:
            self.status_label.configure(
                text=(
                    "All scanned assets are already "
                    "in their planned folders."
                ),
            )
        else:
            self.status_label.configure(
                text=(
                    f"Preview created for "
                    f"{len(self.organization_plan)} files."
                ),
            )

        self._open_preview_window()

    def _open_preview_window(self) -> None:
        """Open a window containing the organization plan."""
        if self.selected_folder is None:
            return

        preview_window = ctk.CTkToplevel(
            self
        )

        preview_window.title(
            "Aniccoli Organization Preview"
        )

        preview_window.geometry(
            "1050x650"
        )

        preview_window.minsize(
            850,
            500,
        )

        preview_window.transient(
            self
        )

        preview_window.grab_set()

        preview_window.grid_rowconfigure(
            2,
            weight=1,
        )

        preview_window.grid_columnconfigure(
            0,
            weight=1,
        )

        title_label = ctk.CTkLabel(
            master=preview_window,
            text="Organization Preview",
            font=ctk.CTkFont(
                size=28,
                weight="bold",
            ),
        )

        title_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=(25, 5),
        )

        conflict_count = count_conflict_renames(
            self.organization_plan
        )

        options = (
            self._build_organization_options()
        )

        summary_label = ctk.CTkLabel(
            master=preview_window,
            text=(
                f"{len(self.organization_plan)} files will move. "
                f"{conflict_count} filename conflict"
                f"{'' if conflict_count == 1 else 's'} "
                "will be safely renamed.\n"
                f"Date grouping: {options.date_grouping} • "
                f"Date source: {options.date_source}"
            ),
            font=ctk.CTkFont(
                size=14,
            ),
            anchor="w",
            justify="left",
        )

        summary_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 15),
        )

        preview_scroll = ctk.CTkScrollableFrame(
            master=preview_window,
            corner_radius=12,
        )

        preview_scroll.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=25,
            pady=(0, 15),
        )

        preview_scroll.grid_columnconfigure(
            0,
            weight=1,
        )

        if not self.organization_plan:
            empty_label = ctk.CTkLabel(
                master=preview_scroll,
                text=(
                    "Nothing needs to be moved.\n"
                    "The scanned assets are already organized."
                ),
                font=ctk.CTkFont(
                    size=15,
                ),
                justify="center",
            )

            empty_label.grid(
                row=0,
                column=0,
                padx=20,
                pady=70,
            )
        else:
            for row_number, planned_move in enumerate(
                self.organization_plan
            ):
                self._create_preview_row(
                    parent=preview_scroll,
                    planned_move=planned_move,
                    row_number=row_number,
                )

        action_frame = ctk.CTkFrame(
            master=preview_window,
            fg_color="transparent",
        )

        action_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 25),
        )

        action_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        close_button = ctk.CTkButton(
            master=action_frame,
            text="Close Preview",
            command=preview_window.destroy,
            width=145,
            height=40,
        )

        close_button.grid(
            row=0,
            column=1,
            padx=(0, 10),
        )

        organize_button = ctk.CTkButton(
            master=action_frame,
            text="Organize Files",
            command=lambda: (
                self._confirm_and_organize(
                    preview_window
                )
            ),
            width=155,
            height=40,
            state=(
                "normal"
                if self.organization_plan
                else "disabled"
            ),
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        organize_button.grid(
            row=0,
            column=2,
        )

    def _create_preview_row(
        self,
        parent: ctk.CTkScrollableFrame,
        planned_move: PlannedMove,
        row_number: int,
    ) -> None:
        """Create one source-to-destination preview row."""
        if self.selected_folder is None:
            return

        row_frame = ctk.CTkFrame(
            master=parent,
            corner_radius=9,
        )

        row_frame.grid(
            row=row_number,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        row_frame.grid_columnconfigure(
            0,
            weight=3,
        )

        row_frame.grid_columnconfigure(
            1,
            weight=4,
        )

        row_frame.grid_columnconfigure(
            2,
            weight=1,
        )

        source_label = ctk.CTkLabel(
            master=row_frame,
            text=(
                "From\n"
                f"{planned_move.asset.relative_path}"
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
            justify="left",
        )

        source_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=12,
        )

        destination_relative = (
            planned_move.destination_path.relative_to(
                self.selected_folder
            )
        )

        destination_label = ctk.CTkLabel(
            master=row_frame,
            text=(
                "To\n"
                f"{destination_relative}"
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
            justify="left",
        )

        destination_label.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=14,
            pady=12,
        )

        conflict_label = ctk.CTkLabel(
            master=row_frame,
            text=(
                "Renamed"
                if planned_move.renamed_for_conflict
                else "Ready"
            ),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        )

        conflict_label.grid(
            row=0,
            column=2,
            padx=14,
            pady=12,
        )

    def _confirm_and_organize(
        self,
        preview_window: ctk.CTkToplevel,
    ) -> None:
        """Confirm and execute the organization plan."""
        if (
            self.selected_folder is None
            or not self.organization_plan
        ):
            return

        file_count = len(
            self.organization_plan
        )

        confirmed = messagebox.askyesno(
            title="Confirm File Organization",
            message=(
                f"Aniccoli will move {file_count} file"
                f"{'' if file_count == 1 else 's'}.\n\n"
                "Existing files will not be overwritten.\n"
                "Do you want to continue?"
            ),
            parent=preview_window,
        )

        if not confirmed:
            return

        self.status_label.configure(
            text="Organizing files...",
        )

        self.update_idletasks()

        try:
            result = execute_organization_plan(
                project_folder=self.selected_folder,
                planned_moves=self.organization_plan,
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            messagebox.showerror(
                title="Organization Failed",
                message=str(
                    error
                ),
                parent=preview_window,
            )

            self.status_label.configure(
                text=f"Organization failed: {error}",
            )
            return

        preview_window.destroy()

        if result.failed_count == 0:
            messagebox.showinfo(
                title="Organization Complete",
                message=(
                    f"{result.moved_count} file"
                    f"{'' if result.moved_count == 1 else 's'} "
                    "were organized successfully."
                ),
                parent=self,
            )
        else:
            messagebox.showwarning(
                title="Organization Partially Complete",
                message=(
                    f"Moved: {result.moved_count}\n"
                    f"Failed: {result.failed_count}"
                ),
                parent=self,
            )

        moved_count = result.moved_count
        failed_count = result.failed_count

        self.organization_plan = []

        self._scan_selected_folder()
        self._refresh_undo_button()

        self.status_label.configure(
            text=(
                f"Organization finished. "
                f"Moved: {moved_count}. "
                f"Failed: {failed_count}."
            ),
        )

    def _refresh_undo_button(self) -> None:
        """Enable undo when the project has undoable history."""
        if self.selected_folder is None:
            self.undo_button.configure(
                state="disabled",
            )
            return

        try:
            latest_log = find_latest_undoable_log(
                self.selected_folder
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            OSError,
            ValueError,
        ):
            latest_log = None

        self.undo_button.configure(
            state=(
                "normal"
                if latest_log is not None
                else "disabled"
            ),
        )

    def _undo_last_organization(self) -> None:
        """Confirm and undo the latest organization."""
        if self.selected_folder is None:
            return

        confirmed = messagebox.askyesno(
            title="Undo Last Organization",
            message=(
                "Aniccoli will restore files from the latest "
                "organization operation to their original locations.\n\n"
                "Existing files will not be overwritten.\n"
                "Do you want to continue?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.undo_button.configure(
            state="disabled",
            text="Undoing...",
        )

        self.status_label.configure(
            text=(
                "Restoring files to their "
                "original locations..."
            ),
        )

        self.update_idletasks()

        try:
            result = undo_latest_organization(
                self.selected_folder
            )
        except NoUndoHistoryError as error:
            messagebox.showinfo(
                title="Nothing to Undo",
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=str(
                    error
                ),
            )
            return
        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            messagebox.showerror(
                title="Undo Failed",
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=f"Undo failed: {error}",
            )
            return
        finally:
            self.undo_button.configure(
                text="Undo Last Organization",
            )

        if result.failed_count == 0:
            messagebox.showinfo(
                title="Undo Complete",
                message=(
                    f"Restored: {result.restored_count}\n"
                    f"Already restored: "
                    f"{result.already_restored_count}\n"
                    "Failed: 0"
                ),
                parent=self,
            )
        else:
            failure_lines = [
                (
                    f"• {failure.undo_move.current_file_name}: "
                    f"{failure.error_message}"
                )
                for failure in result.failed_files[:5]
            ]

            messagebox.showwarning(
                title="Undo Partially Complete",
                message=(
                    f"Restored: {result.restored_count}\n"
                    f"Already restored: "
                    f"{result.already_restored_count}\n"
                    f"Failed: {result.failed_count}\n\n"
                    + "\n".join(
                        failure_lines
                    )
                ),
                parent=self,
            )

        restored_count = result.restored_count
        failed_count = result.failed_count

        self._scan_selected_folder()
        self._refresh_undo_button()

        self.status_label.configure(
            text=(
                f"Undo finished. "
                f"Restored: {restored_count}. "
                f"Failed: {failed_count}."
            ),
        )


def create_app() -> AniccoliApp:
    """Create and return the Aniccoli application."""
    ctk.set_appearance_mode(
        "System"
    )

    ctk.set_default_color_theme(
        "green"
    )

    return AniccoliApp()