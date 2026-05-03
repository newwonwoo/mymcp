"""Presets 테이블 CRUD. created_status=`<iso>#<status>` 합성키."""
from boto3.dynamodb.conditions import Key

from src.config import get_settings
from src.db.client import get_table


class PresetsRepository:
    def __init__(self):
        self.table = get_table(get_settings().presets_table)

    def create(self, preset: dict) -> str:
        self.table.put_item(Item=preset)
        return preset.get("preset_id") or preset["created_status"]

    def list_by_status(self, project_id: str, status: str) -> list[dict]:
        resp = self.table.query(
            KeyConditionExpression=Key("project_id").eq(project_id),
        )
        items = resp.get("Items", [])
        return [
            i
            for i in items
            if i.get("status") == status or i["created_status"].endswith(f"#{status}")
        ]

    def get_active(self, project_id: str) -> dict | None:
        actives = self.list_by_status(project_id, "active")
        if not actives:
            return None
        return sorted(actives, key=lambda p: p["created_status"])[-1]

    def update_status(
        self,
        project_id: str,
        old_key: str,
        new_status: str,
        activated_at: str | None = None,
    ) -> dict:
        old_item = self.table.get_item(
            Key={"project_id": project_id, "created_status": old_key}
        ).get("Item")
        if not old_item:
            raise KeyError(f"preset not found: {project_id} / {old_key}")
        self.table.delete_item(
            Key={"project_id": project_id, "created_status": old_key}
        )
        # 새 SK 생성: created_at 부분은 유지, status 부분만 교체
        created_at = old_key.rsplit("#", 1)[0]
        new_key = f"{created_at}#{new_status}"
        new_item = {**old_item, "created_status": new_key, "status": new_status}
        if activated_at:
            new_item["activated_at"] = activated_at
        self.table.put_item(Item=new_item)
        return new_item

    def add_unlocked_role(self, project_id: str, role: str, reason: str) -> dict:
        active = self.get_active(project_id)
        if not active:
            raise KeyError(f"no active preset for {project_id}")
        existing = {r["role"] for r in active.get("role_assignments", [])}
        if role in existing:
            return active
        next_priority = max(
            (r["priority"] for r in active["role_assignments"]), default=0
        ) + 1
        active["role_assignments"].append(
            {"role": role, "priority": next_priority, "reason": f"[unlocked] {reason}"}
        )
        self.table.put_item(Item=active)
        return active

    def list_active(self) -> list[dict]:
        resp = self.table.scan()
        return [i for i in resp.get("Items", []) if i.get("status") == "active"]
