from __future__ import annotations

import argparse
import json
import logging

from collector.pipeline import crawl, enrich_existing
from collector.store import init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="국내 대학생 IT 공모전 수집")
    parser.add_argument("--init-db", action="store_true")
    parser.add_argument("--enrich", action="store_true", help="애매한 기존 행만 Gemini로 재분류한다")
    parser.add_argument(
        "--snapshot",
        metavar="PATH",
        help="현재 DB 목록을 동아리 사이트용 JSON으로 저장한다",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.init_db:
        init_db()
        print("db ready")
        return
    if args.enrich:
        result = enrich_existing()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.snapshot:
        from pathlib import Path

        from collector.snapshot import stamp_first_seen, write_snapshot
        from collector.store import ContestRow, SessionLocal, row_to_canonical
        from sqlalchemy import select

        init_db()
        with SessionLocal() as session:
            rows = session.scalars(select(ContestRow).where(ContestRow.included.is_(True))).all()
        items = stamp_first_seen([row_to_canonical(row) for row in rows])
        path = write_snapshot(items, Path(args.snapshot))
        print(json.dumps({"path": str(path), "count": len(items)}, ensure_ascii=False))
        return
    result = crawl()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
