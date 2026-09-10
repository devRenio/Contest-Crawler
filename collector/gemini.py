from __future__ import annotations

import json
import logging
from typing import Any

from collector.config import settings
from collector.schema import CanonicalContest

log = logging.getLogger(__name__)

REVIEW_FALLBACKS = ("gemini-2.5-flash", "gemini-2.0-flash")


def _client():
    if not settings.gemini_api_key:
        return None
    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


def _generate(client: Any, model: str, prompt: str) -> str:
    config: dict[str, Any] = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }
    try:
        config["thinking_config"] = {"thinking_level": "minimal"}
        response = client.models.generate_content(model=model, contents=prompt, config=config)
    except TypeError:
        config.pop("thinking_config", None)
        response = client.models.generate_content(model=model, contents=prompt, config=config)
    except Exception as exc:
        if "thinking" in str(exc).lower() or "MINIMAL" in str(exc):
            config.pop("thinking_config", None)
            response = client.models.generate_content(model=model, contents=prompt, config=config)
        else:
            raise
    return getattr(response, "text", "") or ""


def _chunks(items: list[CanonicalContest], size: int = 8) -> list[list[CanonicalContest]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def enrich(items: list[CanonicalContest], review: bool = False) -> tuple[list[CanonicalContest], int]:
    """Classify/summarize. Returns items and number of API calls used."""
    client = _client()
    if client is None or not items:
        return items, 0

    model = settings.gemini_model_review if review else settings.gemini_model
    calls = 0
    cap = settings.review_daily_cap if review else settings.lite_daily_cap

    for group in _chunks(items):
        if calls >= cap:
            for item in group:
                item.needs_review = True
            continue
        payload = [
            {
                "id": item.canonical_key,
                "title": item.title,
                "organizer": item.organizer,
                "categories": item.categories,
                "type": item.contest_type,
            }
            for item in group
        ]
        prompt = (
            "너는 대학생 IT 동아리 큐레이터다. 코드·모델·앱/웹·데이터 분석·보안 과제 "
            "또는 대학생 아이디어 공모전이면 include=true.\n"
            "영상·숏폼·광고·네이밍·교육과정·고등/청소년은 false.\n"
            "애매하면 false. 요약 문장은 쓰지 마라.\n"
            "JSON 배열만. 각 원소: "
            '{"id":"...","include":true,"type":"hackathon|contest|datathon|idea|security|etc",'
            '"tags":["AI"],"confidence":0.0}\n'
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            text = _generate(client, model, prompt)
            calls += 1
        except Exception as exc:
            log.warning("gemini %s failed: %s", model, exc)
            if review and model == settings.gemini_model_review:
                for fallback in REVIEW_FALLBACKS[1:]:
                    try:
                        text = _generate(client, fallback, prompt)
                        calls += 1
                        break
                    except Exception:
                        text = ""
                else:
                    continue
            elif "404" in str(exc) or "not found" in str(exc).lower():
                try:
                    text = _generate(client, "gemini-2.0-flash", prompt)
                    calls += 1
                except Exception:
                    continue
            else:
                continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "items" in parsed:
                parsed = parsed["items"]
            if not isinstance(parsed, list):
                continue
        except json.JSONDecodeError:
            continue
        by_id = {item.canonical_key: item for item in group}
        for row in parsed:
            item = by_id.get(str(row.get("id", "")))
            if item is None:
                continue
            item.included = bool(row.get("include", False))
            if row.get("type") in {"hackathon", "contest", "datathon", "idea", "security", "etc"}:
                item.contest_type = row["type"]
            if isinstance(row.get("tags"), list):
                item.tags = list(dict.fromkeys([str(t) for t in row["tags"] if t] + item.tags))
            if "confidence" in row:
                try:
                    item.confidence = float(row["confidence"])
                except (TypeError, ValueError):
                    pass
            item.needs_review = bool(row.get("needs_review", False)) or item.confidence < 0.45
    return items, calls
