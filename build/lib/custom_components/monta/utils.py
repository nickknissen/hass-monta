"""Utility functions."""

import re


def snake_case(key: str) -> str:
    """Convert a string to snake_case."""
    string = re.sub(r"[\-\.\s]", "_", str(key))
    return (
        (string[0]).lower()
        + re.sub(
            r"[A-Z]",
            lambda matched: f"_{matched.group(0).lower()}",  # type:ignore[str-bytes-safe]
            string[1:],
        )
    )
