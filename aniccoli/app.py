"""Main desktop window for Aniccoli."""

from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk


class AniccoliApp(ctk.CTk):
    """Main application window for Aniccoli."""

    def __init__(self) -> None:
        """Create and configure the application window."""
        super().__init__()

        self.selected_folder: Optional[Path] = None

        self._configure_window()
        self._create_welcome_screen()

    def _configure_window(self) -> None:
        """Configure the main application window."""
        self.title("Aniccoli")
        self.geometry("1000x650")
        self.minsize(800, 500)

    def _create_welcome_screen(self) -> None:
        """Create the welcome screen and folder-selection controls."""
        self.welcome_frame = ctk.CTkFrame(
            master=self,
            corner_radius=20,
        )
        self.welcome_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=40,
        )

        self.content_frame = ctk.CTkFrame(
            master=self.welcome_frame,
            fg_color="transparent",
        )
        self.content_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=40,
        )

        logo_label = ctk.CTkLabel(
            master=self.content_frame,
            text="🥦",
            font=ctk.CTkFont(size=64),
        )
        logo_label.pack(
            pady=(20, 5),
        )

        title_label = ctk.CTkLabel(
            master=self.content_frame,
            text="Aniccoli",
            font=ctk.CTkFont(
                size=34,
                weight="bold",
            ),
        )
        title_label.pack(
            pady=5,
        )

        description_label = ctk.CTkLabel(
            master=self.content_frame,
            text=(
                "Keep your Blender, Maya, Unity, texture, render,\n"
                "and reference files fresh and organized."
            ),
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        description_label.pack(
            pady=(5, 30),
        )

        self.folder_card = ctk.CTkFrame(
            master=self.content_frame,
            corner_radius=15,
        )
        self.folder_card.pack(
            fill="x",
            padx=60,
            pady=(10, 20),
        )

        folder_heading_label = ctk.CTkLabel(
            master=self.folder_card,
            text="Select a project folder",
            font=ctk.CTkFont(
                size=20,
                weight="bold",
            ),
        )
        folder_heading_label.pack(
            padx=30,
            pady=(25, 5),
        )

        folder_description_label = ctk.CTkLabel(
            master=self.folder_card,
            text=(
                "Choose the folder containing your 3D models, "
                "textures, references, renders, or Unity assets."
            ),
            font=ctk.CTkFont(size=14),
            justify="center",
            wraplength=650,
        )
        folder_description_label.pack(
            padx=30,
            pady=(0, 20),
        )

        select_folder_button = ctk.CTkButton(
            master=self.folder_card,
            text="Choose Project Folder",
            command=self._select_folder,
            width=220,
            height=42,
            corner_radius=10,
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
        )
        select_folder_button.pack(
            padx=30,
            pady=(0, 20),
        )

        selected_heading_label = ctk.CTkLabel(
            master=self.folder_card,
            text="Selected folder",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        )
        selected_heading_label.pack(
            padx=30,
            pady=(0, 3),
        )

        self.selected_folder_label = ctk.CTkLabel(
            master=self.folder_card,
            text="No folder selected",
            font=ctk.CTkFont(size=13),
            justify="center",
            wraplength=650,
        )
        self.selected_folder_label.pack(
            padx=30,
            pady=(0, 10),
        )

        self.status_label = ctk.CTkLabel(
            master=self.folder_card,
            text="Choose a folder to begin.",
            font=ctk.CTkFont(size=13),
        )
        self.status_label.pack(
            padx=30,
            pady=(0, 25),
        )

    def _select_folder(self) -> None:
        """Open a folder picker and store the selected project folder."""
        selected_path = filedialog.askdirectory(
            parent=self,
            title="Select a 3D project folder",
            mustexist=True,
        )

        if not selected_path:
            return

        self.selected_folder = Path(selected_path)

        self.selected_folder_label.configure(
            text=str(self.selected_folder),
        )

        self.status_label.configure(
            text="Project folder selected successfully.",
        )


def create_app() -> AniccoliApp:
    """Create and return the Aniccoli application."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")

    return AniccoliApp()