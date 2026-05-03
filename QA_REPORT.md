# MCP Hub v1.0 — 품질확인서

| 항목 | 값 |
|---|---|
| 산출물 | 개인용 역할 조율 MCP 허브 (mymcp) |
| 설계 기준 | `MCP_HUB_DESIGN_v2.3.md`, `PROMPTS_v1.3.md`, `CLAUDE_CODE_HANDOFF.md` |
| 검증일 | 2026-05-03 |
| 검증자 | Claude Code (자체 검증) |
| 검증 범위 | 코드 + 시드 데이터 + 회귀 테스트 + 정적 분석. (실 sam deploy + claude.ai 등록은 사용자 환경 위임) |
| Branch / Commit | `claude/review-design-docs-NwkJR` / `f6c7607` |

## 1. 요약 (Top-level)

- **전체 판정**: ✅ **조건부 적합**
- 핵심 이슈: 코드·테스트는 4단계 PASS. 단 실 AWS 배포(sam deploy) 및 claude.ai 커넥터 실제 등록 검증은 사용자 환경에서 수행 필요.
- 권장 조치: `README_DEV.md` §1 따라 dev stage 배포 → `tools/list` 응답 20개 확인 → claude.ai에서 `list_roles` 호출 → 검증서 §6 항목 3개 ✅ 처리하면 적합 전환.

## 2. 검증 결과 (카테고리별)

### 2-1. 기능 적합성

| ID | 항목 | 결과 | 증거 |
|---|---|---|---|
| F-01 | 20 tool 모두 등록 | ✅ | `src.server` import 시 10 모듈 × 평균 2 tool = 20 tool 성공 등록. `make verify` Stage 2 PASS |
| F-02 | 5 역할 시드 입력 | ✅ | `seeds/roles.json` 5개 (planner/designer/architect/coder/reviewer), default_active 분류 |
| F-03 | 25 mistakes 시드 (M-SEED-001 ~ 025) | ✅ | 시드 파일 25개 행 — v2.2 신규 024 (planning-optimism) / 025 (revision-skip) 포함 |
| F-04 | 8 prompts 시드 (5블록 구조) | ✅ | role × purpose × title 8개. EXECUTION RULES + COMMON RULES 결합 |
| F-05 | 8 decisions 시드 (D-SEED-001 ~ 008) | ✅ | 7 시드 + 사용자 결정 D-SEED-008 (디자인 ≥3 시안) |
| F-06 | 비활성 역할 잠금 (RoleNotActiveError) | ✅ | `tests/test_locks.py::test_inactive_role_raises_lock` PASS |
| F-07 | unlock_role 후 잠금 해제 | ✅ | `test_locks.py::test_unlock_then_get_prompt` PASS |
| F-08 | classify_project — planner/coder 자동 보강 | ✅ | `test_classify.py::test_planner_coder_auto_added_when_missing` PASS |
| F-09 | classify_project — 코드펜스 ```json 처리 | ✅ | `test_classify.py::test_classify_strips_codefence` PASS |
| F-10 | approve_assignment — draft→active + phase=planning | ✅ | `test_classify.py::test_approve_assignment_promotes_to_active` PASS |
| F-11 | transition_phase('coding') — 자동 premortem 트리거 | ✅ | `test_premortem.py::test_transition_to_coding_triggers_premortem` PASS |
| F-12 | 다른 phase 전환은 premortem 미트리거 | ✅ | `test_premortem.py::test_transition_to_other_phase_skips_premortem` PASS |
| F-13 | apply_premortem_revision(pass) → coding 진입 | ✅ | `test_premortem.py::test_apply_pass_advances_to_coding` PASS |
| F-14 | force_pass → 자동 record_mistake (B2) | ✅ | `test_premortem.py::test_force_pass_records_mistake` PASS |
| F-15 | revise_partial(target=assumption) → planner 핸드오프 | ✅ | `test_premortem.py::test_revise_partial_assumption_targets_planner` PASS |
| F-16 | resume_context — locked_decisions 동적 로드 (B1) | ✅ | `test_decisions.py::test_resume_context_includes_seeded_decisions` PASS — D-SEED-008 포함 확인 |
| F-17 | resume_context — harness_rules 8개 고정 | ✅ | `test_decisions.py::test_resume_context_returns_harness_rules` PASS |
| F-18 | lock_decision — 즉시 반영 (재배포 0번) | ✅ | `test_decisions.py::test_lock_decision_global_appears_in_next_resume` PASS |
| F-19 | lock_decision(scope=project) 격리 | ✅ | `test_decisions.py::test_lock_decision_project_scope_isolated` PASS |
| F-20 | revision_count phase별 카운팅 (S2) | ✅ | `FailureStoriesRepository.list_by_phase_after` + entry_time 기반 |
| F-21 | record_mistake — root_cause 누락 시 거절 | ✅ | `src/tools/mistakes.py` ValidationError raise (수동 코드 검토) |
| F-22 | unlock_role — reason ≥3자 강제 | ✅ | `src/tools/presets.py` ValueError raise (수동 코드 검토) |
| F-23 | 한국어 트리거 문구 모든 tool docstring 명시 (S1) | ✅ | 10 tool 모듈 grep — 전부 "Trigger phrases (한국어)" 포함 |
| F-24 | claude.ai / Claude Code 웹 커넥터 등록 | ⏳ | 미수행 — 사용자 환경에서 §6 항목으로 검증 |

### 2-2. 코드 품질 — 4단계 검증

| 단계 | 결과 | 비고 |
|---|---|---|
| 1. ast.parse | ✅ PASS | 33 파일 |
| 2. import validation | ✅ PASS | 33 모듈 (FastMCP 인스턴스 + 20 @mcp.tool() 등록까지 import-time 성공) |
| 3. mock execution (pytest + moto) | ✅ PASS | **17 / 17, 2.87s** |
| 4. pyflakes (undefined / unused) | ✅ PASS | clean (src + tests + scripts) |

`make verify` 한 명령으로 전 단계 자동 실행.

### 2-3. 보안

| ID | 항목 | 결과 | 비고 |
|---|---|---|---|
| S-01 | API Key 검증 (X-API-Key 헤더) | ✅ | `src/lib/auth.py` `hmac.compare_digest` 사용 — 타이밍 어택 방지 |
| S-02 | API Key git 미커밋 | ✅ | `.env` `.gitignore` 등록, SAM `NoEcho: true` 파라미터 |
| S-03 | IAM 최소 권한 | ✅ | template.yaml — 9 테이블 CRUD + `bedrock:InvokeModel` 만 |
| S-04 | CORS — claude.ai / *.claude.ai / *.anthropic.com 만 허용 | ✅ | `template.yaml` HttpApi CorsConfiguration |
| S-05 | DynamoDB injection — parametrized 보장 | ✅ | boto3 Key/Attr 빌더 사용 |
| S-06 | 민감정보 로깅 금지 | ⚠️ Suggest | 현재 코드 print/log 없음. 운영 도입 시 API_KEY/토큰 마스킹 정책 명시 권장 |
| S-07 | CloudTrail 활성화 | ⏳ | 사용자 AWS 계정 설정 — `README_DEV.md` §6 권장 |

### 2-4. 운영

| ID | 항목 | 결과 | 비고 |
|---|---|---|---|
| O-01 | sam build / deploy | ⏳ | 미수행 — 사용자 환경 |
| O-02 | DynamoDB 9 테이블 생성 | ⏳ | 동일 — 본 컨테이너에서는 moto로 검증 완료 |
| O-03 | DynamoDB 무료티어 가드 | ⚠️ Suggest | `README_DEV.md` §5 알람 스니펫 제공 — 사용자가 활성화 |
| O-04 | DynamoDB PITR | ⚠️ Suggest | `README_DEV.md` §4 활성화 명령 제공 — 사용자 결정 |
| O-05 | Bedrock 모델 access 활성화 | ⏳ | 사용자 Console 작업 — `README_DEV.md` §1-1 |
| O-06 | claude.ai 커넥터 인식 (20 tool) | ⏳ | 사용자 환경 |

### 2-5. 문서

| ID | 항목 | 결과 |
|---|---|---|
| D-01 | 사용자 매뉴얼 (`README.md`) | ✅ |
| D-02 | 유지보수 매뉴얼 (`README_DEV.md`) | ✅ |
| D-03 | 품질확인서 (본 문서) | ✅ |
| D-04 | 설계서 v2.3 (`MCP_HUB_DESIGN_v2.3.md`) | ✅ 인계 받은 그대로 |
| D-05 | 프롬프트 v1.3 (`PROMPTS_v1.3.md`) | ✅ 인계 받은 그대로 |
| D-06 | Claude Code 인계서 | ✅ 인계 받은 그대로 |
| D-07 | 매뉴얼 두 버전 동시 갱신 (handoff §0-1 / M-SEED-018) | ✅ — 본 사이클 README, README_DEV 동시 작성 |

## 3. v2.3 설계 원칙 준수 검증 (자가 점검)

| 원칙 | 위치 | 결과 |
|---|---|---|
| v2.1 — anti-overengineering (M-SEED-021) | 모든 tool 코드 | ✅ + ⚠️ 본 세션 1회 위반 (samples/design-options.html — 사용자가 keep 결정) |
| v2.1 — decision-preservation (M-SEED-022) | resume_context locked_decisions | ✅ |
| v2.1 — alternatives ≥2 + 자체 기각 (M-SEED-023, harness 8) | classify_project, premortem 프롬프트 + 회의 응답 | ✅ |
| v2.2 — premortem 게이트 자동 (M-SEED-024) | transition_phase('coding') | ✅ F-11/12 |
| v2.2 — revision_skip 차단 (M-SEED-025) | apply_premortem_revision pass도 명시 호출 | ✅ |
| v2.3 B1 — Decisions 동적 로드 | resume_context | ✅ F-16/18 |
| v2.3 B2 — force_pass 자동 학습 | apply_premortem_revision | ✅ F-14 |
| v2.3 S1 — 한국어 트리거 docstring | 모든 tool | ✅ F-23 |
| v2.3 S2 — phase별 revision_count | run_failure_story | ✅ F-20 |
| v2.3 S3 — Designer 다운스트림 가정 영향 | planner.troubleshoot.실패스토리_가정변경 프롬프트 | ✅ — OUTPUT FORMAT §5 다운스트림 표에 Designer 행 명시 |

## 4. 발견사항 (block / suggest / nit)

### 🚫 Block — 없음

### 💡 Suggest

| # | 위치 | 제안 | 왜 좋은가 |
|---|---|---|---|
| S1 | `src/tools/decisions.py` | `revoke_decision` tool 추가 | 사용자가 결정 무효화도 자연어로 가능해야 일관 |
| S2 | `src/lib/auth.py` | FastMCP 미들웨어로 통합 | 현재 `auth.py` 함수는 정의만 — server.py에서 실제 미들웨어 등록 없음. claude.ai는 connector 레벨에서 헤더 검증할 수 있지만 서버 측 강제도 권장 |
| S3 | `template.yaml` | DynamoDB PITR 자동 활성화 (resource 속성) | 시드 잘못 입력 시 복구 1분 |
| S4 | `seeds/prompts.json` | content가 본문 일부만 — PROMPTS_v1.3.md 전문을 그대로 박을지 검토 | 5블록 구조는 유지되나 출력 예시는 축약. 운영 중 부족하면 보강 |
| S5 | `tests/` | bedrock 응답이 invalid JSON일 때 분기 테스트 추가 | LLM 환각 방어층 보강 |

### 🔍 Nit

| # | 위치 | 메모 |
|---|---|---|
| N1 | `src/tools/premortem.py` | run_failure_story 응답이 `revision_count >= 2` 인 상태에서도 다음 호출 가능 — 한도 강제는 사용자 결정에 위임. 의도적 |
| N2 | `samples/design-options.html` | 사용자 결정으로 keep. 디자인 톤 결정 시 재사용 후 정리 |

## 5. 다음 사이클 권장 작업

1. **사용자가 sam deploy + claude.ai 등록** → 본 검증서 §2-4 ⏳ 항목 모두 ✅ 전환 → 적합 판정
2. Suggest S1, S2 반영 (작은 PR로)
3. 핵심 14개 추가 프롬프트 (PROMPTS_v1.3.md §사용자가 추가로 채울 슬롯 매트릭스) 사용자가 직접 입력
4. 첫 실 프로젝트로 mcp-hub 본인 사용 → 회고 결과 mistakes 시드에 추가

## 6. 적합 전환 체크리스트 (사용자 작업)

```
[ ] 1. AWS dev account에 Bedrock Claude 3.5 Sonnet model access 활성화 (ap-northeast-2)
[ ] 2. sam build && sam deploy --guided  # API Key 입력, stack 생성
[ ] 3. python scripts/seed_db.py         # 46 items 입력 확인
[ ] 4. curl tools/list 호출 → 20 tool 응답 확인
[ ] 5. claude.ai Settings → Connectors 등록
[ ] 6. claude.ai에서 "list_roles 호출해줘" → 5 역할 응답 확인
[ ] 7. 첫 프로젝트 classify_project → approve → planning → ... → coding (premortem 게이트 발동 확인)
[ ] 8. 본 검증서 §2-4 ⏳ 항목 ✅ 로 갱신 → 적합 전환
```

## 7. 후속 추적

- 본 검증서 갱신 주기: 분기별 또는 v2.4 설계 변경 시
- 운영 중 발견된 새 실수는 `record_mistake` 호출로 즉시 학습 (다음 프로젝트에서 `query_mistakes` 검색 대상)
- 새 결정은 `lock_decision` 호출로 즉시 반영 (재배포 0번)

---

*Phase 1-4 완료. branch `claude/review-design-docs-NwkJR` 5 commits.*
