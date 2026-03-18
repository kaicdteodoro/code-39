"""Formatting helpers for Atlântico Gastrobar references."""

from __future__ import annotations

PREFIX = "ATL"
MIN_REFERENCE = 1
MAX_REFERENCE = 500
WIDTH = 3


def validate_number(number: int) -> int:
    """Ensure the reference number is inside the allowed range."""
    if number < MIN_REFERENCE or number > MAX_REFERENCE:
        raise ValueError(
            f"Reference number must be between {MIN_REFERENCE} and {MAX_REFERENCE}."
        )
    return number


def format_reference(number: int, prefix: str = PREFIX) -> str:
    """Convert an integer into the canonical ATL001 format."""
    valid = validate_number(number)
    return f"{prefix}{valid:0{WIDTH}d}"


def parse_reference(reference: str, prefix: str = PREFIX) -> int:
    """Convert ATL001-like references into their numeric form."""
    normalized = reference.strip().upper()
    if not normalized.startswith(prefix):
        raise ValueError(f"Reference must start with '{prefix}'.")

    numeric = normalized[len(prefix) :]
    if len(numeric) != WIDTH or not numeric.isdigit():
        raise ValueError(
            f"Reference must follow the {prefix}{'0' * (WIDTH - 1)}1 format."
        )

    return validate_number(int(numeric))
