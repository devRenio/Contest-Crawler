from __future__ import annotations

import re
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from collector.adapters.base import SourceAdapter
from collector.http import fetch
from collector.schema import RawContest

LIST_URL = "https://dacon.io/competitions"
BASE = "https://dacon.io"


def _status(text: str) -> str:
    if "마감" in text:
        return "closed"
    if "예정" in text:
        return "upcoming"
    return "open"


def parse_competitions(html: str) -> list[RawContest]:
    tree = HTMLParser(html)
    items: list[RawContest] = []
    seen: set[str] = set()
    for card in tree.css("div.comp"):
        link = card.css_first('a[href*="/competitions/"]')
        if link is None:
            continue
        href = link.attributes.get("href") or ""
        id_match = re.search(r"/competitions/(?:official/)?(\d+)", href)
        if not id_match:
            continue
        source_id = id_match.group(1)
        if source_id in seen:
            continue
        name = card.css_first("p.name")
        title = name.text(strip=True) if name else ""
        if not title:
            img = card.css_first("img[alt]")
            title = (img.attributes.get("alt") if img else "") or ""
        if not title:
            continue
        keyword = card.css_first("p.keyword, p.info2")
        categories = []
        if keyword:
            categories = [c.strip() for c in keyword.text(strip=True).split("|") if c.strip()]
        dday = card.css_first("div.dday")
        status_text = dday.text(strip=True) if dday else ""
        if "시상식" in title and "경진" not in title:
            continue
        source_url = urljoin(BASE, href)
        is_hackathon = any(k in title.lower() + " ".join(categories).lower() for k in ("해커톤", "hackathon", "데이커"))
        items.append(
            RawContest(
                source_name="dacon",
                source_id=source_id,
                source_url=source_url,
                title=title.strip(),
                organizer="DACON" if not is_hackathon else "DAKER/DACON",
                categories=categories or (["해커톤"] if is_hackathon else ["데이터/AI"]),
                apply_url=source_url,
                status_hint=_status(status_text),
                extra={"kind": "hackathon" if is_hackathon else "datathon"},
            )
        )
        seen.add(source_id)
    return items


class DaconAdapter(SourceAdapter):
    name = "dacon"

    def fetch_list(self) -> list[RawContest]:
        html = fetch(LIST_URL).text
        return parse_competitions(html)
