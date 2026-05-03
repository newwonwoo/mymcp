"""pytest fixtures.

moto 5.x로 DynamoDB 9테이블을 메모리에 띄우고, 시드 데이터를 입력한다.
Bedrock 호출은 monkeypatch로 차단 — 각 테스트가 응답 모양을 직접 결정.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# 환경변수는 import 시점에 잡혀야 한다 (config.get_settings 캐시 X 구조라 OK).
os.environ.setdefault("AWS_REGION", "us-east-1")  # moto 호환 기본
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("STAGE", "test")
os.environ.setdefault("API_KEY", "test-api-key-32-characters-min-aaaa")

SEEDS = REPO_ROOT / "seeds"


# ─────────────────────────── DynamoDB 9 tables ───────────────────────────
@pytest.fixture
def aws_mock():
    """moto 컨텍스트 — 모든 boto3 호출이 메모리 가짜 AWS로 라우팅."""
    from moto import mock_aws

    with mock_aws():
        yield


@pytest.fixture
def dynamodb_tables(aws_mock):
    """9개 DynamoDB 테이블을 생성. SAM template과 동일한 스키마."""
    import boto3

    from src.config import get_settings
    from src.db import client as db_client

    db_client.reset_for_tests()
    s = get_settings()
    ddb = boto3.client("dynamodb", region_name=s.region)

    def create(name, keys, attrs, gsi=None):
        kwargs = dict(
            TableName=name,
            KeySchema=keys,
            AttributeDefinitions=attrs,
            BillingMode="PAY_PER_REQUEST",
        )
        if gsi:
            kwargs["GlobalSecondaryIndexes"] = gsi
        ddb.create_table(**kwargs)

    create(
        s.roles_table,
        [{"AttributeName": "role_name", "KeyType": "HASH"}],
        [{"AttributeName": "role_name", "AttributeType": "S"}],
    )
    create(
        s.prompts_table,
        [
            {"AttributeName": "role_name", "KeyType": "HASH"},
            {"AttributeName": "purpose_title", "KeyType": "RANGE"},
        ],
        [
            {"AttributeName": "role_name", "AttributeType": "S"},
            {"AttributeName": "purpose_title", "AttributeType": "S"},
            {"AttributeName": "purpose", "AttributeType": "S"},
        ],
        gsi=[
            {
                "IndexName": "purpose-index",
                "KeySchema": [{"AttributeName": "purpose", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    create(
        s.projects_table,
        [{"AttributeName": "project_id", "KeyType": "HASH"}],
        [{"AttributeName": "project_id", "AttributeType": "S"}],
    )
    create(
        s.presets_table,
        [
            {"AttributeName": "project_id", "KeyType": "HASH"},
            {"AttributeName": "created_status", "KeyType": "RANGE"},
        ],
        [
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "created_status", "AttributeType": "S"},
        ],
    )
    create(
        s.sessions_table,
        [{"AttributeName": "session_id", "KeyType": "HASH"}],
        [
            {"AttributeName": "session_id", "AttributeType": "S"},
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "started_at", "AttributeType": "S"},
        ],
        gsi=[
            {
                "IndexName": "project-time-index",
                "KeySchema": [
                    {"AttributeName": "project_id", "KeyType": "HASH"},
                    {"AttributeName": "started_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    create(
        s.mistakes_table,
        [{"AttributeName": "mistake_id", "KeyType": "HASH"}],
        [
            {"AttributeName": "mistake_id", "AttributeType": "S"},
            {"AttributeName": "role_name", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
        ],
        gsi=[
            {
                "IndexName": "role-category-index",
                "KeySchema": [
                    {"AttributeName": "role_name", "KeyType": "HASH"},
                    {"AttributeName": "category", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    create(
        s.phases_table,
        [
            {"AttributeName": "project_id", "KeyType": "HASH"},
            {"AttributeName": "phase_name", "KeyType": "RANGE"},
        ],
        [
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "phase_name", "AttributeType": "S"},
        ],
    )
    create(
        s.failure_stories_table,
        [
            {"AttributeName": "project_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        [
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        gsi=[
            {
                "IndexName": "project-status-index",
                "KeySchema": [
                    {"AttributeName": "project_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    create(
        s.decisions_table,
        [{"AttributeName": "decision_id", "KeyType": "HASH"}],
        [
            {"AttributeName": "decision_id", "AttributeType": "S"},
            {"AttributeName": "scope", "AttributeType": "S"},
            {"AttributeName": "active", "AttributeType": "S"},
        ],
        gsi=[
            {
                "IndexName": "scope-active-index",
                "KeySchema": [
                    {"AttributeName": "scope", "KeyType": "HASH"},
                    {"AttributeName": "active", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    yield
    db_client.reset_for_tests()


# ─────────────────────────── Seeded data ───────────────────────────
@pytest.fixture
def seeded(dynamodb_tables):
    """4종 시드 (roles 5 / mistakes 25 / prompts 8 / decisions 8) 입력."""
    from src.config import get_settings
    from src.db.client import get_table

    s = get_settings()
    plan = [
        (s.roles_table, "roles.json"),
        (s.mistakes_table, "mistakes.json"),
        (s.prompts_table, "prompts.json"),
        (s.decisions_table, "decisions.json"),
    ]
    for table_name, file_name in plan:
        items = json.loads((SEEDS / file_name).read_text(encoding="utf-8"))
        table = get_table(table_name)
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
    yield


# ─────────────────────────── Bedrock mock ───────────────────────────
@pytest.fixture
def bedrock_stub(monkeypatch):
    """src.llm.bedrock.invoke_claude 를 monkeypatch.

    각 테스트는 stub.set_response(json_string) 으로 다음 호출 응답 결정.
    """
    from src.llm import bedrock

    class Stub:
        def __init__(self):
            self._response = "{}"
            self.calls: list[str] = []

        def set_response(self, text: str) -> None:
            self._response = text

        def fake_invoke(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
            self.calls.append(prompt)
            return self._response

    stub = Stub()
    monkeypatch.setattr(bedrock, "invoke_claude", stub.fake_invoke)
    # tools 모듈이 from-import로 이미 잡았을 수 있으니 거기도 패치
    import src.tools.projects as projects
    import src.tools.premortem as premortem

    monkeypatch.setattr(projects, "invoke_claude", stub.fake_invoke)
    monkeypatch.setattr(premortem, "invoke_claude", stub.fake_invoke)
    return stub
