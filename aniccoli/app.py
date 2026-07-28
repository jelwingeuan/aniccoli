"""Main desktop window for Aniccoli."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from aniccoli.scanner import (
    AssetFile,
    calculate_total_size,
    format_file_size,
    scan_folder,
    summarize_assets,
)


class AniccoliApp(ctk.CTk):
    """Main application window for Aniccoli."""

    def __init__(self) -> None:
        """Create and configure the application window."""
        super().__init__()

        self.selected_folder: Optional[Path] = None
        self.scanned_assets: list[AssetFile] = []

        self.recursive_scan_var = ctk.BooleanVar(
            value=True,
        )

        self._configure_window()
        self._create_interface()

    def _configure_window(self) -> None:
        """Configure the main application window."""
        self.title("Aniccoli")
        self.geometry("1150x760")
        self.minsize(900, 650)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

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
            font=ctk.CTkFont(size=48),
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
                "Scan and organize your Blender, Maya, Unity, "
                "texture, render, and reference files."
            ),
            font=ctk.CTkFont(size=14),
            anchor="w",
        )
        description_label.grid(
            row=1,
            column=1,
            sticky="w",
        )

    def _create_folder_controls(self) -> None:
        """Create the folder-selection and scanning controls."""
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
            columnspan=3,
            sticky="w",
            padx=25,
            pady=(20, 5),
        )

        self.selected_folder_label = ctk.CTkLabel(
            master=folder_card,
            text="No folder selected",
            font=ctk.CTkFont(size=13),
            anchor="w",
            justify="left",
            wraplength=700,
        )
        self.selected_folder_label.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=25,
            pady=(0, 15),
        )

        choose_folder_button = ctk.CTkButton(
            master=folder_card,
            text="Choose Project Folder",
            command=self._select_folder,
            width=190,
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
            padx=(25, 10),
            pady=(0, 20),
        )

        recursive_checkbox = ctk.CTkCheckBox(
            master=folder_card,
            text="Scan subfolders",
            variable=self.recursive_scan_var,
            onvalue=True,
            offvalue=False,
            font=ctk.CTkFont(size=14),
        )
        recursive_checkbox.grid(
            row=2,
            column=1,
            sticky="w",
            padx=10,
            pady=(0, 20),
        )

        self.scan_button = ctk.CTkButton(
            master=folder_card,
            text="Scan Folder",
            command=self._scan_selected_folder,
            width=150,
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
            sticky="e",
            padx=(10, 25),
            pady=(0, 20),
        )

        self.status_label = ctk.CTkLabel(
            master=folder_card,
            text="Choose a folder to begin.",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self.status_label.grid(
            row=3,
            column=0,
            columnspan=3,
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

        files_card = self._create_summary_card(
            parent=summary_frame,
            column=0,
            heading="Files found",
            starting_value="0",
        )
        self.files_count_label = files_card

        size_card = self._create_summary_card(
            parent=summary_frame,
            column=1,
            heading="Combined size",
            starting_value="0 B",
        )
        self.total_size_label = size_card

        categories_card = self._create_summary_card(
            parent=summary_frame,
            column=2,
            heading="Categories",
            starting_value="0",
        )
        self.categories_count_label = categories_card

    def _create_summary_card(
        self,
        parent: ctk.CTkFrame,
        column: int,
        heading: str,
        starting_value: str,
    ) -> ctk.CTkLabel:
        """Create one reusable summary card and return its value label."""
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
            font=ctk.CTkFont(size=13),
        )
        heading_label.pack(
            padx=20,
            pady=(0, 17),
        )

        return value_label

    def _create_results_section(self) -> None:
        """Create the scrollable asset-results section."""
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
            2,
            weight=1,
        )

        results_heading = ctk.CTkLabel(
            master=results_card,
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
            sticky="ew",
            padx=20,
            pady=(18, 12),
        )

        self.results_header = ctk.CTkFrame(
            master=results_card,
            corner_radius=8,
        )
        self.results_header.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 5),
        )

        self.results_header.grid_columnconfigure(
            0,
            weight=3,
        )
        self.results_header.grid_columnconfigure(
            1,
            weight=2,
        )
        self.results_header.grid_columnconfigure(
            2,
            weight=1,
        )
        self.results_header.grid_columnconfigure(
            3,
            weight=2,
        )

        self._create_column_heading(
            parent=self.results_header,
            text="File",
            column=0,
        )
        self._create_column_heading(
            parent=self.results_header,
            text="Category",
            column=1,
        )
        self._create_column_heading(
            parent=self.results_header,
            text="Size",
            column=2,
        )
        self._create_column_heading(
            parent=self.results_header,
            text="Planned folder",
            column=3,
        )

        self.results_scroll_frame = ctk.CTkScrollableFrame(
            master=results_card,
            corner_radius=8,
        )
        self.results_scroll_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=15,
            pady=(0, 15),
        )

        self.results_scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        self.empty_results_label = ctk.CTkLabel(
            master=self.results_scroll_frame,
            text=(
                "No scan results yet.\n"
                "Select a project folder and click Scan Folder."
            ),
            font=ctk.CTkFont(size=14),
            justify="center",
        )
        self.empty_results_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=60,
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
            text=str(self.selected_folder),
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

            self.status_label.configure(
                text=f"Scan failed: {error}",
            )

            self._display_assets()
        else:
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
        finally:
            self.scan_button.configure(
                state="normal",
                text="Scan Folder",
            )

    def _reset_scan_results(self) -> None:
        """Clear results when the user chooses another folder."""
        self.scanned_assets = []

        self.files_count_label.configure(
            text="0",
        )
        self.total_size_label.configure(
            text="0 B",
        )
        self.categories_count_label.configure(
            text="0",
        )

        self._clear_result_rows()

        self.empty_results_label = ctk.CTkLabel(
            master=self.results_scroll_frame,
            text=(
                "Folder selected.\n"
                "Click Scan Folder to inspect its assets."
            ),
            font=ctk.CTkFont(size=14),
            justify="center",
        )
        self.empty_results_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=60,
        )

    def _display_assets(self) -> None:
        """Update the summary and results table."""
        self._clear_result_rows()

        total_size = calculate_total_size(
            self.scanned_assets
        )

        category_summary = summarize_assets(
            self.scanned_assets
        )

        self.files_count_label.configure(
            text=str(len(self.scanned_assets)),
        )

        self.total_size_label.configure(
            text=format_file_size(total_size),
        )

        self.categories_count_label.configure(
            text=str(len(category_summary)),
        )

        if not self.scanned_assets:
            empty_label = ctk.CTkLabel(
                master=self.results_scroll_frame,
                text="No supported or visible files were found.",
                font=ctk.CTkFont(size=14),
            )
            empty_label.grid(
                row=0,
                column=0,
                padx=20,
                pady=60,
            )
            return

        for row_number, asset in enumerate(
            self.scanned_assets
        ):
            self._create_asset_row(
                asset=asset,
                row_number=row_number,
            )

    def _clear_result_rows(self) -> None:
        """Remove every existing widget from the results area."""
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

        file_label = ctk.CTkLabel(
            master=row_frame,
            text=str(asset.relative_path),
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
        )
        file_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=10,
        )

        category_label = ctk.CTkLabel(
            master=row_frame,
            text=str(asset.category),
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        category_label.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=12,
            pady=10,
        )

        size_label = ctk.CTkLabel(
            master=row_frame,
            text=asset.size_text,
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        size_label.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=12,
            pady=10,
        )

        destination_label = ctk.CTkLabel(
            master=row_frame,
            text=str(asset.destination),
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
        )
        destination_label.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=12,
            pady=10,
        )


def create_app() -> AniccoliApp:
    """Create and return the Aniccoli application."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")

    return AniccoliApp()