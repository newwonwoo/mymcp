"""실수 기록·검색 tool.

Trigger phrases (한국어): "실수 기록", "실수 검색", "예전에 어떤 실수"
Trigger phrases (English): "record mistake", "query mistakes"
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db.repositories.mistakes import MistakesRepository
from src.lib.errors import ValidationError
from src.server import mcp


@mcp.tool()
def query_mistakes(
    role: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
) -> list[dict]:
    """과거 실수 검색. 새 작업 전 호출 권장.

    Trigger phrases (한국어): "실수 검색", "예전에 비슷한 실수", "관련 실수 보여줘"
    Trigger phrases (English): "query mistakes", "search mistakes"
    """
    return MistakesRepository().query(role=role, category=category, keyword=keyword)


@mcp.tool()
def record_mistake(
    role: str,
    category: str,
    description: str,
    root_cause: Optional[str] = None,
    resolution: Optional[str] = None,
) -> dict:
    """실수 기록. root_cause 누락 시 ValidationError.

    Trigger phrases (한국어): "이 실수 기록해줘", "실수 저장"
    Trigger phrases (English): "record mistake", "log mistake"

    사용자 명시 요청 또는 자동 학습(예: force_pass) 시에만 호출.
    """
    if not root_cause:
        raise ValidationError(
            "record_mistake requires root_cause (근본 원인 명시 — workaround 금지)."
        )
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "mistake_id": str(uuid.uuid4()),
        "role_name": role,
        "category": category,
        "description": description,
        "root_cause": root_cause,
        "resolution": resolution,
        "resolved_at": now if resolution else None,
        "created_at": now,
    }
    MistakesRepository().put(item)
    return item
