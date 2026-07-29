"""Main desktop window for Aniccoli."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from aniccoli.history import (
    NoUndoHistoryError,
    find_latest_undoable_log,
    undo_latest_organization,
)
from aniccoli.organizer import (
    PlannedMove,
    build_organization_plan,
    count_conflict_renames,
    execute_organization_plan,
)
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
        self.organization_plan: list[PlannedMove] = []

        self.recursive_scan_var = ctk.BooleanVar(
            value=True,
        )

        self._configure_window()
        self._create_interface()

    def _configure_window(self) -> None:
        """Configure the main application window."""
        self.title("Aniccoli")
        self.geometry("1220x780")
        self.minsize(980, 670)

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
                size=48
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
                "Scan, preview, organize, and restore "
                "your 3D production assets."
            ),
            font=ctk.CTkFont(
                size=14
            ),
            anchor="w",
        )

        description_label.grid(
            row=1,
            column=1,
            sticky="w",
        )

    def _create_folder_controls(self) -> None:
        """Create folder and organization controls."""
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
            columnspan=5,
            sticky="w",
            padx=25,
            pady=(20, 5),
        )

        self.selected_folder_label = ctk.CTkLabel(
            master=folder_card,
            text="No folder selected",
            font=ctk.CTkFont(
                size=13
            ),
            anchor="w",
            justify="left",
            wraplength=950,
        )

        self.selected_folder_label.grid(
            row=1,
            column=0,
            columnspan=5,
            sticky="ew",
            padx=25,
            pady=(0, 15),
        )

        choose_folder_button = ctk.CTkButton(
            master=folder_card,
            text="Choose Project Folder",
            command=self._select_folder,
            width=185,
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
            font=ctk.CTkFont(
                size=14
            ),
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
            width=130,
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
            padx=10,
            pady=(0, 20),
        )

        self.preview_button = ctk.CTkButton(
            master=folder_card,
            text="Preview Organization",
            command=self._preview_organization,
            width=175,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.preview_button.grid(
            row=2,
            column=3,
            padx=10,
            pady=(0, 20),
        )

        self.undo_button = ctk.CTkButton(
            master=folder_card,
            text="Undo Last Organization",
            command=self._undo_last_organization,
            width=185,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.undo_button.grid(
            row=2,
            column=4,
            sticky="e",
            padx=(10, 25),
            pady=(0, 20),
        )

        self.status_label = ctk.CTkLabel(
            master=folder_card,
            text="Choose a folder to begin.",
            font=ctk.CTkFont(
                size=13
            ),
            anchor="w",
        )

        self.status_label.grid(
            row=3,
            column=0,
            columnspan=5,
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
                size=13
            ),
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

        results_header = ctk.CTkFrame(
            master=results_card,
            corner_radius=8,
        )

        results_header.grid(
            row=1,
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

        self._show_empty_results_message(
            "No scan results yet.\n"
            "Select a project folder and click Scan Folder."
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
            self.organization_plan = []

            self.status_label.configure(
                text=f"Scan failed: {error}",
            )

            self._display_assets()
        else:
            self.organization_plan = []
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
        finally:
            self.scan_button.configure(
                state="normal",
                text="Scan Folder",
            )

            self._refresh_undo_button()

    def _reset_scan_results(self) -> None:
        """Clear results when another folder is selected."""
        self.scanned_assets = []
        self.organization_plan = []

        self.files_count_label.configure(
            text="0",
        )

        self.total_size_label.configure(
            text="0 B",
        )

        self.categories_count_label.configure(
            text="0",
        )

        self.preview_button.configure(
            state="disabled",
        )

        self._clear_result_rows()

        self._show_empty_results_message(
            "Folder selected.\n"
            "Click Scan Folder to inspect its assets."
        )

    def _display_assets(self) -> None:
        """Update the summary cards and results table."""
        self._clear_result_rows()

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

        if not self.scanned_assets:
            self._show_empty_results_message(
                "No supported or visible files were found."
            )
            return

        for row_number, asset in enumerate(
            self.scanned_assets
        ):
            self._create_asset_row(
                asset=asset,
                row_number=row_number,
            )

    def _show_empty_results_message(
        self,
        message: str,
    ) -> None:
        """Display a message in the results area."""
        empty_label = ctk.CTkLabel(
            master=self.results_scroll_frame,
            text=message,
            font=ctk.CTkFont(
                size=14
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

        values = (
            str(asset.relative_path),
            str(asset.category),
            asset.size_text,
            str(asset.destination),
        )

        for column, value in enumerate(
            values
        ):
            value_label = ctk.CTkLabel(
                master=row_frame,
                text=value,
                font=ctk.CTkFont(
                    size=12
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

    def _preview_organization(self) -> None:
        """Build and display the safe organization preview."""
        if (
            self.selected_folder is None
            or not self.scanned_assets
        ):
            self.status_label.configure(
                text="Scan a folder before creating a preview.",
            )
            return

        try:
            self.organization_plan = (
                build_organization_plan(
                    project_folder=self.selected_folder,
                    assets=self.scanned_assets,
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

        summary_label = ctk.CTkLabel(
            master=preview_window,
            text=(
                f"{len(self.organization_plan)} files will move. "
                f"{conflict_count} filename conflict"
                f"{'' if conflict_count == 1 else 's'} "
                "will be safely renamed."
            ),
            font=ctk.CTkFont(
                size=14
            ),
            anchor="w",
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
                    size=15
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
            command=lambda: self._confirm_and_organize(
                preview_window
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
                size=12
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
                size=12
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

        conflict_text = (
            "Renamed"
            if planned_move.renamed_for_conflict
            else "Ready"
        )

        conflict_label = ctk.CTkLabel(
            master=row_frame,
            text=conflict_text,
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
        """Ask for confirmation and execute the organization plan."""
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
                message=str(error),
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
        """Enable undo when the selected project has undoable history."""
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
        """Confirm and undo the latest organization operation."""
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
            text="Restoring files to their original locations...",
        )

        self.update_idletasks()

        try:
            result = undo_latest_organization(
                self.selected_folder
            )
        except NoUndoHistoryError as error:
            messagebox.showinfo(
                title="Nothing to Undo",
                message=str(error),
                parent=self,
            )

            self.status_label.configure(
                text=str(error),
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
                message=str(error),
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
                    + "\n".join(failure_lines)
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