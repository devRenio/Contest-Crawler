from collector.filter import canonical_key, rule_include
from collector.schema import RawContest


def test_exclude_literature():
    raw = RawContest(
        source_name="wevity",
        source_id="1",
        source_url="https://example.com/1",
        title="제26회 가람이병기청년시 문학상 공모",
        categories=["문학/글"],
    )
    included, _, _ = rule_include(raw)
    assert included is False


def test_include_hackathon():
    raw = RawContest(
        source_name="thinkyou",
        source_id="2",
        source_url="https://example.com/2",
        title="2026 뉴스빅데이터 해커톤",
        organizer="한국언론진흥재단",
        categories=["IT/SW"],
    )
    included, confidence, _ = rule_include(raw)
    assert included is True
    assert confidence >= 0.7


def test_canonical_key_stable():
    from datetime import date

    a = canonical_key("2026 AI 해커톤", "과학기술정보통신부", date(2026, 9, 30))
    b = canonical_key("2026  AI  해커톤", "과학기술정보통신부", date(2026, 9, 30))
    assert a == b


def test_exclude_highschool_even_with_ai():
    raw = RawContest(
        source_name="wevity",
        source_id="3",
        source_url="https://example.com/3",
        title="제5회 2026 대한민국 고등학생 AI·SW 개발 공모전",
        categories=["IT/SW"],
    )
    included, _, review = rule_include(raw)
    assert included is False
    assert review is False


def test_exclude_naming_and_shortform():
    naming = RawContest(
        source_name="wevity",
        source_id="4",
        source_url="https://example.com/4",
        title="제주 디지털 통합 신원인증 앱 명칭 공모",
        categories=["IT/SW"],
    )
    shortform = RawContest(
        source_name="wevity",
        source_id="5",
        source_url="https://example.com/5",
        title="2026 춘천 반려동물 AI 숏폼 공모전",
        categories=["영상"],
    )
    idea = RawContest(
        source_name="thinkyou",
        source_id="6",
        source_url="https://example.com/6",
        title="2026 인천관광 혁신아이디어 공모전",
        categories=["기획/아이디어"],
    )
    assert rule_include(naming)[0] is False
    assert rule_include(shortform)[0] is False
    assert rule_include(idea)[0] is True


def test_include_idea_contest():
    raw = RawContest(
        source_name="wevity",
        source_id="9",
        source_url="https://example.com/9",
        title="AI기반 지속 가능한 통일 아이디어 공모전",
        categories=["기획/아이디어"],
    )
    included, confidence, _ = rule_include(raw)
    assert included is True
    assert confidence >= 0.8


def test_category_it_sw_does_not_save_startup_contest():
    raw = RawContest(
        source_name="thinkyou",
        source_id="8",
        source_url="https://example.com/8",
        title="2026년 GovTech 창업경진대회",
        categories=["IT/SW"],
    )
    included, _, review = rule_include(raw)
    assert included is False
    assert review is False
    raw = RawContest(
        source_name="dacon",
        source_id="7",
        source_url="https://example.com/7",
        title="딥보이스 범죄 대응을 위한 AI 탐지 모델 경진대회",
        categories=["데이터/AI"],
    )
    included, confidence, _ = rule_include(raw)
    assert included is True
    assert confidence >= 0.85
