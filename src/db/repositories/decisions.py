"""Decisions 테이블 CRUD. v2.3."""
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr, Key

from src.config import get_settings
from src.db.client import get_table


class DecisionsRepository:
    def __init__(self):
        self.table = get_table(get_settings().decisions_table)

    def create(self, decision: dict) -> None:
        self.table.put_item(Item=decision)

    def list_active_for_project(self, project_id: str | None) -> list[dict]:
        """전역(scope=global, active="true") + 해당 프로젝트(scope=project) 중 active 결정.

        active 컬럼은 GSI 키로 쓰이기 때문에 문자열 "true"/"false"로 저장한다.
        """
        global_resp = self.table.query(
            IndexName="scope-active-index",
            KeyConditionExpression=Key("scope").eq("global") & Key("active").eq("true"),
        )
        items = list(global_resp.get("Items", []))

        if project_id:
            project_resp = self.table.query(
                IndexName="scope-active-index",
                KeyConditionExpression=Key("scope").eq("project")
                & Key("active").eq("true"),
                FilterExpression=Attr("project_id").eq(project_id),
            )
            items.extend(project_resp.get("Items", []))

        return sorted(items, key=lambda d: d.get("created_at", ""))

    def revoke(self, decision_id: str) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        resp = self.table.update_item(
            Key={"decision_id": decision_id},
            UpdateExpression="SET active = :a, revoked_at = :r",
            ConditionExpression=Attr("decision_id").exists(),
            ExpressionAttributeValues={":a": "false", ":r": now},
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")

    def get(self, decision_id: str) -> dict | None:
        return self.table.get_item(Key={"decision_id": decision_id}).get("Item")
