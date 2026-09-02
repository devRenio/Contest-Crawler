from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from collector.schema import RawContest


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
