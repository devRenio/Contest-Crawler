from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Optional
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from collector.adapters.base import SourceAdapter, status_from_dates
from collector.config import settings
from collector.http import fetch
from collector.schema import RawContest

LIST_URL = "https://linkareer.com/list/contest?page={page}"
BASE = "https://linkareer.com"


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    text = str(value)
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", text)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def _walk(obj: Any) -> list[dict]:
    found: list[dict] = []
    if isinstance(obj, dict):
        keys = {k.lower() for k in obj.keys()}
        if {"title", "id"} <= keys or {"title", "activityid"} <= {k.lower() for k in obj}:
            found.append(obj)
        for value in obj.values():
            found.extend(_walk(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk(item))
    return found


def parse_next_data(html: str) -> list[RawContest]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    items: list[RawContest] = []
    seen: set[str] = set()
    if match:
        payload = json.loads(match.group(1))
        for node in _walk(payload):
            title = str(node.get("title") or node.get("activityTitle") or "").strip()
            title = re.sub(r"^추천\s*", "", title)
            raw_id = node.get("id") or node.get("activityId") or node.get("activityID")
            if not title or raw_id is None:
                continue
            source_id = str(raw_id)
            if source_id in seen:
                continue
            seen.add(source_id)
            href = f"{BASE}/activity/{source_id}"
            organizer = (
                node.get("organizationName")
                or node.get("host")
                or node.get("companyName")
                or ""
            )
            apply_start = _parse_date(node.get("recruitmentStartDate") or node.get("startDate"))
            apply_end = _parse_date(node.get("recruitmentEndDate") or node.get("endDate"))
            items.append(
                RawContest(
                    source_name="linkareer",
                    source_id=source_id,
                    source_url=href if str(href).startswith("http") else href,
                    title=title,
                    organizer=str(organizer or ""),
                    categories=[str(c) for c in (node.get("categories") or node.get("jobTypes") or []) if c],
                    eligibility=str(node.get("target") or node.get("eligibility") or ""),
                    apply_start=apply_start,
                    apply_end=apply_end,
                    apply_url=urljoin(BASE, str(node.get("url") or href)),
                    status_hint=status_from_dates(apply_start, apply_end),
                )
            )
    if items:
        return items
    return parse_html_cards(html)


def parse_html_cards(html: str) -> list[RawContest]:
    tree = HTMLParser(html)
    items: list[RawContest] = []
    seen: set[str] = set()
    for link in tree.css('a[href*="/activity/"]'):
        href = link.attributes.get("href") or ""
        id_match = re.search(r"/activity/(\d+)", href)
        if not id_match:
            continue
        source_id = id_match.group(1)
        if source_id in seen:
            continue
        title = link.text(strip=True)
        if len(title) < 4:
            parent = link.parent
            if parent:
                title_el = parent.css_first(".activity-title") or parent.css_first("h3") or parent.css_first("p")
                if title_el:
                    title = title_el.text(strip=True)
        if len(title) < 4:
            continue
        title = re.sub(r"^추천\s*", "", re.sub(r"\s+", " ", title))
        seen.add(source_id)
        source_url = urljoin(BASE, href.split("?")[0])
        items.append(
            RawContest(
                source_name="linkareer",
                source_id=source_id,
                source_url=source_url,
                title=title,
                apply_url=source_url,
                status_hint="open",
            )
        )
    return items


class LinkareerAdapter(SourceAdapter):
    name = "linkareer"

    def fetch_list(self) -> list[RawContest]:
        collected: list[RawContest] = []
        seen: set[str] = set()
        for page in range(1, min(settings.max_pages, 5) + 1):
            html = fetch(LIST_URL.format(page=page)).text
            batch = parse_next_data(html)
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
