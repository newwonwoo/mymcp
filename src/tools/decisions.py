"""결정사항 동적 관리. v2.3 신규.

Trigger phrases (한국어): "결정 잠가줘", "이거 락 걸어", "결정사항 추가", "lock 해줘"
Trigger phrases (English): "lock decision", "save decision"
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from botocore.exceptions import ClientError

from src.db.repositories.decisions import DecisionsRepository
from src.lib.errors import NotFoundError, ValidationError
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


@mcp.tool()
def revoke_decision(decision_id: str) -> dict:
    """확정 결정을 무효화. 행은 보존(active="false" + revoked_at) — 감사 로그용.

    Trigger phrases (한국어): "결정 무효화", "이 결정 풀어줘", "락 해제", "revoke 해줘"
    Trigger phrases (English): "revoke decision", "unlock decision", "deactivate decision"

    무효화 후 즉시 다음 resume_context 호출의 locked_decisions 배열에서 빠진다.
    원본 행은 삭제되지 않고 active="false" 상태로 보존되어 회고·감사 가능.

    Raises:
        NotFoundError: 존재하지 않는 decision_id.
    """
    repo = DecisionsRepository()
    try:
        updated = repo.revoke(decision_id)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise NotFoundError(f"Decision not found: {decision_id}") from exc
        raise
    if not updated:
        raise NotFoundError(f"Decision not found: {decision_id}")
    return updated
