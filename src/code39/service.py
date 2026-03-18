"""Application service for planning batches of references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .formatting import MAX_REFERENCE, MIN_REFERENCE, format_reference, parse_reference


@dataclass(frozen=True)
class BatchPlan:
    """Represents a batch to be rendered into a PDF."""

    references: list[str]

    @property
    def quantity(self) -> int:
        return len(self.references)

    @property
    def first_reference(self) -> str:
        return self.references[0]

    @property
    def last_reference(self) -> str:
        return self.references[-1]


def build_batch_plan(
    *,
    start: int = MIN_REFERENCE,
    end: int = MAX_REFERENCE,
    limit: int | None = None,
    reference: str | None = None,
) -> BatchPlan:
    """Build the list of references that should be generated."""
    if reference:
        return BatchPlan(references=[format_reference(parse_reference(reference))])

    if start > end:
        raise ValueError("Start cannot be greater than end.")

    if start < MIN_REFERENCE or end > MAX_REFERENCE:
        raise ValueError(
            f"Batch range must stay between {MIN_REFERENCE} and {MAX_REFERENCE}."
        )

    references = [format_reference(number) for number in range(start, end + 1)]

    if limit is not None:
        if limit <= 0:
            raise ValueError("Limit must be greater than zero.")
        references = references[:limit]

    if not references:
        raise ValueError("Batch cannot be empty.")

    return BatchPlan(references=references)


def find_duplicates(references: Iterable[str], generated: set[str]) -> list[str]:
    """Return references that already exist in the registry."""
    return [reference for reference in references if reference in generated]


def next_available_reference(generated: set[str]) -> str | None:
    """Return the next unissued reference, or None when all are used."""
    for number in range(MIN_REFERENCE, MAX_REFERENCE + 1):
        reference = format_reference(number)
        if reference not in generated:
            return reference
    return None
