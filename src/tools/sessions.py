"""세션 관리 + resume_context (v2.3).

Trigger phrases (한국어): "세션 시작", "세션 복원", "이어서 작업", "어디까지 했지"
Trigger phrases (English): "start session", "resume context", "continue from"
"""
import uuid
from datetime import datetime, timezone

from src.db.repositories.decisions import DecisionsRepository
from src.db.repositories.mistakes import MistakesRepository
from src.db.repositories.phases import PhasesRepository
from src.db.repositories.presets import PresetsRepository
from src.db.repositories.projects import ProjectsRepository
from src.db.repositories.sessions import SessionsRepository
from src.lib.errors import NotFoundError
from src.server import mcp


# v2.1+ 하네스 — 코드 상수로 보존 (8개 고정)
HARNESS_RULES = [
    "1. 의도 고정",
    "2. 역할 경계",
    "3. Skill 과잉배정 제한",
    "4. 위험 변경 제한",
    "5. 사용자 승인",
    "6. 세션 승계",
    "7. 반복 실수 기록",
    "8. 대안 N개 + 자체 기각",
]


@mcp.tool()
def start_session(project_id: str, role: str) -> dict:
    """새 세션 시작. session_id 발급 후 sessions 테이블에 저장.

    Trigger phrases (한국어): "세션 시작해줘", "{역할} 작업 시작"
    Trigger phrases (English): "start session", "begin session"
    """
    if not ProjectsRepository().get(project_id):
        raise NotFoundError(f"Project not found: {project_id}")
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": str(uuid.uuid4()),
        "project_id": project_id,
        "role_name": role,
        "started_at": now,
        "context_percent": 0,
    }
    SessionsRepository().create(session)
    return session


@mcp.tool()
def update_context(session_id: str, percent: int) -> dict:
    """세션의 컨텍스트 사용률 갱신. 80% 초과 시 핸드오프 권장.

    Trigger phrases (한국어): "컨텍스트 갱신", "사용률 {n}퍼"
    Trigger phrases (English): "update context", "context at"
    """
    sess = SessionsRepository().update_context(session_id, percent)
    if not sess:
        raise NotFoundError(f"Session not found: {session_id}")
    if percent >= 80:
        sess["warning"] = "context_percent ≥ 80 — save_handoff 후 새 세션 시작 권장"
    return sess


@mcp.tool()
def resume_context(project_id: str) -> dict:
    """새 세션 시작 시 자동 호출. 직전 작업 상태 + locked_decisions + harness_rules 반환.

    Trigger phrases (한국어): "이어서", "어디까지 했지", "복원", "리줌"
    Trigger phrases (English): "resume context", "continue from last"

    v2.3: locked_decisions는 Decisions 테이블에서 동적 로드.
    """
    project = ProjectsRepository().get(project_id)
    if not project:
        raise NotFoundError(f"Project not found: {project_id}")

    active_preset = PresetsRepository().get_active(project_id)
    last_session = SessionsRepository().get_latest(project_id)
    current_phase = PhasesRepository().get_current(project_id)
    unresolved = MistakesRepository().list_unresolved(limit=5)
    locked_decisions = [
        d["text"]
        for d in DecisionsRepository().list_active_for_project(project_id)
    ]

    last_session_summary = None
    if last_session:
        last_session_summary = {
            "id": last_session["session_id"],
            "role": last_session.get("role_name"),
            "handoff_note": last_session.get("handoff_note"),
            "context_percent": last_session.get("context_percent", 0),
            "ended_at": last_session.get("ended_at"),
        }

    return {
        "project": project,
        "active_preset": active_preset,
        "current_phase": current_phase,
        "last_session": last_session_summary,
        "unresolved_mistakes": unresolved,
        "locked_decisions": locked_decisions,
        "harness_rules": HARNESS_RULES,
        "suggested_next_action": _suggest(active_preset, last_session, current_phase),
    }


def _suggest(preset: dict | None, last_session: dict | None, phase: dict | None) -> str:
    if not preset:
        return "approve_assignment 먼저 호출하여 역할 배정 활성화"
    if not last_session:
        first_role = preset["role_assignments"][0]["role"]
        return f"start_session(project_id, role='{first_role}') 호출하여 첫 세션 시작"
    if last_session.get("handoff_note"):
        return "직전 핸드오프 확인 후 다음 역할로 transition_phase 호출"
    if last_session.get("context_percent", 0) >= 80:
        return "직전 세션 80% 초과 — save_handoff 후 새 세션 시작"
    phase_name = phase.get("phase_name") if phase else "planning"
    return f"{phase_name} 단계 계속 진행"
