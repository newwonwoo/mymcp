"""잠금 메커니즘 — get_prompt 가 비활성 역할에 대해 RoleNotActiveError 발생.

설계서 §3-3 / handoff §5-3 핵심 동작.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.db.repositories.presets import PresetsRepository
from src.db.repositories.projects import ProjectsRepository
from src.lib.errors import RoleNotActiveError
from src.tools.prompts import get_prompt


def _seed_project_with_active_roles(roles: list[str]) -> str:
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    ProjectsRepository().create(
        {
            "project_id": project_id,
            "name": "test",
            "description": "test",
            "created_at": now,
            "current_phase": "planning",
        }
    )
    PresetsRepository().create(
        {
            "project_id": project_id,
            "created_status": f"{now}#active",
            "preset_id": str(uuid.uuid4()),
            "scores": {"ui_weight": 0, "system_complexity": 5, "risk_level": 3, "verify_intensity": 5},
            "role_assignments": [
                {"role": r, "priority": i + 1, "reason": "seed"} for i, r in enumerate(roles)
            ],
            "skipped_roles": [],
            "status": "active",
            "activated_at": now,
        }
    )
    return project_id


def test_active_role_returns_prompt(seeded):
    """planner 가 active이면 planner 프롬프트 정상 반환."""
    project_id = _seed_project_with_active_roles(["planner", "coder"])
    result = get_prompt(
        role="planner",
        purpose="workflow",
        title="requirements_정리",
        project_id=project_id,
    )
    assert isinstance(result, dict)
    assert result["role_name"] == "planner"
    assert "requirements" in result["title"]


def test_inactive_role_raises_lock(seeded):
    """designer 가 비활성이면 RoleNotActiveError + unlock 안내 메시지."""
    project_id = _seed_project_with_active_roles(["planner", "coder"])
    with pytest.raises(RoleNotActiveError) as exc:
        get_prompt(
            role="designer",
            purpose="workflow",
            title="ui_레이아웃_설계",
            project_id=project_id,
        )
    msg = str(exc.value)
    assert "designer" in msg
    assert "unlock_role" in msg


def test_no_project_id_skips_lock(seeded):
    """project_id 없이 호출하면 잠금 검증 스킵 (어느 역할이든 조회 가능)."""
    result = get_prompt(role="designer", purpose="workflow", title="ui_레이아웃_설계")
    assert isinstance(result, dict)
    assert result["role_name"] == "designer"


def test_unlock_then_get_prompt(seeded):
    """unlock_role 호출 후 designer 프롬프트가 잠금 풀리는지."""
    from src.tools.presets import unlock_role

    project_id = _seed_project_with_active_roles(["planner", "coder"])
    unlock_role(project_id=project_id, role="designer", reason="UI 작업 추가됨")
    result = get_prompt(
        role="designer",
        purpose="workflow",
        title="ui_레이아웃_설계",
        project_id=project_id,
    )
    assert result["role_name"] == "designer"
