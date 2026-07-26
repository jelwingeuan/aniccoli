"""Main desktop window for Animated Broccoli."""

import customtkinter as ctk


class AnimatedBroccoliApp(ctk.CTk):
    """Main application window for Animated Broccoli."""

    def __init__(self) -> None:
        """Create and configure the application window."""
        super().__init__()

        self.title("Animated Broccoli")
        self.geometry("1000x650")
        self.minsize(800, 500)

        self._create_welcome_screen()

    def _create_welcome_screen(self) -> None:
        """Create the welcome screen."""

        self.welcome_frame = ctk.CTkFrame(
            self,
            corner_radius=20,
        )
        self.welcome_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=40,
        )

        self.content_frame = ctk.CTkFrame(
            self.welcome_frame,
            fg_color="transparent",
        )
        self.content_frame.pack(
            expand=True,
            padx=20,
            pady=20,
        )

        self.logo_label = ctk.CTkLabel(
            self.content_frame,
            text="🥦",
            font=ctk.CTkFont(size=72),
        )
        self.logo_label.pack(pady=(10, 5))

        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text="Animated Broccoli",
            font=ctk.CTkFont(
                size=34,
                weight="bold",
            ),
        )
        self.title_label.pack(pady=5)

        self.description_label = ctk.CTkLabel(
            self.content_frame,
            text=(
                "Keep your Blender, Maya, Unity, texture, render,\n"
                "and reference files fresh and organized."
            ),
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        self.description_label.pack(pady=(5, 20))


def create_app() -> AnimatedBroccoliApp:
    """Create and return the application."""
    # Force a visible light appearance by default so widgets are readable
    ctk.set_appearance_mode("Light")
    # Use a standard built-in theme name for predictable colors
    try:
        ctk.set_default_color_theme("blue")
    except Exception:
        pass

    return AnimatedBroccoliApp()