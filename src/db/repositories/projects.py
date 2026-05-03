"""Projects 테이블 CRUD."""
from src.config import get_settings
from src.db.client import get_table


class ProjectsRepository:
    def __init__(self):
        self.table = get_table(get_settings().projects_table)

    def create(self, project: dict) -> None:
        self.table.put_item(Item=project)

    def get(self, project_id: str) -> dict | None:
        return self.table.get_item(Key={"project_id": project_id}).get("Item")

    def update_phase(self, project_id: str, phase_name: str) -> None:
        self.table.update_item(
            Key={"project_id": project_id},
            UpdateExpression="SET current_phase = :p",
            ExpressionAttributeValues={":p": phase_name},
        )
