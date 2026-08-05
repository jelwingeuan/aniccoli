"""Help and application-information window for Aniccoli."""

from __future__ import annotations

import customtkinter as ctk


class AboutWindow(ctk.CTkToplevel):
    """Display Aniccoli help, workflow guidance, and shortcuts."""

    def __init__(
        self,
        master: ctk.CTk,
        version: str,
        shortcut_modifier: str,
    ) -> None:
        """Create the help and about window."""
        super().__init__(
            master
        )

        self.title(
            "About Aniccoli"
        )

        self.geometry(
            "780x690"
        )

        self.minsize(
            680,
            560,
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
            1,
            weight=1,
        )

        self._create_header(
            version=version,
        )

        self._create_content(
            shortcut_modifier=shortcut_modifier,
        )

        self._create_close_button()

    def _create_header(
        self,
        version: str,
    ) -> None:
        """Create the window heading."""
        header_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )

        header_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(28, 16),
        )

        header_frame.grid_columnconfigure(
            1,
            weight=1,
        )

        logo_label = ctk.CTkLabel(
            master=header_frame,
            text="🥦",
            font=ctk.CTkFont(
                size=52,
            ),
        )

        logo_label.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(0, 16),
        )

        title_label = ctk.CTkLabel(
            master=header_frame,
            text="Aniccoli",
            font=ctk.CTkFont(
                size=30,
                weight="bold",
            ),
            anchor="w",
        )

        title_label.grid(
            row=0,
            column=1,
            sticky="w",
        )

        version_label = ctk.CTkLabel(
            master=header_frame,
            text=f"Version {version}",
            font=ctk.CTkFont(
                size=13,
            ),
            anchor="w",
        )

        version_label.grid(
            row=1,
            column=1,
            sticky="w",
        )

    def _create_content(
        self,
        shortcut_modifier: str,
    ) -> None:
        """Create help sections inside a scrollable panel."""
        scroll_frame = ctk.CTkScrollableFrame(
            master=self,
            corner_radius=14,
        )

        scroll_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(0, 16),
        )

        scroll_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        intro_text = (
            "Aniccoli is a local desktop organizer for 3D-production "
            "assets. It scans project folders, classifies files, previews "
            "safe organization plans, finds exact duplicates, exports "
            "reports, and keeps undo or restoration records."
        )

        self._create_section(
            parent=scroll_frame,
            row=0,
            heading="What Aniccoli does",
            body=intro_text,
        )

        workflow_text = (
            "1. Choose a project folder.\n"
            "2. Scan the folder and review detected assets.\n"
            "3. Search, filter, sort, and select the files to use.\n"
            "4. Preview organization before moving anything.\n"
            "5. Confirm the plan only after reviewing every destination.\n"
            "6. Use Undo Last Organization or duplicate restoration when needed."
        )

        self._create_section(
            parent=scroll_frame,
            row=1,
            heading="Recommended workflow",
            body=workflow_text,
        )

        safety_text = (
            "• Organization always begins with a preview.\n"
            "• Filename conflicts are renamed instead of overwritten.\n"
            "• Organization operations write undo history.\n"
            "• Duplicate cleanup moves copies into private quarantine.\n"
            "• Existing files are never overwritten during restoration.\n"
            "• Reports and statistics do not modify project files."
        )

        self._create_section(
            parent=scroll_frame,
            row=2,
            heading="Safety protections",
            body=safety_text,
        )

        shortcut_text = (
            f"{shortcut_modifier} + O    Choose project folder\n"
            f"{shortcut_modifier} + R    Scan selected folder\n"
            f"{shortcut_modifier} + F    Focus asset search\n"
            f"{shortcut_modifier} + Shift + A    Select visible assets\n"
            f"{shortcut_modifier} + Shift + C    Clear asset selection\n"
            "F1    Open this help window"
        )

        self._create_section(
            parent=scroll_frame,
            row=3,
            heading="Keyboard shortcuts",
            body=shortcut_text,
        )

        storage_text = (
            "Aniccoli stores its organization logs and duplicate-cleanup "
            "records inside a hidden .aniccoli folder within the selected "
            "project. Keep this folder while you may still need undo or "
            "restoration features."
        )

        self._create_section(
            parent=scroll_frame,
            row=4,
            heading="Project history",
            body=storage_text,
        )

    def _create_section(
        self,
        parent: ctk.CTkScrollableFrame,
        row: int,
        heading: str,
        body: str,
    ) -> None:
        """Create one help-information card."""
        card = ctk.CTkFrame(
            master=parent,
            corner_radius=11,
        )

        card.grid(
            row=row,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )

        card.grid_columnconfigure(
            0,
            weight=1,
        )

        heading_label = ctk.CTkLabel(
            master=card,
            text=heading,
            font=ctk.CTkFont(
                size=16,
                weight="bold",
            ),
            anchor="w",
        )

        heading_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=16,
            pady=(14, 5),
        )

        body_label = ctk.CTkLabel(
            master=card,
            text=body,
            font=ctk.CTkFont(
                size=13,
            ),
            anchor="w",
            justify="left",
            wraplength=650,
        )

        body_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=16,
            pady=(0, 15),
        )

    def _create_close_button(self) -> None:
        """Create the close action."""
        action_frame = ctk.CTkFrame(
            master=self,
            fg_color="transparent",
        )

        action_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 28),
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
