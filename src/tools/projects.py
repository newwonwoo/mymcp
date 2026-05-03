"""프로젝트 분류 + 승인 tool. v2.1 LLM 단독 추천.

Trigger phrases (한국어): "프로젝트 분류", "역할 배정 추천", "승인할게"
Trigger phrases (English): "classify project", "approve assignment"
"""
import json
import re
import uuid
from datetime import datetime, timezone

from src.db.repositories.phases import PhasesRepository
from src.db.repositories.presets import PresetsRepository
from src.db.repositories.projects import ProjectsRepository
from src.lib.errors import NotFoundError, ValidationError
from src.llm.bedrock import invoke_claude
from src.server import mcp


CLASSIFICATION_PROMPT = """프로젝트 설명을 보고 다음을 한 번에 결정하라.

프로젝트 설명:
{description}

5역할 중 활성화할 역할 + 우선순위 + 근거를 출력하라.

**제약 (반드시 준수)**:
- planner와 coder는 항상 포함 (모든 프로젝트의 출발점·구현 필수)
- 활성 역할 평균 3개 권장 (Skill 과잉배정 제한)
- 4축 점수(ui_weight, system_complexity, risk_level, verify_intensity)는 0-10 정수, 참고용
- 9역할 등 폐기된 옵션 거론 금지

**자체 기각 대상** (제시 자체 금지):
- 폐기된 역할 구성 (9역할 등)
- locked_decisions 위반 추천

OUTPUT (JSON only, no markdown, no other text):
{{
  "scores": {{
    "ui_weight": 0,
    "system_complexity": 0,
    "risk_level": 0,
    "verify_intensity": 0
  }},
  "recommended_roles": [
    {{"role": "planner", "priority": 1, "reason": "..."}}
  ],
  "skipped_roles": [
    {{"role": "designer", "reason": "..."}}
  ]
}}
"""


@mcp.tool()
def classify_project(description: str) -> dict:
    """LLM 단독 추천. draft preset 저장 — 자동 활성화 안 함.

    Trigger phrases (한국어): "프로젝트 분류해줘", "역할 추천", "이 프로젝트 어떻게"
    Trigger phrases (English): "classify project", "recommend roles"
    """
    if not description.strip():
        raise ValidationError("description is empty")

    raw = invoke_claude(
        prompt=CLASSIFICATION_PROMPT.format(description=description),
        max_tokens=900,
    )
    result = _validate_recommendation(json.loads(_strip_codefence(raw)))

    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    ProjectsRepository().create(
        {
            "project_id": project_id,
            "name": _extract_name(description),
            "description": description,
            "created_at": now,
            "current_phase": "planning",
            "owner": "owner",
        }
    )

    preset_id = str(uuid.uuid4())
    preset = {
        "project_id": project_id,
        "created_status": f"{now}#draft",
        "preset_id": preset_id,
        "scores": result["scores"],
        "role_assignments": result["recommended_roles"],
        "skipped_roles": result.get("skipped_roles", []),
        "status": "draft",
    }
    PresetsRepository().create(preset)

    return {
        "project_id": project_id,
        "preset_id": preset_id,
        "scores": result["scores"],
        "recommended_roles": result["recommended_roles"],
        "skipped_roles": result.get("skipped_roles", []),
        "status": "draft",
        "next_action": (
            f"approve_assignment(project_id='{project_id}') 호출하여 활성화"
        ),
    }


@mcp.tool()
def approve_assignment(project_id: str) -> dict:
    """draft preset → active로 승격. 사용자가 명시 승인해야 호출.

    Trigger phrases (한국어): "승인", "활성화", "approve 해줘"
    Trigger phrases (English): "approve assignment", "activate preset"

    승인 후 phase=planning 자동 시작.
    """
    presets_repo = PresetsRepository()
    drafts = presets_repo.list_by_status(project_id, "draft")
    if not drafts:
        raise NotFoundError(f"No draft preset found for project {project_id}")
    latest = sorted(drafts, key=lambda p: p["created_status"])[-1]

    now = datetime.now(timezone.utc).isoformat()
    activated = presets_repo.update_status(
        project_id=project_id,
        old_key=latest["created_status"],
        new_status="active",
        activated_at=now,
    )
    PhasesRepository().transition(project_id, "planning", reason="approved assignment")

    return {
        "preset_id": activated.get("preset_id"),
        "status": "active",
        "active_roles": [r["role"] for r in activated.get("role_assignments", [])],
        "activated_at": now,
        "next_action": (
            f"start_session(project_id='{project_id}', role='planner') 호출하여 첫 세션 시작"
        ),
    }


def _validate_recommendation(result: dict) -> dict:
    """LLM 출력 형식 검증. 룰 결정이 아니라 형식 강제 (planner/coder 누락 시 자동 보강)."""
    if "recommended_roles" not in result or "scores" not in result:
        raise ValidationError("LLM 응답 형식 오류 — recommended_roles / scores 누락")

    roles_in = {r["role"] for r in result["recommended_roles"]}
    next_priority = (
        max((r["priority"] for r in result["recommended_roles"]), default=0) + 1
    )
    if "planner" not in roles_in:
        result["recommended_roles"].insert(
            0,
            {
                "role": "planner",
                "priority": 1,
                "reason": "[자동 추가] 모든 프로젝트의 필수 출발점",
            },
        )
    if "coder" not in roles_in:
        result["recommended_roles"].append(
            {
                "role": "coder",
                "priority": next_priority,
                "reason": "[자동 추가] 코드 산출물이 있는 프로젝트의 필수 역할",
            }
        )
    if not result["recommended_roles"]:
        raise ValidationError("LLM 추천 실패: 활성 역할 0개")
    return result


def _strip_codefence(raw: str) -> str:
    """Claude가 ```json ... ``` 코드펜스로 감쌀 때 안쪽 JSON만 추출."""
    raw = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    return fence.group(1) if fence else raw


def _extract_name(description: str) -> str:
    first_line = description.split("\n")[0].strip()
    return first_line[:30] if first_line else "Untitled Project"
