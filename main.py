"""Entry point for the Vibe with Crab desktop application."""

from aniccoli.app import create_app


def main() -> None:
    """Start the Vibe with Crab application."""
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()