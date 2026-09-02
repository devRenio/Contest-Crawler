from __future__ import annotations

import time
from typing import Optional

import httpx

from collector.config import settings

_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    wait = settings.request_delay_sec - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def fetch(
    url: str,
    *,
    method: str = "GET",
    data: Optional[dict] = None,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float = 25.0,
) -> httpx.Response:
    _throttle()
    req_headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }
    if headers:
        req_headers.update(headers)
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=req_headers) as client:
        if json_body is not None:
            response = client.request(method, url, json=json_body)
        else:
            response = client.request(method, url, data=data)
    if response.status_code == 403 or "just a moment" in response.text.lower()[:800]:
        raise RuntimeError(f"blocked or challenged: {url} ({response.status_code})")
    response.raise_for_status()
    return response
