from __future__ import annotations

from collector.filter import canonical_key, normalize_title
from collector.schema import CanonicalContest

GENERIC_ORGANIZERS = {"", "dacon", "daker", "daker/dacon", "daker dacon"}


def _is_generic_organizer(value: str) -> bool:
    return normalize_title(value) in GENERIC_ORGANIZERS


def merge_item(existing: CanonicalContest, item: CanonicalContest) -> CanonicalContest:
    existing.sources = list(dict.fromkeys(existing.sources + item.sources))
    if _is_generic_organizer(existing.organizer) and not _is_generic_organizer(item.organizer):
        existing.organizer = item.organizer
    elif not existing.organizer and item.organizer:
        existing.organizer = item.organizer
    if existing.apply_end is None and item.apply_end:
        existing.apply_end = item.apply_end
        existing.canonical_key = canonical_key(existing.title, existing.organizer, existing.apply_end)
    if existing.apply_start is None and item.apply_start:
        existing.apply_start = item.apply_start
    if not existing.apply_url and item.apply_url:
        existing.apply_url = item.apply_url
    if not existing.source_url and item.source_url:
        existing.source_url = item.source_url
    existing.tags = list(dict.fromkeys(existing.tags + item.tags))
    existing.categories = list(dict.fromkeys(existing.categories + item.categories))
    if item.confidence > existing.confidence:
        existing.confidence = item.confidence
        existing.contest_type = item.contest_type
    existing.needs_review = existing.needs_review or item.needs_review
    existing.included = existing.included or item.included
    if item.first_seen_at and (
        existing.first_seen_at is None or item.first_seen_at < existing.first_seen_at
    ):
        existing.first_seen_at = item.first_seen_at
    return existing


def merge_duplicates(items: list[CanonicalContest]) -> list[CanonicalContest]:
    by_key: dict[str, CanonicalContest] = {}
    for item in items:
        existing = by_key.get(item.canonical_key)
        if existing is None:
            by_key[item.canonical_key] = item
            continue
        merge_item(existing, item)

    by_title: dict[str, list[CanonicalContest]] = {}
    for item in by_key.values():
        by_title.setdefault(normalize_title(item.title), []).append(item)

    merged: list[CanonicalContest] = []
    for group in by_title.values():
        if len(group) == 1:
            merged.append(group[0])
            continue
        dated = [item for item in group if item.apply_end is not None]
        undated = [item for item in group if item.apply_end is None]
        unique_ends = {item.apply_end for item in dated}
        if len(unique_ends) <= 1:
            base = dated[0] if dated else group[0]
            for other in group:
                if other is not base:
                    merge_item(base, other)
            merged.append(base)
            continue
        bases = []
        seen_ends: set = set()
        for item in dated:
            if item.apply_end in seen_ends:
                target = next(b for b in bases if b.apply_end == item.apply_end)
                merge_item(target, item)
                continue
            seen_ends.add(item.apply_end)
            bases.append(item)
        if undated and bases:
            for extra in undated:
                merge_item(bases[0], extra)
        elif undated:
            bases.extend(undated)
        merged.extend(bases)
    return merged
