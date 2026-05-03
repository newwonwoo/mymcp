"""Prompts 테이블 CRUD."""
from boto3.dynamodb.conditions import Key

from src.config import get_settings
from src.db.client import get_table


class PromptsRepository:
    def __init__(self):
        self.table = get_table(get_settings().prompts_table)

    def get(self, role_name: str, purpose: str, title: str) -> dict | None:
        purpose_title = f"{purpose}#{title}"
        return self.table.get_item(
            Key={"role_name": role_name, "purpose_title": purpose_title}
        ).get("Item")

    def list_by_role_purpose(self, role_name: str, purpose: str) -> list[dict]:
        resp = self.table.query(
            KeyConditionExpression=Key("role_name").eq(role_name)
            & Key("purpose_title").begins_with(f"{purpose}#"),
        )
        return resp.get("Items", [])

    def put(self, prompt: dict) -> None:
        self.table.put_item(Item=prompt)
