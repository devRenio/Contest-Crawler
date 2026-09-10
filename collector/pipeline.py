from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from collector.adapters import ADAPTERS
from collector.dedup import merge_duplicates
from collector.filter import rule_include, to_canonical
from collector.gemini import enrich
from collector.schema import CanonicalContest
from collector.snapshot import carry_forward, stamp_first_seen, write_snapshot
from collector.store import (
    ContestRow,
    SessionLocal,
    exclude_contests,
    init_db,
    record_run,
    row_to_canonical,
    sync_included,
    upsert_contests,
)

log = logging.getLogger(__name__)


def _existing_map() -> dict[str, ContestRow]:
    with SessionLocal() as session:
        rows = session.scalars(select(ContestRow)).all()
        return {row.canonical_key: row for row in rows}


def _needs_llm(item: CanonicalContest) -> bool:
    if item.source_name == "dacon":
        return False
    return item.needs_review


def crawl() -> dict:
    init_db()
    started = datetime.utcnow()
    raw_items = []
    errors: list[str] = []
    successful_sources: set[str] = set()
    for adapter in ADAPTERS:
        batch, error = adapter.safe_fetch()
        log.info("%s fetched %s", adapter.name, len(batch))
        if error:
            errors.append(error)
            log.warning(error)
            continue
        successful_sources.add(adapter.name)
        raw_items.extend(batch)

    canonical: list[CanonicalContest] = []
    skipped = 0
    for raw in raw_items:
        included, confidence, needs_review = rule_include(raw)
        item = to_canonical(raw, included, confidence, needs_review)
        if not included and not needs_review:
            skipped += 1
            continue
        canonical.append(item)

    merged = merge_duplicates(canonical)
    pending = [item for item in merged if item.included or item.needs_review]
    to_enrich = [item for item in pending if _needs_llm(item)]
    review_queue = [item for item in to_enrich if item.needs_review or item.confidence < 0.5]
    hot_path = [item for item in to_enrich if item not in review_queue]

    hot_path, hot_calls = enrich(hot_path, review=False)
    review_queue, review_calls = enrich(review_queue, review=True)
    by_key = {item.canonical_key: item for item in merged}
    for item in hot_path + review_queue:
        by_key[item.canonical_key] = item
    final = [item for item in by_key.values() if item.included]
    excluded = [item.canonical_key for item in by_key.values() if not item.included]
    dropped = exclude_contests(excluded)

    failed_sources = {adapter.name for adapter in ADAPTERS} - successful_sources
    final = carry_forward(final, failed_sources=failed_sources)
    final = stamp_first_seen(final)

    stored = upsert_contests(final)
    synced = sync_included({item.canonical_key for item in final}, successful_sources)
    record_run(started, len(raw_items), stored, errors)
    write_snapshot(final)
    return {
        "fetched": len(raw_items),
        "kept": len(final),
        "stored": stored,
        "skipped": skipped,
        "excluded": dropped + synced,
        "llm_calls": hot_calls + review_calls,
        "errors": errors,
    }


def enrich_existing() -> dict:
    """Re-run LLM gate on borderline rows already stored."""
    init_db()
    existing = _existing_map()
    pending = [
        row_to_canonical(row)
        for row in existing.values()
        if row.included or row.needs_review
    ]
    to_enrich = [item for item in pending if _needs_llm(item)]
    review_queue = [item for item in to_enrich if item.needs_review or item.confidence < 0.5]
    hot_path = [item for item in to_enrich if item not in review_queue]
    hot_path, hot_calls = enrich(hot_path, review=False)
    review_queue, review_calls = enrich(review_queue, review=True)
    enriched = hot_path + review_queue
    excluded = [item.canonical_key for item in enriched if not item.included]
    dropped = exclude_contests(excluded)
    stored = upsert_contests([item for item in enriched if item.included])
    return {
        "pending": len(pending),
        "stored": stored,
        "excluded": dropped,
        "llm_calls": hot_calls + review_calls,
    }
