# MCP Hub — 사용자 매뉴얼

개인용 역할 조율 MCP 서버. claude.ai · Claude Code 웹·앱·IDE 어디서든 자연어로 호출.

> 유지보수·디버깅은 [`README_DEV.md`](./README_DEV.md). 검증 결과는 [`QA_REPORT.md`](./QA_REPORT.md).

## 무엇을 해주나

1. **매번 같은 거 설명 안 함** — 5개 역할(planner/designer/architect/coder/reviewer)과 8개 시드 프롬프트 자동 매칭
2. **새 세션 피곤함 해결** — `resume_context(project_id)` 한 번이면 직전 작업·결정·실수까지 복원
3. **같은 실수 반복 차단** — `query_mistakes`로 25개 시드 + 누적 실수 검색

## 0. 1회 등록 — claude.ai / Claude Code 웹

배포 후 발급된 URL과 API Key가 필요합니다 (배포 절차는 `README_DEV.md` §1).

### claude.ai 데스크톱·모바일
1. Settings → **Connectors** → "Add custom connector"
2. URL: `https://<your-api-id>.execute-api.ap-northeast-2.amazonaws.com/dev/mcp`
3. Authentication: **API Key**, Header `X-API-Key`, Value: 본인 키
4. Save → 도구 목록에 20개 tool이 뜨면 OK

### Claude Code 웹 (claude.ai/code)
- 동일하게 Connectors에 등록. 코드 작업 중 `mcp__mcp-hub__*` 형태로 자동 노출.
- 로컬 Claude Code(CLI)에 추가하려면: `claude mcp add mcp-hub https://<url>/mcp --header "X-API-Key: <키>"`

### 동작 확인 (등록 직후 한 번)
대화창에 입력:
```
mcp-hub의 list_roles 호출해줘
```
5개 역할(planner/designer/architect/coder/reviewer)이 반환되면 정상.

## 1. 첫 프로젝트 시작 — 5단계

```
1) 프로젝트 분류해줘: "<프로젝트 한 줄 설명>"
   → classify_project 호출, draft preset 생성, 추천 역할 + 점수 출력

2) 승인할게
   → approve_assignment, phase=planning 자동 시작, 첫 세션 안내

3) planner 세션 시작해줘
   → start_session, planner 프롬프트 자동 매칭 (get_prompt 자동 호출)

4) 작업 진행 → 다음 역할 핸드오프
   → save_handoff, transition_phase("designing"|"architecting"|"coding"|"reviewing")
   → coding 진입 시 ⚠️ 자동 실패스토리 (premortem) 게이트 발동

5) 컨텍스트 80% 도달 시 → save_handoff 후 새 세션
   → 다음 세션 시작 직후: "이어서 작업할게" → resume_context 자동 호출
```

## 2. 자주 쓰는 명령 — 자연어 → 호출되는 tool

| 자연어 | tool | 비고 |
|---|---|---|
| "이어서" / "어디까지 했지" / "복원" | `resume_context` | 새 세션 첫 호출 권장 |
| "역할 목록" / "어떤 역할 있어" | `list_roles` | |
| "{역할} 프롬프트 줘" | `get_prompt` | 비활성 역할이면 잠금 안내 |
| "이거 락 걸어 / 결정 잠가줘" | `lock_decision` | scope=global 기본, 다음 resume부터 자동 노출 |
| "{역할} 잠금 풀어줘 / 활성화" | `unlock_role` | reason 필수 (3자 이상) |
| "실패스토리 / 프리모템 / 위험 분석" | `run_failure_story` | 코딩 진입 자동 또는 명시 호출 |
| "전체 보완 / 부분 보완 / 통과 / 강제 통과" | `apply_premortem_revision` | premortem 결과 결정 |
| "지금 어느 단계" / "현재 phase" | `get_current_phase` | |
| "단계 바꿔 / 코딩 단계로" | `transition_phase` | coding은 premortem 자동 |
| "예전에 어떤 실수" / "관련 실수 보여줘" | `query_mistakes` | role/category/keyword 필터 |
| "이 실수 기록해줘" | `record_mistake` | root_cause 필수 |
| "핸드오프 저장 / 다음 역할에 넘기자" | `save_handoff` | session_id 필요 |
| "활성 프리셋 목록" | `list_active_presets` | |
| "실패스토리 이력" | `get_premortem_history` | 회고용 |

전체 20개 tool 시그니처는 `MCP_HUB_DESIGN_v2.3.md` §4-3 참조.

## 3. 실패스토리 게이트 — 가장 중요한 흐름

코딩 단계로 가려고 하면 mcp-hub가 자동으로:

```
사용자: "코딩 단계로 가자"
   ↓
[자동] run_failure_story → 4개 보고서 (stories 3개 / warnings / assumption / revised_plan)
   ↓
phase = pending_premortem (대기)
   ↓
[Claude가 사용자에게 묻는다] "보완하시겠어요? (전체 보완 / 부분 보완 / 통과)"
   ↓
사용자 선택 → apply_premortem_revision(mode=...)
   ├─ pass → 코딩 진입
   ├─ revise_all → architect 핸드오프 → 보완 후 재실행 (최대 2회)
   ├─ revise_partial(target_items=["assumption"]) → planner 핸드오프
   └─ force_pass (2회 후만) → 코딩 진입 + 자동 record_mistake (학습)
```

이 게이트는 LLM의 낙관 환각을 차단하는 핵심 장치 (M-SEED-024 / 025 회피).

## 4. 디자인 작업 시 룰 (D-SEED-008)

> **디자인 결정은 항상 시안 ≥3개를 본 뒤에 한다 — 시안 없이 단일 안 채택 금지 (designer 한정)**

`resume_context` 가 매 세션 자동으로 이 룰을 노출. designer 작업 시작 전에 Claude가 인지.

## 5. 결정 추가 / 무효화

```
"이 결정 잠가줘: API 응답은 200ms 이내"
   → lock_decision(text="...", scope="global")  # 모든 프로젝트
   → 다음 resume_context 부터 locked_decisions 배열에 자동 포함

"프로젝트 X에서만: 모바일 우선"
   → lock_decision(text="...", project_id="X", scope="project")
```

결정 폐기는 `DecisionsRepository.revoke(decision_id)` 호출 (현재는 코드 호출 — 추후 `revoke_decision` tool 추가 검토).

## 6. 외부 도구 조합 (참고)

mcp-hub는 "어떤 역할로 무슨 규칙으로 일할지"만 결정. 실제 작업 도구는 별도:

| 역할 | 권장 외부 도구 |
|---|---|
| Planner | 내장 Read/Write, (선택) Notion/Gmail MCP |
| Designer | 내장 Read + Artifacts 미리보기 (현재 외부 디자인 도구 미사용 — D-SEED 별도 결정) |
| Architect | 내장 Read/Write/Edit |
| Coder | **내장 Read/Write/Edit/Bash/Grep/Glob** + GitHub MCP (PR 생성 시) |
| Reviewer | 내장 Read/Grep/Bash + GitHub MCP (PR 코멘트) |

## 7. 자주 묻는 것

**Q. 비활성 역할 프롬프트를 받고 싶을 때**
→ `unlock_role(project_id, role, reason)` 호출 후 다시 `get_prompt`. reason 3자 이상.

**Q. 컨텍스트 80% 넘었어요**
→ `update_context(session_id, 80)` 부터 mcp-hub가 핸드오프 권장 메시지 동봉. `save_handoff` 후 새 세션 시작.

**Q. 같은 실수가 또 났어요**
→ `record_mistake(role, category, description, root_cause=...)` 호출. root_cause 누락 시 거절됨 (workaround 금지).

**Q. 비용은?**
→ 무료티어 안에서 운영 가능. Bedrock classify/premortem 호출만 월 ~$0.5 예상. 자세한 모니터링은 `README_DEV.md` §5.

**Q. 새 결정을 lock 했는데 적용이 안 된 것 같아요**
→ `resume_context` 호출했는지 확인. 결정 동적 로드는 매 resume마다 새로 조회.
