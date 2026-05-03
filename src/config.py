"""환경변수 로드. SAM 템플릿에서 주입한 값들을 한 곳에서 읽는다."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    region: str
    stage: str
    api_key: str
    bedrock_model: str
    roles_table: str
    prompts_table: str
    projects_table: str
    presets_table: str
    sessions_table: str
    mistakes_table: str
    phases_table: str
    failure_stories_table: str
    decisions_table: str


def get_settings() -> Settings:
    stage = os.environ.get("STAGE", "dev")

    def t(env_key: str, default_suffix: str) -> str:
        return os.environ.get(env_key, f"mcp-hub-{default_suffix}-{stage}")

    return Settings(
        region=os.environ.get("AWS_REGION", "ap-northeast-2"),
        stage=stage,
        api_key=os.environ.get("API_KEY", ""),
        bedrock_model=os.environ.get(
            "BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        ),
        roles_table=t("ROLES_TABLE", "roles"),
        prompts_table=t("PROMPTS_TABLE", "prompts"),
        projects_table=t("PROJECTS_TABLE", "projects"),
        presets_table=t("PRESETS_TABLE", "presets"),
        sessions_table=t("SESSIONS_TABLE", "sessions"),
        mistakes_table=t("MISTAKES_TABLE", "mistakes"),
        phases_table=t("PHASES_TABLE", "phases"),
        failure_stories_table=t("FAILURE_STORIES_TABLE", "failure-stories"),
        decisions_table=t("DECISIONS_TABLE", "decisions"),
    )
