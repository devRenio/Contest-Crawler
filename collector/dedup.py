from __future__ import annotations

from collector.schema import CanonicalContest


def merge_duplicates(items: list[CanonicalContest]) -> list[CanonicalContest]:
    by_key: dict[str, CanonicalContest] = {}
    for item in items:
        existing = by_key.get(item.canonical_key)
        if existing is None:
            by_key[item.canonical_key] = item
            continue
        sources = list(dict.fromkeys(existing.sources + item.sources))
        existing.sources = sources
        if not existing.organizer and item.organizer:
            existing.organizer = item.organizer
        if existing.apply_end is None and item.apply_end:
            existing.apply_end = item.apply_end
        if existing.apply_start is None and item.apply_start:
            existing.apply_start = item.apply_start
        existing.tags = list(dict.fromkeys(existing.tags + item.tags))
        existing.categories = list(dict.fromkeys(existing.categories + item.categories))
        if item.confidence > existing.confidence:
            existing.confidence = item.confidence
        existing.needs_review = existing.needs_review or item.needs_review
    return list(by_key.values())
