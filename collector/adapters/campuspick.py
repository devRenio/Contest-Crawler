from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from collector.adapters.base import SourceAdapter
from collector.config import settings
from collector.http import fetch
from collector.schema import RawContest

LIST_URL = "https://api2.campuspick.com/find/activity/list"
VIEW_URL = "https://www.campuspick.com/contest/view?id={id}"
TARGET_CONTEST = 1
PAGE_SIZE = 50
# 최신순. 한 페이지가 전부 지난 마감이면 중단한다.
MAX_PAGES = 16


def _parse_day(value: Any) -> Optional[date]:
    if not value:
        return None
    text = str(value)[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_activities(payload: dict) -> list[RawContest]:
    result = payload.get("result") or {}
    items: list[RawContest] = []
    seen: set[str] = set()
    for row in result.get("activities") or []:
        raw_id = row.get("id")
        title = str(row.get("title") or "").strip()
        if raw_id is None or not title:
            continue
        source_id = str(raw_id)
        if source_id in seen:
            continue
        seen.add(source_id)
        apply_end = _parse_day(row.get("endDate") or row.get("end_date"))
        apply_start = _parse_day(row.get("startDate") or row.get("start_date"))
        cats = row.get("categories") or []
        source_url = VIEW_URL.format(id=source_id)
        status = "open"
        if apply_end and apply_end < date.today():
            status = "closed"
        items.append(
            RawContest(
                source_name="campuspick",
                source_id=source_id,
                source_url=source_url,
                title=title,
                organizer=str(row.get("company") or row.get("organizer") or "").strip(),
                categories=[str(c) for c in cats if c is not None],
                apply_start=apply_start,
                apply_end=apply_end,
                apply_url=source_url,
                status_hint=status,
            )
        )
    return items


class CampuspickAdapter(SourceAdapter):
    name = "campuspick"

    def fetch_list(self) -> list[RawContest]:
        collected: list[RawContest] = []
        seen: set[str] = set()
        pages = max(settings.max_pages, MAX_PAGES)
        for page in range(pages):
            payload = fetch(
                LIST_URL,
                method="POST",
                json_body={"target": TARGET_CONTEST, "limit": PAGE_SIZE, "offset": page * PAGE_SIZE},
                headers={
                    "Accept": "application/json",
                    "Origin": "https://www.campuspick.com",
                    "Referer": "https://www.campuspick.com/contest",
                    "Content-Type": "application/json",
                },
            ).json()
            batch = parse_activities(payload)
            if not batch:
                break
            added = 0
            for item in batch:
                if item.source_id in seen:
                    continue
                seen.add(item.source_id)
                collected.append(item)
                added += 1
            if added == 0:
                break
        return collected
