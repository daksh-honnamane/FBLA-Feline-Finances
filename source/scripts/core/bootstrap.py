import sys


def configure_runtime():
    """Apply early runtime flags shared by all launch paths."""
    # Keep project folders clean by avoiding __pycache__ files during local runs.
    sys.dont_write_bytecode = True