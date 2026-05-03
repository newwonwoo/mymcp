"""Phases 테이블 CRUD. (project_id, phase_name) 합성키."""
from boto3.dynamodb.conditions import Key

from src.config import get_settings
from src.db.client import get_table


class PhasesRepository:
    def __init__(self):
        self.table = get_table(get_settings().phases_table)

    def put(self, phase: dict) -> None:
        self.table.put_item(Item=phase)

    def get_current(self, project_id: str) -> dict | None:
        """status='active' 인 phase 반환. 없으면 가장 최근."""
        resp = self.table.query(KeyConditionExpression=Key("project_id").eq(project_id))
        items = resp.get("Items", [])
        active = [i for i in items if i.get("status") == "active"]
        if active:
            return sorted(active, key=lambda p: p.get("started_at", ""))[-1]
        if not items:
            return None
        return sorted(items, key=lambda p: p.get("started_at", ""))[-1]

    def get_entry_time(self, project_id: str, phase_name: str) -> str | None:
        item = self.table.get_item(
            Key={"project_id": project_id, "phase_name": phase_name}
        ).get("Item")
        return item.get("started_at") if item else None

    def transition(self, project_id: str, new_phase: str, reason: str) -> dict:
        """현재 active phase를 completed로, 새 phase를 active로."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        current = self.get_current(project_id)
        if current and current["phase_name"] != new_phase:
            current["status"] = "completed"
            current["ended_at"] = now
            self.table.put_item(Item=current)

        new_item = {
            "project_id": project_id,
            "phase_name": new_phase,
            "started_at": now,
            "status": "active",
            "reason": reason,
        }
        self.table.put_item(Item=new_item)
        return new_item
