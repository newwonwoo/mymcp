"""FailureStories 테이블 CRUD. v2.2."""
from boto3.dynamodb.conditions import Key

from src.config import get_settings
from src.db.client import get_table


class FailureStoriesRepository:
    def __init__(self):
        self.table = get_table(get_settings().failure_stories_table)

    def create(self, story: dict) -> None:
        self.table.put_item(Item=story)

    def get(self, project_id: str, story_id: str) -> dict | None:
        items = self.list_by_project(project_id)
        for it in items:
            if it.get("story_id") == story_id:
                return it
        return None

    def list_by_project(self, project_id: str) -> list[dict]:
        resp = self.table.query(
            KeyConditionExpression=Key("project_id").eq(project_id),
        )
        return resp.get("Items", [])

    def list_by_phase_after(
        self, project_id: str, target_phase: str, after_iso: str
    ) -> list[dict]:
        all_stories = self.list_by_project(project_id)
        return [
            s
            for s in all_stories
            if s.get("target_phase") == target_phase
            and s.get("created_at", "") > after_iso
        ]

    def update_status(
        self,
        project_id: str,
        story_id: str,
        status: str,
        user_decision: str,
        target_items: list[str] | None = None,
    ) -> dict | None:
        story = self.get(project_id, story_id)
        if not story:
            return None
        from datetime import datetime, timezone

        story["status"] = status
        story["user_decision"] = user_decision
        if target_items is not None:
            story["target_items"] = target_items
        story["applied_at"] = datetime.now(timezone.utc).isoformat()
        self.table.put_item(Item=story)
        return story
