"""Main desktop window for Aniccoli."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import sys
from tkinter import filedialog, messagebox
from typing import Optional, TypeVar

import customtkinter as ctk

from aniccoli.audit import audit_assets
from aniccoli.audit_window import AssetAuditWindow
from aniccoli.categories import AssetCategory
from aniccoli.duplicate_window import DuplicateResultsWindow
from aniccoli.duplicates import (
    DuplicateGroup,
    count_duplicate_copies,
    find_duplicate_groups,
)
from aniccoli.file_actions import reveal_in_file_manager
from aniccoli.i18n import LANGUAGES, choice_key, translate
from aniccoli.filters import (
    AssetQuery,
    FolderMatchMode,
    SortDirection,
    SortField,
    collect_available_categories,
    collect_available_extensions,
    collect_available_folders,
    query_assets,
)
from aniccoli.moves import (
    JournalKind,
    NothingToReverseError,
    apply_moves,
    latest_journal,
    reverse_latest,
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
)
from aniccoli.preferences import (
    AppPreferences,
    load_preferences,
    save_preferences,
    update_preferences,
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
from aniccoli.selection import (
    AssetSelection,
    clear_asset_selection,
    select_all_assets,
    selected_assets,
    summarize_selection,
)
from aniccoli.statistics import build_asset_statistics
from aniccoli.statistics_window import AssetStatisticsWindow


_OriginalCTkScrollableFrame = ctk.CTkScrollableFrame


class NaturalScrollableFrame(_OriginalCTkScrollableFrame):
    """
    CustomTkinter scrollable frame with reliable trackpad and wheel input.

    The wheel handler is attached to the containing window rather than the
    global "all" binding. Every gesture is routed directly to the canvas
    underneath the pointer.
    """

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Create the frame and install window-level scrolling."""
        super().__init__(
            *args,
            **kwargs,
        )

        top_level = self.winfo_toplevel()

        top_level.bind(
            "<MouseWheel>",
            self._handle_natural_scroll,
            add="+",
        )

        top_level.bind(
            "<Button-4>",
            self._handle_natural_scroll,
            add="+",
        )

        top_level.bind(
            "<Button-5>",
            self._handle_natural_scroll,
            add="+",
        )

        try:
            self._parent_canvas.configure(
                yscrollincrement=1,
            )

            top_level.bind(
                "<TouchpadScroll>",
                self._handle_touchpad_scroll,
                add="+",
            )
        except Exception:
            # Tk 8.6 does not provide the TouchpadScroll event.
            pass

    def _pointer_is_over_canvas(
        self,
        event: Any,
    ) -> bool:
        """Return True when the pointer is inside this frame's canvas."""
        canvas = self._parent_canvas

        try:
            if not canvas.winfo_ismapped():
                return False

            pointer_x = int(
                getattr(
                    event,
                    "x_root",
                    canvas.winfo_pointerx(),
                )
            )

            pointer_y = int(
                getattr(
                    event,
                    "y_root",
                    canvas.winfo_pointery(),
                )
            )

            left = canvas.winfo_rootx()
            top = canvas.winfo_rooty()
            right = left + canvas.winfo_width()
            bottom = top + canvas.winfo_height()
        except Exception:
            return False

        return (
            left <= pointer_x < right
            and top <= pointer_y < bottom
        )

    def _wheel_units(
        self,
        event: Any,
    ) -> int:
        """Convert a platform wheel event into canvas scroll units."""
        button_number = getattr(
            event,
            "num",
            None,
        )

        if button_number == 4:
            return -1

        if button_number == 5:
            return 1

        try:
            delta = int(
                getattr(
                    event,
                    "delta",
                    0,
                )
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0

        if delta == 0:
            return 0

        if sys.platform == "darwin":
            return -delta

        if sys.platform.startswith(
            "win"
        ):
            units = -int(
                delta / 120
            )

            if units == 0:
                return (
                    -1
                    if delta > 0
                    else 1
                )

            return units

        return (
            -1
            if delta > 0
            else 1
        )

    def _touchpad_vertical_delta(
        self,
        event: Any,
    ) -> int:
        """Extract Tk 8.7/9's precise vertical touchpad delta."""
        try:
            packed_delta = int(
                getattr(
                    event,
                    "delta",
                    0,
                )
                or 0
            )

            delta_values = self.tk.call(
                "tk::PreciseScrollDeltas",
                packed_delta,
            )

            delta_x_text, delta_y_text = (
                self.tk.splitlist(
                    delta_values
                )
            )

            del delta_x_text

            return int(
                delta_y_text
            )
        except Exception:
            return 0

    def _handle_touchpad_scroll(
        self,
        event: Any,
    ) -> str | None:
        """Handle native two-finger scrolling on Tk 8.7 and Tk 9."""
        if self._orientation != "vertical":
            return None

        if not self._pointer_is_over_canvas(
            event
        ):
            return None

        delta_y = self._touchpad_vertical_delta(
            event
        )

        if delta_y == 0:
            return None

        pixel_units = -delta_y

        try:
            first_visible, last_visible = (
                self._parent_canvas.yview()
            )
        except Exception:
            return None

        if (
            pixel_units < 0
            and first_visible <= 0.0
        ):
            return "break"

        if (
            pixel_units > 0
            and last_visible >= 1.0
        ):
            return "break"

        self._parent_canvas.yview_scroll(
            pixel_units,
            "units",
        )

        return "break"

    def _handle_natural_scroll(
        self,
        event: Any,
    ) -> str | None:
        """Scroll this frame when the pointer is over its canvas."""
        if self._orientation != "vertical":
            return None

        if not self._pointer_is_over_canvas(
            event
        ):
            return None

        units = self._wheel_units(
            event
        )

        if units == 0:
            return None

        try:
            first_visible, last_visible = (
                self._parent_canvas.yview()
            )
        except Exception:
            return None

        if (
            units < 0
            and first_visible <= 0.0
        ):
            return "break"

        if (
            units > 0
            and last_visible >= 1.0
        ):
            return "break"

        self._parent_canvas.yview_scroll(
            units,
            "units",
        )

        return "break"


ctk.CTkScrollableFrame = NaturalScrollableFrame


APP_NAME = "Aniccoli"
APP_VERSION = "1.0.0"

APP_BACKGROUND = ("#ECEEE9", "#252726")
SIDEBAR_BACKGROUND = ("#E1E4DE", "#1F2120")
PANEL_BACKGROUND = ("#F7F8F5", "#2C2E2D")
CARD_BACKGROUND = ("#FFFFFF", "#313332")
ROW_BACKGROUND = ("#FFFFFF", "#313332")
ROW_ALT_BACKGROUND = ("#F3F5F1", "#2C2E2D")
BORDER_COLOR = ("#D2D7CF", "#3A3D3B")
TEXT_COLOR = ("#1E231F", "#E3E6E1")
MUTED_TEXT = ("#5B635C", "#9AA19A")
ACCENT_COLOR = ("#2E6B3A", "#7DBF73")
ACCENT_HOVER = ("#245830", "#6AAE60")
ACCENT_SOFT = ("#DCE9D8", "#2C3D2C")
DANGER_TEXT = ("#8E3B2C", "#E79B8C")
DANGER_SOFT = ("#F2DEDA", "#45302C")
CONTROL_BUTTON = ("#E1E4DE", "#3A3D3B")
CONTROL_HOVER = ("#D2D7CF", "#454947")

PATH_FONT_FAMILY = (
    "Menlo"
    if sys.platform == "darwin"
    else "Consolas"
    if sys.platform.startswith("win")
    else "DejaVu Sans Mono"
)

# Colour is reserved for asset type: the composition bar, legend, and
# row stripes all use these, so one hue always means one kind of file.
CATEGORY_GROUP_COLORS: dict[str, tuple[str, str]] = {
    "scenes": ("#A9531A", "#E8995A"),
    "models": ("#2D74A8", "#72AEDB"),
    "textures": ("#806500", "#DDBB4C"),
    "unity": ("#6A55AE", "#A996E0"),
    "media": ("#1A7A70", "#62C2B6"),
    "other": ("#6B716C", "#9BA19C"),
}


def _category_group(category: AssetCategory) -> str:
    """Return the colour group an asset category belongs to."""
    if category in (
        AssetCategory.BLENDER,
        AssetCategory.MAYA,
        AssetCategory.UNITY_SCENE,
    ):
        return "scenes"

    if category.name.startswith("TEXTURE_"):
        return "textures"

    if category.name.startswith("UNITY_"):
        return "unity"

    if category.value.endswith("Model"):
        return "models"

    if category in (
        AssetCategory.REFERENCE,
        AssetCategory.RENDER,
        AssetCategory.AUDIO,
        AssetCategory.VIDEO,
    ):
        return "media"

    return "other"


# shortcut: rows render in pages because each CTk row costs ~10 ms and the
# cost grows with count; switch to ttk.Treeview if users need 10k+ rows.
ROW_PAGE_SIZE = 100

# Dropdown choices are stored as translation keys and shown translated.
ALL_CATEGORIES = "all_categories"
ALL_EXTENSIONS = "all_extensions"
ALL_FOLDERS = "all_folders"
ANY_SIZE = "size_any"
ANY_TIME = "modified_any"


SIZE_FILTER_OPTIONS: dict[
    str,
    tuple[int | None, int | None],
] = {
    ANY_SIZE: (None, None),
    "size_up_to_1mb": (
        None,
        1024**2,
    ),
    "size_1_to_10mb": (
        1024**2,
        10 * 1024**2,
    ),
    "size_10_to_100mb": (
        10 * 1024**2,
        100 * 1024**2,
    ),
    "size_over_100mb": (
        100 * 1024**2,
        None,
    ),
}


MODIFIED_FILTER_OPTIONS: dict[str, int | None] = {
    ANY_TIME: None,
    "modified_24h": 1,
    "modified_7d": 7,
    "modified_30d": 30,
    "modified_90d": 90,
}

_Choice = TypeVar("_Choice")


class AniccoliApp(ctk.CTk):
    """Main application window for Aniccoli."""

    def __init__(self) -> None:
        """Create and configure the application window."""
        super().__init__()

        self.preferences: AppPreferences = load_preferences()

        self.language_code = self.preferences.language
        self.language_var = ctk.StringVar(
            value=LANGUAGES[
                self.language_code
            ],
        )

        saved_project_path = self.preferences.last_project_path

        self.selected_folder: Optional[Path] = (
            saved_project_path.resolve()
            if (
                saved_project_path is not None
                and saved_project_path.exists()
                and saved_project_path.is_dir()
            )
            else None
        )

        self.scanned_assets: list[AssetFile] = []
        self.filtered_assets: list[AssetFile] = []
        self._search_job: str | None = None
        self.organization_plan: list[PlannedMove] = []
        self.duplicate_groups: list[DuplicateGroup] = []

        self.asset_selection = AssetSelection()

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
            value=self.preferences.recursive_scan,
        )

        self.search_var = ctk.StringVar(
            value="",
        )

        self.category_filter_var = ctk.StringVar(
            value=self._label(ALL_CATEGORIES),
        )

        self.extension_filter_var = ctk.StringVar(
            value=self._label(ALL_EXTENSIONS),
        )

        self.size_filter_var = ctk.StringVar(
            value=self._label(ANY_SIZE),
        )

        self.modified_filter_var = ctk.StringVar(
            value=self._label(ANY_TIME),
        )

        self.folder_filter_var = ctk.StringVar(
            value=self._label(ALL_FOLDERS),
        )

        self.folder_match_mode_var = ctk.StringVar(
            value=self._label(FolderMatchMode.INCLUDE_SUBFOLDERS),
        )

        self.sort_field_var = ctk.StringVar(
            value=self._label(SortField.NAME),
        )

        self.sort_direction_var = ctk.StringVar(
            value=self._label(SortDirection.ASCENDING),
        )

        self.date_grouping_var = ctk.StringVar(
            value=self._label(self.preferences.date_grouping),
        )

        self.date_source_var = ctk.StringVar(
            value=self._label(self.preferences.date_source),
        )

        self._configure_window()
        self._create_interface()
        self._bind_keyboard_shortcuts()
        self._restore_saved_project_folder()

        self.protocol(
            "WM_DELETE_WINDOW",
            self._on_close,
        )

    def _t(
        self,
        key: str,
        **values: object,
    ) -> str:
        """Return translated interface text."""
        return translate(
            self.language_code,
            key,
            **values,
        )

    def _label(
        self,
        choice: object,
    ) -> str:
        """Return the translated label a dropdown shows for a choice."""
        return self._t(
            choice_key(choice)
        )

    def _chosen(
        self,
        variable: ctk.StringVar,
        choices: Iterable[_Choice],
    ) -> _Choice:
        """Return the choice whose translated label a dropdown shows."""
        options = list(
            choices
        )

        return next(
            (
                option
                for option in options
                if self._label(option) == variable.get()
            ),
            options[0],
        )

    def _change_language(
        self,
        selected_label: str,
    ) -> None:
        """Change language and rebuild the main interface."""
        selected_code = next(
            (
                code
                for code, label in LANGUAGES.items()
                if label == selected_label
            ),
            "en",
        )

        if selected_code == self.language_code:
            return

        options = self._build_organization_options()

        self.language_code = selected_code
        self.language_var.set(
            LANGUAGES[
                selected_code
            ],
        )

        # Dropdowns show translated labels, so relabel the kept settings.
        self.date_grouping_var.set(
            self._label(options.date_grouping),
        )

        self.date_source_var.set(
            self._label(options.date_source),
        )

        self._save_current_preferences()

        self.main_container.destroy()
        self._create_interface()

        self._reset_filter_controls()
        self.sort_field_var.set(
            self._label(SortField.NAME),
        )
        self.sort_direction_var.set(
            self._label(SortDirection.ASCENDING),
        )

        if self.selected_folder is not None:
            self.selected_folder_label.configure(
                text=str(
                    self.selected_folder
                ),
            )
            self.scan_button.configure(
                state="normal",
            )

        options = self._build_organization_options()
        self.date_source_menu.configure(
            state=(
                "normal"
                if options.uses_date_grouping
                else "disabled"
            ),
        )

        self._refresh_filter_options()

        if self.scanned_assets:
            self._display_assets()
            self.duplicate_button.configure(
                state="normal",
            )
            self.statistics_button.configure(
                state="normal",
            )
            self.audit_button.configure(
                state="normal",
            )
            self._update_selection_summary()
        else:
            self._reset_scan_results()
            self._clear_result_rows()

            if self.selected_folder is not None:
                self.selected_folder_label.configure(
                    text=str(
                        self.selected_folder
                    ),
                )
                self.scan_button.configure(
                    state="normal",
                )
                empty_message = self._t(
                    "empty_folder_selected"
                )
            else:
                empty_message = self._t(
                    "empty_initial"
                )

            self._show_empty_results_message(
                empty_message
            )

        self._refresh_undo_button()
        self.status_label.configure(
            text=self._t(
                "language_changed",
                language=selected_label,
            ),
        )

    def _configure_window(self) -> None:
        """Configure the main application window."""
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1480x920")
        self.minsize(1180, 760)
        self.configure(
            fg_color=APP_BACKGROUND,
        )

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
        )

        self.main_container.grid_columnconfigure(
            0,
            minsize=300,
        )

        self.main_container.grid_columnconfigure(
            1,
            weight=1,
        )

        self.main_container.grid_rowconfigure(
            0,
            weight=1,
        )

        self.sidebar = ctk.CTkScrollableFrame(
            master=self.main_container,
            width=300,
            corner_radius=0,
            fg_color=SIDEBAR_BACKGROUND,
            scrollbar_button_color=BORDER_COLOR,
            scrollbar_button_hover_color=ACCENT_COLOR,
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.sidebar.grid_columnconfigure(
            0,
            weight=1,
        )

        self.workspace = ctk.CTkFrame(
            master=self.main_container,
            corner_radius=0,
            fg_color="transparent",
        )

        self.workspace.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(26, 30),
            pady=24,
        )

        self.workspace.grid_columnconfigure(
            0,
            weight=1,
        )

        self.workspace.grid_rowconfigure(
            2,
            weight=1,
        )

        self._create_header()
        self._create_folder_controls()
        self._create_summary_section()
        self._create_results_section()

    def _create_header(self) -> None:
        """Create the brand area and workspace heading."""
        brand_frame = ctk.CTkFrame(
            master=self.sidebar,
            fg_color="transparent",
        )

        brand_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(22, 18),
        )

        brand_frame.grid_columnconfigure(
            1,
            weight=1,
        )

        logo_frame = ctk.CTkFrame(
            master=brand_frame,
            width=54,
            height=54,
            corner_radius=16,
            fg_color=ACCENT_SOFT,
        )

        logo_frame.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(0, 12),
        )

        logo_frame.grid_propagate(
            False
        )

        logo_label = ctk.CTkLabel(
            master=logo_frame,
            text="🥦",
            font=ctk.CTkFont(
                size=30,
            ),
        )

        logo_label.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

        title_label = ctk.CTkLabel(
            master=brand_frame,
            text=APP_NAME,
            font=ctk.CTkFont(
                size=23,
                weight="bold",
            ),
            anchor="w",
        )

        title_label.grid(
            row=0,
            column=1,
            sticky="sw",
        )

        stage_label = ctk.CTkLabel(
            master=brand_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        stage_label.grid(
            row=1,
            column=1,
            sticky="nw",
            pady=(2, 0),
        )

        workspace_header = ctk.CTkFrame(
            master=self.workspace,
            fg_color="transparent",
        )

        workspace_header.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 18),
        )

        workspace_header.grid_columnconfigure(
            0,
            weight=1,
        )

        heading_label = ctk.CTkLabel(
            master=workspace_header,
            text=self._t("workspace_title"),
            font=ctk.CTkFont(
                size=24,
                weight="bold",
            ),
            anchor="w",
        )

        heading_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        subtitle_label = ctk.CTkLabel(
            master=workspace_header,
            text=self._t("workspace_subtitle"),
            font=ctk.CTkFont(
                size=13,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        subtitle_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(3, 0),
        )

        language_frame = ctk.CTkFrame(
            master=workspace_header,
            fg_color="transparent",
        )

        language_frame.grid(
            row=0,
            column=1,
            rowspan=2,
            padx=(15, 8),
        )

        language_label = ctk.CTkLabel(
            master=language_frame,
            text=self._t("language"),
            font=ctk.CTkFont(
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        language_label.pack(
            fill="x",
            pady=(0, 3),
        )

        self.language_menu = ctk.CTkOptionMenu(
            master=language_frame,
            variable=self.language_var,
            values=list(
                LANGUAGES.values()
            ),
            command=self._change_language,
            width=145,
            height=34,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.language_menu.pack()

        help_button = ctk.CTkButton(
            master=workspace_header,
            text=self._t("help_shortcuts"),
            command=self._open_about_window,
            width=135,
            height=38,
            corner_radius=10,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        help_button.grid(
            row=0,
            column=2,
            rowspan=2,
            padx=(15, 0),
        )

    def _create_folder_controls(self) -> None:
        """Create the project workflow controls inside the sidebar."""
        project_section_label = ctk.CTkLabel(
            master=self.sidebar,
            text=self._t("project"),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=TEXT_COLOR,
            anchor="w",
        )

        project_section_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 7),
        )

        project_card = ctk.CTkFrame(
            master=self.sidebar,
            fg_color="transparent",
        )

        project_card.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 18),
        )

        project_card.grid_columnconfigure(
            0,
            weight=1,
        )

        selected_title = ctk.CTkLabel(
            master=project_card,
            text=self._t("selected_folder"),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        selected_title.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=15,
            pady=(14, 3),
        )

        self.selected_folder_label = ctk.CTkLabel(
            master=project_card,
            text=self._t("no_folder"),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            anchor="w",
            justify="left",
            wraplength=235,
        )

        self.selected_folder_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 12),
        )

        choose_folder_button = ctk.CTkButton(
            master=project_card,
            text=self._t("choose_project"),
            command=self._select_folder,
            height=39,
            corner_radius=10,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        choose_folder_button.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10),
        )

        recursive_checkbox = ctk.CTkCheckBox(
            master=project_card,
            text=self._t("include_subfolders"),
            variable=self.recursive_scan_var,
            onvalue=True,
            offvalue=False,
            command=self._on_recursive_scan_changed,
            font=ctk.CTkFont(
                size=12,
            ),
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
        )

        recursive_checkbox.grid(
            row=3,
            column=0,
            sticky="w",
            padx=16,
            pady=(0, 12),
        )

        self.scan_button = ctk.CTkButton(
            master=project_card,
            text=self._t("scan_project"),
            command=self._scan_selected_folder,
            height=42,
            state="disabled",
            corner_radius=11,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        )

        self.scan_button.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 15),
        )

        workflow_section_label = ctk.CTkLabel(
            master=self.sidebar,
            text=self._t("workflow"),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=TEXT_COLOR,
            anchor="w",
        )

        workflow_section_label.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 7),
        )

        workflow_card = ctk.CTkFrame(
            master=self.sidebar,
            fg_color="transparent",
        )

        workflow_card.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 18),
        )

        workflow_card.grid_columnconfigure(
            0,
            weight=1,
        )

        self.preview_button = ctk.CTkButton(
            master=workflow_card,
            text=self._t("preview_organization"),
            command=self._preview_organization,
            height=40,
            state="disabled",
            corner_radius=10,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        self.preview_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=(14, 8),
        )

        self.duplicate_button = ctk.CTkButton(
            master=workflow_card,
            text=self._t("analyze_duplicates"),
            command=self._analyze_duplicates,
            height=38,
            state="disabled",
            corner_radius=10,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        self.duplicate_button.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 14),
        )

        organization_section_label = ctk.CTkLabel(
            master=self.sidebar,
            text=self._t("organization"),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=TEXT_COLOR,
            anchor="w",
        )

        organization_section_label.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 7),
        )

        organization_card = ctk.CTkFrame(
            master=self.sidebar,
            fg_color="transparent",
        )

        organization_card.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 18),
        )

        organization_card.grid_columnconfigure(
            0,
            weight=1,
        )

        grouping_label = ctk.CTkLabel(
            master=organization_card,
            text=self._t("date_grouping"),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            anchor="w",
        )

        grouping_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=(13, 5),
        )

        self.date_grouping_menu = ctk.CTkOptionMenu(
            master=organization_card,
            variable=self.date_grouping_var,
            values=[
                self._label(option)
                for option in DateGrouping
            ],
            command=lambda _value: (
                self._on_organization_options_changed()
            ),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.date_grouping_menu.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 10),
        )

        source_label = ctk.CTkLabel(
            master=organization_card,
            text=self._t("date_source"),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            anchor="w",
        )

        source_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 5),
        )

        self.date_source_menu = ctk.CTkOptionMenu(
            master=organization_card,
            variable=self.date_source_var,
            values=[
                self._label(option)
                for option in DateSource
            ],
            command=lambda _value: (
                self._on_organization_options_changed()
            ),
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.date_source_menu.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 14),
        )

        tools_section_label = ctk.CTkLabel(
            master=self.sidebar,
            text=self._t("tools_recovery"),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=TEXT_COLOR,
            anchor="w",
        )

        tools_section_label.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 7),
        )

        tools_card = ctk.CTkFrame(
            master=self.sidebar,
            fg_color="transparent",
        )

        tools_card.grid(
            row=8,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 18),
        )

        tools_card.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="sidebar-tools",
        )

        self.statistics_button = ctk.CTkButton(
            master=tools_card,
            text=self._t("statistics"),
            command=self._open_project_statistics,
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        self.statistics_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(12, 5),
            pady=(12, 8),
        )

        self.audit_button = ctk.CTkButton(
            master=tools_card,
            text=self._t("asset_health"),
            command=self._open_asset_health_audit,
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        self.audit_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 12),
            pady=(12, 8),
        )

        self.export_button = ctk.CTkButton(
            master=tools_card,
            text=self._t("export_report"),
            command=self._export_inventory_report,
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        self.export_button.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(12, 5),
            pady=(0, 12),
        )

        self.undo_button = ctk.CTkButton(
            master=tools_card,
            text=self._t("undo_organize"),
            command=self._undo_last_organization,
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color="transparent",
            hover_color=DANGER_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=DANGER_TEXT,
        )

        self.undo_button.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(5, 12),
            pady=(0, 12),
        )

        status_card = ctk.CTkFrame(
            master=self.sidebar,
            corner_radius=14,
            fg_color=ACCENT_SOFT,
        )

        status_card.grid(
            row=9,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 20),
        )

        status_title = ctk.CTkLabel(
            master=status_card,
            text=self._t("status"),
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            text_color=ACCENT_COLOR,
            anchor="w",
        )

        status_title.pack(
            fill="x",
            padx=14,
            pady=(12, 3),
        )

        self.status_label = ctk.CTkLabel(
            master=status_card,
            text=self._t("choose_begin"),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
            justify="left",
            wraplength=235,
        )

        self.status_label.pack(
            fill="x",
            padx=14,
            pady=(0, 13),
        )

    def _create_summary_section(self) -> None:
        """Create the scan totals and the category composition bar."""
        summary_frame = ctk.CTkFrame(
            master=self.workspace,
            fg_color="transparent",
        )

        summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 18),
        )

        summary_frame.grid_columnconfigure(
            4,
            weight=1,
        )

        self.files_count_label = self._create_summary_figure(
            parent=summary_frame,
            column=0,
            heading=self._t("files_found"),
            starting_value="0",
        )

        self.total_size_label = self._create_summary_figure(
            parent=summary_frame,
            column=1,
            heading=self._t("combined_size"),
            starting_value="0 B",
        )

        self.categories_count_label = self._create_summary_figure(
            parent=summary_frame,
            column=2,
            heading=self._t("categories"),
            starting_value="0",
        )

        self.selection_count_label = self._create_summary_figure(
            parent=summary_frame,
            column=3,
            heading=self._t("selected"),
            starting_value="0 / 0",
        )

        self.category_bar = ctk.CTkFrame(
            master=summary_frame,
            fg_color="transparent",
            height=10,
        )

        self.category_bar.grid(
            row=1,
            column=0,
            columnspan=5,
            sticky="ew",
            pady=(14, 8),
        )

        self.category_legend = ctk.CTkFrame(
            master=summary_frame,
            fg_color="transparent",
            height=18,
        )

        self.category_legend.grid(
            row=2,
            column=0,
            columnspan=5,
            sticky="ew",
        )

        self._refresh_category_bar()

    def _create_summary_figure(
        self,
        parent: ctk.CTkFrame,
        column: int,
        heading: str,
        starting_value: str,
    ) -> ctk.CTkLabel:
        """Create one summary figure and return its value label."""
        figure_frame = ctk.CTkFrame(
            master=parent,
            fg_color="transparent",
        )

        figure_frame.grid(
            row=0,
            column=column,
            sticky="w",
            padx=(0, 40),
        )

        value_label = ctk.CTkLabel(
            master=figure_frame,
            text=starting_value,
            font=ctk.CTkFont(
                size=21,
                weight="bold",
            ),
            anchor="w",
            height=28,
        )

        value_label.pack(
            anchor="w",
        )

        heading_label = ctk.CTkLabel(
            master=figure_frame,
            text=heading,
            font=ctk.CTkFont(
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
            height=16,
        )

        heading_label.pack(
            anchor="w",
        )

        return value_label

    def _refresh_category_bar(self) -> None:
        """Redraw the composition bar and legend from the scanned assets."""
        for widget in (
            *self.category_bar.winfo_children(),
            *self.category_legend.winfo_children(),
        ):
            widget.destroy()

        group_counts = Counter(
            _category_group(asset.category)
            for asset in self.scanned_assets
        )

        # An empty scan still draws one grey track so the layout never jumps.
        segments = [
            (group, CATEGORY_GROUP_COLORS[group], group_counts[group])
            for group in CATEGORY_GROUP_COLORS
            if group_counts[group]
        ] or [("", BORDER_COLOR, 1)]

        for column in range(len(CATEGORY_GROUP_COLORS)):
            self.category_bar.grid_columnconfigure(
                column,
                weight=0,
            )

        for column, (group, color, count) in enumerate(
            segments
        ):
            self.category_bar.grid_columnconfigure(
                column,
                weight=count,
            )

            segment = ctk.CTkFrame(
                master=self.category_bar,
                width=1,
                height=10,
                corner_radius=3,
                fg_color=color,
            )

            segment.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(
                    0,
                    0 if column == len(segments) - 1 else 2,
                ),
            )

            if not group:
                continue

            legend_dot = ctk.CTkFrame(
                master=self.category_legend,
                width=8,
                height=8,
                corner_radius=4,
                fg_color=color,
            )

            legend_dot.pack(
                side="left",
                padx=(0, 6),
            )

            legend_label = ctk.CTkLabel(
                master=self.category_legend,
                text=f"{self._t('group_' + group)}  {count}",
                font=ctk.CTkFont(
                    size=11,
                ),
                text_color=MUTED_TEXT,
                height=18,
            )

            legend_label.pack(
                side="left",
                padx=(0, 18),
            )

    def _create_results_section(self) -> None:
        """Create filters and the scrollable results section."""
        results_card = ctk.CTkFrame(
            master=self.workspace,
            corner_radius=16,
            fg_color=PANEL_BACKGROUND,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        results_card.grid(
            row=2,
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
            padx=18,
            pady=(16, 10),
        )

        heading_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        results_heading = ctk.CTkLabel(
            master=heading_frame,
            text=self._t("scanned_assets"),
            font=ctk.CTkFont(
                size=16,
                weight="bold",
            ),
            anchor="w",
        )

        results_heading.grid(
            row=0,
            column=0,
            sticky="w",
        )

        results_hint = ctk.CTkLabel(
            master=heading_frame,
            text=self._t("results_hint"),
            font=ctk.CTkFont(
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        results_hint.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 0),
        )

        count_pill = ctk.CTkFrame(
            master=heading_frame,
            corner_radius=12,
            fg_color=ACCENT_SOFT,
        )

        count_pill.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
        )

        self.filter_count_label = ctk.CTkLabel(
            master=count_pill,
            text=self._t("showing_files", visible=0, total=0),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=ACCENT_COLOR,
        )

        self.filter_count_label.pack(
            padx=12,
            pady=7,
        )

        self._create_filter_controls(
            results_card
        )

        results_header = ctk.CTkFrame(
            master=results_card,
            fg_color="transparent",
        )

        results_header.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 6),
        )

        results_header.grid_columnconfigure(0, weight=0)
        results_header.grid_columnconfigure(1, weight=3)
        results_header.grid_columnconfigure(2, weight=2)
        results_header.grid_columnconfigure(3, weight=1)
        results_header.grid_columnconfigure(4, weight=2)
        results_header.grid_columnconfigure(5, weight=0)

        headings = (
            self._t("use"),
            self._t("asset"),
            self._t("category"),
            self._t("size"),
            self._t("planned_destination"),
            self._t("action"),
        )

        for column, heading in enumerate(
            headings
        ):
            self._create_column_heading(
                parent=results_header,
                text=heading,
                column=column,
            )

        self.results_scroll_frame = ctk.CTkScrollableFrame(
            master=results_card,
            corner_radius=10,
            fg_color="transparent",
            scrollbar_button_color=BORDER_COLOR,
            scrollbar_button_hover_color=ACCENT_COLOR,
        )

        self.results_scroll_frame.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=14,
            pady=(0, 14),
        )

        self.results_scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        self._show_empty_results_message(
            self._t(
                "empty_initial"
            )
        )

    def _create_filter_controls(
        self,
        parent: ctk.CTkFrame,
    ) -> None:
        """Create compact search, filtering, sorting, and selection controls."""
        filter_frame = ctk.CTkFrame(
            master=parent,
            fg_color="transparent",
        )

        filter_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
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
            placeholder_text=self._t("search_placeholder"),
            height=40,
            corner_radius=10,
            border_color=BORDER_COLOR,
        )

        self.search_entry.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=(12, 6),
            pady=(12, 8),
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda _event: self._schedule_search(),
        )

        clear_button = ctk.CTkButton(
            master=filter_frame,
            text=self._t("clear_filters"),
            command=self._clear_filters,
            width=112,
            height=40,
            corner_radius=10,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        clear_button.grid(
            row=0,
            column=4,
            sticky="ew",
            padx=(6, 12),
            pady=(12, 8),
        )

        self.category_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.category_filter_var,
            values=[self._label(ALL_CATEGORIES)],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.category_filter_menu.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(12, 5),
            pady=5,
        )

        self.extension_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.extension_filter_var,
            values=[self._label(ALL_EXTENSIONS)],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.extension_filter_menu.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=5,
            pady=5,
        )

        self.size_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.size_filter_var,
            values=[self._label(option) for option in SIZE_FILTER_OPTIONS],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.size_filter_menu.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=5,
            pady=5,
        )

        self.modified_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.modified_filter_var,
            values=[self._label(option) for option in MODIFIED_FILTER_OPTIONS],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.modified_filter_menu.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=5,
            pady=5,
        )

        filter_caption = ctk.CTkLabel(
            master=filter_frame,
            text=self._t("quick_filters"),
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
        )

        filter_caption.grid(
            row=1,
            column=4,
            padx=(8, 12),
            pady=5,
        )

        self.folder_filter_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.folder_filter_var,
            values=[self._label(ALL_FOLDERS)],
            command=lambda _value: self._on_folder_filter_changed(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.folder_filter_menu.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=(12, 5),
            pady=5,
        )

        self.folder_match_mode_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.folder_match_mode_var,
            values=[self._label(option) for option in FolderMatchMode],
            command=lambda _value: self._apply_filters(),
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.folder_match_mode_menu.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=5,
            pady=5,
        )

        self.sort_field_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.sort_field_var,
            values=[self._label(option) for option in SortField],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.sort_field_menu.grid(
            row=2,
            column=2,
            sticky="ew",
            padx=5,
            pady=5,
        )

        self.sort_direction_menu = ctk.CTkOptionMenu(
            master=filter_frame,
            variable=self.sort_direction_var,
            values=[self._label(option) for option in SortDirection],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=CONTROL_BUTTON,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT_COLOR,
        )

        self.sort_direction_menu.grid(
            row=2,
            column=3,
            sticky="ew",
            padx=5,
            pady=5,
        )

        reset_sort_button = ctk.CTkButton(
            master=filter_frame,
            text=self._t("reset_sort"),
            command=self._reset_sort,
            height=36,
            corner_radius=9,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        reset_sort_button.grid(
            row=2,
            column=4,
            sticky="ew",
            padx=(5, 12),
            pady=5,
        )

        selection_bar = ctk.CTkFrame(
            master=filter_frame,
            fg_color="transparent",
        )

        selection_bar.grid(
            row=3,
            column=0,
            columnspan=5,
            sticky="ew",
            padx=12,
            pady=(6, 12),
        )

        selection_bar.grid_columnconfigure(
            0,
            weight=1,
        )

        selection_hint = ctk.CTkLabel(
            master=selection_bar,
            text=self._t("selection_controls"),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        selection_hint.grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=8,
        )

        select_visible_button = ctk.CTkButton(
            master=selection_bar,
            text=self._t("select_visible"),
            command=self._select_visible_assets,
            width=110,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        select_visible_button.grid(
            row=0,
            column=1,
            padx=(6, 4),
            pady=8,
        )

        invert_visible_button = ctk.CTkButton(
            master=selection_bar,
            text=self._t("invert_visible"),
            command=self._invert_visible_selection,
            width=110,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        invert_visible_button.grid(
            row=0,
            column=2,
            padx=4,
            pady=8,
        )

        clear_selection_button = ctk.CTkButton(
            master=selection_bar,
            text=self._t("clear_selection"),
            command=self._clear_asset_selection,
            width=115,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=DANGER_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=DANGER_TEXT,
        )

        clear_selection_button.grid(
            row=0,
            column=3,
            padx=(4, 8),
            pady=8,
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
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
            height=20,
        )

        label.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=12,
            pady=9,
        )

    @property
    def _shortcut_modifier_label(self) -> str:
        """Return the platform's readable primary shortcut key."""
        return (
            "Command"
            if sys.platform == "darwin"
            else "Ctrl"
        )

    def _bind_keyboard_shortcuts(self) -> None:
        """Bind cross-platform shortcuts for common Aniccoli actions."""
        primary_prefix = (
            "Command"
            if sys.platform == "darwin"
            else "Control"
        )

        self.bind_all(
            f"<{primary_prefix}-o>",
            self._shortcut_choose_folder,
        )

        self.bind_all(
            f"<{primary_prefix}-r>",
            self._shortcut_scan_folder,
        )

        self.bind_all(
            f"<{primary_prefix}-f>",
            self._shortcut_focus_search,
        )

        self.bind_all(
            f"<{primary_prefix}-Shift-A>",
            self._shortcut_select_visible,
        )

        self.bind_all(
            f"<{primary_prefix}-Shift-C>",
            self._shortcut_clear_selection,
        )

        self.bind_all(
            "<F1>",
            self._shortcut_open_help,
        )

    def _shortcut_choose_folder(
        self,
        _event: object | None = None,
    ) -> str:
        """Open the project-folder chooser from a keyboard shortcut."""
        self._select_folder()
        return "break"

    def _shortcut_scan_folder(
        self,
        _event: object | None = None,
    ) -> str:
        """Scan the selected folder from a keyboard shortcut."""
        if self.selected_folder is not None:
            self._scan_selected_folder()

        return "break"

    def _shortcut_focus_search(
        self,
        _event: object | None = None,
    ) -> str:
        """Focus and select the asset-search field."""
        self.search_entry.focus_set()
        self.search_entry.select_range(
            0,
            "end",
        )

        return "break"

    def _shortcut_select_visible(
        self,
        _event: object | None = None,
    ) -> str:
        """Select every visible asset from a keyboard shortcut."""
        self._select_visible_assets()
        return "break"

    def _shortcut_clear_selection(
        self,
        _event: object | None = None,
    ) -> str:
        """Clear the asset selection from a keyboard shortcut."""
        self._clear_asset_selection()
        return "break"

    def _shortcut_open_help(
        self,
        _event: object | None = None,
    ) -> str:
        """Open the help window from a keyboard shortcut."""
        self._open_about_window()
        return "break"

    def _open_about_window(self) -> None:
        """Open localized help and shortcut guidance."""
        help_window = ctk.CTkToplevel(
            self
        )

        help_window.title(
            self._t(
                "help_title"
            )
        )

        help_window.geometry(
            "720x610"
        )

        help_window.minsize(
            620,
            500,
        )

        help_window.transient(
            self
        )

        help_window.grab_set()

        help_window.grid_columnconfigure(
            0,
            weight=1,
        )

        help_window.grid_rowconfigure(
            1,
            weight=1,
        )

        heading = ctk.CTkLabel(
            master=help_window,
            text=self._t(
                "help_title"
            ),
            font=ctk.CTkFont(
                size=26,
                weight="bold",
            ),
            anchor="w",
        )

        heading.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=26,
            pady=(24, 12),
        )

        content = ctk.CTkScrollableFrame(
            master=help_window,
            corner_radius=14,
            fg_color=PANEL_BACKGROUND,
        )

        content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=26,
            pady=(0, 14),
        )

        content.grid_columnconfigure(
            0,
            weight=1,
        )

        sections = (
            (
                APP_NAME,
                self._t(
                    "help_intro"
                ),
            ),
            (
                self._t(
                    "help_workflow"
                ),
                self._t(
                    "help_workflow_body"
                ),
            ),
            (
                self._t(
                    "help_safety"
                ),
                self._t(
                    "help_safety_body"
                ),
            ),
            (
                self._t(
                    "help_keys"
                ),
                (
                    f"{self._shortcut_modifier_label} + O — "
                    f"{self._t('choose_project')}\n"
                    f"{self._shortcut_modifier_label} + R — "
                    f"{self._t('scan_project')}\n"
                    f"{self._shortcut_modifier_label} + F — "
                    f"{self._t('search_placeholder')}\n"
                    f"{self._shortcut_modifier_label} + Shift + A — "
                    f"{self._t('select_visible')}\n"
                    f"{self._shortcut_modifier_label} + Shift + C — "
                    f"{self._t('clear_selection')}\n"
                    f"F1 — {self._t('help_shortcuts')}"
                ),
            ),
        )

        for row, (
            section_title,
            section_body,
        ) in enumerate(
            sections
        ):
            card = ctk.CTkFrame(
                master=content,
                corner_radius=12,
                fg_color=CARD_BACKGROUND,
                border_width=1,
                border_color=BORDER_COLOR,
            )

            card.grid(
                row=row,
                column=0,
                sticky="ew",
                pady=(0, 10),
            )

            card.grid_columnconfigure(
                0,
                weight=1,
            )

            title_label = ctk.CTkLabel(
                master=card,
                text=section_title,
                font=ctk.CTkFont(
                    size=15,
                    weight="bold",
                ),
                anchor="w",
            )

            title_label.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=15,
                pady=(13, 5),
            )

            body_label = ctk.CTkLabel(
                master=card,
                text=section_body,
                font=ctk.CTkFont(
                    size=13,
                ),
                text_color=MUTED_TEXT,
                anchor="w",
                justify="left",
                wraplength=610,
            )

            body_label.grid(
                row=1,
                column=0,
                sticky="ew",
                padx=15,
                pady=(0, 14),
            )

        close_button = ctk.CTkButton(
            master=help_window,
            text=self._t(
                "close"
            ),
            command=help_window.destroy,
            width=120,
            height=38,
            corner_radius=10,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
        )

        close_button.grid(
            row=2,
            column=0,
            sticky="e",
            padx=26,
            pady=(0, 24),
        )

    def _save_current_preferences(self) -> None:
        """Save the current persistent application settings."""
        try:
            current_options = self._build_organization_options()

            self.preferences = update_preferences(
                self.preferences,
                recursive_scan=self.recursive_scan_var.get(),
                date_grouping=current_options.date_grouping,
                date_source=current_options.date_source,
                last_project_folder=self.selected_folder,
                clear_last_project_folder=(
                    self.selected_folder is None
                ),
                language=self.language_code,
            )

            save_preferences(
                self.preferences
            )
        except (
            PermissionError,
            OSError,
            TypeError,
            ValueError,
        ) as error:
            if hasattr(
                self,
                "status_label",
            ):
                self.status_label.configure(
                    text=(
                        self._t("preferences_failed", error=error)
                    ),
                )

    def _restore_saved_project_folder(self) -> None:
        """Restore the previous project folder without scanning it."""
        options = self._build_organization_options()

        self.date_source_menu.configure(
            state=(
                "normal"
                if options.uses_date_grouping
                else "disabled"
            ),
        )

        if self.selected_folder is None:
            if self.preferences.last_project_folder is not None:
                self.preferences = update_preferences(
                    self.preferences,
                    clear_last_project_folder=True,
                )

                try:
                    save_preferences(
                        self.preferences
                    )
                except (
                    PermissionError,
                    OSError,
                    TypeError,
                    ValueError,
                ):
                    pass

            return

        self.selected_folder_label.configure(
            text=str(
                self.selected_folder
            ),
        )

        self.scan_button.configure(
            state="normal",
        )

        self.status_label.configure(
            text=self._t(
                "restored_folder_status"
            ),
        )

        self._refresh_undo_button()

    def _on_recursive_scan_changed(self) -> None:
        """Save the recursive-scan preference when it changes."""
        self._save_current_preferences()

    def _on_close(self) -> None:
        """Save preferences before closing Aniccoli."""
        self._save_current_preferences()
        self.destroy()

    def _build_organization_options(
        self,
    ) -> OrganizationOptions:
        """Build organization rules from the selected controls."""
        date_grouping = self._chosen(self.date_grouping_var, DateGrouping)

        date_source = self._chosen(self.date_source_var, DateSource)

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
        self._save_current_preferences()

        if self.scanned_assets:
            self._display_assets()

            self.status_label.configure(
                text=self._t(
                    "filters_updated"
                ),
            )

    def _select_folder(self) -> None:
        """Open the folder picker and store the selected folder."""
        selected_path = filedialog.askdirectory(
            parent=self,
            title=self._t("folder_dialog"),
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
            text=self._t(
                "folder_selected_status"
            ),
        )

        self.scan_button.configure(
            state="normal",
        )

        self._save_current_preferences()
        self._reset_scan_results()
        self._refresh_undo_button()

    def _scan_selected_folder(self) -> None:
        """Scan the selected folder and display its assets."""
        if self.selected_folder is None:
            self.status_label.configure(
                text=self._t("choose_first"),
            )
            return

        self.scan_button.configure(
            state="disabled",
            text=self._t("scanning"),
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

        self.statistics_button.configure(
            state="disabled",
        )

        self.audit_button.configure(
            state="disabled",
        )

        self.status_label.configure(
            text=self._t("scanning_status"),
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
            self.asset_selection = clear_asset_selection()

            self.status_label.configure(
                text=self._t("scan_failed", error=error),
            )

            self._refresh_filter_options()
            self._display_assets()
        else:
            self.organization_plan = []
            self.duplicate_groups = []
            self.asset_selection = select_all_assets(
                self.scanned_assets
            )

            self._refresh_filter_options()
            self._reset_filter_controls()
            self._display_assets()
            self._update_selection_summary()

            file_count = len(
                self.scanned_assets
            )

            self.status_label.configure(
                text=self._t(
                    "scan_complete",
                    count=file_count,
                ),
            )

            if self.scanned_assets:
                self.duplicate_button.configure(
                    state="normal",
                )

                self.statistics_button.configure(
                    state="normal",
                )

                self.audit_button.configure(
                    state="normal",
                )
        finally:
            self.scan_button.configure(
                state="normal",
                text=self._t("scan_project"),
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
            self._label(ALL_CATEGORIES),
        ] + [
            str(category)
            for category in self.available_categories
        ]

        extension_values = [
            self._label(ALL_EXTENSIONS),
        ] + list(
            self.available_extensions
        )

        self.folder_display_lookup = {
            (
                self._t("project_root")
                if folder == Path(".")
                else str(folder)
            ): folder
            for folder in self.available_folders
        }

        folder_values = [
            self._label(ALL_FOLDERS),
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
                self._label(ALL_CATEGORIES),
            )

        if (
            self.extension_filter_var.get()
            not in extension_values
        ):
            self.extension_filter_var.set(
                self._label(ALL_EXTENSIONS),
            )

        if (
            self.folder_filter_var.get()
            not in folder_values
        ):
            self.folder_filter_var.set(
                self._label(ALL_FOLDERS),
            )

        self.folder_match_mode_menu.configure(
            state=(
                "normal"
                if self.folder_filter_var.get()
                != self._label(ALL_FOLDERS)
                else "disabled"
            ),
        )

    def _reset_filter_controls(self) -> None:
        """Reset all filter controls."""
        self.search_var.set(
            "",
        )

        self.category_filter_var.set(
            self._label(ALL_CATEGORIES),
        )

        self.extension_filter_var.set(
            self._label(ALL_EXTENSIONS),
        )

        self.size_filter_var.set(
            self._label(ANY_SIZE),
        )

        self.modified_filter_var.set(
            self._label(ANY_TIME),
        )

        self.folder_filter_var.set(
            self._label(ALL_FOLDERS),
        )

        self.folder_match_mode_var.set(
            self._label(FolderMatchMode.INCLUDE_SUBFOLDERS),
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
                != self._label(ALL_FOLDERS)
                else "disabled"
            ),
        )

        self._apply_filters()

    def _reset_sort(self) -> None:
        """Restore filename sorting in ascending order."""
        self.sort_field_var.set(
            self._label(SortField.NAME),
        )

        self.sort_direction_var.set(
            self._label(SortDirection.ASCENDING),
        )

        self._apply_filters()

    def _update_selection_summary(self) -> None:
        """Refresh selection counts and selection-dependent actions."""
        summary = summarize_selection(
            self.scanned_assets,
            self.asset_selection,
        )

        self.selection_count_label.configure(
            text=(
                f"{summary.selected_assets} / "
                f"{summary.total_assets}"
            ),
        )

        action_state = (
            "normal"
            if summary.has_selection
            else "disabled"
        )

        self.preview_button.configure(
            state=action_state,
        )

        self.export_button.configure(
            state=action_state,
        )

    def _select_visible_assets(self) -> None:
        """Add every currently visible asset to the selection."""
        if not self.filtered_assets:
            return

        visible_selection = select_all_assets(
            self.filtered_assets
        )

        self.asset_selection = AssetSelection(
            selected_paths=(
                self.asset_selection.selected_paths
                | visible_selection.selected_paths
            )
        )

        self._apply_filters()

    def _invert_visible_selection(self) -> None:
        """Invert selection only for assets visible in the table."""
        if not self.filtered_assets:
            return

        visible_selection = select_all_assets(
            self.filtered_assets
        )

        self.asset_selection = AssetSelection(
            selected_paths=(
                self.asset_selection.selected_paths
                ^ visible_selection.selected_paths
            )
        )

        self._apply_filters()

    def _clear_asset_selection(self) -> None:
        """Clear every selected asset."""
        self.asset_selection = clear_asset_selection()
        self._apply_filters()

    def _set_asset_selected(
        self,
        asset: AssetFile,
        selected: bool,
    ) -> None:
        """Set the selection state of one scanned asset."""
        if selected:
            self.asset_selection = self.asset_selection.select(
                asset
            )
        else:
            self.asset_selection = self.asset_selection.deselect(
                asset
            )

        self._update_selection_summary()

    def _selected_assets_for_action(
        self,
    ) -> tuple[AssetFile, ...]:
        """Return selected assets in their original scan order."""
        return selected_assets(
            self.scanned_assets,
            self.asset_selection,
        )

    def _build_query(self) -> AssetQuery:
        """Build the asset query from the search, filter and sort controls."""
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
            if selected_extension != self._label(ALL_EXTENSIONS)
            else frozenset()
        )

        minimum_size, maximum_size = SIZE_FILTER_OPTIONS[
            self._chosen(
                self.size_filter_var,
                SIZE_FILTER_OPTIONS,
            )
        ]

        modified_days = MODIFIED_FILTER_OPTIONS[
            self._chosen(
                self.modified_filter_var,
                MODIFIED_FILTER_OPTIONS,
            )
        ]

        modified_after = (
            datetime.now()
            - timedelta(
                days=modified_days,
            )
            if modified_days is not None
            else None
        )

        return AssetQuery(
            search_text=self.search_var.get(),
            categories=selected_categories,
            extensions=selected_extensions,
            minimum_size_bytes=minimum_size,
            maximum_size_bytes=maximum_size,
            modified_after=modified_after,
            folder=self.folder_display_lookup.get(
                self.folder_filter_var.get()
            ),
            folder_match_mode=self._chosen(self.folder_match_mode_var, FolderMatchMode),
            sort_field=self._chosen(self.sort_field_var, SortField),
            sort_direction=self._chosen(self.sort_direction_var, SortDirection),
        )

    def _apply_filters(self) -> None:
        """Filter scanned assets and refresh the visible rows."""
        if not self.scanned_assets:
            self.filtered_assets = []

            self.filter_count_label.configure(
                text=self._t("showing_files", visible=0, total=0),
            )

            self._update_selection_summary()
            return

        try:
            result = query_assets(
                self.scanned_assets,
                self._build_query(),
            )
        except ValueError as error:
            self.status_label.configure(
                text=self._t("filter_error", error=error),
            )
            return

        self.filtered_assets = list(
            result.matched
        )

        visible_count = len(
            self.filtered_assets
        )

        self.filter_count_label.configure(
            text=self._t(
                "showing_files",
                visible=visible_count,
                total=result.total_count,
            ),
        )

        self._update_selection_summary()
        self._clear_result_rows()

        if not self.filtered_assets:
            self._show_empty_results_message(
                self._t(
                    "empty_no_match"
                )
            )
            return

        self._render_row_page(
            parent=self.results_scroll_frame,
            items=self.filtered_assets,
            create_row=lambda asset, row_number: (
                self._create_asset_row(
                    asset=asset,
                    row_number=row_number,
                )
            ),
        )

    def _schedule_search(self) -> None:
        """Re-filter once typing pauses instead of on every key."""
        if self._search_job is not None:
            self.after_cancel(
                self._search_job
            )

        self._search_job = self.after(
            250,
            self._apply_filters,
        )

    def _render_row_page(
        self,
        parent: ctk.CTkScrollableFrame,
        items: Sequence[Any],
        create_row: Callable[[Any, int], None],
        start: int = 0,
    ) -> None:
        """Render one page of rows, then a button that renders the next."""
        end = min(
            start + ROW_PAGE_SIZE,
            len(items),
        )

        for row_number in range(start, end):
            create_row(
                items[row_number],
                row_number,
            )

        remaining = len(items) - end

        if remaining <= 0:
            return

        def show_next_page() -> None:
            # Hidden, not destroyed: CTk still runs a click animation on it.
            more_button.grid_forget()
            self._render_row_page(
                parent=parent,
                items=items,
                create_row=create_row,
                start=end,
            )

        more_button = ctk.CTkButton(
            master=parent,
            text=self._t(
                "show_more",
                count=min(ROW_PAGE_SIZE, remaining),
                remaining=remaining,
            ),
            command=show_next_page,
            height=32,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
        )

        more_button.grid(
            row=end,
            column=0,
            pady=(10, 6),
        )

    def _reset_scan_results(self) -> None:
        """Clear results when another folder is selected."""
        self.scanned_assets = []
        self.filtered_assets = []
        self.organization_plan = []
        self.duplicate_groups = []
        self.asset_selection = clear_asset_selection()

        self.files_count_label.configure(
            text="0",
        )

        self.total_size_label.configure(
            text="0 B",
        )

        self.categories_count_label.configure(
            text="0",
        )

        self._refresh_category_bar()

        self.filter_count_label.configure(
            text=self._t("showing_files", visible=0, total=0),
        )

        self.selection_count_label.configure(
            text="0 / 0",
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

        self.statistics_button.configure(
            state="disabled",
        )

        self.audit_button.configure(
            state="disabled",
        )

        self.available_categories = ()
        self.available_extensions = ()
        self.available_folders = ()
        self.folder_display_lookup = {}

        self.category_filter_menu.configure(
            values=[
                self._label(ALL_CATEGORIES),
            ],
        )

        self.extension_filter_menu.configure(
            values=[
                self._label(ALL_EXTENSIONS),
            ],
        )

        self.folder_filter_menu.configure(
            values=[
                self._label(ALL_FOLDERS),
            ],
        )

        self._reset_filter_controls()
        self._clear_result_rows()

        self._show_empty_results_message(
            self._t(
                "empty_folder_selected"
            )
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

        self._refresh_category_bar()
        self._clear_result_rows()

        if not self.scanned_assets:
            self.filtered_assets = []

            self.filter_count_label.configure(
                text=self._t("showing_files", visible=0, total=0),
            )

            self._show_empty_results_message(
                self._t(
                    "empty_no_files"
                )
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
                weight="bold",
            ),
            text_color=MUTED_TEXT,
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
        """Create one polished row representing a scanned asset."""
        row_color = (
            ROW_BACKGROUND
            if row_number % 2 == 0
            else ROW_ALT_BACKGROUND
        )

        row_frame = ctk.CTkFrame(
            master=self.results_scroll_frame,
            corner_radius=6,
            fg_color=row_color,
        )

        row_frame.grid(
            row=row_number,
            column=0,
            sticky="ew",
            pady=(0, 2),
        )

        group_color = CATEGORY_GROUP_COLORS[
            _category_group(asset.category)
        ]

        category_stripe = ctk.CTkFrame(
            master=row_frame,
            width=4,
            corner_radius=2,
            fg_color=group_color,
        )

        category_stripe.place(
            x=3,
            rely=0.2,
            relheight=0.6,
        )

        row_frame.grid_columnconfigure(0, weight=0)
        row_frame.grid_columnconfigure(1, weight=3)
        row_frame.grid_columnconfigure(2, weight=2)
        row_frame.grid_columnconfigure(3, weight=1)
        row_frame.grid_columnconfigure(4, weight=2)
        row_frame.grid_columnconfigure(5, weight=0)

        selection_var = ctk.BooleanVar(
            value=self.asset_selection.contains(asset),
        )

        selection_checkbox = ctk.CTkCheckBox(
            master=row_frame,
            text="",
            variable=selection_var,
            onvalue=True,
            offvalue=False,
            width=24,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            command=lambda: self._set_asset_selected(
                asset,
                selection_var.get(),
            ),
        )

        selection_checkbox.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(14, 4),
            pady=8,
        )

        parent_path = asset.relative_path.parent
        parent_text = (
            self._t("project_root")
            if parent_path == Path(".")
            else str(parent_path)
        )

        file_name_label = ctk.CTkLabel(
            master=row_frame,
            text=asset.file_name,
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            anchor="w",
            height=18,
        )

        file_name_label.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=12,
            pady=(8, 0),
        )

        path_label = ctk.CTkLabel(
            master=row_frame,
            text=parent_text,
            font=ctk.CTkFont(
                family=PATH_FONT_FAMILY,
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
            height=16,
        )

        path_label.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=12,
            pady=(0, 8),
        )

        category_label = ctk.CTkLabel(
            master=row_frame,
            text=str(asset.category),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=group_color,
            anchor="w",
        )

        category_label.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="ew",
            padx=12,
            pady=8,
        )

        size_label = ctk.CTkLabel(
            master=row_frame,
            text=asset.size_text,
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
        )

        size_label.grid(
            row=0,
            column=3,
            rowspan=2,
            sticky="ew",
            padx=12,
            pady=8,
        )

        planned_destination = build_destination_folder(
            asset=asset,
            options=self._build_organization_options(),
        )

        destination_label = ctk.CTkLabel(
            master=row_frame,
            text=str(planned_destination),
            font=ctk.CTkFont(
                family=PATH_FONT_FAMILY,
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
            justify="left",
            wraplength=250,
        )

        destination_label.grid(
            row=0,
            column=4,
            rowspan=2,
            sticky="ew",
            padx=12,
            pady=8,
        )

        reveal_button = ctk.CTkButton(
            master=row_frame,
            text=self._t("reveal"),
            command=lambda selected_asset=asset: (
                self._reveal_asset_in_file_manager(selected_asset)
            ),
            width=64,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(
                size=11,
            ),
        )

        reveal_button.grid(
            row=0,
            column=5,
            rowspan=2,
            padx=(6, 12),
            pady=8,
        )

    def _reveal_asset_in_file_manager(
        self,
        asset: AssetFile,
    ) -> None:
        """Reveal a scanned asset in Finder or the system file manager."""
        try:
            revealed_path = reveal_in_file_manager(
                asset.source_path
            )
        except (
            FileNotFoundError,
            OSError,
        ) as error:
            messagebox.showerror(
                title=self._t("cannot_reveal"),
                message=str(error),
                parent=self,
            )

            self.status_label.configure(
                text=self._t("cannot_reveal_status", error=error),
            )
            return

        self.status_label.configure(
            text=self._t(
                "revealed_status",
                name=revealed_path.name,
            ),
        )

    def _open_asset_health_audit(self) -> None:
        """Audit all scanned assets and display detected health issues."""
        if not self.scanned_assets:
            self.status_label.configure(
                text=self._t("scan_before_health"),
            )
            return

        self.audit_button.configure(
            state="disabled",
            text=self._t("auditing"),
        )

        self.status_label.configure(
            text=self._t("health_checking"),
        )

        self.update_idletasks()

        try:
            report = audit_assets(
                self.scanned_assets,
                large_file_threshold_bytes=500 * 1024**2,
                stale_after_days=365,
            )
        except ValueError as error:
            messagebox.showerror(
                title=self._t("health_failed_title"),
                message=str(error),
                parent=self,
            )

            self.status_label.configure(
                text=self._t("health_failed", error=error),
            )
            return
        finally:
            self.audit_button.configure(
                state=(
                    "normal"
                    if self.scanned_assets
                    else "disabled"
                ),
                text=self._t("asset_health"),
            )

        AssetAuditWindow(
            master=self,
            report=report,
            translate=self._t,
        )

        if report.is_healthy:
            status_text = (
                self._t("health_none", count=report.scanned_asset_count)
            )
        else:
            status_text = (
                self._t(
                    "health_issues",
                    issues=report.issue_count,
                    count=report.scanned_asset_count,
                )
            )

        self.status_label.configure(
            text=status_text,
        )

    def _open_project_statistics(self) -> None:
        """Calculate and display statistics for all scanned assets."""
        if not self.scanned_assets:
            self.status_label.configure(
                text=self._t("scan_before_stats"),
            )
            return

        self.statistics_button.configure(
            state="disabled",
            text=self._t("calculating"),
        )

        self.status_label.configure(
            text=self._t("stats_calculating"),
        )

        self.update_idletasks()

        try:
            statistics = build_asset_statistics(
                self.scanned_assets,
                largest_limit=20,
                recent_limit=20,
            )
        except ValueError as error:
            messagebox.showerror(
                title=self._t("stats_failed_title"),
                message=str(error),
                parent=self,
            )

            self.status_label.configure(
                text=self._t("stats_failed", error=error),
            )
            return
        finally:
            self.statistics_button.configure(
                state=(
                    "normal"
                    if self.scanned_assets
                    else "disabled"
                ),
                text=self._t("project_statistics"),
            )

        AssetStatisticsWindow(
            master=self,
            statistics=statistics,
            translate=self._t,
        )

        self.status_label.configure(
            text=(
                self._t("stats_opened", count=statistics.total_assets)
            ),
        )

    def _export_inventory_report(self) -> None:
        """Export all scanned assets as a JSON or CSV inventory report."""
        selected_asset_records = (
            self._selected_assets_for_action()
        )

        if (
            self.selected_folder is None
            or not self.scanned_assets
        ):
            self.status_label.configure(
                text=self._t("scan_before_export"),
            )
            return

        if not selected_asset_records:
            self.status_label.configure(
                text=self._t("select_before_export"),
            )
            return

        selected_path = filedialog.asksaveasfilename(
            parent=self,
            title=self._t("export_title"),
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
            text=self._t("exporting"),
        )

        self.status_label.configure(
            text=self._t("export_status"),
        )

        self.update_idletasks()

        try:
            result = export_asset_report(
                output_path=output_path,
                assets=selected_asset_records,
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
                title=self._t("export_failed_title"),
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=self._t("export_failed", error=error),
            )
            return
        finally:
            self.export_button.configure(
                state=(
                    "normal"
                    if self.scanned_assets
                    else "disabled"
                ),
                text=self._t("export_report"),
            )

        messagebox.showinfo(
            title=self._t("exported_title"),
            message=(
                self._t(
                    "export_done_message",
                    format=result.report_format,
                    count=result.asset_count,
                    size=result.total_size_text,
                    path=result.report_path,
                )
            ),
            parent=self,
        )

        self.status_label.configure(
            text=(
                self._t("export_done_status", name=result.report_path.name)
            ),
        )

    def _analyze_duplicates(self) -> None:
        """Analyze and display exact-content duplicates."""
        if not self.scanned_assets:
            self.status_label.configure(
                text=self._t(
                    "duplicate_before"
                ),
            )
            return

        self.duplicate_button.configure(
            state="disabled",
            text=self._t("analyzing"),
        )

        self.status_label.configure(
            text=self._t(
                "duplicate_status"
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
                title=self._t("duplicate_failed_title"),
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=self._t(
                    "duplicate_failed",
                    error=error,
                ),
            )
            return
        finally:
            self.duplicate_button.configure(
                state="normal",
                text=self._t("analyze_duplicates"),
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
                    self._t(
                        "duplicates_found",
                        groups=group_count,
                        copies=duplicate_copy_count,
                    )
                ),
            )
        else:
            self.status_label.configure(
                text=(
                    self._t("duplicates_none")
                ),
            )

        DuplicateResultsWindow(
            master=self,
            duplicate_groups=self.duplicate_groups,
            project_folder=self.selected_folder,
            on_project_changed=(
                self._refresh_after_duplicate_cleanup
            ),
            translate=self._t,
        )

    def _refresh_after_duplicate_cleanup(self) -> None:
        """Rescan the project after duplicate files move or return."""
        if self.selected_folder is None:
            return

        self.status_label.configure(
            text=(
                self._t("duplicate_refreshing")
            ),
        )

        self._scan_selected_folder()

    def _preview_organization(self) -> None:
        """Build and display the organization preview."""
        if (
            self.selected_folder is None
            or not self.scanned_assets
        ):
            self.status_label.configure(
                text=self._t(
                    "scan_before_preview"
                ),
            )
            return

        selected_asset_records = (
            self._selected_assets_for_action()
        )

        if not selected_asset_records:
            self.status_label.configure(
                text=self._t(
                    "select_before_preview"
                ),
            )
            return

        try:
            self.organization_plan = (
                build_organization_plan(
                    project_folder=self.selected_folder,
                    assets=selected_asset_records,
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
                text=self._t("preview_failed", error=error),
            )
            return

        if not self.organization_plan:
            self.status_label.configure(
                text=(
                    self._t("preview_nothing_status")
                ),
            )
        else:
            self.status_label.configure(
                text=(
                    self._t(
                        "preview_ready_status",
                        count=len(self.organization_plan),
                    )
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
            f"{APP_NAME} — {self._t('preview_title')}"
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
            text=self._t("preview_title"),
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
                self._t(
                    "preview_summary",
                    count=len(self.organization_plan),
                    conflicts=conflict_count,
                    grouping=self._label(options.date_grouping),
                    source=self._label(options.date_source),
                )
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
                    self._t("preview_nothing")
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
            self._render_row_page(
                parent=preview_scroll,
                items=self.organization_plan,
                create_row=lambda planned_move, row_number: (
                    self._create_preview_row(
                        parent=preview_scroll,
                        planned_move=planned_move,
                        row_number=row_number,
                    )
                ),
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
            text=self._t("close_preview"),
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
            text=self._t("organize_files"),
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
                f"{self._t('from')}\n"
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
                f"{self._t('to')}\n"
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
                self._t("renamed")
                if planned_move.renamed_for_conflict
                else self._t("ready")
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
            title=self._t("confirm_organization"),
            message=(
                self._t("confirm_organize_message", count=file_count)
            ),
            parent=preview_window,
        )

        if not confirmed:
            return

        self.status_label.configure(
            text=self._t("organizing"),
        )

        self.update_idletasks()

        try:
            result = apply_moves(
                self.selected_folder,
                [
                    planned_move.as_move()
                    for planned_move in self.organization_plan
                ],
                JournalKind.ORGANIZE,
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            messagebox.showerror(
                title=self._t("organization_failed_title"),
                message=str(
                    error
                ),
                parent=preview_window,
            )

            self.status_label.configure(
                text=self._t("organization_failed", error=error),
            )
            return

        preview_window.destroy()

        moved_count = len(
            result.done
        )

        failed_count = len(
            result.failed
        )

        if failed_count == 0:
            messagebox.showinfo(
                title=self._t("organization_complete_title"),
                message=(
                    self._t("organized_message", count=moved_count)
                ),
                parent=self,
            )
        else:
            messagebox.showwarning(
                title=self._t("organization_partial_title"),
                message=(
                    self._t(
                        "moved_failed_message",
                        moved=moved_count,
                        failed=failed_count,
                    )
                ),
                parent=self,
            )

        self.organization_plan = []

        self._scan_selected_folder()
        self._refresh_undo_button()

        self.status_label.configure(
            text=(
                self._t(
                    "organization_finished",
                    moved=moved_count,
                    failed=failed_count,
                )
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
            latest_log = latest_journal(
                self.selected_folder,
                JournalKind.ORGANIZE,
            )
        except OSError:
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
            title=self._t("undo_title"),
            message=(
                self._t("confirm_undo_message")
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.undo_button.configure(
            state="disabled",
            text=self._t("undoing"),
        )

        self.status_label.configure(
            text=self._t(
                "restoring"
            ),
        )

        self.update_idletasks()

        try:
            result = reverse_latest(
                self.selected_folder,
                JournalKind.ORGANIZE,
            )
        except NothingToReverseError:
            messagebox.showinfo(
                title=self._t("nothing_undo"),
                message=self._t("nothing_undo_message"),
                parent=self,
            )

            self.status_label.configure(
                text=self._t("nothing_undo_message"),
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
                title=self._t("undo_failed_title"),
                message=str(
                    error
                ),
                parent=self,
            )

            self.status_label.configure(
                text=self._t("undo_failed", error=error),
            )
            return
        finally:
            self.undo_button.configure(
                text=self._t("undo_organize"),
            )

        restored_count = len(
            result.done
        )

        failed_count = len(
            result.failed
        )

        if failed_count == 0:
            messagebox.showinfo(
                title=self._t("undo_complete_title"),
                message=(
                    self._t(
                        "undo_result_message",
                        restored=restored_count,
                        skipped=len(result.skipped),
                        failed=0,
                    )
                ),
                parent=self,
            )
        else:
            failure_lines = [
                (
                    f"• {failure.move.source.name}: "
                    f"{failure.error}"
                )
                for failure in result.failed[:5]
            ]

            messagebox.showwarning(
                title=self._t("undo_partial_title"),
                message=(
                    self._t(
                        "undo_result_message",
                        restored=restored_count,
                        skipped=len(result.skipped),
                        failed=failed_count,
                    )
                    + "\n\n"
                    + "\n".join(
                        failure_lines
                    )
                ),
                parent=self,
            )

        self._scan_selected_folder()
        self._refresh_undo_button()

        self.status_label.configure(
            text=(
                self._t(
                    "undo_finished",
                    restored=restored_count,
                    failed=failed_count,
                )
            ),
        )


def create_app() -> AniccoliApp:
    """Create and return the Aniccoli application."""
    ctk.set_appearance_mode(
        "System"
    )

    ctk.set_default_color_theme(
        str(Path(__file__).with_name("theme.json"))
    )

    return AniccoliApp()