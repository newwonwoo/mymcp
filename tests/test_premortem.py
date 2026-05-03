"""실패스토리 게이트 — transition_phase('coding') 시 자동 트리거.

설계서 §3-4, §3-5 / handoff §0-3-2.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from src.db.repositories.presets import PresetsRepository
from src.db.repositories.projects import ProjectsRepository
from src.db.repositories.sessions import SessionsRepository
from src.tools.phases import transition_phase
from src.tools.premortem import apply_premortem_revision


PREMORTEM_FAKE_RESPONSE = json.dumps({
    "stories": [
        "배포 후 3일 만에 콜드스타트 누적 비용이 예산을 초과했다.",
        "DynamoDB GSI 키 설계 오류로 분당 throttle 폭주가 일어났다.",
        "Bedrock 모델 응답 지연이 30초 timeout을 초과해 사용자 흐름이 끊겼다.",
    ],
    "warnings": [
        "p95 응답이 8초를 넘어가는 빈도가 늘어남",
        "월간 비용이 첫 주에 무료티어 50% 도달",
    ],
    "assumption": "Bedrock 호출이 평균 3초 안에 끝난다는 가정",
    "revised_plan": "Bedrock 호출에 5초 timeout + 실패 시 사용자 수동 입력 옵션 추가, GSI 재설계.",
})


def _seed_project_at_phase(phase_name: str = "architecting") -> str:
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    ProjectsRepository().create(
        {
            "project_id": project_id,
            "name": "test",
            "description": "test",
            "created_at": now,
            "current_phase": phase_name,
        }
    )
    PresetsRepository().create(
        {
            "project_id": project_id,
            "created_status": f"{now}#active",
            "preset_id": str(uuid.uuid4()),
            "scores": {"ui_weight": 0, "system_complexity": 6, "risk_level": 6, "verify_intensity": 7},
            "role_assignments": [
                {"role": "planner", "priority": 1, "reason": "seed"},
                {"role": "architect", "priority": 2, "reason": "seed"},
                {"role": "coder", "priority": 3, "reason": "seed"},
                {"role": "reviewer", "priority": 4, "reason": "seed"},
            ],
            "skipped_roles": [],
            "status": "active",
            "activated_at": now,
        }
    )
    # session + handoff 한 건 (premortem이 직전 산출물을 사용하도록)
    session_id = str(uuid.uuid4())
    SessionsRepository().create(
        {
            "session_id": session_id,
            "project_id": project_id,
            "role_name": "architect",
            "started_at": now,
            "context_percent": 50,
            "handoff_note": {
                "summary": "API Gateway + Lambda + DynamoDB 9테이블 + Bedrock으로 설계 완료.",
                "from_role": "architect",
                "to_role": "coder",
            },
        }
    )
    return project_id


def test_transition_to_coding_triggers_premortem(seeded, bedrock_stub):
    """coding 전환 시도가 pending_premortem 으로 보류되고 4보고서 출력."""
    bedrock_stub.set_response(PREMORTEM_FAKE_RESPONSE)
    project_id = _seed_project_at_phase("architecting")

    result = transition_phase(
        project_id=project_id,
        new_phase="coding",
        reason="아키텍처 완료",
    )
    assert result["phase"] == "pending_premortem"
    report = result["premortem_report"]
    assert len(report["stories"]) == 3
    assert report["assumption"]
    assert report["revised_plan"]
    assert report["status"] == "pending"
    assert "apply_premortem_revision" in result["next_action"]


def test_transition_to_other_phase_skips_premortem(seeded, bedrock_stub):
    """coding 외 전환은 트리거되지 않음 (Bedrock 호출 0건)."""
    project_id = _seed_project_at_phase("planning")
    result = transition_phase(
        project_id=project_id,
        new_phase="designing",
        reason="UI 작업 시작",
    )
    assert result["phase"] == "designing"
    assert bedrock_stub.calls == []


def test_apply_pass_advances_to_coding(seeded, bedrock_stub):
    """mode=pass 적용 시 phase=coding 으로 전환."""
    bedrock_stub.set_response(PREMORTEM_FAKE_RESPONSE)
    project_id = _seed_project_at_phase("architecting")
    triggered = transition_phase(project_id, "coding", "ready")
    story_id = triggered["premortem_report"]["story_id"]

    applied = apply_premortem_revision(project_id, story_id, mode="pass")
    assert applied["phase_status"] == "coding"
    assert applied["mode_applied"] == "pass"


def test_force_pass_records_mistake(seeded, bedrock_stub):
    """force_pass 시 자동 record_mistake (B2 — premortem-loop-failure)."""
    from src.db.repositories.mistakes import MistakesRepository

    bedrock_stub.set_response(PREMORTEM_FAKE_RESPONSE)
    project_id = _seed_project_at_phase("architecting")
    triggered = transition_phase(project_id, "coding", "ready")
    story_id = triggered["premortem_report"]["story_id"]

    apply_premortem_revision(project_id, story_id, mode="force_pass")

    found = MistakesRepository().query(category="premortem-loop-failure")
    assert any(project_id in (m.get("description") or "") for m in found)


def test_revise_partial_assumption_targets_planner(seeded, bedrock_stub):
    """target_items 에 'assumption' 포함 시 handoff_target=planner."""
    bedrock_stub.set_response(PREMORTEM_FAKE_RESPONSE)
    project_id = _seed_project_at_phase("architecting")
    triggered = transition_phase(project_id, "coding", "ready")
    story_id = triggered["premortem_report"]["story_id"]

    applied = apply_premortem_revision(
        project_id, story_id, mode="revise_partial", target_items=["assumption"]
    )
    assert applied["handoff_target"] == "planner"
    assert applied["phase_status"] == "under_revision"
    assert applied["revision_count"] == 1
