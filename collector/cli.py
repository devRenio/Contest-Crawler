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

        from collector.store import list_contests

        init_db()
        path = Path(args.snapshot)
        path.parent.mkdir(parents=True, exist_ok=True)
        items = [item.model_dump(mode="json") for item in list_contests()]
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"path": str(path), "count": len(items)}, ensure_ascii=False))
        return
    result = crawl()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
