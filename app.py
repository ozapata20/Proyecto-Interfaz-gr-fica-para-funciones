"""Application entry point for the function graphing tool."""

from ui.main_window import GraphingApplication


def main() -> None:
    GraphingApplication().run()


if __name__ == "__main__":
    main()