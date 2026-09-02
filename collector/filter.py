from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from typing import Optional

from collector.schema import CanonicalContest, RawContest

# 대상·형식이 동아리 보드와 안 맞으면 AI가 들어가도 버린다.
HARD_EXCLUDE = (
    "독후감",
    "시낭송",
    "문학상",
    "소설",
    "시인",
    "그림 공모",
    "세밀화",
    "풍경화",
    "미술대전",
    "사진공모",
    "웹툰",
    "슬로건",
    "네이밍",
    "표어",
    "명칭 공모",
    "명칭공모",
    "서포터즈",
    "기자단",
    "체험단",
    "봉사",
    "고등학생",
    "초등",
    "중학생",
    "중·고",
    "중고등",
    "어린이",
    "유아",
    "청소년",
    "레시피",
    "요리",
    "책갈피",
    "독서편지",
    "시상식",
    "교육생 모집",
    "양성 과정",
    "아카데미",
    "굿즈",
    "숏폼",
    "광고제",
    "생성아트",
    "ai 아트",
    "ai아트",
    "패키지 디자인",
)

# 창작·홍보물은 경진/해커톤이 아니면 제외.
CONTENT_EXCLUDE = (
    "영상 공모",
    "영상공모",
    "디자인 공모",
    "디자인공모",
    "광고",
    "대본",
    "스토리 공모",
    "콘텐츠 공모",
    "콘텐츠 제작",
)

IT_CATEGORIES = (
    "웹/모바일",
    "게임/소프트웨어",
    "it/sw",
    "알고리즘",
    "데이터/ai",
    "해커톤",
)

WHITESPACE = re.compile(r"\s+")
BRACKETS = re.compile(r"[\(\)\[\]\{\}〈〉《》]")


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", title).lower()
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = BRACKETS.sub(" ", text)
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return WHITESPACE.sub(" ", text).strip()


def canonical_key(title: str, organizer: str, apply_end: Optional[date]) -> str:
    end = apply_end.isoformat() if apply_end else ""
    blob = f"{normalize_title(title)}|{normalize_title(organizer)}|{end}"
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _blob(raw: RawContest) -> str:
    return " ".join(
        [
            raw.title,
            raw.organizer,
            " ".join(raw.categories),
            raw.eligibility,
            raw.status_hint,
        ]
    ).lower()


def _has_it_category(raw: RawContest) -> bool:
    for cat in raw.categories:
        lowered = cat.lower()
        if any(hint in lowered for hint in IT_CATEGORIES):
            return True
    return False


def _is_strong_it(text: str) -> bool:
    if any(
        k in text
        for k in (
            "해커톤",
            "hackathon",
            "프로그래밍",
            "코딩테스트",
            "코딩 테스트",
            "알고리즘",
            "ctf",
            "정보보호",
            "소프트웨어",
            "sw중심",
            "sw 중심",
            "앱 개발",
            "웹 개발",
            "개발 콘테스트",
            "머신러닝",
            "딥러닝",
            "datathon",
        )
    ):
        return True
    if any(k in text for k in ("데이터 분석", "데이터 활용", "공공데이터", "빅데이터", "제조데이터", "빅 데이터")):
        return True
    if ("경진대회" in text or "경진 대회" in text) and any(
        k in text for k in ("ai", "인공지능", "데이터", "소프트웨어", "sw", "보안", "정보보호")
    ):
        return True
    if "챌린지" in text and any(k in text for k in ("ai", "인공지능", "소프트웨어", "sw", "데이터")):
        if not any(k in text for k in ("영상", "숏폼", "광고", "디자인", "아트")):
            return True
    return False


def _is_idea_contest(text: str) -> bool:
    return any(
        k in text
        for k in (
            "아이디어 공모",
            "아이디어공모",
            "아이디어 경진",
            "아이디어경진",
            "아이디어 챌린지",
            "기획 아이디어",
        )
    )


def _is_content_piece(text: str) -> bool:
    if any(pat in text for pat in CONTENT_EXCLUDE):
        return True
    if "영상" in text and "경진" not in text and "해커톤" not in text and "아이디어" not in text:
        return True
    return False


def rule_include(raw: RawContest) -> tuple[bool, float, bool]:
    """Keep IT build contests and university idea contests. Drop 예체능·네이밍·고등·홍보 콘텐츠."""
    text = _blob(raw)
    if any(pat in text for pat in HARD_EXCLUDE):
        return False, 0.92, False
    if _is_content_piece(text) and not any(k in text for k in ("해커톤", "hackathon", "경진대회", "아이디어")):
        return False, 0.88, False
    if raw.source_name == "dacon":
        return True, 0.95, False
    title_text = f"{raw.title} {raw.organizer}".lower()
    if _is_strong_it(title_text):
        return True, 0.86, False
    if _is_idea_contest(title_text):
        return True, 0.8, False
    if _has_it_category(raw) and any(k in text for k in ("ai", "인공지능", "소프트웨어", "데이터", "보안", "개발")):
        return False, 0.4, True
    return False, 0.75, False


def guess_type(raw: RawContest) -> str:
    text = _blob(raw)
    extra = str(raw.extra.get("kind", ""))
    if extra in {"hackathon", "datathon"}:
        return extra
    if any(k in text for k in ("해커톤", "hackathon", "hackathon")):
        return "hackathon"
    if any(k in text for k in ("데이터", "데이콘", "datathon", "알고리즘")):
        return "datathon"
    if any(k in text for k in ("보안", "정보보호", "해킹")):
        return "security"
    if "아이디어" in text:
        return "idea"
    return "contest"


def guess_tags(raw: RawContest) -> list[str]:
    text = _blob(raw)
    tags: list[str] = []
    mapping = {
        "AI": ("ai", "인공지능", "머신러닝", "딥러닝", "llm"),
        "web": ("웹", "web"),
        "app": ("앱", "모바일", "app"),
        "data": ("데이터", "데이터", "정형"),
        "security": ("보안", "정보보호"),
        "UX": ("ux", "ui", "디자인"),
        "startup": ("스타트업", "창업"),
        "hackathon": ("해커톤", "hackathon"),
    }
    for tag, keys in mapping.items():
        if any(k in text for k in keys):
            tags.append(tag)
    return tags


def to_canonical(raw: RawContest, included: bool, confidence: float, needs_review: bool) -> CanonicalContest:
    contest_type = guess_type(raw)
    tags = guess_tags(raw)
    return CanonicalContest(
        canonical_key=canonical_key(raw.title, raw.organizer, raw.apply_end),
        title=raw.title.strip(),
        organizer=raw.organizer.strip(),
        contest_type=contest_type,  # type: ignore[arg-type]
        tags=tags,
        categories=list(raw.categories),
        eligibility=raw.eligibility,
        summary="",
        apply_start=raw.apply_start,
        apply_end=raw.apply_end,
        event_start=raw.event_start,
        event_end=raw.event_end,
        apply_url=raw.apply_url or raw.source_url,
        source_url=raw.source_url,
        source_name=raw.source_name,
        sources=[raw.source_name],
        status=raw.status_hint if raw.status_hint in {"open", "upcoming", "closed"} else "open",
        included=included,
        confidence=confidence,
        needs_review=needs_review,
    )
