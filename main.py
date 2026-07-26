"""Entry point for the Animated Broccoli desktop application."""

from animated_broccoli.app import create_app


def main() -> None:
    """Start the Animated Broccoli application."""
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()