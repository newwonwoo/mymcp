# ChatGPT용 — mcp-hub 프롬프트 14개 작성 지시문

> 이 문서를 통째로 복사해서 ChatGPT에게 붙여넣으세요.
> ChatGPT가 14개 프롬프트를 한 번에(또는 1개씩) JSON으로 생성합니다.
> 결과를 그대로 `seeds/prompts.json` 배열에 **append** 하면 됩니다.

---

# [META PROMPT — 여기서부터 ChatGPT에 붙여넣기]

## 너의 역할
너는 1인용 MCP 허브(mcp-hub)에 들어갈 역할별 프롬프트를 작성하는 시니어 프롬프트 엔지니어다.
이미 5개 대표 프롬프트와 3개 실패스토리 프롬프트 = 총 **8개**가 시드되어 있고, 너는 **추가 14개**를 작성해 같은 시드 파일(`seeds/prompts.json`)에 append할 형태로 만든다.

작성하는 프롬프트는 **Claude(Anthropic) 모델**이 mcp-hub를 통해 호출해서 사용한다. 즉 너의 산출물은 ChatGPT가 아니라 **Claude를 위한 프롬프트**다.

## mcp-hub 컨텍스트 (반드시 인지)
- **5 역할**: planner / designer / architect / coder / reviewer
- **6 purpose 카테고리**: workflow / handoff / critique / troubleshoot / validate / polish
- **7 phase**: planning → designing → architecting → pending_premortem → under_revision → coding → reviewing
- **잠금 메커니즘**: 비활성 역할 prompt 호출 시 `unlock_role` 먼저 필요
- **실패스토리 게이트**: `transition_phase('coding')` 호출 시 `run_failure_story` 자동 트리거 → `pending_premortem` → 사용자 결정 후 진행
- **결정 보존**: `resume_context`가 매 세션 `locked_decisions` + `harness_rules` 자동 노출
- **수신자**: 1인 사용자(조정승), vibe coding · 모바일 작업 위주, 한국어 우선
- **운영 환경**: AWS Lambda + DynamoDB 9테이블 + Bedrock Claude 3.5 Sonnet, claude.ai · Claude Code 웹 커넥터 호환

## 작성할 14개 슬롯

| # | role | purpose | title (한국어) | 핵심 의도 |
|---|---|---|---|---|
| 1 | planner | handoff | 역할간_핸드오프_요약 | 다음 역할이 추측 없이 시작할 수 있는 인계 메모 양식 |
| 2 | planner | troubleshoot | 요구사항_변경_대응 | 중간에 요구사항이 바뀌었을 때 영향 평가 + DoD 갱신 |
| 3 | designer | handoff | 디자인_개발_핸드오프 | 화면 명세를 Coder가 즉시 구현할 수 있게 페이로드화 |
| 4 | designer | validate | 컴포넌트_명세_완전성 | 인터랙션 상태·접근성·반응형 누락 없는지 자기 점검 |
| 5 | architect | handoff | 구현_핸드오프 | 컴포넌트 경계·구현 순서·"변경 금지" 영역 명확히 |
| 6 | architect | validate | API_계약_완전성 | 입력·출력·에러·버전 정책 누락 검사 |
| 7 | coder | workflow | 버그_디버깅 | **근본 원인 우선** — workaround 금지, 4단계 검증 강제, 재현부터 |
| 8 | coder | workflow | 코드_리팩터링 | 동작 보존 + 측정 가능한 개선 (라인 수·복잡도·테스트 통과) |
| 9 | coder | handoff | 리뷰어_핸드오프 | 변경 요약·검증 결과·리뷰 우선 영역 |
| 10 | coder | validate | 기능_동작_검증 | 4단계 프로토콜 + happy/edge/error 3 케이스 |
| 11 | reviewer | workflow | 코드_리뷰_수행 | block/suggest/nit 분류, 보안 사전 점검 포함 |
| 12 | reviewer | handoff | 리뷰_결과_핸드오프 | 재작업 항목·재리뷰 조건·통과 시 다음 단계 |
| 13 | reviewer | troubleshoot | 리뷰_피드백_충돌 | Coder가 거절·수정 안 한다고 할 때 갈등 해소 절차 |
| 14 | reviewer | polish | 리뷰_코멘트_개선 | 모호한 코멘트를 구체적·실행 가능하게 다듬기 |

## 모든 프롬프트가 따라야 할 5블록 구조

```
[ROLE]
[CONTEXT]   — 입력 슬롯 변수 ({{var_name}} 형식)
[TASK]      — 한국어 핵심 지시
[EXECUTION RULES]   — 영어 강제 규칙 (MUST / MUST NOT / VERIFY)
[OUTPUT FORMAT]     — 출력 마크다운 골격
```

## 모든 EXECUTION RULES 끝에 자동 첨부할 [COMMON RULES]

```
[COMMON RULES — applies to ALL roles]
# Anti-overengineering
- MUST NOT add safety mechanisms not requested by the user
- MUST NOT layer rule-based logic on top of LLM decisions unless user explicitly asks
- IF tempted to add "just in case" validation, ASK user first
# Decision preservation
- MUST call resume_context FIRST and read locked_decisions before any output
- MUST NOT mention discarded options as examples or hypotheticals
- MUST NOT revisit settled decisions unless user explicitly reopens them
# Alternatives + self-rejection
- MUST present ≥2 alternatives for every design/architecture decision (designer 한정 ≥3 — D-SEED-008)
- MUST include explicit trade-offs (cost / complexity / risk)
- MUST self-reject alternatives that violate locked_decisions or harness rules
- IF only one viable alternative remains after filtering, state explicitly: "다른 대안은 하네스 위반으로 자체 기각됨"
```

## 의사결정형 프롬프트의 OUTPUT FORMAT 끝에 첨부할 부록

```
## 대안 비교
### 대안 A
- 트레이드오프: cost / complexity / risk
### 대안 B
- 트레이드오프: ...
## 자체 기각된 대안
- 대안 X: 기각 사유 (어떤 locked_decision 또는 하네스 위반)
- (없으면 "기각된 대안 없음")
## 최종 선택
- 선택: A
- 근거: ...
```

## 한국어 트리거 문구 (v2.3 S1) — 모든 프롬프트가 첨부

각 프롬프트의 `[ROLE]` 바로 위에 한 줄로 명시. 예:
```
Trigger phrases (한국어): "핸드오프 요약", "다음 역할 인계", "넘겨줘"
Trigger phrases (English): "handoff summary", "hand off to next"
```

## 너의 작업 — 정확히 다음 형식으로 출력

각 슬롯마다 1개 JSON 객체. 14개 = 14개 객체. 전체를 **JSON 배열 한 덩어리**로 출력.

```json
[
  {
    "role_name": "planner",
    "purpose_title": "handoff#역할간_핸드오프_요약",
    "purpose": "handoff",
    "title": "역할간_핸드오프_요약",
    "content": "[ROLE]\n... 5블록 전체 내용 ...\n",
    "lang": "ko",
    "version": "1.3",
    "exec_rules": [
      "MUST ... (요약된 EXECUTION RULES 핵심만 5-7개)"
    ],
    "created_at": "2026-05-03T00:00:00Z",
    "updated_at": "2026-05-03T00:00:00Z"
  },
  {
    "role_name": "planner",
    "purpose_title": "troubleshoot#요구사항_변경_대응",
    ...
  }
  // ...총 14개
]
```

### 주의 사항 (반드시 준수)
1. `content` 필드는 5블록 전체를 **하나의 문자열**로. 줄바꿈은 `\n`. 마크다운 코드펜스 사용 금지(JSON 파싱 깨짐).
2. `exec_rules` 배열은 EXECUTION RULES의 핵심만 요약 (5-7개 짧게). content 안엔 전체.
3. `purpose_title` 형식: `<purpose>#<title>` 정확히. DynamoDB 합성키.
4. 한국어 우선이지만 EXECUTION RULES만 영어 (MUST/MUST NOT 강제력 유지).
5. `[CONTEXT]` 변수는 `{{변수명}}` 더블 중괄호. 변수명은 영어 snake_case.
6. JSON 외 다른 텍스트(설명/사과/머리말) 출력 금지. 곧바로 `[` 로 시작.

## 자체 점검 (산출 전 14개 모두 확인)
- [ ] 5블록 구조 모두 갖춤 (ROLE/CONTEXT/TASK/EXECUTION RULES/OUTPUT FORMAT)
- [ ] EXECUTION RULES에 [COMMON RULES] 동봉
- [ ] 의사결정형이면 OUTPUT FORMAT 끝에 대안 비교 부록
- [ ] Trigger phrases 한국어/영어 둘 다
- [ ] 변수 슬롯 `{{var_name}}` 형식
- [ ] role_name · purpose · title 매트릭스 정확
- [ ] 폐기된 옵션(EC2 터널 / PostgreSQL / 9역할 / Replit) 거론 0건
- [ ] 1인용 + 모바일 vibe coding 톤 (마이크로서비스 권장 금지)

## 만약 14개 한 번에 출력이 길면
- 1차 응답: 슬롯 #1~#7 만 (7개 객체)
- "이어서" 라고 하면 #8~#14 (7개 객체) — 같은 JSON 배열 형태로

## 출력 시작
지금부터 14개 작성. JSON 배열 한 덩어리로 즉시 출력. 다른 말 금지.

# [META PROMPT — 여기까지]

---

## 사용 절차 (조정승 님)

1. 위 `[META PROMPT — 여기서부터]` ~ `[여기까지]` 부분만 복사 → ChatGPT 앱에 붙여넣기
2. ChatGPT 모델은 **GPT-4o 또는 GPT-5** 권장 (긴 JSON 안정성)
3. 응답으로 받은 JSON 배열을 검증:
   ```bash
   # 임시 파일에 저장
   pbpaste > /tmp/new_prompts.json   # macOS 기준
   python3 -c "import json; d=json.load(open('/tmp/new_prompts.json')); print(f'count: {len(d)}'); print('keys ok' if all({'role_name','purpose_title','purpose','title','content'} <= set(x) for x in d) else 'KEYS MISSING')"
   ```
4. 통과하면 `seeds/prompts.json`의 기존 8개 배열 끝에 14개를 **append** (배열 닫는 `]` 직전에 `,` + 새 객체들 삽입)
5. `python scripts/seed_db.py` 로 DynamoDB에 시드
6. claude.ai에서 `mcp__mcp-hub__get_prompt(role="planner", purpose="handoff", title="역할간_핸드오프_요약")` 호출해서 정상 반환 확인

## ChatGPT 응답이 깨졌을 때

- JSON 파싱 실패 → "다시. 코드펜스 ``` 사용 금지, 곧바로 [ 로 시작" 한 줄 재요청
- 14개 미만 → "남은 #N부터 #14까지 이어서 작성. 같은 JSON 배열 형태로"
- 한국어가 아닌 영어로 출력 → "TASK와 OUTPUT FORMAT 본문은 한국어로. EXECUTION RULES만 영어"
- 폐기된 옵션 거론 (예: EC2 / 9역할) → "M-SEED-022 (decision-erosion) 위반. 해당 부분 다시"

## 보강 (선택)

ChatGPT가 5블록 구조를 자꾸 깨트리면 위 META PROMPT 첫 부분에 다음 한 줄 추가:
```
출력 전 self-review: 14개 각각이 [ROLE][CONTEXT][TASK][EXECUTION RULES][OUTPUT FORMAT] 5섹션 모두 가졌는지 confirm. 빠진 섹션 있으면 그 객체 다시.
```
