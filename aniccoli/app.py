"""Main desktop window for Aniccoli."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import sys
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from aniccoli.about_window import AboutWindow
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
from aniccoli.sorting import (
    AssetSortOptions,
    SortDirection,
    SortField,
    sort_assets,
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



LANGUAGE_LABELS = {
    "en": "English",
    "ms": "Bahasa Melayu",
    "zh": "简体中文",
    "ja": "日本語",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "language": "Language",
        "workspace_title": "Asset workspace",
        "workspace_subtitle": "Review first, then organize with safe undo and restoration tools.",
        "help_shortcuts": "Help & shortcuts",
        "project": "PROJECT",
        "selected_folder": "Selected folder",
        "no_folder": "No folder selected",
        "choose_project": "Choose project folder",
        "include_subfolders": "Include subfolders",
        "scan_project": "Scan project",
        "scanning": "Scanning...",
        "workflow": "WORKFLOW",
        "preview_organization": "Preview organization",
        "analyze_duplicates": "Analyze duplicates",
        "analyzing": "Analyzing...",
        "organization": "ORGANIZATION",
        "date_grouping": "Date grouping",
        "date_source": "Date source",
        "tools_recovery": "TOOLS & RECOVERY",
        "statistics": "Statistics",
        "calculating": "Calculating...",
        "asset_health": "Asset health",
        "auditing": "Auditing...",
        "export_report": "Export report",
        "exporting": "Exporting...",
        "undo_organize": "Undo organize",
        "undoing": "Undoing...",
        "status": "STATUS",
        "choose_begin": "Choose a folder to begin.",
        "files_found": "FILES FOUND",
        "files_scan": "Files in the current scan",
        "combined_size": "COMBINED SIZE",
        "total_size": "Total detected asset size",
        "categories": "CATEGORIES",
        "asset_groups": "Detected asset groups",
        "selected": "SELECTED",
        "selected_use": "Used for preview and export",
        "scanned_assets": "Scanned assets",
        "results_hint": "Filter and select the files used by organization and reports.",
        "showing_files": "Showing {visible} of {total} files",
        "search_placeholder": "Search assets, paths, categories, or folders…",
        "clear_filters": "Clear filters",
        "quick_filters": "Quick filters",
        "reset_sort": "Reset sort",
        "selection_controls": "Selection controls",
        "select_visible": "Select visible",
        "invert_visible": "Invert visible",
        "clear_selection": "Clear selection",
        "use": "USE",
        "asset": "ASSET",
        "category": "CATEGORY",
        "size": "SIZE",
        "planned_destination": "PLANNED DESTINATION",
        "action": "ACTION",
        "empty_initial": "No scan results yet.\nChoose a project folder from the sidebar.",
        "empty_folder_selected": "Folder selected.\nClick Scan Project to inspect its assets.",
        "empty_no_files": "No supported or visible files were found.",
        "empty_no_match": "No assets match the current filters.",
        "project_root": "Project root",
        "reveal": "Reveal",
        "folder_dialog": "Select a 3D project folder",
        "folder_selected_status": "Folder selected. Click Scan Project to inspect its assets.",
        "restored_folder_status": "Previous project folder restored. Click Scan Project to inspect its assets.",
        "choose_first": "Please choose a project folder first.",
        "scanning_status": "Scanning the selected folder...",
        "scan_failed": "Scan failed: {error}",
        "scan_complete": "Scan complete. {count} file{suffix} found.",
        "select_before_preview": "Select at least one asset before creating an organization preview.",
        "scan_before_preview": "Scan a folder before creating a preview.",
        "filters_updated": "Organization settings updated. Open Preview Organization to review the new destinations.",
        "filter_error": "Filter error: {error}",
        "cannot_reveal": "Cannot Reveal Asset",
        "cannot_reveal_status": "Could not reveal asset: {error}",
        "revealed_status": "Revealed asset in the system file manager: {name}",
        "scan_before_health": "Scan a folder before opening Asset Health.",
        "health_checking": "Checking the scanned project for asset health issues...",
        "health_failed_title": "Asset Audit Failed",
        "health_failed": "Asset audit failed: {error}",
        "scan_before_stats": "Scan a folder before opening project statistics.",
        "stats_calculating": "Calculating project statistics...",
        "stats_failed_title": "Statistics Failed",
        "stats_failed": "Statistics failed: {error}",
        "project_statistics": "Project Statistics",
        "scan_before_export": "Scan a folder before exporting a report.",
        "select_before_export": "Select at least one asset before exporting.",
        "export_title": "Export Aniccoli Asset Inventory",
        "export_status": "Exporting the asset inventory report...",
        "export_failed_title": "Report Export Failed",
        "export_failed": "Report export failed: {error}",
        "exported_title": "Report Exported",
        "duplicate_before": "Scan a folder before analyzing duplicates.",
        "duplicate_status": "Analyzing possible duplicates. Large files may take a moment...",
        "duplicate_failed_title": "Duplicate Analysis Failed",
        "duplicate_failed": "Duplicate analysis failed: {error}",
        "preview_title": "Organization Preview",
        "close_preview": "Close Preview",
        "organize_files": "Organize Files",
        "confirm_organization": "Confirm File Organization",
        "organizing": "Organizing files...",
        "organization_failed_title": "Organization Failed",
        "organization_complete_title": "Organization Complete",
        "organization_partial_title": "Organization Partially Complete",
        "undo_title": "Undo Last Organization",
        "restoring": "Restoring files to their original locations...",
        "nothing_undo": "Nothing to Undo",
        "undo_failed_title": "Undo Failed",
        "undo_complete_title": "Undo Complete",
        "undo_partial_title": "Undo Partially Complete",
        "ready": "Ready",
        "renamed": "Renamed",
        "from": "From",
        "to": "To",
        "language_changed": "Language changed to {language}.",
        "help_title": "Help & shortcuts",
        "help_intro": "Aniccoli helps you scan, review, organize, audit, and recover 3D project assets safely.",
        "help_workflow": "Recommended workflow",
        "help_workflow_body": "1. Choose a project folder.\n2. Scan the project.\n3. Search, filter, and select assets.\n4. Preview organization.\n5. Confirm only after reviewing destinations.",
        "help_safety": "Safety",
        "help_safety_body": "Organization uses previews and undo history. Duplicate cleanup uses quarantine instead of permanent deletion.",
        "help_keys": "Keyboard shortcuts",
        "close": "Close",
    },
    "ms": {
        "language": "Bahasa",
        "workspace_title": "Ruang kerja aset",
        "workspace_subtitle": "Semak dahulu, kemudian susun dengan alat buat asal dan pemulihan yang selamat.",
        "help_shortcuts": "Bantuan & pintasan",
        "project": "PROJEK",
        "selected_folder": "Folder dipilih",
        "no_folder": "Tiada folder dipilih",
        "choose_project": "Pilih folder projek",
        "include_subfolders": "Sertakan subfolder",
        "scan_project": "Imbas projek",
        "scanning": "Mengimbas...",
        "workflow": "ALIRAN KERJA",
        "preview_organization": "Pratonton susunan",
        "analyze_duplicates": "Analisis pendua",
        "analyzing": "Menganalisis...",
        "organization": "PENYUSUNAN",
        "date_grouping": "Pengumpulan tarikh",
        "date_source": "Sumber tarikh",
        "tools_recovery": "ALAT & PEMULIHAN",
        "statistics": "Statistik",
        "calculating": "Mengira...",
        "asset_health": "Kesihatan aset",
        "auditing": "Mengaudit...",
        "export_report": "Eksport laporan",
        "exporting": "Mengeksport...",
        "undo_organize": "Buat asal susunan",
        "undoing": "Membuat asal...",
        "status": "STATUS",
        "choose_begin": "Pilih folder untuk bermula.",
        "files_found": "FAIL DITEMUI",
        "files_scan": "Fail dalam imbasan semasa",
        "combined_size": "SAIZ GABUNGAN",
        "total_size": "Jumlah saiz aset dikesan",
        "categories": "KATEGORI",
        "asset_groups": "Kumpulan aset dikesan",
        "selected": "DIPILIH",
        "selected_use": "Digunakan untuk pratonton dan eksport",
        "scanned_assets": "Aset diimbas",
        "results_hint": "Tapis dan pilih fail untuk penyusunan dan laporan.",
        "showing_files": "Memaparkan {visible} daripada {total} fail",
        "search_placeholder": "Cari aset, laluan, kategori atau folder…",
        "clear_filters": "Kosongkan penapis",
        "quick_filters": "Penapis pantas",
        "reset_sort": "Tetapkan semula susunan",
        "selection_controls": "Kawalan pilihan",
        "select_visible": "Pilih yang kelihatan",
        "invert_visible": "Songsangkan pilihan",
        "clear_selection": "Kosongkan pilihan",
        "use": "GUNA",
        "asset": "ASET",
        "category": "KATEGORI",
        "size": "SAIZ",
        "planned_destination": "DESTINASI DIRANCANG",
        "action": "TINDAKAN",
        "empty_initial": "Belum ada hasil imbasan.\nPilih folder projek dari bar sisi.",
        "empty_folder_selected": "Folder dipilih.\nKlik Imbas projek untuk memeriksa aset.",
        "empty_no_files": "Tiada fail yang disokong atau kelihatan ditemui.",
        "empty_no_match": "Tiada aset sepadan dengan penapis semasa.",
        "project_root": "Akar projek",
        "reveal": "Tunjukkan",
        "folder_dialog": "Pilih folder projek 3D",
        "folder_selected_status": "Folder dipilih. Klik Imbas projek untuk memeriksa aset.",
        "restored_folder_status": "Folder projek sebelumnya dipulihkan. Klik Imbas projek untuk memeriksa aset.",
        "choose_first": "Sila pilih folder projek dahulu.",
        "scanning_status": "Sedang mengimbas folder yang dipilih...",
        "scan_failed": "Imbasan gagal: {error}",
        "scan_complete": "Imbasan selesai. {count} fail ditemui.",
        "select_before_preview": "Pilih sekurang-kurangnya satu aset sebelum membuat pratonton susunan.",
        "scan_before_preview": "Imbas folder sebelum membuat pratonton.",
        "filters_updated": "Tetapan penyusunan dikemas kini. Buka Pratonton susunan untuk menyemak destinasi baharu.",
        "filter_error": "Ralat penapis: {error}",
        "cannot_reveal": "Tidak dapat menunjukkan aset",
        "cannot_reveal_status": "Tidak dapat menunjukkan aset: {error}",
        "revealed_status": "Aset ditunjukkan dalam pengurus fail sistem: {name}",
        "scan_before_health": "Imbas folder sebelum membuka Kesihatan aset.",
        "health_checking": "Sedang memeriksa isu kesihatan aset projek...",
        "health_failed_title": "Audit aset gagal",
        "health_failed": "Audit aset gagal: {error}",
        "scan_before_stats": "Imbas folder sebelum membuka statistik projek.",
        "stats_calculating": "Sedang mengira statistik projek...",
        "stats_failed_title": "Statistik gagal",
        "stats_failed": "Statistik gagal: {error}",
        "project_statistics": "Statistik projek",
        "scan_before_export": "Imbas folder sebelum mengeksport laporan.",
        "select_before_export": "Pilih sekurang-kurangnya satu aset sebelum mengeksport.",
        "export_title": "Eksport inventori aset Aniccoli",
        "export_status": "Sedang mengeksport laporan inventori aset...",
        "export_failed_title": "Eksport laporan gagal",
        "export_failed": "Eksport laporan gagal: {error}",
        "exported_title": "Laporan dieksport",
        "duplicate_before": "Imbas folder sebelum menganalisis pendua.",
        "duplicate_status": "Sedang menganalisis pendua. Fail besar mungkin mengambil masa...",
        "duplicate_failed_title": "Analisis pendua gagal",
        "duplicate_failed": "Analisis pendua gagal: {error}",
        "preview_title": "Pratonton penyusunan",
        "close_preview": "Tutup pratonton",
        "organize_files": "Susun fail",
        "confirm_organization": "Sahkan penyusunan fail",
        "organizing": "Sedang menyusun fail...",
        "organization_failed_title": "Penyusunan gagal",
        "organization_complete_title": "Penyusunan selesai",
        "organization_partial_title": "Penyusunan separa selesai",
        "undo_title": "Buat asal penyusunan terakhir",
        "restoring": "Sedang memulihkan fail ke lokasi asal...",
        "nothing_undo": "Tiada yang boleh dibuat asal",
        "undo_failed_title": "Buat asal gagal",
        "undo_complete_title": "Buat asal selesai",
        "undo_partial_title": "Buat asal separa selesai",
        "ready": "Sedia",
        "renamed": "Dinamakan semula",
        "from": "Dari",
        "to": "Ke",
        "language_changed": "Bahasa ditukar kepada {language}.",
        "help_title": "Bantuan & pintasan",
        "help_intro": "Aniccoli membantu anda mengimbas, menyemak, menyusun, mengaudit dan memulihkan aset projek 3D dengan selamat.",
        "help_workflow": "Aliran kerja disyorkan",
        "help_workflow_body": "1. Pilih folder projek.\n2. Imbas projek.\n3. Cari, tapis dan pilih aset.\n4. Pratonton penyusunan.\n5. Sahkan selepas menyemak destinasi.",
        "help_safety": "Keselamatan",
        "help_safety_body": "Penyusunan menggunakan pratonton dan sejarah buat asal. Pembersihan pendua menggunakan kuarantin, bukan pemadaman kekal.",
        "help_keys": "Pintasan papan kekunci",
        "close": "Tutup",
    },
    "zh": {
        "language": "语言",
        "workspace_title": "素材工作区",
        "workspace_subtitle": "先检查，再使用安全的撤销与恢复工具整理素材。",
        "help_shortcuts": "帮助与快捷键",
        "project": "项目",
        "selected_folder": "已选文件夹",
        "no_folder": "尚未选择文件夹",
        "choose_project": "选择项目文件夹",
        "include_subfolders": "包含子文件夹",
        "scan_project": "扫描项目",
        "scanning": "扫描中...",
        "workflow": "工作流程",
        "preview_organization": "预览整理方案",
        "analyze_duplicates": "分析重复文件",
        "analyzing": "分析中...",
        "organization": "整理设置",
        "date_grouping": "日期分组",
        "date_source": "日期来源",
        "tools_recovery": "工具与恢复",
        "statistics": "统计",
        "calculating": "计算中...",
        "asset_health": "素材健康检查",
        "auditing": "检查中...",
        "export_report": "导出报告",
        "exporting": "导出中...",
        "undo_organize": "撤销整理",
        "undoing": "撤销中...",
        "status": "状态",
        "choose_begin": "请选择文件夹开始。",
        "files_found": "找到的文件",
        "files_scan": "当前扫描中的文件",
        "combined_size": "总大小",
        "total_size": "检测到的素材总大小",
        "categories": "类别",
        "asset_groups": "检测到的素材类别",
        "selected": "已选择",
        "selected_use": "用于预览和导出",
        "scanned_assets": "已扫描素材",
        "results_hint": "筛选并选择用于整理和报告的文件。",
        "showing_files": "显示 {visible} / {total} 个文件",
        "search_placeholder": "搜索素材、路径、类别或文件夹…",
        "clear_filters": "清除筛选",
        "quick_filters": "快速筛选",
        "reset_sort": "重置排序",
        "selection_controls": "选择控制",
        "select_visible": "选择可见项",
        "invert_visible": "反选可见项",
        "clear_selection": "清除选择",
        "use": "使用",
        "asset": "素材",
        "category": "类别",
        "size": "大小",
        "planned_destination": "计划目标位置",
        "action": "操作",
        "empty_initial": "尚无扫描结果。\n请从侧边栏选择项目文件夹。",
        "empty_folder_selected": "已选择文件夹。\n点击“扫描项目”检查素材。",
        "empty_no_files": "未找到受支持或可见的文件。",
        "empty_no_match": "没有素材符合当前筛选条件。",
        "project_root": "项目根目录",
        "reveal": "显示位置",
        "folder_dialog": "选择 3D 项目文件夹",
        "folder_selected_status": "已选择文件夹。点击“扫描项目”检查素材。",
        "restored_folder_status": "已恢复上次的项目文件夹。点击“扫描项目”检查素材。",
        "choose_first": "请先选择项目文件夹。",
        "scanning_status": "正在扫描所选文件夹...",
        "scan_failed": "扫描失败：{error}",
        "scan_complete": "扫描完成。找到 {count} 个文件。",
        "select_before_preview": "创建整理预览前，请至少选择一个素材。",
        "scan_before_preview": "创建预览前请先扫描文件夹。",
        "filters_updated": "整理设置已更新。请打开“预览整理方案”检查新的目标位置。",
        "filter_error": "筛选错误：{error}",
        "cannot_reveal": "无法显示素材",
        "cannot_reveal_status": "无法显示素材：{error}",
        "revealed_status": "已在系统文件管理器中显示素材：{name}",
        "scan_before_health": "打开素材健康检查前请先扫描文件夹。",
        "health_checking": "正在检查项目素材健康问题...",
        "health_failed_title": "素材检查失败",
        "health_failed": "素材检查失败：{error}",
        "scan_before_stats": "打开项目统计前请先扫描文件夹。",
        "stats_calculating": "正在计算项目统计...",
        "stats_failed_title": "统计失败",
        "stats_failed": "统计失败：{error}",
        "project_statistics": "项目统计",
        "scan_before_export": "导出报告前请先扫描文件夹。",
        "select_before_export": "导出前请至少选择一个素材。",
        "export_title": "导出 Aniccoli 素材清单",
        "export_status": "正在导出素材清单报告...",
        "export_failed_title": "报告导出失败",
        "export_failed": "报告导出失败：{error}",
        "exported_title": "报告已导出",
        "duplicate_before": "分析重复文件前请先扫描文件夹。",
        "duplicate_status": "正在分析可能的重复文件，大文件可能需要一些时间...",
        "duplicate_failed_title": "重复文件分析失败",
        "duplicate_failed": "重复文件分析失败：{error}",
        "preview_title": "整理预览",
        "close_preview": "关闭预览",
        "organize_files": "整理文件",
        "confirm_organization": "确认整理文件",
        "organizing": "正在整理文件...",
        "organization_failed_title": "整理失败",
        "organization_complete_title": "整理完成",
        "organization_partial_title": "部分整理完成",
        "undo_title": "撤销上次整理",
        "restoring": "正在将文件恢复到原始位置...",
        "nothing_undo": "没有可撤销的操作",
        "undo_failed_title": "撤销失败",
        "undo_complete_title": "撤销完成",
        "undo_partial_title": "部分撤销完成",
        "ready": "就绪",
        "renamed": "已重命名",
        "from": "来源",
        "to": "目标",
        "language_changed": "语言已切换为{language}。",
        "help_title": "帮助与快捷键",
        "help_intro": "Aniccoli 帮助你安全地扫描、检查、整理、审核和恢复 3D 项目素材。",
        "help_workflow": "建议工作流程",
        "help_workflow_body": "1. 选择项目文件夹。\n2. 扫描项目。\n3. 搜索、筛选并选择素材。\n4. 预览整理方案。\n5. 检查目标位置后再确认。",
        "help_safety": "安全机制",
        "help_safety_body": "整理操作使用预览和撤销记录。重复文件清理使用隔离区，而不是永久删除。",
        "help_keys": "键盘快捷键",
        "close": "关闭",
    },
    "ja": {
        "language": "言語",
        "workspace_title": "アセットワークスペース",
        "workspace_subtitle": "まず確認し、安全な元に戻す・復元ツールで整理します。",
        "help_shortcuts": "ヘルプとショートカット",
        "project": "プロジェクト",
        "selected_folder": "選択中のフォルダ",
        "no_folder": "フォルダ未選択",
        "choose_project": "プロジェクトフォルダを選択",
        "include_subfolders": "サブフォルダを含める",
        "scan_project": "プロジェクトをスキャン",
        "scanning": "スキャン中...",
        "workflow": "ワークフロー",
        "preview_organization": "整理内容をプレビュー",
        "analyze_duplicates": "重複を分析",
        "analyzing": "分析中...",
        "organization": "整理設定",
        "date_grouping": "日付グループ",
        "date_source": "日付の参照元",
        "tools_recovery": "ツールと復元",
        "statistics": "統計",
        "calculating": "計算中...",
        "asset_health": "アセット健全性",
        "auditing": "監査中...",
        "export_report": "レポートを書き出す",
        "exporting": "書き出し中...",
        "undo_organize": "整理を元に戻す",
        "undoing": "元に戻しています...",
        "status": "ステータス",
        "choose_begin": "開始するフォルダを選択してください。",
        "files_found": "検出ファイル",
        "files_scan": "現在のスキャン内のファイル",
        "combined_size": "合計サイズ",
        "total_size": "検出アセットの合計サイズ",
        "categories": "カテゴリ",
        "asset_groups": "検出されたアセット分類",
        "selected": "選択済み",
        "selected_use": "プレビューと書き出しに使用",
        "scanned_assets": "スキャン済みアセット",
        "results_hint": "整理とレポートに使用するファイルを絞り込み、選択します。",
        "showing_files": "{total} 件中 {visible} 件を表示",
        "search_placeholder": "アセット、パス、カテゴリ、フォルダを検索…",
        "clear_filters": "フィルターを解除",
        "quick_filters": "クイックフィルター",
        "reset_sort": "並び順をリセット",
        "selection_controls": "選択操作",
        "select_visible": "表示中を選択",
        "invert_visible": "表示中を反転",
        "clear_selection": "選択を解除",
        "use": "使用",
        "asset": "アセット",
        "category": "カテゴリ",
        "size": "サイズ",
        "planned_destination": "予定の保存先",
        "action": "操作",
        "empty_initial": "スキャン結果はまだありません。\nサイドバーからプロジェクトフォルダを選択してください。",
        "empty_folder_selected": "フォルダを選択しました。\n「プロジェクトをスキャン」をクリックしてください。",
        "empty_no_files": "対応する表示可能なファイルが見つかりませんでした。",
        "empty_no_match": "現在のフィルターに一致するアセットはありません。",
        "project_root": "プロジェクトルート",
        "reveal": "場所を表示",
        "folder_dialog": "3D プロジェクトフォルダを選択",
        "folder_selected_status": "フォルダを選択しました。「プロジェクトをスキャン」をクリックしてください。",
        "restored_folder_status": "前回のプロジェクトフォルダを復元しました。「プロジェクトをスキャン」をクリックしてください。",
        "choose_first": "先にプロジェクトフォルダを選択してください。",
        "scanning_status": "選択したフォルダをスキャンしています...",
        "scan_failed": "スキャンに失敗しました：{error}",
        "scan_complete": "スキャン完了。{count} 件のファイルが見つかりました。",
        "select_before_preview": "整理プレビューを作成する前に、1つ以上のアセットを選択してください。",
        "scan_before_preview": "プレビューを作成する前にフォルダをスキャンしてください。",
        "filters_updated": "整理設定を更新しました。新しい保存先をプレビューで確認してください。",
        "filter_error": "フィルターエラー：{error}",
        "cannot_reveal": "アセットの場所を表示できません",
        "cannot_reveal_status": "アセットの場所を表示できません：{error}",
        "revealed_status": "システムのファイルマネージャーで表示しました：{name}",
        "scan_before_health": "アセット健全性を開く前にフォルダをスキャンしてください。",
        "health_checking": "プロジェクトのアセット健全性を確認しています...",
        "health_failed_title": "アセット監査に失敗しました",
        "health_failed": "アセット監査に失敗しました：{error}",
        "scan_before_stats": "プロジェクト統計を開く前にフォルダをスキャンしてください。",
        "stats_calculating": "プロジェクト統計を計算しています...",
        "stats_failed_title": "統計の計算に失敗しました",
        "stats_failed": "統計に失敗しました：{error}",
        "project_statistics": "プロジェクト統計",
        "scan_before_export": "レポートを書き出す前にフォルダをスキャンしてください。",
        "select_before_export": "書き出す前に1つ以上のアセットを選択してください。",
        "export_title": "Aniccoli アセット一覧を書き出す",
        "export_status": "アセット一覧レポートを書き出しています...",
        "export_failed_title": "レポートの書き出しに失敗しました",
        "export_failed": "レポートの書き出しに失敗しました：{error}",
        "exported_title": "レポートを書き出しました",
        "duplicate_before": "重複を分析する前にフォルダをスキャンしてください。",
        "duplicate_status": "重複候補を分析しています。大きなファイルは時間がかかる場合があります...",
        "duplicate_failed_title": "重複分析に失敗しました",
        "duplicate_failed": "重複分析に失敗しました：{error}",
        "preview_title": "整理プレビュー",
        "close_preview": "プレビューを閉じる",
        "organize_files": "ファイルを整理",
        "confirm_organization": "ファイル整理の確認",
        "organizing": "ファイルを整理しています...",
        "organization_failed_title": "整理に失敗しました",
        "organization_complete_title": "整理が完了しました",
        "organization_partial_title": "一部の整理が完了しました",
        "undo_title": "前回の整理を元に戻す",
        "restoring": "ファイルを元の場所へ復元しています...",
        "nothing_undo": "元に戻せる操作はありません",
        "undo_failed_title": "元に戻せませんでした",
        "undo_complete_title": "元に戻しました",
        "undo_partial_title": "一部を元に戻しました",
        "ready": "準備完了",
        "renamed": "名前変更",
        "from": "移動元",
        "to": "移動先",
        "language_changed": "言語を{language}に変更しました。",
        "help_title": "ヘルプとショートカット",
        "help_intro": "Aniccoli は 3D プロジェクトのアセットを安全にスキャン、確認、整理、監査、復元するためのツールです。",
        "help_workflow": "おすすめの流れ",
        "help_workflow_body": "1. プロジェクトフォルダを選択。\n2. プロジェクトをスキャン。\n3. 検索、絞り込み、選択。\n4. 整理内容をプレビュー。\n5. 保存先を確認してから実行。",
        "help_safety": "安全機能",
        "help_safety_body": "整理にはプレビューと元に戻す履歴を使用します。重複の整理は永久削除ではなく隔離を使用します。",
        "help_keys": "キーボードショートカット",
        "close": "閉じる",
    },
}

LANGUAGE_SETTINGS_PATH = (
    Path.home()
    / ".aniccoli"
    / "ui_language.txt"
)


def _load_ui_language() -> str:
    """Load the saved interface language."""
    try:
        language_code = LANGUAGE_SETTINGS_PATH.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return "en"

    return (
        language_code
        if language_code in TRANSLATIONS
        else "en"
    )


def _save_ui_language(language_code: str) -> None:
    """Save the selected interface language."""
    try:
        LANGUAGE_SETTINGS_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        LANGUAGE_SETTINGS_PATH.write_text(
            language_code,
            encoding="utf-8",
        )
    except OSError:
        pass


APP_NAME = "Aniccoli"
APP_VERSION = "1.0.0-rc.2"

APP_STAGE = "RELEASE CANDIDATE"

APP_BACKGROUND = ("#F3F6F4", "#101512")
SIDEBAR_BACKGROUND = ("#E9F0EB", "#151C18")
PANEL_BACKGROUND = ("#FFFFFF", "#1B231E")
CARD_BACKGROUND = ("#F9FBFA", "#202A24")
ROW_BACKGROUND = ("#FFFFFF", "#1D251F")
ROW_ALT_BACKGROUND = ("#F5F8F6", "#202922")
BORDER_COLOR = ("#D8E2DB", "#324038")
MUTED_TEXT = ("#617067", "#9BAAA0")
ACCENT_COLOR = ("#247A4D", "#46B978")
ACCENT_HOVER = ("#1D6841", "#3AA368")
ACCENT_SOFT = ("#DCEFE3", "#203F2D")
DANGER_SOFT = ("#F6E2E2", "#432727")

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

        self.preferences: AppPreferences = load_preferences()

        self.language_code = _load_ui_language()
        self.language_var = ctk.StringVar(
            value=LANGUAGE_LABELS[
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
                self.preferences.date_grouping
            ),
        )

        self.date_source_var = ctk.StringVar(
            value=str(
                self.preferences.date_source
            ),
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
        language = TRANSLATIONS.get(
            self.language_code,
            TRANSLATIONS["en"],
        )

        template = language.get(
            key,
            TRANSLATIONS["en"].get(
                key,
                key,
            ),
        )

        try:
            return template.format(
                **values
            )
        except (
            KeyError,
            ValueError,
        ):
            return template

    def _change_language(
        self,
        selected_label: str,
    ) -> None:
        """Change language and rebuild the main interface."""
        selected_code = next(
            (
                code
                for code, label in LANGUAGE_LABELS.items()
                if label == selected_label
            ),
            "en",
        )

        if selected_code == self.language_code:
            return

        self.language_code = selected_code
        self.language_var.set(
            LANGUAGE_LABELS[
                selected_code
            ],
        )

        _save_ui_language(
            selected_code
        )

        self.main_container.destroy()
        self._create_interface()

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
            text=f"{APP_STAGE}  •  {APP_VERSION}",
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            text_color=ACCENT_COLOR,
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
                size=28,
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
                size=10,
                weight="bold",
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
                LANGUAGE_LABELS.values()
            ),
            command=self._change_language,
            width=145,
            height=34,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#27332C", "#E6EEE9"),
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
                size=11,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
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
            corner_radius=14,
            fg_color=PANEL_BACKGROUND,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        project_card.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
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
            text_color=("#27332C", "#E6EEE9"),
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
                size=11,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
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
            corner_radius=14,
            fg_color=PANEL_BACKGROUND,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        workflow_card.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=14,
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
            text_color=("#27332C", "#E6EEE9"),
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
                size=11,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
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
            corner_radius=14,
            fg_color=PANEL_BACKGROUND,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        organization_card.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=14,
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
                str(option)
                for option in DateGrouping
            ],
            command=lambda _value: (
                self._on_organization_options_changed()
            ),
            height=36,
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
                str(option)
                for option in DateSource
            ],
            command=lambda _value: (
                self._on_organization_options_changed()
            ),
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
                size=11,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
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
            corner_radius=14,
            fg_color=PANEL_BACKGROUND,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        tools_card.grid(
            row=8,
            column=0,
            sticky="ew",
            padx=14,
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
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#7A3030", "#F0B8B8"),
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
                size=10,
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
        """Create the scan-summary cards."""
        summary_frame = ctk.CTkFrame(
            master=self.workspace,
            fg_color="transparent",
        )

        summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 16),
        )

        summary_frame.grid_columnconfigure(
            (0, 1, 2, 3),
            weight=1,
            uniform="summary",
        )

        self.files_count_label = self._create_summary_card(
            parent=summary_frame,
            column=0,
            heading=self._t("files_found"),
            starting_value="0",
            accent=self._t("files_scan"),
        )

        self.total_size_label = self._create_summary_card(
            parent=summary_frame,
            column=1,
            heading=self._t("combined_size"),
            starting_value="0 B",
            accent=self._t("total_size"),
        )

        self.categories_count_label = self._create_summary_card(
            parent=summary_frame,
            column=2,
            heading=self._t("categories"),
            starting_value="0",
            accent=self._t("asset_groups"),
        )

        self.selection_count_label = self._create_summary_card(
            parent=summary_frame,
            column=3,
            heading=self._t("selected"),
            starting_value="0 / 0",
            accent=self._t("selected_use"),
        )

    def _create_summary_card(
        self,
        parent: ctk.CTkFrame,
        column: int,
        heading: str,
        starting_value: str,
        accent: str,
    ) -> ctk.CTkLabel:
        """Create a summary card and return its value label."""
        card = ctk.CTkFrame(
            master=parent,
            corner_radius=14,
            fg_color=PANEL_BACKGROUND,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(
                0 if column == 0 else 6,
                0 if column == 3 else 6,
            ),
        )

        heading_label = ctk.CTkLabel(
            master=card,
            text=heading,
            font=ctk.CTkFont(
                size=10,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        heading_label.pack(
            fill="x",
            padx=16,
            pady=(14, 4),
        )

        value_label = ctk.CTkLabel(
            master=card,
            text=starting_value,
            font=ctk.CTkFont(
                size=25,
                weight="bold",
            ),
            anchor="w",
        )

        value_label.pack(
            fill="x",
            padx=16,
            pady=(0, 1),
        )

        accent_label = ctk.CTkLabel(
            master=card,
            text=accent,
            font=ctk.CTkFont(
                size=11,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        accent_label.pack(
            fill="x",
            padx=16,
            pady=(0, 14),
        )

        return value_label

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
            corner_radius=9,
            fg_color=CARD_BACKGROUND,
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
            corner_radius=12,
            fg_color=CARD_BACKGROUND,
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
            lambda _event: self._apply_filters(),
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
            text_color=("#27332C", "#E6EEE9"),
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
            values=[ALL_CATEGORIES],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=[ALL_EXTENSIONS],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=list(SIZE_FILTER_OPTIONS),
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=list(MODIFIED_FILTER_OPTIONS),
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=[ALL_FOLDERS],
            command=lambda _value: self._on_folder_filter_changed(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=[str(option) for option in FolderMatchMode],
            command=lambda _value: self._apply_filters(),
            height=36,
            state="disabled",
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=[str(option) for option in SortField],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            values=[str(option) for option in SortDirection],
            command=lambda _value: self._apply_filters(),
            height=36,
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#27332C", "#E6EEE9"),
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
            corner_radius=9,
            fg_color=PANEL_BACKGROUND,
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
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#27332C", "#E6EEE9"),
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
            text_color=("#7A3030", "#F0B8B8"),
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
                size=10,
                weight="bold",
            ),
            text_color=MUTED_TEXT,
            anchor="w",
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
                        "Could not save preferences: "
                        f"{error}"
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
                    suffix=(
                        ""
                        if file_count == 1
                        else "s"
                    ),
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
                text=self._t("showing_files", visible=0, total=0),
            )

            self._update_selection_summary()
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
                text=self._t("filter_error", error=error),
            )
            return

        self.filtered_assets = list(
            sorted_assets
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
            corner_radius=10,
            fg_color=row_color,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        row_frame.grid(
            row=row_number,
            column=0,
            sticky="ew",
            pady=(0, 7),
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
            padx=(12, 4),
            pady=12,
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
        )

        file_name_label.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=12,
            pady=(10, 1),
        )

        path_label = ctk.CTkLabel(
            master=row_frame,
            text=parent_text,
            font=ctk.CTkFont(
                size=10,
            ),
            text_color=MUTED_TEXT,
            anchor="w",
        )

        path_label.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=12,
            pady=(0, 10),
        )

        category_label = ctk.CTkLabel(
            master=row_frame,
            text=str(asset.category),
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            fg_color=ACCENT_SOFT,
            text_color=ACCENT_COLOR,
            corner_radius=10,
        )

        category_label.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="w",
            padx=12,
            pady=12,
            ipadx=8,
            ipady=3,
        )

        size_label = ctk.CTkLabel(
            master=row_frame,
            text=asset.size_text,
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            anchor="w",
        )

        size_label.grid(
            row=0,
            column=3,
            rowspan=2,
            sticky="ew",
            padx=12,
            pady=12,
        )

        planned_destination = build_destination_folder(
            asset=asset,
            options=self._build_organization_options(),
        )

        destination_label = ctk.CTkLabel(
            master=row_frame,
            text=str(planned_destination),
            font=ctk.CTkFont(
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
            pady=10,
        )

        reveal_button = ctk.CTkButton(
            master=row_frame,
            text=self._t("reveal"),
            command=lambda selected_asset=asset: (
                self._reveal_asset_in_file_manager(selected_asset)
            ),
            width=78,
            height=31,
            corner_radius=8,
            fg_color="transparent",
            hover_color=ACCENT_SOFT,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=("#27332C", "#E6EEE9"),
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
        )

        reveal_button.grid(
            row=0,
            column=5,
            rowspan=2,
            padx=(6, 12),
            pady=12,
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
        )

        if report.is_healthy:
            status_text = (
                "Asset Health found no issues in "
                f"{report.scanned_asset_count} asset"
                f"{'' if report.scanned_asset_count == 1 else 's'}."
            )
        else:
            status_text = (
                "Asset Health found "
                f"{report.issue_count} issue"
                f"{'' if report.issue_count == 1 else 's'} "
                f"across {report.scanned_asset_count} scanned assets."
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
        )

        self.status_label.configure(
            text=(
                "Project statistics opened for "
                f"{statistics.total_assets} asset"
                f"{'' if statistics.total_assets == 1 else 's'}."
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
            project_folder=self.selected_folder,
            on_project_changed=(
                self._refresh_after_duplicate_cleanup
            ),
        )

    def _refresh_after_duplicate_cleanup(self) -> None:
        """Rescan the project after duplicate files move or return."""
        if self.selected_folder is None:
            return

        self.status_label.configure(
            text=(
                "Duplicate cleanup changed the project. "
                "Refreshing the scan..."
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
            text=self._t("organizing"),
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
                title=self._t("organization_failed_title"),
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
                title=self._t("organization_complete_title"),
                message=(
                    f"{result.moved_count} file"
                    f"{'' if result.moved_count == 1 else 's'} "
                    "were organized successfully."
                ),
                parent=self,
            )
        else:
            messagebox.showwarning(
                title=self._t("organization_partial_title"),
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
            title=self._t("undo_title"),
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
            text=self._t("undoing"),
        )

        self.status_label.configure(
            text=self._t(
                "restoring"
            ),
        )

        self.update_idletasks()

        try:
            result = undo_latest_organization(
                self.selected_folder
            )
        except NoUndoHistoryError as error:
            messagebox.showinfo(
                title=self._t("nothing_undo"),
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
                title=self._t("undo_failed_title"),
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
                text=self._t("undo_organize"),
            )

        if result.failed_count == 0:
            messagebox.showinfo(
                title=self._t("undo_complete_title"),
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
                title=self._t("undo_partial_title"),
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