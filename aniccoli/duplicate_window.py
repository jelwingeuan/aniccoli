"""Duplicate-analysis and safe-cleanup window for Aniccoli."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from aniccoli.duplicate_cleanup import build_duplicate_cleanup_plan
from aniccoli.duplicates import DuplicateGroup
from aniccoli.file_actions import reveal_in_file_manager
from aniccoli.moves import (
    JournalKind,
    NothingToReverseError,
    apply_moves,
    latest_journal,
    reverse_latest,
)
from aniccoli.scanner import (
    AssetFile,
    format_file_size,
)


ProjectChangedCallback = Callable[[], None]


def _group_assets(
    group: DuplicateGroup,
) -> tuple[AssetFile, ...]:
    """
    Return the AssetFile records stored in a duplicate group.

    Earlier Aniccoli commits used slightly different field names while the
    duplicate engine was being built. Supporting those names keeps this
    window compatible with the user's current project.
    """
    possible_attribute_names = (
        "assets",
        "files",
        "members",
        "duplicates",
        "asset_files",
    )

    for attribute_name in possible_attribute_names:
        value = getattr(
            group,
            attribute_name,
            None,
        )

        if value is None:
            continue

        try:
            records = tuple(
                value
            )
        except TypeError:
            continue

        if all(
            isinstance(
                record,
                AssetFile,
            )
            for record in records
        ):
            return tuple(
                sorted(
                    records,
                    key=lambda asset: str(
                        asset.relative_path
                    ).casefold(),
                )
            )

    raise AttributeError(
        "DuplicateGroup does not contain a supported asset collection."
    )


def _group_hash_text(
    group: DuplicateGroup,
) -> str:
    """Return a short readable hash description for a duplicate group."""
    possible_attribute_names = (
        "content_hash",
        "file_hash",
        "sha256",
        "digest",
        "hash_value",
    )

    for attribute_name in possible_attribute_names:
        value = getattr(
            group,
            attribute_name,
            None,
        )

        if isinstance(
            value,
            str,
        ) and value:
            return (
                value[:14]
                + ("…" if len(value) > 14 else "")
            )

    return "Exact content match"


class DuplicateResultsWindow(ctk.CTkToplevel):
    """Display duplicate groups and safely quarantine selected copies."""

    def __init__(
        self,
        master: ctk.CTk,
        duplicate_groups: Iterable[DuplicateGroup],
        project_folder: str | Path | None = None,
        on_project_changed: ProjectChangedCallback | None = None,
        *,
        translate: Callable[..., str],
    ) -> None:
        """Create the duplicate-results window."""
        super().__init__(
            master
        )

        self._t = translate

        self.duplicate_groups = tuple(
            duplicate_groups
        )

        self.project_folder = (
            Path(
                project_folder
            ).expanduser().resolve()
            if project_folder is not None
            else None
        )

        self.on_project_changed = on_project_changed

        self.group_assets = tuple(
            _group_assets(
                group
            )
            for group in self.duplicate_groups
        )

        self.selection_vars: dict[
            Path,
            ctk.BooleanVar,
        ] = {}

        self.asset_lookup: dict[
            Path,
            AssetFile,
        ] = {}

        self.title(
            self._t("dup_window_title")
        )

        self.geometry(
            "1180x780"
        )

        self.minsize(
            940,
            620,
        )

        self.transient(
            master
        )

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
        self._create_summary()
        self._create_results()
        self._create_actions()
        self._update_selection_summary()

    @property
    def duplicate_copy_count(self) -> int:
        """Return the number of extra copies across all groups."""
        return sum(
            max(
                0,
                len(
                    assets
                )
                - 1,
            )
            for assets in self.group_assets
        )

    @property
    def reclaimable_size_bytes(self) -> int:
        """Return the maximum size recoverable while keeping one copy."""
        total_size = 0

        for assets in self.group_assets:
            if not assets:
                continue

            total_size += (
                max(
                    0,
                    len(
                        assets
                    )
                    - 1,
                )
                * assets[0].size_bytes
            )

        return total_size

    def _create_header(self) -> None:
        """Create the duplicate-results heading."""
        header_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )

        header_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=25,
            pady=(25, 12),
        )

        header_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        title_label = ctk.CTkLabel(
            master=header_frame,
            text=self._t("dup_heading"),
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
                self._t("dup_description")
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

    def _create_summary(self) -> None:
        """Create duplicate summary cards and selection controls."""
        summary_frame = ctk.CTkFrame(
            master=self,
            corner_radius=12,
        )

        summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 14),
        )

        for column in range(4):
            summary_frame.grid_columnconfigure(
                column,
                weight=1,
                uniform="duplicate-summary",
            )

        summary_values = (
            (
                self._t("dup_groups"),
                str(
                    len(
                        self.duplicate_groups
                    )
                ),
            ),
            (
                self._t("dup_extra_copies"),
                str(
                    self.duplicate_copy_count
                ),
            ),
            (
                self._t("dup_reclaimable"),
                format_file_size(
                    self.reclaimable_size_bytes
                ),
            ),
            (
                self._t("selected"),
                self._t("dup_files_count", count=0),
            ),
        )

        for column, (heading, value) in enumerate(
            summary_values
        ):
            card = ctk.CTkFrame(
                master=summary_frame,
                corner_radius=10,
            )

            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=6,
                pady=8,
            )

            value_label = ctk.CTkLabel(
                master=card,
                text=value,
                font=ctk.CTkFont(
                    size=20,
                    weight="bold",
                ),
            )

            value_label.pack(
                padx=12,
                pady=(12, 2),
            )

            heading_label = ctk.CTkLabel(
                master=card,
                text=heading,
                font=ctk.CTkFont(
                    size=11,
                ),
            )

            heading_label.pack(
                padx=12,
                pady=(0, 12),
            )

            if heading == self._t("selected"):
                self.selected_summary_label = value_label

    def _create_results(self) -> None:
        """Create duplicate-group cards."""
        self.results_scroll_frame = ctk.CTkScrollableFrame(
            master=self,
            corner_radius=12,
        )

        self.results_scroll_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=25,
            pady=(0, 14),
        )

        self.results_scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        if not self.duplicate_groups:
            empty_label = ctk.CTkLabel(
                master=self.results_scroll_frame,
                text=(
                    self._t("dup_none")
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
                pady=80,
            )
            return

        for group_number, (
            group,
            assets,
        ) in enumerate(
            zip(
                self.duplicate_groups,
                self.group_assets,
                strict=True,
            ),
            start=1,
        ):
            self._create_group_card(
                group=group,
                assets=assets,
                group_number=group_number,
            )

    def _create_group_card(
        self,
        group: DuplicateGroup,
        assets: tuple[AssetFile, ...],
        group_number: int,
    ) -> None:
        """Create one duplicate-group card."""
        card = ctk.CTkFrame(
            master=self.results_scroll_frame,
            corner_radius=12,
        )

        card.grid(
            row=group_number - 1,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )

        card.grid_columnconfigure(
            0,
            weight=1,
        )

        group_size_text = (
            assets[0].size_text
            if assets
            else "0 B"
        )

        heading_frame = ctk.CTkFrame(
            master=card,
            fg_color="transparent",
        )

        heading_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=(12, 8),
        )

        heading_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        heading_label = ctk.CTkLabel(
            master=heading_frame,
            text=(
                self._t(
                    "dup_group_heading",
                    number=group_number,
                    count=len(assets),
                    size=group_size_text,
                    hash=_group_hash_text(group),
                )
            ),
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
            anchor="w",
        )

        heading_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        select_extras_button = ctk.CTkButton(
            master=heading_frame,
            text=self._t("dup_select_extras"),
            command=lambda records=assets: (
                self._select_group_extras(
                    records
                )
            ),
            width=110,
            height=30,
        )

        select_extras_button.grid(
            row=0,
            column=1,
            padx=(8, 6),
        )

        clear_group_button = ctk.CTkButton(
            master=heading_frame,
            text=self._t("dup_clear_group"),
            command=lambda records=assets: (
                self._clear_group_selection(
                    records
                )
            ),
            width=105,
            height=30,
        )

        clear_group_button.grid(
            row=0,
            column=2,
        )

        rows_frame = ctk.CTkFrame(
            master=card,
            corner_radius=9,
        )

        rows_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 14),
        )

        rows_frame.grid_columnconfigure(
            1,
            weight=1,
        )

        for row_number, asset in enumerate(
            assets
        ):
            self._create_asset_row(
                parent=rows_frame,
                asset=asset,
                row_number=row_number,
            )

    def _create_asset_row(
        self,
        parent: ctk.CTkFrame,
        asset: AssetFile,
        row_number: int,
    ) -> None:
        """Create one selectable duplicate-file row."""
        relative_path = Path(
            asset.relative_path
        )

        selection_var = ctk.BooleanVar(
            value=False,
        )

        self.selection_vars[
            relative_path
        ] = selection_var

        self.asset_lookup[
            relative_path
        ] = asset

        checkbox = ctk.CTkCheckBox(
            master=parent,
            text=self._t("dup_quarantine"),
            variable=selection_var,
            onvalue=True,
            offvalue=False,
            width=115,
            command=self._update_selection_summary,
        )

        checkbox.grid(
            row=row_number,
            column=0,
            padx=(12, 8),
            pady=9,
        )

        details_label = ctk.CTkLabel(
            master=parent,
            text=(
                self._t(
                    "dup_modified",
                    path=asset.relative_path,
                    date=f"{asset.modified_at:%Y-%m-%d %H:%M}",
                )
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
            justify="left",
        )

        details_label.grid(
            row=row_number,
            column=1,
            sticky="ew",
            padx=8,
            pady=9,
        )

        size_label = ctk.CTkLabel(
            master=parent,
            text=asset.size_text,
            font=ctk.CTkFont(
                size=12,
            ),
            width=90,
        )

        size_label.grid(
            row=row_number,
            column=2,
            padx=8,
            pady=9,
        )

        reveal_button = ctk.CTkButton(
            master=parent,
            text=self._t("reveal"),
            command=lambda selected_asset=asset: (
                self._reveal_asset(
                    selected_asset
                )
            ),
            width=80,
            height=30,
        )

        reveal_button.grid(
            row=row_number,
            column=3,
            padx=(8, 12),
            pady=9,
        )

    def _create_actions(self) -> None:
        """Create cleanup, restore, and close controls."""
        action_frame = ctk.CTkFrame(
            master=self,
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

        self.selection_status_label = ctk.CTkLabel(
            master=action_frame,
            text=self._t("dup_select_prompt"),
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
        )

        self.selection_status_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        restore_button = ctk.CTkButton(
            master=action_frame,
            text=self._t("dup_restore_last"),
            command=self._restore_last_cleanup,
            width=165,
            height=40,
            state=(
                "normal"
                if self.project_folder is not None
                else "disabled"
            ),
        )

        restore_button.grid(
            row=0,
            column=1,
            padx=(8, 8),
        )

        close_button = ctk.CTkButton(
            master=action_frame,
            text=self._t("close"),
            command=self.destroy,
            width=105,
            height=40,
        )

        close_button.grid(
            row=0,
            column=2,
            padx=(0, 8),
        )

        self.cleanup_button = ctk.CTkButton(
            master=action_frame,
            text=self._t("dup_quarantine_selected"),
            command=self._quarantine_selected,
            width=175,
            height=40,
            state="disabled",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )

        self.cleanup_button.grid(
            row=0,
            column=3,
        )

    def _selected_assets(
        self,
    ) -> tuple[AssetFile, ...]:
        """Return files selected for quarantine."""
        return tuple(
            self.asset_lookup[
                relative_path
            ]
            for relative_path, variable in self.selection_vars.items()
            if variable.get()
        )

    def _selected_size_bytes(
        self,
    ) -> int:
        """Return the combined size of selected copies."""
        return sum(
            asset.size_bytes
            for asset in self._selected_assets()
        )

    def _update_selection_summary(self) -> None:
        """Refresh selected duplicate counts and action state."""
        selected_records = self._selected_assets()
        selected_count = len(
            selected_records
        )

        selected_size = format_file_size(
            self._selected_size_bytes()
        )

        self.selected_summary_label.configure(
            text=(
                self._t("dup_files_count", count=selected_count)
            ),
        )

        self.selection_status_label.configure(
            text=(
                self._t(
                    "dup_selection_summary",
                    count=selected_count,
                    size=selected_size,
                )
                if selected_count
                else self._t("dup_select_prompt")
            ),
        )

        self.cleanup_button.configure(
            state=(
                "normal"
                if (
                    selected_count
                    and self.project_folder is not None
                )
                else "disabled"
            ),
        )

    def _select_group_extras(
        self,
        assets: tuple[AssetFile, ...],
    ) -> None:
        """Select every file except the first sorted copy in a group."""
        for index, asset in enumerate(
            assets
        ):
            variable = self.selection_vars.get(
                Path(
                    asset.relative_path
                )
            )

            if variable is not None:
                variable.set(
                    index > 0
                )

        self._update_selection_summary()

    def _clear_group_selection(
        self,
        assets: tuple[AssetFile, ...],
    ) -> None:
        """Clear selected files within one duplicate group."""
        for asset in assets:
            variable = self.selection_vars.get(
                Path(
                    asset.relative_path
                )
            )

            if variable is not None:
                variable.set(
                    False
                )

        self._update_selection_summary()

    def _selection_keeps_one_copy_per_group(
        self,
    ) -> bool:
        """Return True when at least one copy remains in every group."""
        selected_paths = {
            Path(
                asset.relative_path
            )
            for asset in self._selected_assets()
        }

        return all(
            any(
                Path(
                    asset.relative_path
                )
                not in selected_paths
                for asset in assets
            )
            for assets in self.group_assets
            if assets
        )

    def _reveal_asset(
        self,
        asset: AssetFile,
    ) -> None:
        """Reveal a duplicate copy in the system file manager."""
        try:
            reveal_in_file_manager(
                asset.source_path
            )
        except (
            FileNotFoundError,
            OSError,
        ) as error:
            messagebox.showerror(
                title=self._t("dup_cannot_reveal_title"),
                message=str(
                    error
                ),
                parent=self,
            )

    def _quarantine_selected(self) -> None:
        """Confirm and safely quarantine selected duplicate copies."""
        if self.project_folder is None:
            return

        selected_records = self._selected_assets()

        if not selected_records:
            return

        if not self._selection_keeps_one_copy_per_group():
            messagebox.showerror(
                title=self._t("dup_keep_one_title"),
                message=(
                    self._t("dup_keep_one_message")
                ),
                parent=self,
            )
            return

        selected_count = len(
            selected_records
        )

        confirmed = messagebox.askyesno(
            title=self._t("dup_confirm_title"),
            message=(
                self._t("dup_confirm_message", count=selected_count)
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.cleanup_button.configure(
            state="disabled",
            text=self._t("dup_quarantining"),
        )

        self.update_idletasks()

        try:
            result = apply_moves(
                self.project_folder,
                build_duplicate_cleanup_plan(
                    project_folder=self.project_folder,
                    assets_to_quarantine=selected_records,
                ),
                JournalKind.QUARANTINE,
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            messagebox.showerror(
                title=self._t("dup_cleanup_failed_title"),
                message=str(
                    error
                ),
                parent=self,
            )

            self.cleanup_button.configure(
                state="normal",
                text=self._t("dup_quarantine_selected"),
            )
            return

        quarantined_count = len(
            result.done
        )

        if result.failed:
            messagebox.showwarning(
                title=self._t("dup_cleanup_partial_title"),
                message=(
                    self._t(
                        "dup_cleanup_partial_message",
                        done=quarantined_count,
                        failed=len(result.failed),
                    )
                ),
                parent=self,
            )
        else:
            manifest_text = (
                "\n\n" + self._t("dup_cleanup_record", path=result.journal_path)
                if result.journal_path is not None
                else ""
            )

            messagebox.showinfo(
                title=self._t("dup_cleanup_done_title"),
                message=(
                    self._t("dup_cleanup_done_message", count=quarantined_count)
                    + manifest_text
                ),
                parent=self,
            )

        if quarantined_count:
            self._finish_project_change()
        else:
            self.cleanup_button.configure(
                state="normal",
                text=self._t("dup_quarantine_selected"),
            )

    def _restore_last_cleanup(self) -> None:
        """Restore the latest available duplicate cleanup."""
        if self.project_folder is None:
            return

        try:
            manifest_path = latest_journal(
                self.project_folder,
                JournalKind.QUARANTINE,
            )
        except OSError:
            manifest_path = None

        if manifest_path is None:
            messagebox.showinfo(
                title=self._t("dup_nothing_restore_title"),
                message=(
                    self._t("dup_nothing_restore_message")
                ),
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            title=self._t("dup_restore_title"),
            message=(
                self._t("dup_restore_message", path=manifest_path)
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            result = reverse_latest(
                self.project_folder,
                JournalKind.QUARANTINE,
            )
        except (
            NothingToReverseError,
            FileNotFoundError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            messagebox.showerror(
                title=self._t("dup_restore_failed_title"),
                message=str(
                    error
                ),
                parent=self,
            )
            return

        restored_count = len(
            result.done
        )

        if result.failed:
            messagebox.showwarning(
                title=self._t("dup_restore_partial_title"),
                message=(
                    self._t(
                        "dup_restore_partial_message",
                        done=restored_count,
                        failed=len(result.failed),
                    )
                ),
                parent=self,
            )
        else:
            messagebox.showinfo(
                title=self._t("dup_restore_done_title"),
                message=(
                    self._t("dup_restore_done_message", count=restored_count)
                ),
                parent=self,
            )

        if restored_count:
            self._finish_project_change()

    def _finish_project_change(self) -> None:
        """Close this window and refresh the main project scan."""
        callback = self.on_project_changed

        try:
            self.grab_release()
        except Exception:
            pass

        self.destroy()

        if callback is not None:
            callback()
