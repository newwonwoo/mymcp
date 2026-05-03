"""프롬프트 조회 tool. 비활성 역할 잠금 메커니즘 포함.

Trigger phrases (한국어): "프롬프트 줘", "프롬프트 가져와", "{역할} 프롬프트"
Trigger phrases (English): "get prompt", "fetch prompt"
"""
from typing import Optional, Union

from src.db.repositories.presets import PresetsRepository
from src.db.repositories.prompts import PromptsRepository
from src.lib.errors import NotFoundError, RoleNotActiveError
from src.server import mcp


@mcp.tool()
def get_prompt(
    role: str,
    purpose: str,
    title: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Union[dict, list[dict]]:
    """역할 + 목적(+ 선택적 제목)으로 프롬프트 조회.

    Trigger phrases (한국어): "프롬프트 줘", "{역할} {목적} 프롬프트"
    Trigger phrases (English): "get prompt", "load prompt for"

    project_id가 주어지면 잠금 검증: 활성 preset에 role이 없으면 RoleNotActiveError.
    title 미지정 시 해당 role+purpose의 모든 프롬프트 목록 반환.
    """
    if project_id:
        active = PresetsRepository().get_active(project_id)
        if active and not _is_role_active(active, role):
            raise RoleNotActiveError(
                f"역할 '{role}'은 프로젝트 {project_id}에서 비활성 상태. "
                f"unlock_role(project_id='{project_id}', role='{role}', reason='이유') "
                "먼저 호출 필요."
            )

    repo = PromptsRepository()
    if title:
        prompt = repo.get(role, purpose, title)
        if not prompt:
            raise NotFoundError(
                f"Prompt not found: role={role}, purpose={purpose}, title={title}"
            )
        return prompt
    return repo.list_by_role_purpose(role, purpose)


def _is_role_active(preset: dict, role: str) -> bool:
    return any(r["role"] == role for r in preset.get("role_assignments", []))
