from datetime import date

from collector.dedup import merge_duplicates
from collector.filter import canonical_key
from collector.schema import CanonicalContest


def test_merge_same_key():
    key = "abc"
    a = CanonicalContest(
        canonical_key=key,
        title="AI 해커톤",
        organizer="과기부",
        source_url="https://a.example/1",
        source_name="wevity",
        sources=["wevity"],
        apply_end=date(2026, 9, 30),
    )
    b = CanonicalContest(
        canonical_key=key,
        title="AI 해커톤",
        organizer="과기부",
        source_url="https://b.example/1",
        source_name="linkareer",
        sources=["linkareer"],
        tags=["AI"],
    )
    merged = merge_duplicates([a, b])
    assert len(merged) == 1
    assert set(merged[0].sources) == {"wevity", "linkareer"}
    assert "AI" in merged[0].tags


def test_merge_same_title_generic_organizer():
    title = "딥보이스 범죄 대응을 위한 AI 탐지 모델 경진대회"
    end = date(2026, 10, 1)
    thinkyou = CanonicalContest(
        canonical_key=canonical_key(title, "한국데이터산업진흥원", end),
        title=title,
        organizer="한국데이터산업진흥원, 한국데이터산업진흥원협회",
        source_url="https://thinkyou.co.kr/contest/65988/",
        source_name="thinkyou",
        sources=["thinkyou"],
        apply_end=end,
    )
    dacon = CanonicalContest(
        canonical_key=canonical_key(title, "DACON", end),
        title=title,
        organizer="DACON",
        source_url="https://dacon.io/competitions/official/236754/overview/",
        source_name="dacon",
        sources=["dacon"],
        apply_end=end,
    )
    merged = merge_duplicates([thinkyou, dacon])
    assert len(merged) == 1
    assert set(merged[0].sources) == {"thinkyou", "dacon"}
    assert merged[0].organizer != "DACON"


def test_merge_same_title_missing_end():
    title = "2026 과학기술 정책 아이디어 공모전"
    dated = CanonicalContest(
        canonical_key=canonical_key(title, "과학기술부", date(2026, 10, 20)),
        title=title,
        organizer="과학기술부",
        source_url="https://thinkyou.example/1",
        source_name="thinkyou",
        sources=["thinkyou"],
        apply_end=date(2026, 10, 20),
    )
    undated = CanonicalContest(
        canonical_key=canonical_key(title, "", None),
        title=title,
        organizer="",
        source_url="https://linkareer.com/activity/1",
        source_name="linkareer",
        sources=["linkareer"],
    )
    merged = merge_duplicates([dated, undated])
    assert len(merged) == 1
    assert merged[0].apply_end == date(2026, 10, 20)
    assert set(merged[0].sources) == {"thinkyou", "linkareer"}
