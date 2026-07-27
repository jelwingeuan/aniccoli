"""Main desktop window for Aniccoli."""

import customtkinter as ctk


class AniccoliApp(ctk.CTk):
    """Main application window for Aniccoli."""

    def __init__(self) -> None:
        """Create and configure the application window."""
        super().__init__()

        self.title("Aniccoli")
        self.geometry("1000x650")
        self.minsize(800, 500)

        self._create_welcome_screen()

    def _create_welcome_screen(self) -> None:
        """Create the welcome screen."""
        welcome_frame = ctk.CTkFrame(
            master=self,
            corner_radius=20,
        )
        welcome_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=40,
        )

        logo_label = ctk.CTkLabel(
            master=welcome_frame,
            text="🥦",
            font=ctk.CTkFont(size=72),
        )
        logo_label.pack(pady=(120, 5))

        title_label = ctk.CTkLabel(
            master=welcome_frame,
            text="Aniccoli",
            font=ctk.CTkFont(
                size=34,
                weight="bold",
            ),
        )
        title_label.pack(pady=5)

        description_label = ctk.CTkLabel(
            master=welcome_frame,
            text=(
                "Keep your Blender, Maya, Unity, texture, render,\n"
                "and reference files fresh and organized."
            ),
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        description_label.pack(pady=(5, 20))


def create_app() -> AniccoliApp:
    """Create and return the Aniccoli application."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")

    return AniccoliApp()