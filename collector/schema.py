from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ContestType = Literal["hackathon", "contest", "datathon", "idea", "security", "etc"]
ContestStatus = Literal["open", "upcoming", "closed"]
Tab = Literal["all", "new", "closing", "upcoming"]


class RawContest(BaseModel):
    source_name: str
    source_id: str
    source_url: str
    title: str
    organizer: str = ""
    categories: list[str] = Field(default_factory=list)
    eligibility: str = ""
    apply_start: Optional[date] = None
    apply_end: Optional[date] = None
    event_start: Optional[date] = None
    event_end: Optional[date] = None
    apply_url: str = ""
    status_hint: str = ""
    extra: dict = Field(default_factory=dict)


class CanonicalContest(BaseModel):
    canonical_key: str
    title: str
    organizer: str
    contest_type: ContestType = "contest"
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    eligibility: str = ""
    apply_start: Optional[date] = None
    apply_end: Optional[date] = None
    event_start: Optional[date] = None
    event_end: Optional[date] = None
    apply_url: str = ""
    source_url: str
    source_name: str
    sources: list[str] = Field(default_factory=list)
    summary: str = ""
    status: ContestStatus = "open"
    included: bool = True
    confidence: float = 0.5
    needs_review: bool = False
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class ContestOut(BaseModel):
    id: str
    title: str
    organizer: str
    contest_type: ContestType
    tags: list[str]
    eligibility: str
    apply_start: Optional[date] = None
    apply_end: Optional[date] = None
    apply_url: str
    source_url: str
    source_name: str
    sources: list[str]
    summary: str
    status: ContestStatus
    dday: Optional[int] = None
    is_new: bool = False
    first_seen_at: Optional[datetime] = None
    needs_review: bool = False
