"""결정사항 동적 관리. v2.3 신규.

Trigger phrases (한국어): "결정 잠가줘", "이거 락 걸어", "결정사항 추가", "lock 해줘"
Trigger phrases (English): "lock decision", "save decision"
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db.repositories.decisions import DecisionsRepository
from src.lib.errors import ValidationError
from src.server import mcp


@mcp.tool()
def lock_decision(
    text: str,
    project_id: Optional[str] = None,
    scope: str = "global",
) -> dict:
    """확정된 결정을 동적으로 추가. 코드 재배포 없이 채팅으로 결정 잠금.

    Trigger phrases (한국어): "결정 잠가줘", "이거 락 걸어", "결정사항 추가"
    Trigger phrases (English): "lock decision", "save decision"

    다음 resume_context 호출 시 locked_decisions 배열에 자동 포함된다.
    """
    if scope not in {"global", "project"}:
        raise ValidationError(f"scope must be 'global' or 'project', got '{scope}'")
    if scope == "project" and not project_id:
        raise ValidationError("scope='project' requires project_id")
    if not text.strip():
        raise ValidationError("decision text is empty")

    decision = {
        "decision_id": str(uuid.uuid4()),
        "text": text.strip(),
        "scope": scope,
        "project_id": project_id if scope == "project" else None,
        "active": "true",  # GSI 호환 — 문자열로 저장
        "created_at": datetime.now(timezone.utc).isoformat(),
        "revoked_at": None,
        "source": "user_lock",
    }
    DecisionsRepository().create(decision)
    return decision
