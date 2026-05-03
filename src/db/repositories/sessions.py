"""Sessions + Handoffs 테이블 CRUD.

핸드오프는 Session 항목에 부속 attribute로 저장한다 (별도 테이블 없음).
get_handoff은 session_id로 세션을 찾아 handoff_note 필드를 반환.
"""
from boto3.dynamodb.conditions import Key

from src.config import get_settings
from src.db.client import get_table


class SessionsRepository:
    def __init__(self):
        self.table = get_table(get_settings().sessions_table)

    def create(self, session: dict) -> None:
        self.table.put_item(Item=session)

    def get(self, session_id: str) -> dict | None:
        return self.table.get_item(Key={"session_id": session_id}).get("Item")

    def update_context(self, session_id: str, percent: int) -> dict | None:
        self.table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET context_percent = :p",
            ExpressionAttributeValues={":p": percent},
        )
        return self.get(session_id)

    def attach_handoff(self, session_id: str, handoff: dict) -> dict | None:
        self.table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET handoff_note = :h",
            ExpressionAttributeValues={":h": handoff},
        )
        return self.get(session_id)

    def get_latest(self, project_id: str) -> dict | None:
        resp = self.table.query(
            IndexName="project-time-index",
            KeyConditionExpression=Key("project_id").eq(project_id),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None
