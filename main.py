"""Entry point for the Aniccoli desktop application."""

from aniccoli.app import create_app


def main() -> None:
    """Start the Aniccoli application."""
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()