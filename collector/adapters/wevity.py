from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

from selectolax.parser import HTMLParser

from collector.adapters.base import SourceAdapter
from collector.config import settings
from collector.http import fetch
from collector.schema import RawContest

BASE = "https://www.wevity.com/"
LIST_URL = "https://www.wevity.com/index.php?c=find&s=1&gbn=list&mode=ing&gp={page}"


def _parse_ix(href: str) -> str:
    qs = parse_qs(urlparse(href).query)
    values = qs.get("ix") or []
    return values[0] if values else href


def _dday_to_end(text: str) -> Optional[date]:
    match = re.search(r"D-(\d+)", text, re.I)
    if not match:
        if re.search(r"D-day|D-Day|오늘", text, re.I):
            return date.today()
        return None
    return date.today() + timedelta(days=int(match.group(1)))


def parse_list(html: str) -> list[RawContest]:
    tree = HTMLParser(html)
    items: list[RawContest] = []
    for row in tree.css("div.ms-list ul.list > li"):
        link = row.css_first("div.tit a[href]")
        if link is None:
            continue
        href = link.attributes.get("href") or ""
        title = re.sub(r"\s+", " ", link.text(separator=" ", strip=True))
        title = re.sub(r"\b(SPECIAL|신규|IDEA|마감임박)\b", "", title).strip()
        if not title or "공모전명" in title:
            continue
        organ = row.css_first("div.organ")
        day = row.css_first("div.day")
        sub = row.css_first("div.sub-tit")
        categories = []
        if sub:
            cats = sub.text(strip=True).replace("분야 :", "").replace("분야:", "")
            categories = [c.strip() for c in cats.split(",") if c.strip()]
        day_text = day.text(strip=True) if day else ""
        status = "open"
        if "예정" in day_text:
            status = "upcoming"
        elif "마감" in day_text and "임박" not in day_text:
            status = "closed"
        source_url = urljoin(BASE, href)
        items.append(
            RawContest(
                source_name="wevity",
                source_id=_parse_ix(href),
                source_url=source_url,
                title=title,
                organizer=organ.text(strip=True) if organ else "",
                categories=categories,
                apply_end=_dday_to_end(day_text),
                apply_url=source_url,
                status_hint=status,
            )
        )
    return items


class WevityAdapter(SourceAdapter):
    name = "wevity"

    def fetch_list(self) -> list[RawContest]:
        collected: list[RawContest] = []
        seen: set[str] = set()
        for page in range(1, settings.max_pages + 1):
            html = fetch(LIST_URL.format(page=page)).text
            batch = parse_list(html)
            if not batch:
                break
            new_items = [item for item in batch if item.source_id not in seen]
            if not new_items:
                break
            for item in new_items:
                seen.add(item.source_id)
                collected.append(item)
            if f"gp={page + 1}" not in html:
                break
        return collected
