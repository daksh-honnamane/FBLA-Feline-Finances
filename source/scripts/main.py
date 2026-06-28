"""Application entry point for the Feline Finances game."""

from core.bootstrap import configure_runtime
from gameplay.game import run


# Disable bytecode creation before loading the rest of the game modules.
configure_runtime()


if __name__ == "__main__":
    run()