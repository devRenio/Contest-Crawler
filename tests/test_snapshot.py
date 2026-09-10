from datetime import date, datetime
import json

from collector.filter import canonical_key, normalize_title
from collector.schema import CanonicalContest
from collector.snapshot import (
    LEGACY_FIRST_SEEN,
    carry_forward,
    dict_to_canonical,
    stamp_first_seen,
    to_snapshot_item,
    write_snapshot,
)


def _item(**kwargs) -> CanonicalContest:
    title = kwargs.get("title", "테스트 공모전")
    apply_end = kwargs.get("apply_end")
    organizer = kwargs.get("organizer", "")
    defaults = dict(
        canonical_key=canonical_key(title, organizer, apply_end),
        title=title,
        organizer=organizer,
        source_url=kwargs.get("source_url", "https://example.com/1"),
        source_name=kwargs.get("source_name", "thinkyou"),
        sources=kwargs.get("sources", [kwargs.get("source_name", "thinkyou")]),
        included=True,
    )
    defaults.update(kwargs)
    return CanonicalContest(**defaults)


def test_carry_forward_keeps_failed_source(tmp_path, monkeypatch):
    previous = [
        _item(title="위비티만 있는 대회", source_name="wevity", sources=["wevity"], apply_end=date(2026, 12, 1)),
        _item(title="씽유 대회", source_name="thinkyou", sources=["thinkyou"], apply_end=date(2026, 12, 1)),
    ]
    current = [
        _item(title="씽유 대회", source_name="thinkyou", sources=["thinkyou"], apply_end=date(2026, 12, 1)),
    ]
    out = carry_forward(
        current,
        failed_sources={"wevity"},
        previous=previous,
        today=date(2026, 9, 10),
    )
    titles = {item.title for item in out}
    assert "위비티만 있는 대회" in titles
    assert "씽유 대회" in titles


def test_carry_forward_drops_expired(tmp_path):
    previous = [
        _item(title="지난 위비티", source_name="wevity", sources=["wevity"], apply_end=date(2026, 9, 1)),
    ]
    out = carry_forward(
        [],
        failed_sources={"wevity"},
        previous=previous,
        today=date(2026, 9, 10),
    )
    assert out == []


def test_stamp_first_seen_reuses_title(tmp_path, monkeypatch):
    import collector.snapshot as snapshot

    monkeypatch.setattr(snapshot, "SEEN_PATH", tmp_path / "first_seen.json")
    monkeypatch.setattr(snapshot, "SNAPSHOT_PATH", tmp_path / "missing.json")
    snapshot.save_first_seen({}, {normalize_title("기존 대회"): "2026-09-03T00:00:00"})
    items = stamp_first_seen(
        [_item(title="기존 대회", apply_end=date(2026, 11, 1))],
        now=datetime(2026, 9, 10, 12, 0, 0),
    )
    assert items[0].first_seen_at == datetime(2026, 9, 3, 0, 0, 0)


def test_snapshot_omits_is_new_and_dday(tmp_path, monkeypatch):
    import collector.snapshot as snapshot

    monkeypatch.setattr(snapshot, "SEEN_PATH", tmp_path / "first_seen.json")
    item = _item(title="새 대회", apply_end=date(2026, 11, 1), first_seen_at=LEGACY_FIRST_SEEN)
    row = to_snapshot_item(item)
    assert "is_new" not in row
    assert "dday" not in row
    assert row["id"] == item.canonical_key
    assert row["first_seen_at"] == "2026-09-03T00:00:00"
    path = write_snapshot([item], tmp_path / "contests.json")
    assert path.exists()


def test_write_snapshot_drops_expired(tmp_path):
    expired = _item(title="지난 대회", apply_end=date(2026, 1, 1), first_seen_at=LEGACY_FIRST_SEEN)
    live = _item(title="진행 대회", apply_end=date(2026, 12, 1), first_seen_at=LEGACY_FIRST_SEEN)
    path = write_snapshot([expired, live], tmp_path / "out.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert [row["title"] for row in rows] == ["진행 대회"]


def test_dict_to_canonical_recomputes_key():
    row = {
        "id": "old-organizer-hash",
        "title": "동일 제목 공모전",
        "organizer": "DACON",
        "contest_type": "datathon",
        "tags": ["AI"],
        "apply_end": "2026-10-01",
        "apply_url": "https://dacon.io/1",
        "source_url": "https://dacon.io/1",
        "source_name": "dacon",
        "sources": ["dacon"],
        "status": "open",
    }
    item = dict_to_canonical(row)
    assert item.canonical_key == canonical_key("동일 제목 공모전", "ignored", date(2026, 10, 1))
