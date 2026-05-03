"""Preset 관리 tool — 활성 목록 조회 + 비활성 역할 임시 활성화.

Trigger phrases (한국어): "활성 프리셋", "역할 풀어줘", "잠금 해제"
Trigger phrases (English): "list active presets", "unlock role"
"""
from src.db.repositories.presets import PresetsRepository
from src.lib.errors import NotFoundError
from src.server import mcp


@mcp.tool()
def list_active_presets() -> list[dict]:
    """현재 active 상태인 모든 프리셋 목록.

    Trigger phrases (한국어): "활성 프리셋 목록", "어떤 프리셋 살아있어"
    Trigger phrases (English): "list active presets"
    """
    return PresetsRepository().list_active()


@mcp.tool()
def unlock_role(project_id: str, role: str, reason: str) -> dict:
    """비활성 역할을 활성 preset에 임시 추가.

    Trigger phrases (한국어): "{역할} 잠금 풀어줘", "{역할} 활성화"
    Trigger phrases (English): "unlock role", "activate role"

    skill 과잉배정 제한(하네스 3) — 사용자가 명시 reason 제공해야 함.
    """
    if not reason or len(reason.strip()) < 3:
        raise ValueError("unlock_role requires a meaningful 'reason' (>= 3 chars).")
    repo = PresetsRepository()
    try:
        updated = repo.add_unlocked_role(project_id, role, reason)
    except KeyError as exc:
        raise NotFoundError(str(exc)) from exc
    return updated
