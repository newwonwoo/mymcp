"""DynamoDB에 시드 데이터 4종 입력.

전제: SAM deploy 후 9개 테이블이 생성되어 있어야 함.
환경변수: AWS_REGION, STAGE, *_TABLE 들 (template.yaml 기준).

실행:
    python scripts/seed_db.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.db.client import get_table  # noqa: E402
from src.config import get_settings  # noqa: E402


SEEDS_DIR = REPO_ROOT / "seeds"


def seed_table(table_name: str, items_file: Path) -> int:
    table = get_table(table_name)
    items = json.loads(items_file.read_text(encoding="utf-8"))
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    return len(items)


def main() -> int:
    s = get_settings()
    plan = [
        (s.roles_table, SEEDS_DIR / "roles.json"),
        (s.mistakes_table, SEEDS_DIR / "mistakes.json"),
        (s.prompts_table, SEEDS_DIR / "prompts.json"),
        (s.decisions_table, SEEDS_DIR / "decisions.json"),
    ]
    total = 0
    for table_name, file_path in plan:
        count = seed_table(table_name, file_path)
        print(f"  {table_name}: {count} items")
        total += count
    print(f"\nseeded {total} items across {len(plan)} tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
