"""Pydantic 모델 — 9개 테이블 매핑.

DynamoDB 항목을 dict로 직접 다루지 않고 모델로 통일하면
필드 누락·타입 오류를 보낼 때마다 잡을 수 있다.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ── Roles ────────────────────────────────────────────────────────────────
class Role(BaseModel):
    role_name: str
    display_name: str
    description: str
    color: str
    submodes: list[str]
    default_active: bool = False


# ── Prompts ──────────────────────────────────────────────────────────────
class Prompt(BaseModel):
    role_name: str
    purpose_title: str  # purpose#title 합성키
    purpose: str
    title: str
    content: str
    lang: str = "ko"
    version: str = "1.0"
    exec_rules: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


# ── Projects ─────────────────────────────────────────────────────────────
class Project(BaseModel):
    project_id: str
    name: str
    description: str
    created_at: str
    current_phase: str = "planning"
    owner: str = "owner"


# ── Presets ──────────────────────────────────────────────────────────────
class RoleAssignment(BaseModel):
    role: str
    priority: int
    reason: str


class Preset(BaseModel):
    project_id: str
    created_status: str  # created_at#status 합성키
    scores: dict[str, int]
    role_assignments: list[RoleAssignment]
    skipped_roles: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["draft", "active", "archived"]
    preset_id: Optional[str] = None
    approved_at: Optional[str] = None
    activated_at: Optional[str] = None


class ClassificationDraft(BaseModel):
    project_id: str
    preset_id: str
    scores: dict[str, int]
    recommended_roles: list[RoleAssignment]
    skipped_roles: list[dict[str, Any]]
    status: Literal["draft"] = "draft"
    next_action: str


# ── Sessions ─────────────────────────────────────────────────────────────
class Session(BaseModel):
    session_id: str
    project_id: str
    role_name: str
    started_at: str
    ended_at: Optional[str] = None
    context_percent: int = 0
    handoff_note: Optional[str] = None


class HandoffNote(BaseModel):
    handoff_id: str
    session_id: str
    from_role: str
    to_role: str
    summary: str
    context: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    created_at: str


# ── Mistakes ─────────────────────────────────────────────────────────────
class Mistake(BaseModel):
    mistake_id: str
    role_name: str
    category: str
    description: str
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str


# ── Phases ───────────────────────────────────────────────────────────────
PhaseName = Literal[
    "planning",
    "designing",
    "architecting",
    "pending_premortem",
    "under_revision",
    "coding",
    "reviewing",
]


class Phase(BaseModel):
    project_id: str
    phase_name: str
    started_at: str
    ended_at: Optional[str] = None
    status: Literal["active", "completed", "skipped"] = "active"
    reason: Optional[str] = None


# ── FailureStories ───────────────────────────────────────────────────────
class FailureStory(BaseModel):
    project_id: str
    created_at: str
    story_id: str
    target_phase: str
    source_artifact: str
    stories: list[str]
    warnings: list[str]
    assumption: str
    revised_plan: str
    revision_count: int = 0
    status: Literal["pending", "revised", "passed", "forced"] = "pending"
    user_decision: Optional[str] = None
    target_items: list[str] = Field(default_factory=list)
    applied_at: Optional[str] = None


# ── Decisions (v2.3) ─────────────────────────────────────────────────────
class Decision(BaseModel):
    decision_id: str
    text: str
    scope: Literal["global", "project"]
    project_id: Optional[str] = None
    active: str = "true"  # GSI 호환 위해 문자열로 저장
    created_at: str
    revoked_at: Optional[str] = None
    source: Literal["system_seed", "user_lock"] = "user_lock"
