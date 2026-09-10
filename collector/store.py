from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    String,
    Text,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from collector.config import ROOT, settings
from collector.schema import CanonicalContest, ContestOut

GENERIC_SUMMARY = "상세는 출처 페이지에서 확인하세요."


class Base(DeclarativeBase):
    pass


class ContestRow(Base):
    __tablename__ = "contests"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    organizer: Mapped[str] = mapped_column(String(300), default="")
    contest_type: Mapped[str] = mapped_column(String(32), default="contest")
    tags: Mapped[str] = mapped_column(Text, default="")
    categories: Mapped[str] = mapped_column(Text, default="")
    eligibility: Mapped[str] = mapped_column(String(300), default="")
    apply_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    apply_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    event_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    event_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    apply_url: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(64))
    sources: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)


class SubmissionRow(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    organizer: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CrawlRunRow(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched: Mapped[int] = mapped_column(default=0)
    stored: Mapped[int] = mapped_column(default=0)
    errors: Mapped[str] = mapped_column(Text, default="")


def _engine():
    url = settings.database_url
    if url.startswith("sqlite:///./"):
        (ROOT / "data").mkdir(exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


engine = _engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    (ROOT / "data").mkdir(exist_ok=True)
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    if "contests" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("contests")}
        if "categories" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE contests ADD COLUMN categories TEXT DEFAULT ''"))


def _join(values: list[str]) -> str:
    return ",".join(dict.fromkeys(values))


def upsert_contests(items: list[CanonicalContest]) -> int:
    now = datetime.utcnow()
    stored = 0
    with SessionLocal() as session:
        for item in items:
            if not item.included:
                continue
            row = session.get(ContestRow, item.canonical_key)
            if row is None:
                session.add(
                    ContestRow(
                        id=item.canonical_key,
                        canonical_key=item.canonical_key,
                        title=item.title,
                        organizer=item.organizer,
                        contest_type=item.contest_type,
                        tags=_join(item.tags),
                        categories=_join(item.categories),
                        eligibility=item.eligibility,
                        apply_start=item.apply_start,
                        apply_end=item.apply_end,
                        event_start=item.event_start,
                        event_end=item.event_end,
                        apply_url=item.apply_url,
                        source_url=item.source_url,
                        source_name=item.source_name,
                        sources=_join(item.sources),
                        summary=item.summary,
                        status=item.status,
                        included=item.included,
                        confidence=item.confidence,
                        needs_review=item.needs_review,
                        first_seen_at=item.first_seen_at or now,
                        last_seen_at=now,
                    )
                )
                stored += 1
            else:
                row.title = item.title
                row.organizer = item.organizer or row.organizer
                row.contest_type = item.contest_type
                row.tags = _join((row.tags.split(",") if row.tags else []) + item.tags)
                row.categories = _join((row.categories.split(",") if row.categories else []) + item.categories)
                row.eligibility = item.eligibility or row.eligibility
                row.apply_start = item.apply_start or row.apply_start
                row.apply_end = item.apply_end or row.apply_end
                row.apply_url = item.apply_url or row.apply_url
                row.source_url = item.source_url
                row.source_name = item.source_name
                row.sources = _join((row.sources.split(",") if row.sources else []) + item.sources)
                if is_llm_summary(item.summary):
                    row.summary = item.summary
                elif row.summary.strip() == GENERIC_SUMMARY:
                    row.summary = ""
                row.status = item.status
                row.included = item.included
                row.confidence = item.confidence
                row.needs_review = item.needs_review
                row.last_seen_at = now
                stored += 1
        session.commit()
    return stored


def exclude_contests(keys: list[str]) -> int:
    if not keys:
        return 0
    dropped = 0
    with SessionLocal() as session:
        for key in keys:
            row = session.get(ContestRow, key)
            if row is None or not row.included:
                continue
            row.included = False
            dropped += 1
        session.commit()
    return dropped


def sync_included(keep_keys: set[str], sources: set[str]) -> int:
    """Show only this crawl's kept rows for sources that succeeded."""
    if not sources:
        return 0
    changed = 0
    with SessionLocal() as session:
        rows = session.scalars(select(ContestRow)).all()
        for row in rows:
            row_sources = {s for s in (row.sources or "").split(",") if s} or {row.source_name}
            if not (row_sources & sources):
                continue
            should_show = row.canonical_key in keep_keys
            if row.included != should_show:
                row.included = should_show
                changed += 1
        session.commit()
    return changed


def is_llm_summary(text: str) -> bool:
    value = (text or "").strip()
    return bool(value) and value != GENERIC_SUMMARY


def row_to_canonical(row: ContestRow) -> CanonicalContest:
    tags = [t for t in row.tags.split(",") if t]
    categories = [c for c in (row.categories or "").split(",") if c]
    return CanonicalContest(
        canonical_key=row.canonical_key,
        title=row.title,
        organizer=row.organizer,
        contest_type=row.contest_type,  # type: ignore[arg-type]
        tags=tags,
        categories=categories,
        eligibility=row.eligibility,
        apply_start=row.apply_start,
        apply_end=row.apply_end,
        event_start=row.event_start,
        event_end=row.event_end,
        apply_url=row.apply_url,
        source_url=row.source_url,
        source_name=row.source_name,
        sources=[s for s in row.sources.split(",") if s],
        summary=row.summary if is_llm_summary(row.summary) else "",
        status=row.status,  # type: ignore[arg-type]
        included=row.included,
        confidence=row.confidence,
        needs_review=row.needs_review,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
    )


def record_run(started: datetime, fetched: int, stored: int, errors: list[str]) -> None:
    with SessionLocal() as session:
        session.add(
            CrawlRunRow(
                started_at=started,
                finished_at=datetime.utcnow(),
                fetched=fetched,
                stored=stored,
                errors="\n".join(errors),
            )
        )
        session.commit()


def add_submission(title: str, organizer: str, url: str, note: str) -> None:
    with SessionLocal() as session:
        session.add(SubmissionRow(title=title, organizer=organizer, url=url, note=note))
        session.commit()


def _dday(end: Optional[date]) -> Optional[int]:
    if end is None:
        return None
    return (end - date.today()).days


def to_out(row: ContestRow) -> ContestOut:
    now = datetime.utcnow()
    dday = _dday(row.apply_end)
    tags = [t for t in row.tags.split(",") if t]
    return ContestOut(
        id=row.id,
        title=row.title,
        organizer=row.organizer,
        contest_type=row.contest_type,  # type: ignore[arg-type]
        tags=tags,
        eligibility=row.eligibility,
        apply_start=row.apply_start,
        apply_end=row.apply_end,
        apply_url=row.apply_url,
        source_url=row.source_url,
        source_name=row.source_name,
        sources=[s for s in row.sources.split(",") if s],
        summary="",
        status=row.status,  # type: ignore[arg-type]
        dday=dday,
        is_new=(now - row.first_seen_at).days <= settings.new_days,
        first_seen_at=row.first_seen_at,
        needs_review=row.needs_review,
    )


def list_contests(tab: str = "all", tag: str = "", q: str = "") -> list[ContestOut]:
    with SessionLocal() as session:
        rows = session.scalars(select(ContestRow).where(ContestRow.included.is_(True))).all()
    items = [to_out(row) for row in rows]
    if tab == "new":
        items = [i for i in items if i.is_new and i.status == "open"]
    elif tab == "closing":
        items = [
            i
            for i in items
            if i.status == "open" and i.dday is not None and 0 <= i.dday <= settings.closing_days
        ]
    else:
        items = [i for i in items if i.status != "closed" or (i.dday is not None and i.dday >= 0)]
    if tag:
        needle = tag.lower()
        items = [i for i in items if needle in {t.lower() for t in i.tags} or needle in i.contest_type]
    if q:
        needle = q.lower()
        items = [
            i
            for i in items
            if needle in i.title.lower() or needle in i.organizer.lower()
        ]

    def sort_key(item: ContestOut):
        if tab == "new":
            return (0 if item.is_new else 1, item.dday if item.dday is not None else 9999)
        if item.dday is None:
            return (1, 9999, item.title)
        return (0 if item.dday >= 0 else 2, item.dday, item.title)

    items.sort(key=sort_key)
    return items
