"""Main desktop window for Animated Broccoli."""

import customtkinter as ctk


class AnimatedBroccoliApp(ctk.CTk):
    """Main application window for the Animated Broccoli asset organizer."""

    def __init__(self) -> None:
        """Create and configure the main application window."""
        super().__init__()

        self._configure_window()
        self._create_welcome_screen()

    def _configure_window(self) -> None:
        """Configure the title, size, theme, and layout of the window."""
        self.title("Animated Broccoli")

        self.geometry("1000x650")
        self.minsize(800, 500)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _create_welcome_screen(self) -> None:
        """Create the temporary welcome screen shown at application startup."""
        welcome_frame = ctk.CTkFrame(
            master=self,
            corner_radius=20,
        )
        welcome_frame.grid(
            row=0,
            column=0,
            padx=40,
            pady=40,
            sticky="nsew",
        )

        welcome_frame.grid_columnconfigure(0, weight=1)
        welcome_frame.grid_rowconfigure(0, weight=1)
        welcome_frame.grid_rowconfigure(4, weight=1)

        logo_label = ctk.CTkLabel(
            master=welcome_frame,
            text="🥦",
            font=ctk.CTkFont(size=72),
        )
        logo_label.grid(
            row=1,
            column=0,
            padx=20,
            pady=(20, 5),
        )

        title_label = ctk.CTkLabel(
            master=welcome_frame,
            text="Animated Broccoli",
            font=ctk.CTkFont(size=34, weight="bold"),
        )
        title_label.grid(
            row=2,
            column=0,
            padx=20,
            pady=5,
        )

        description_label = ctk.CTkLabel(
            master=welcome_frame,
            text=(
                "Keep your Blender, Maya, Unity, texture, render,\n"
                "and reference files fresh and organized."
            ),
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        description_label.grid(
            row=3,
            column=0,
            padx=20,
            pady=(5, 20),
        )


def create_app() -> AnimatedBroccoliApp:
    """Create and return the main application instance."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")

    return AnimatedBroccoliApp()