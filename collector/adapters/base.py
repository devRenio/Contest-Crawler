from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from collector.schema import RawContest


def status_from_dates(
    apply_start: Optional[date],
    apply_end: Optional[date],
    hint: str = "open",
) -> str:
    today = date.today()
    if apply_end is not None and apply_end < today:
        return "closed"
    if hint == "upcoming" or (apply_start is not None and apply_start > today):
        return "upcoming"
    if hint == "closed":
        return "closed"
    return "open"


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch_list(self) -> list[RawContest]:
        """Return public list metadata. Must not follow login or payment flows."""

    def safe_fetch(self) -> tuple[list[RawContest], Optional[str]]:
        try:
            return self.fetch_list(), None
        except Exception as exc:  # noqa: BLE001 - isolate adapter failures
            return [], f"{self.name}: {exc}"
