"""
Module that provides utility functions for creating progress bars.
"""


def create_progress_bar(current: int, total: int, width: int = 10) -> str:
    """Create a visual progress bar for limited resources."""
    if total == 0:
        return "[" + "░" * width + "] 0/0 (0%)"

    filled = int((current / total) * width)
    empty = width - filled
    percentage = (current / total) * 100

    bar = "█" * filled + "░" * empty
    return f"[{bar}] {current}/{total} ({percentage:.1f}%)"
