from __future__ import annotations

import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from collector.adapters.base import SourceAdapter, status_from_dates
from collector.config import settings
from collector.http import fetch
from collector.schema import RawContest

AJAX_URL = "https://thinkyou.co.kr/contest/ajax_contestList.asp"
BASE = "https://thinkyou.co.kr"


def _parse_yy_date(text: str) -> Optional[date]:
    match = re.search(r"(\d{2})-(\d{2})-(\d{2})", text)
    if not match:
        return None
    year = 2000 + int(match.group(1))
    return date(year, int(match.group(2)), int(match.group(3)))


def _status(text: str) -> str:
    if "예정" in text:
        return "upcoming"
    if "마감" in text and "임박" not in text:
        return "closed"
    return "open"


def parse_ajax(html: str, field_label: str) -> list[RawContest]:
    tree = HTMLParser(html)
    items: list[RawContest] = []
    for row in tree.css("div.board_list .tr"):
        if "thead" in (row.attributes.get("class") or ""):
            continue
        link = row.css_first("div.title a[href]")
        if link is None:
            continue
        href = link.attributes.get("href") or ""
        title_el = row.css_first("h3")
        title = title_el.text(strip=True) if title_el else link.text(strip=True)
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue
        organizer = ""
        dd = row.css_first("dd")
        if dd:
            organizer = re.sub(r"^주최\s*:\s*", "", dd.text(strip=True)).strip()
        period = ""
        for etc in row.css("div.etc"):
            if "~" in etc.text():
                period = etc.text(strip=True)
                break
        dates = re.findall(r"\d{2}-\d{2}-\d{2}", period)
        apply_start = _parse_yy_date(dates[0]) if dates else None
        apply_end = _parse_yy_date(dates[1]) if len(dates) > 1 else None
        stat = row.css_first("div.statNew")
        status = status_from_dates(apply_start, apply_end, _status(stat.text() if stat else ""))
        contest_id = ""
        id_match = re.search(r"/contest/(\d+)", href)
        if id_match:
            contest_id = id_match.group(1)
        source_url = urljoin(BASE, href.split("?")[0])
        items.append(
            RawContest(
                source_name="thinkyou",
                source_id=contest_id or source_url,
                source_url=source_url,
                title=title,
                organizer=organizer,
                categories=[field_label],
                apply_start=apply_start,
                apply_end=apply_end,
                apply_url=source_url,
                status_hint=status,
            )
        )
    return items


class ThinkyouAdapter(SourceAdapter):
    name = "thinkyou"

    def fetch_list(self) -> list[RawContest]:
        collected: list[RawContest] = []
        seen: set[str] = set()
        # 5 = IT/SW, 0 = 아이디어/마케팅 (제목 규칙으로 마케팅·서포터즈는 걸러진다)
        # 1 = 접수중, 3 = 접수예정
        for field, label in (("5", "IT/SW"), ("0", "기획/아이디어")):
            for serstatus in ("1", "3"):
                for page in range(1, settings.max_pages + 1):
                    html = fetch(
                        AJAX_URL,
                        method="POST",
                        data={
                            "pageSize": "45",
                            "page": str(page),
                            "serstatus": serstatus,
                            "serfield": field,
                            "sertarget": "",
                            "serprizeMoney": "",
                            "serdivision": "",
                            "seritem": "0",
                            "searchstr": "",
                        },
                        headers={"Referer": "https://thinkyou.co.kr/contest/"},
                    ).text
                    if "Object moved" in html or "board_list" not in html:
                        break
                    batch = parse_ajax(html, label)
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
                    if 'class="btn next"' in html and "다음" in html and f">{page + 1}<" not in html:
                        if "<strong>1</strong>" in html and f">{page + 1}<" not in html:
                            break
        return collected
