"""Phase 관련 tool. transition_phase는 coding 진입 시 실패스토리 자동 트리거 (v2.2).

Trigger phrases (한국어): "단계 전환", "코딩으로 가자", "리뷰 단계"
Trigger phrases (English): "transition phase", "move to coding"
"""
from src.db.repositories.phases import PhasesRepository
from src.db.repositories.presets import PresetsRepository
from src.lib.errors import NotFoundError
from src.server import mcp


@mcp.tool()
def get_current_phase(project_id: str) -> dict:
    """현재 phase + 활성 역할 + 권장 다음 행동.

    Trigger phrases (한국어): "지금 어느 단계", "현재 phase"
    Trigger phrases (English): "current phase", "what phase"
    """
    phase = PhasesRepository().get_current(project_id)
    if not phase:
        raise NotFoundError(
            f"No phase recorded for project {project_id}. "
            "approve_assignment 후 자동 생성됨."
        )
    active = PresetsRepository().get_active(project_id)
    active_roles = (
        [r["role"] for r in active.get("role_assignments", [])] if active else []
    )
    return {**phase, "active_roles": active_roles}


@mcp.tool()
def transition_phase(project_id: str, new_phase: str, reason: str) -> dict:
    """단계 전환. v2.2: new_phase='coding'이면 실패스토리 자동 트리거.

    Trigger phrases (한국어): "단계 바꿔", "코딩 단계로", "리뷰로 전환"
    Trigger phrases (English): "transition to", "move phase to"

    coding 진입 시:
      1) run_failure_story 호출 → 4개 보고서 생성
      2) phase = pending_premortem (대기)
      3) 사용자가 apply_premortem_revision 호출해야 진짜 coding 진입
    """
    if new_phase == "coding":
        from src.tools.premortem import run_failure_story

        report = run_failure_story(project_id=project_id, target_phase="coding")
        PhasesRepository().transition(
            project_id, "pending_premortem", reason=f"auto-triggered: {reason}"
        )
        return {
            "phase": "pending_premortem",
            "premortem_report": report,
            "next_action": (
                "사용자 검토 후 apply_premortem_revision(project_id, story_id, mode) 호출. "
                "mode: revise_all / revise_partial / pass / force_pass"
            ),
            "user_prompt": (
                "실패스토리 검토 완료. 보완하시겠어요? "
                "(전체 보완 / 부분 보완 / 통과)"
            ),
        }

    new_item = PhasesRepository().transition(project_id, new_phase, reason)
    return {"phase": new_phase, "reason": reason, "phase_record": new_item}
