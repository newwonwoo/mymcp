"""핸드오프 저장·조회 tool.

Trigger phrases (한국어): "핸드오프 저장", "다음 역할에 넘겨줘", "핸드오프 보여줘"
Trigger phrases (English): "save handoff", "get handoff"
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db.repositories.sessions import SessionsRepository
from src.lib.errors import NotFoundError
from src.server import mcp


@mcp.tool()
def save_handoff(
    session_id: str,
    from_role: str,
    to_role: str,
    summary: str,
    context: Optional[dict] = None,
    blockers: Optional[list[str]] = None,
) -> dict:
    """현재 세션의 핸드오프 메모 저장 (역할 전환 시).

    Trigger phrases (한국어): "핸드오프 저장", "다음 역할에 넘기자"
    Trigger phrases (English): "save handoff", "hand off to"
    """
    handoff = {
        "handoff_id": str(uuid.uuid4()),
        "session_id": session_id,
        "from_role": from_role,
        "to_role": to_role,
        "summary": summary,
        "context": context or {},
        "blockers": blockers or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    repo = SessionsRepository()
    if not repo.get(session_id):
        raise NotFoundError(f"Session not found: {session_id}")
    repo.attach_handoff(session_id, handoff)
    return handoff


@mcp.tool()
def get_handoff(session_id: str) -> dict:
    """세션의 직전 핸드오프 메모 조회.

    Trigger phrases (한국어): "핸드오프 보여줘", "이전 핸드오프 뭐였지"
    Trigger phrases (English): "get handoff", "show handoff"
    """
    sess = SessionsRepository().get(session_id)
    if not sess:
        raise NotFoundError(f"Session not found: {session_id}")
    handoff = sess.get("handoff_note")
    if not handoff:
        raise NotFoundError(f"No handoff stored for session {session_id}")
    return handoff
