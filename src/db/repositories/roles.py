"""Roles 테이블 CRUD."""
from src.config import get_settings
from src.db.client import get_table


class RolesRepository:
    def __init__(self):
        self.table = get_table(get_settings().roles_table)

    def list_all(self) -> list[dict]:
        return self.table.scan().get("Items", [])

    def get(self, role_name: str) -> dict | None:
        return self.table.get_item(Key={"role_name": role_name}).get("Item")

    def put(self, role: dict) -> None:
        self.table.put_item(Item=role)
