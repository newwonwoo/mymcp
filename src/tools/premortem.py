"""실패스토리(Pre-mortem) tool. v2.2 + v2.3 보완.

Trigger phrases (한국어): "실패스토리", "프리모템", "실패 보고서", "위험 분석"
Trigger phrases (English): "premortem", "failure story", "pre-mortem"

전환 흐름은 phases.transition_phase 와 결합. v2.3:
  - revision_count는 target_phase × phase 진입시점 이후만 카운팅 (S2)
  - force_pass 시 자동 record_mistake (B2)
"""
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db.repositories.failure_stories import FailureStoriesRepository
from src.db.repositories.phases import PhasesRepository
from src.db.repositories.sessions import SessionsRepository
from src.lib.errors import ValidationError
from src.llm.bedrock import invoke_claude
from src.server import mcp


PREMORTEM_PROMPT = """6개월 후 미래로 이동했다고 가정하라.
다음 계획이 어떻게 실패했는지 기정사실로 보고하라.

검토 대상:
{plan_text}

대상 phase: {target_phase}
revision_count: {revision_count}

OUTPUT (JSON only):
{{
  "stories": ["구체적 실패 서사 1", "...2", "...3"],
  "warnings": ["관찰 가능한 신호 1", "...2"],
  "assumption": "단 하나의 핵심 숨은 가정",
  "revised_plan": "실패 모드 반영한 재작성 계획"
}}

규칙:
- 모든 서술 과거형 ("~했다")
- 가능성 표현 금지 ("might", "could")
- 3개 실패 서사는 서로 달라야 함
- assumption은 정확히 1개
"""


@mcp.tool()
def run_failure_story(
    project_id: str,
    plan_text: Optional[str] = None,
    target_phase: str = "coding",
) -> dict:
    """실패스토리(Pre-mortem) 실행.

    Trigger phrases (한국어): "실패스토리", "프리모템 돌려", "실패 시나리오"
    Trigger phrases (English): "premortem", "failure story", "run pre-mortem"

    호출 경로:
      1) transition_phase('coding') 자동 트리거 (plan_text 없음 → 직전 핸드오프 사용)
      2) 사용자 명시 호출 — plan_text 있으면 그대로 사용
    """
    sessions_repo = SessionsRepository()
    stories_repo = FailureStoriesRepository()
    phases_repo = PhasesRepository()

    if not plan_text:
        last_session = sessions_repo.get_latest(project_id)
        if last_session:
            handoff = last_session.get("handoff_note") or {}
            if isinstance(handoff, dict):
                plan_text = handoff.get("summary")
            else:
                plan_text = str(handoff)
        if not plan_text:
            raise ValidationError(
                "검토 대상 없음. plan_text를 명시하거나 직전 세션 핸드오프 필요."
            )

    # v2.3 S2: phase 진입시점 이후 revision_count 만 카운트
    entry_time = phases_repo.get_entry_time(project_id, target_phase) or ""
    history = stories_repo.list_by_phase_after(project_id, target_phase, entry_time)
    revision_count = len(history)

    raw = invoke_claude(
        prompt=PREMORTEM_PROMPT.format(
            plan_text=plan_text,
            target_phase=target_phase,
            revision_count=revision_count,
        ),
        max_tokens=2000,
    )
    result = json.loads(_strip_codefence(raw))

    story_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    stories_repo.create(
        {
            "project_id": project_id,
            "created_at": now,
            "story_id": story_id,
            "target_phase": target_phase,
            "source_artifact": (plan_text or "")[:500],
            "stories": result["stories"],
            "warnings": result["warnings"],
            "assumption": result["assumption"],
            "revised_plan": result["revised_plan"],
            "revision_count": revision_count,
            "status": "pending",
        }
    )

    return {
        "story_id": story_id,
        "stories": result["stories"],
        "warnings": result["warnings"],
        "assumption": result["assumption"],
        "revised_plan": result["revised_plan"],
        "revision_count": revision_count,
        "remaining_attempts": max(0, 2 - revision_count),
        "status": "pending",
        "next_action": (
            "사용자 검토 후 apply_premortem_revision 호출 "
            "(mode: revise_all / revise_partial / pass / force_pass)"
        ),
    }


@mcp.tool()
def apply_premortem_revision(
    project_id: str,
    story_id: str,
    mode: str,
    target_items: Optional[list[str]] = None,
) -> dict:
    """실패스토리 보완 결정 적용.

    Trigger phrases (한국어): "전체 보완", "부분 보완", "통과", "강제 통과"
    Trigger phrases (English): "apply premortem revision"

    mode:
      - revise_all     : revised_plan 전체 채택 → architect 핸드오프
      - revise_partial : target_items 항목만 보완
      - pass           : 원본 유지, 코딩 진행
      - force_pass     : 한도 도달 후 강제 통과 + 자동 record_mistake (B2)
    """
    if mode not in {"revise_all", "revise_partial", "pass", "force_pass"}:
        raise ValidationError(f"Unknown mode: {mode}")

    stories_repo = FailureStoriesRepository()
    phases_repo = PhasesRepository()

    story = stories_repo.get(project_id, story_id)
    if not story:
        raise ValidationError(f"Story not found: {story_id}")

    if mode in {"pass", "force_pass"}:
        new_status = "passed" if mode == "pass" else "forced"
        stories_repo.update_status(project_id, story_id, new_status, mode)
        phases_repo.transition(project_id, "coding", reason=f"premortem {mode}")

        if mode == "force_pass":
            # B2: 자동 학습. 같은 패턴 다음 프로젝트에서 query 가능하게.
            from src.tools.mistakes import record_mistake

            record_mistake(
                role="reviewer",
                category="premortem-loop-failure",
                description=(
                    f"실패스토리 2회 보완 후에도 통과 못 함. "
                    f"project={project_id}, story={story_id}"
                ),
                root_cause=(
                    "revised_plan과 사용자 결정의 간극 — "
                    f"revised={story['revised_plan'][:200]}"
                ),
                resolution=None,
            )

        return {
            "story_id": story_id,
            "mode_applied": mode,
            "phase_status": "coding",
            "next_action": "Coder 작업 시작",
        }

    # revise_all / revise_partial
    if mode == "revise_partial" and target_items and "assumption" in target_items:
        target_role = "planner"
    else:
        target_role = "architect"

    revision_count = story["revision_count"] + 1
    remaining = max(0, 2 - revision_count)

    stories_repo.update_status(
        project_id, story_id, "revised", mode, target_items or []
    )
    phases_repo.transition(
        project_id,
        "under_revision",
        reason=f"premortem revision #{revision_count}",
    )

    return {
        "story_id": story_id,
        "mode_applied": mode,
        "target_items": target_items or ["all"],
        "handoff_target": target_role,
        "revision_count": revision_count,
        "remaining_attempts": remaining,
        "next_action": (
            f"{target_role}가 보완 완료 후 run_failure_story 재실행. "
            f"한도 잔여 {remaining}회"
        ),
        "phase_status": "under_revision",
    }


@mcp.tool()
def get_premortem_history(project_id: str) -> list[dict]:
    """프로젝트의 실패스토리 보완 이력 조회.

    Trigger phrases (한국어): "실패스토리 이력", "프리모템 기록"
    Trigger phrases (English): "premortem history"
    """
    return FailureStoriesRepository().list_by_project(project_id)


def _strip_codefence(raw: str) -> str:
    raw = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    return fence.group(1) if fence else raw


