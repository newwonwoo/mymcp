"""Mistakes 테이블 CRUD."""
from boto3.dynamodb.conditions import Attr, Key

from src.config import get_settings
from src.db.client import get_table


class MistakesRepository:
    def __init__(self):
        self.table = get_table(get_settings().mistakes_table)

    def put(self, mistake: dict) -> None:
        self.table.put_item(Item=mistake)

    def query(
        self,
        role: str | None = None,
        category: str | None = None,
        keyword: str | None = None,
    ) -> list[dict]:
        if role and category:
            resp = self.table.query(
                IndexName="role-category-index",
                KeyConditionExpression=Key("role_name").eq(role)
                & Key("category").eq(category),
            )
            items = resp.get("Items", [])
        elif role:
            resp = self.table.query(
                IndexName="role-category-index",
                KeyConditionExpression=Key("role_name").eq(role),
            )
            items = resp.get("Items", [])
        else:
            scan_kwargs: dict = {}
            if category:
                scan_kwargs["FilterExpression"] = Attr("category").eq(category)
            resp = self.table.scan(**scan_kwargs)
            items = resp.get("Items", [])

        if keyword:
            kw = keyword.lower()
            items = [
                i
                for i in items
                if kw in (i.get("description") or "").lower()
                or kw in (i.get("root_cause") or "").lower()
            ]
        return items

    def list_unresolved(self, limit: int = 5) -> list[dict]:
        resp = self.table.scan(FilterExpression=Attr("resolution").not_exists() | Attr("resolution").eq(None))
        items = resp.get("Items", [])
        return items[:limit]
