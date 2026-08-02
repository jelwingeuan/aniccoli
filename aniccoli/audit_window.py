"""Asset health-audit window for Aniccoli."""

from __future__ import annotations

from collections.abc import Iterable

import customtkinter as ctk

from aniccoli.audit import (
    AssetAuditIssue,
    AssetAuditReport,
    AuditSeverity,
)


class AssetAuditWindow(ctk.CTkToplevel):
    """Display the results of an Aniccoli asset health audit."""

    def __init__(
        self,
        master: ctk.CTk,
        report: AssetAuditReport,
    ) -> None:
        """Create the asset health-audit window."""
        super().__init__(master)

        self.report = report

        self.title("Aniccoli Asset Health")
        self.geometry("1120x760")
        self.minsize(920, 620)
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
        self._create_issue_tabs()
        self._create_close_button()

    def _create_header(self) -> None:
        """Create the audit-window heading."""
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
            text="Asset Health",
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
                "A read-only audit for empty files, large files, "
                "duplicate filenames, missing extensions, and stale assets."
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
        """Create the main audit summary cards."""
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
                uniform="audit-summary",
            )

        summary_values = (
            (
                "Assets scanned",
                str(self.report.scanned_asset_count),
            ),
            (
                "Healthy assets",
                str(self.report.healthy_asset_count),
            ),
            (
                "Errors",
                str(self.report.error_count),
            ),
            (
                "Warnings",
                str(self.report.warning_count),
            ),
            (
                "Total issues",
                str(self.report.issue_count),
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
        """Create one audit-summary card."""
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

    def _create_issue_tabs(self) -> None:
        """Create tabs for all issues and each severity level."""
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
            "All Issues",
            "Errors",
            "Warnings",
            "Info",
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

        self._populate_issue_tab(
            parent=tab_view.tab("All Issues"),
            issues=self.report.issues,
            empty_message=(
                "No health issues were found. "
                "The scanned project looks healthy."
            ),
        )

        self._populate_issue_tab(
            parent=tab_view.tab("Errors"),
            issues=self._issues_for_severity(
                AuditSeverity.ERROR
            ),
            empty_message="No error-level issues were found.",
        )

        self._populate_issue_tab(
            parent=tab_view.tab("Warnings"),
            issues=self._issues_for_severity(
                AuditSeverity.WARNING
            ),
            empty_message="No warning-level issues were found.",
        )

        self._populate_issue_tab(
            parent=tab_view.tab("Info"),
            issues=self._issues_for_severity(
                AuditSeverity.INFO
            ),
            empty_message="No informational issues were found.",
        )

    def _issues_for_severity(
        self,
        severity: AuditSeverity,
    ) -> tuple[AssetAuditIssue, ...]:
        """Return audit issues matching one severity."""
        return tuple(
            issue
            for issue in self.report.issues
            if issue.severity is severity
        )

    def _populate_issue_tab(
        self,
        parent: ctk.CTkFrame,
        issues: Iterable[AssetAuditIssue],
        empty_message: str,
    ) -> None:
        """Populate one audit tab with issue rows."""
        issue_records = tuple(
            issues
        )

        scroll_frame = ctk.CTkScrollableFrame(
            master=parent,
            corner_radius=10,
        )

        scroll_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10,
        )

        scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        if not issue_records:
            empty_label = ctk.CTkLabel(
                master=scroll_frame,
                text=empty_message,
                font=ctk.CTkFont(
                    size=14,
                ),
                justify="center",
            )

            empty_label.grid(
                row=0,
                column=0,
                padx=20,
                pady=70,
            )
            return

        for row_number, issue in enumerate(
            issue_records
        ):
            self._create_issue_row(
                parent=scroll_frame,
                issue=issue,
                row_number=row_number,
            )

    def _create_issue_row(
        self,
        parent: ctk.CTkScrollableFrame,
        issue: AssetAuditIssue,
        row_number: int,
    ) -> None:
        """Create one row describing an audit issue."""
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
            1,
            weight=1,
        )

        severity_label = ctk.CTkLabel(
            master=row_frame,
            text=str(
                issue.severity
            ),
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            width=90,
        )

        severity_label.grid(
            row=0,
            column=0,
            rowspan=3,
            padx=(14, 10),
            pady=12,
        )

        issue_heading = ctk.CTkLabel(
            master=row_frame,
            text=(
                f"{issue.issue_type}  •  "
                f"{issue.relative_path}"
            ),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            anchor="w",
            justify="left",
        )

        issue_heading.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 14),
            pady=(12, 2),
        )

        message_label = ctk.CTkLabel(
            master=row_frame,
            text=issue.message,
            font=ctk.CTkFont(
                size=12,
            ),
            anchor="w",
            justify="left",
            wraplength=850,
        )

        message_label.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 14),
            pady=(0, 4),
        )

        related_text = (
            "Related: "
            + ", ".join(
                str(path)
                for path in issue.related_paths
            )
            if issue.related_paths
            else ""
        )

        related_label = ctk.CTkLabel(
            master=row_frame,
            text=related_text,
            font=ctk.CTkFont(
                size=11,
            ),
            anchor="w",
            justify="left",
            wraplength=850,
        )

        related_label.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(0, 14),
            pady=(0, 12),
        )

    def _create_close_button(self) -> None:
        """Create the close-window action."""
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

        close_button = ctk.CTkButton(
            master=action_frame,
            text="Close",
            command=self.destroy,
            width=130,
            height=40,
        )

        close_button.grid(
            row=0,
            column=1,
        )
