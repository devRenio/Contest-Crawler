from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from collector.config import ROOT
from collector.dedup import merge_duplicates
from collector.filter import canonical_key, normalize_title
from collector.schema import CanonicalContest

SNAPSHOT_PATH = ROOT / "data" / "contests.json"
SEEN_PATH = ROOT / "data" / "first_seen.json"
LEGACY_FIRST_SEEN = datetime(2026, 9, 3, 0, 0, 0)


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None)
    except ValueError:
        day = _parse_date(value)
        return datetime(day.year, day.month, day.day) if day else None


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_first_seen() -> tuple[dict[str, str], dict[str, str]]:
    raw = _read_json(SEEN_PATH) or {}
    if not isinstance(raw, dict):
        return {}, {}
    if "by_key" in raw or "by_title" in raw:
        return dict(raw.get("by_key") or {}), dict(raw.get("by_title") or {})
    return {str(k): str(v) for k, v in raw.items()}, {}


def save_first_seen(by_key: dict[str, str], by_title: dict[str, str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "by_key": dict(sorted(by_key.items())),
        "by_title": dict(sorted(by_title.items())),
    }
    SEEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dict_to_canonical(row: dict) -> CanonicalContest:
    title = str(row.get("title") or "").strip()
    organizer = str(row.get("organizer") or "")
    apply_end = _parse_date(row.get("apply_end"))
    contest_type = row.get("contest_type") or "contest"
    if contest_type not in {"hackathon", "contest", "datathon", "idea", "security", "etc"}:
        contest_type = "contest"
    status = row.get("status") or "open"
    if status not in {"open", "upcoming", "closed"}:
        status = "open"
    sources = [str(s) for s in (row.get("sources") or []) if s]
    source_name = str(row.get("source_name") or (sources[0] if sources else "unknown"))
    if not sources and source_name:
        sources = [source_name]
    return CanonicalContest(
        canonical_key=canonical_key(title, organizer, apply_end),
        title=title,
        organizer=organizer,
        contest_type=contest_type,  # type: ignore[arg-type]
        tags=list(row.get("tags") or []),
        categories=list(row.get("categories") or []),
        eligibility=str(row.get("eligibility") or ""),
        apply_start=_parse_date(row.get("apply_start")),
        apply_end=apply_end,
        apply_url=str(row.get("apply_url") or row.get("source_url") or ""),
        source_url=str(row.get("source_url") or row.get("apply_url") or ""),
        source_name=source_name,
        sources=sources,
        status=status,  # type: ignore[arg-type]
        included=True,
        first_seen_at=_parse_dt(row.get("first_seen_at")),
        needs_review=bool(row.get("needs_review", False)),
    )


def load_previous_snapshot(path: Path | None = None) -> list[CanonicalContest]:
    raw = _read_json(path or SNAPSHOT_PATH)
    if not isinstance(raw, list):
        return []
    items: list[CanonicalContest] = []
    for row in raw:
        if not isinstance(row, dict) or not row.get("title"):
            continue
        items.append(dict_to_canonical(row))
    return items


def _bootstrap_seen_from_snapshot(
    by_key: dict[str, str],
    by_title: dict[str, str],
) -> None:
    if by_key or by_title:
        return
    for item in load_previous_snapshot():
        iso = (item.first_seen_at or LEGACY_FIRST_SEEN).isoformat()
        by_key[item.canonical_key] = iso
        title_key = normalize_title(item.title)
        if title_key:
            by_title[title_key] = iso


def carry_forward(
    current: list[CanonicalContest],
    *,
    failed_sources: set[str],
    previous: list[CanonicalContest] | None = None,
    today: date | None = None,
) -> list[CanonicalContest]:
    """Keep last snapshot rows for sources that failed this crawl."""
    if not failed_sources:
        return current
    today = today or date.today()
    prev = previous if previous is not None else load_previous_snapshot()
    extras: list[CanonicalContest] = []
    for item in prev:
        item_sources = set(item.sources) or {item.source_name}
        if not (item_sources & failed_sources):
            continue
        if item.apply_end is not None and item.apply_end < today:
            continue
        extras.append(item)
    if not extras:
        return current
    return merge_duplicates([*current, *extras])


def stamp_first_seen(
    items: list[CanonicalContest],
    *,
    now: datetime | None = None,
) -> list[CanonicalContest]:
    now = now or datetime.utcnow()
    by_key, by_title = load_first_seen()
    _bootstrap_seen_from_snapshot(by_key, by_title)
    for item in items:
        title_key = normalize_title(item.title)
        candidates: list[datetime] = []
        for raw in (by_key.get(item.canonical_key), by_title.get(title_key) if title_key else None):
            parsed = _parse_dt(raw)
            if parsed:
                candidates.append(parsed)
        if item.first_seen_at:
            candidates.append(item.first_seen_at)
        seen = min(candidates) if candidates else now
        item.first_seen_at = seen
        iso = seen.isoformat()
        by_key[item.canonical_key] = iso
        if title_key:
            previous = _parse_dt(by_title.get(title_key))
            if previous is None or seen <= previous:
                by_title[title_key] = iso
    save_first_seen(by_key, by_title)
    return items


def to_snapshot_item(item: CanonicalContest) -> dict:
    return {
        "id": item.canonical_key,
        "title": item.title,
        "organizer": item.organizer,
        "contest_type": item.contest_type,
        "tags": item.tags,
        "eligibility": item.eligibility,
        "apply_start": item.apply_start.isoformat() if item.apply_start else None,
        "apply_end": item.apply_end.isoformat() if item.apply_end else None,
        "apply_url": item.apply_url,
        "source_url": item.source_url,
        "source_name": item.source_name,
        "sources": item.sources,
        "summary": "",
        "status": item.status,
        "first_seen_at": item.first_seen_at.isoformat() if item.first_seen_at else None,
        "needs_review": item.needs_review,
    }


def _is_current(item: CanonicalContest, today: date) -> bool:
    if not item.included or item.status == "closed":
        return False
    if item.apply_end is not None and item.apply_end < today:
        return False
    return True


def write_snapshot(items: list[CanonicalContest], path: Path | None = None) -> Path:
    out = path or SNAPSHOT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    today = date.today()
    payload = [to_snapshot_item(item) for item in items if _is_current(item, today)]
    payload.sort(
        key=lambda row: (
            row.get("apply_end") is None,
            row.get("apply_end") or "9999",
            row.get("title") or "",
        )
    )
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
