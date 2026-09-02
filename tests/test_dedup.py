from datetime import date

from collector.dedup import merge_duplicates
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
