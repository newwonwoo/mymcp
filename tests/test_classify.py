"""classify_project — LLM 단독 추천 + sanity check (planner/coder 강제 포함).

설계서 §3-1, §3-2 / handoff §5-2.
"""
from __future__ import annotations

import json

from src.tools.projects import _validate_recommendation, classify_project


def test_planner_coder_auto_added_when_missing():
    """LLM이 planner/coder를 빠뜨려도 sanity가 자동 보강."""
    raw = {
        "scores": {"ui_weight": 8, "system_complexity": 3, "risk_level": 2, "verify_intensity": 4},
        "recommended_roles": [
            {"role": "designer", "priority": 1, "reason": "UI 위주"},
        ],
        "skipped_roles": [],
    }
    out = _validate_recommendation(raw)
    roles = {r["role"] for r in out["recommended_roles"]}
    assert "planner" in roles
    assert "coder" in roles
    assert "designer" in roles


def test_classify_creates_draft_preset(seeded, bedrock_stub):
    """classify_project 가 draft preset을 저장하고 next_action 안내."""
    bedrock_stub.set_response(json.dumps({
        "scores": {"ui_weight": 6, "system_complexity": 4, "risk_level": 3, "verify_intensity": 5},
        "recommended_roles": [
            {"role": "planner", "priority": 1, "reason": "기획"},
            {"role": "designer", "priority": 2, "reason": "UI"},
            {"role": "coder", "priority": 3, "reason": "구현"},
        ],
        "skipped_roles": [
            {"role": "architect", "reason": "시스템 단순"},
        ],
    }))
    result = classify_project(description="모바일 운동 기록 앱")
    assert result["status"] == "draft"
    assert "approve_assignment" in result["next_action"]
    assert {r["role"] for r in result["recommended_roles"]} >= {"planner", "coder"}
    # draft preset이 실제로 들어갔는지
    from src.db.repositories.presets import PresetsRepository

    drafts = PresetsRepository().list_by_status(result["project_id"], "draft")
    assert len(drafts) == 1


def test_approve_assignment_promotes_to_active(seeded, bedrock_stub):
    """draft → active 승격 후 phase=planning 자동 시작."""
    bedrock_stub.set_response(json.dumps({
        "scores": {"ui_weight": 0, "system_complexity": 5, "risk_level": 5, "verify_intensity": 7},
        "recommended_roles": [
            {"role": "planner", "priority": 1, "reason": "기획"},
            {"role": "architect", "priority": 2, "reason": "복잡"},
            {"role": "coder", "priority": 3, "reason": "구현"},
        ],
        "skipped_roles": [],
    }))
    classified = classify_project(description="백엔드 API 마이크로서비스")
    project_id = classified["project_id"]

    from src.tools.projects import approve_assignment

    activated = approve_assignment(project_id=project_id)
    assert activated["status"] == "active"
    assert "planner" in activated["active_roles"]
    assert "start_session" in activated["next_action"]

    from src.db.repositories.phases import PhasesRepository

    phase = PhasesRepository().get_current(project_id)
    assert phase is not None
    assert phase["phase_name"] == "planning"


def test_classify_strips_codefence(seeded, bedrock_stub):
    """Claude가 ```json ... ``` 으로 감싸도 파싱 성공."""
    bedrock_stub.set_response("```json\n" + json.dumps({
        "scores": {"ui_weight": 5, "system_complexity": 5, "risk_level": 5, "verify_intensity": 5},
        "recommended_roles": [
            {"role": "planner", "priority": 1, "reason": "기획"},
            {"role": "coder", "priority": 2, "reason": "구현"},
        ],
        "skipped_roles": [],
    }) + "\n```")
    result = classify_project(description="간단 앱")
    assert result["status"] == "draft"
