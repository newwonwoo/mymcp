"""Decisions 동적 로드 + lock_decision + resume_context 합성.

설계서 §3-2 (v2.3 B1) / handoff §0-3-3.
시드 D-SEED-008(디자인 ≥3 시안) 가 resume_context 결과에 자동 포함되는지가 핵심 회귀.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.db.repositories.presets import PresetsRepository
from src.db.repositories.projects import ProjectsRepository
from src.tools.decisions import lock_decision
from src.tools.sessions import resume_context


def _seed_project() -> str:
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
            "scores": {"ui_weight": 5, "system_complexity": 5, "risk_level": 5, "verify_intensity": 5},
            "role_assignments": [
                {"role": "planner", "priority": 1, "reason": "seed"},
                {"role": "coder", "priority": 2, "reason": "seed"},
            ],
            "skipped_roles": [],
            "status": "active",
            "activated_at": now,
        }
    )
    return project_id


def test_resume_context_includes_seeded_decisions(seeded):
    """시드 8개가 resume_context.locked_decisions 에 모두 포함."""
    project_id = _seed_project()
    bundle = resume_context(project_id=project_id)
    decisions = bundle["locked_decisions"]
    assert len(decisions) >= 8
    # 핵심 항목 직접 확인
    assert any("9역할 구성 폐기" in d for d in decisions)
    assert any("실패스토리 자동 트리거" in d for d in decisions)
    assert any("디자인 결정은 항상 시안 ≥3개" in d for d in decisions)


def test_resume_context_returns_harness_rules(seeded):
    """harness_rules 8개가 항상 함께 반환."""
    project_id = _seed_project()
    bundle = resume_context(project_id=project_id)
    rules = bundle["harness_rules"]
    assert len(rules) == 8
    assert "1. 의도 고정" in rules
    assert "8. 대안 N개 + 자체 기각" in rules


def test_lock_decision_global_appears_in_next_resume(seeded):
    """lock_decision(global) 호출 후 resume_context 에 즉시 반영 (재배포 0번)."""
    project_id = _seed_project()
    before = resume_context(project_id=project_id)
    before_count = len(before["locked_decisions"])

    locked = lock_decision(text="API 응답은 200ms 이내")
    assert locked["scope"] == "global"
    assert locked["active"] == "true"
    assert locked["source"] == "user_lock"

    after = resume_context(project_id=project_id)
    assert len(after["locked_decisions"]) == before_count + 1
    assert any("200ms" in d for d in after["locked_decisions"])


def test_lock_decision_project_scope_isolated(seeded):
    """scope=project 결정은 다른 프로젝트의 resume_context에 노출되지 않음."""
    project_a = _seed_project()
    project_b = _seed_project()

    lock_decision(
        text="프로젝트 A 한정: 모바일 우선",
        project_id=project_a,
        scope="project",
    )

    bundle_a = resume_context(project_id=project_a)
    bundle_b = resume_context(project_id=project_b)
    assert any("프로젝트 A 한정" in d for d in bundle_a["locked_decisions"])
    assert not any("프로젝트 A 한정" in d for d in bundle_b["locked_decisions"])
