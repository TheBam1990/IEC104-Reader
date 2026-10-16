"""Pure table filtering helpers."""

from __future__ import annotations

from collections.abc import Sequence


def matches_filter(values: Sequence[object], query: str, column_index: int) -> bool:
    needle = query.strip().casefold()
    if not needle:
        return True
    return 0 <= column_index < len(values) and needle in str(values[column_index]).casefold()


def matches_filters(values: Sequence[object], filters: dict[int, str]) -> bool:
    return all(matches_filter(values, query, index) for index, query in filters.items())
