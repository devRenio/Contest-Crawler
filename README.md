# Contest Crawler

국내 대학생이 참여할 수 있는 **IT + 인접** 공모전·해커톤·경진대회를 모읍니다. 위비티, 씽유, 링커리어, 데이콘, 캠퍼스픽(에브리커리어) 공개 목록만 읽고, Gemini로 분야만 분류합니다.

## 구성

- `collector/` 소스 어댑터와 파이프라인
- `api/` FastAPI (`GET /v1/contests`, `POST /v1/submissions`)
- `web/` Next.js 보드 (`/`, `/contests`, `/submit`)

탭: **전체 / 새로 올라온(7일) / 마감임박(14일)**

## 로컬 실행

Python 3.10+, Node 22.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env`에 [Google AI Studio](https://aistudio.google.com/apikey) 키를 넣습니다. 키가 없으면 규칙 필터만 동작합니다.

```bash
python -m collector.cli
uvicorn api.main:app --reload --port 8000
```

다른 터미널:

```bash
cd web
npm install
npx next dev
```

http://localhost:3000 에서 보드를 엽니다.

## 동아리 Next.js에 붙이기

동아리 사이트는 [goorm](https://goorm.net) (`C:\GitHub\goorm`)입니다. 공모전 보드는 `/contests`입니다.

1. 목록 스냅샷을 동아리 레포에 넣습니다.

```bash
python -m collector.cli --snapshot C:\GitHub\goorm\lib\data\contests.json
```

2. 동아리 사이트를 배포하면 `https://goorm.net/contests`에서 보입니다.
3. 나중에 API를 따로 올리면 `NEXT_PUBLIC_API_URL`과 `CORS_ORIGINS=https://goorm.net`을 맞춥니다.

## GitHub Actions

매일 06:00 KST(`cron: 0 21 * * *`)에 수집합니다. 저장소 Secrets:

- `GEMINI_API_KEY` (선택, 있으면 분류·요약)
- `DATABASE_URL` (선택, Neon 등 Postgres. 없으면 워크플로 안의 SQLite는 휘발)

## 수집 원칙

공개 메타데이터와 공식 URL만 저장합니다. 원문 본문은 재게시하지 않습니다. 소스 하나가 막혀도 나머지는 저장됩니다.
