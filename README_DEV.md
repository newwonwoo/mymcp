# MCP Hub — 유지보수 매뉴얼

배포·디버깅·롤백·비용 모니터링. 사용자용 매뉴얼은 [`README.md`](./README.md).

## 0. 저장소 구조

```
mymcp/
├── template.yaml           # SAM (Lambda + 9 DynamoDB + HttpApi + CORS)
├── requirements.txt        # 런타임 (mcp, boto3, pydantic)
├── requirements-dev.txt    # +pytest, moto, pyflakes
├── Makefile                # install / verify / test / build / deploy
├── .env.example            # 로컬 개발용 환경변수
├── README.md               # 사용자용
├── README_DEV.md           # 본 문서
├── QA_REPORT.md            # 품질확인서
├── MCP_HUB_DESIGN_v2.3.md  # 설계서
├── PROMPTS_v1.3.md         # 프롬프트 + 슬롯 매트릭스
├── CLAUDE_CODE_HANDOFF.md  # Claude Code 인계 명세서
│
├── src/
│   ├── run.sh              # Lambda Web Adapter 진입 (uvicorn)
│   ├── server.py           # FastMCP + 20 tools 자동 등록
│   ├── config.py           # 환경변수 → Settings dataclass
│   ├── lib/{auth,errors,verify}.py
│   ├── db/{client,models}.py + repositories/(9개)
│   ├── llm/bedrock.py
│   └── tools/(10개 모듈, 20개 @mcp.tool())
│
├── seeds/                  # roles 5 / mistakes 25 / prompts 8 / decisions 8
├── scripts/{seed_db,verify_code}.py
├── tests/                  # pytest + moto, 17 cases
└── samples/                # 디자인 톤 PoC (옵션)
```

## 1. 첫 배포 (dev stage)

### 1-1. 사전 준비
```bash
# AWS 자격증명 (본인 계정, ap-northeast-2 권한)
aws sts get-caller-identity

# Bedrock Anthropic Claude Opus 4.7 모델 access 활성화 (D-SEED-009)
# AWS Console → Bedrock → Model access (반드시 ap-northeast-2)
# Cross-region inference profile (apac.*) 사용 시 해당 항목도 함께 활성화

# 정확한 modelId 확인:
aws bedrock list-foundation-models --region ap-northeast-2 \
  --query 'modelSummaries[?contains(modelId, `opus`)].modelId' --output table

# SAM CLI
sam --version  # >= 1.100
```

### 1-2. 배포
```bash
make install                          # 의존성 + 검증 도구
make verify                           # 4단계 검증 (배포 전 게이트)
make test                             # 17 회귀 테스트

sam build
sam deploy --guided                   # 첫 배포만 — 답변:
#   Stack name: mcp-hub-dev
#   Region: ap-northeast-2
#   ApiKey: <랜덤 64자 — 별도 보관>
#   Stage: dev
#   Confirm changes: y
#   Allow SAM to create IAM roles: y
#   Save to samconfig.toml: y
```

### 1-3. 시드 데이터 입력
```bash
export AWS_REGION=ap-northeast-2
export STAGE=dev
# (테이블명은 환경변수로 주입하지 않으면 mcp-hub-<table>-dev 기본 사용)

python scripts/seed_db.py
# 출력: roles 5 / mistakes 25 / prompts 8 / decisions 8 = 46 items
```

### 1-4. URL 확인 + 헬스체크
```bash
sam list endpoints --stack-name mcp-hub-dev
# https://abc123.execute-api.ap-northeast-2.amazonaws.com/dev/mcp

# 헬스 (X-API-Key 필수)
curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools | length'
# → 20
```

### 1-5. claude.ai / Claude Code 웹 등록
사용자 매뉴얼 §0 참조. 등록 직후 `list_roles` 호출로 확인.

## 2. 일상 운영

### 코드 수정 → 검증 → 배포
```bash
make verify    # ast.parse / import / pytest / pyflakes — 한 번에 4단계
make test      # 회귀만
sam build && sam deploy
```

### 시드 갱신
- `seeds/*.json` 직접 편집 후 `python scripts/seed_db.py`
- 운영 데이터는 보존됨 (PutItem이라 같은 키 덮어쓰기만)

### 새 결정 추가 (재배포 0번)
- 사용자가 자연어로 "이거 락 걸어 ..." → `lock_decision` 호출 → DynamoDB Decisions 테이블에 즉시 반영
- 다음 `resume_context` 부터 자동 노출

## 3. 디버깅

### Lambda 로그 (CloudWatch)
```bash
sam logs -n McpHubFunction --stack-name mcp-hub-dev --tail
```

### 자주 마주칠 에러

| 증상 | 원인 | 해결 |
|---|---|---|
| `RoleNotActiveError` | 비활성 역할 prompt 호출 | `unlock_role` 먼저 |
| `record_mistake requires root_cause` | root_cause 누락 | workaround 금지 — 근본 원인 명시 |
| Bedrock `AccessDeniedException` | 모델 access 미활성 | Console → Bedrock → Model access 활성화 |
| Bedrock 응답 JSON 파싱 실패 | Claude가 코드펜스 포함 | `_strip_codefence`가 처리 — 그래도 실패하면 prompt에 "JSON only" 더 강조 |
| DynamoDB `ResourceNotFoundException` | 테이블 미생성 또는 stage 불일치 | `STAGE` 환경변수 / `*_TABLE` 환경변수 확인 |
| Lambda timeout 30s 초과 | Bedrock 응답 지연 | `template.yaml` Timeout 60s로 상향 또는 max_tokens 축소 |
| `RoleNotActiveError` 가 사라지지 않음 (unlock 했는데도) | active preset 캐시 없음 — 다음 호출에서 정상 | 호출 자체가 실패면 preset DB 직접 확인 |
| `transition_phase('coding')` 가 즉시 phase=coding으로 감 | 게이트 우회 — premortem 모듈 import 실패 가능 | `make verify` 로 import 검증 |

### 로컬 재현
```bash
make test       # moto로 9 테이블 + Bedrock mock — 100% 격리 환경
```

## 4. 롤백

### 코드 롤백
```bash
git revert <bad-commit>
sam build && sam deploy
```

### 시드 롤백 (DynamoDB)
PutItem 이라 자동 백업 없음. 안전하게 가려면:
- DynamoDB **PITR(Point-in-Time Recovery)** 활성화 권장:
  ```bash
  for t in roles prompts projects presets sessions mistakes phases failure-stories decisions; do
    aws dynamodb update-continuous-backups \
      --table-name mcp-hub-$t-dev \
      --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
  done
  ```
- 시드 변경 전엔 `aws dynamodb scan` 으로 백업 export

### 결정 무효화
```python
from src.db.repositories.decisions import DecisionsRepository
DecisionsRepository().revoke("D-USER-xxx")
# active="false" 로 표시 + revoked_at 기록. 행은 보존 (감사용).
```

## 5. 비용 모니터링

### 예상 (월간, 1인용)
| 항목 | 무료티어 | 실사용 | 초과 |
|---|---|---|---|
| Lambda 호출 | 100만 | ~1만 | $0 |
| Lambda 실행시간 | 40만 GB-s | ~5만 | $0 |
| API Gateway HTTP | 100만 | ~1만 | $0 |
| DynamoDB 읽/쓰기 | 25 RCU/WCU | 평균 1-2 | $0 |
| DynamoDB 저장 | 25GB | <100MB | $0 |
| **Bedrock Claude Opus 4.7** (D-SEED-009) | 없음 | classify ~5/월 + premortem ~10/월 | **~$2.0** |

총 ~$2/월. Sonnet 대비 5배지만 1인용 절대값은 무시 가능 — 품질 우선 결정.
premortem 게이트(M-SEED-024 차단)의 "단일 hidden_assumption" 식별 정확도가 이 비용을 정당화.

### CloudWatch 알람 (권장)
```bash
# DynamoDB 읽기 80% 도달 시 경고
aws cloudwatch put-metric-alarm \
  --alarm-name mcp-hub-ddb-read-warn \
  --metric-name ConsumedReadCapacityUnits \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 86400 --threshold 20 --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

## 6. 보안

- API Key는 SAM 파라미터 `ApiKey` 로만 주입. **git 절대 금지** (`.env` 는 `.gitignore`)
- 분기별 키 회전 권장: `sam deploy --parameter-overrides ApiKey=<new>`
- `src/lib/auth.py` 는 `hmac.compare_digest` — 타이밍 어택 방지
- IAM: 9개 테이블 CRUD + `bedrock:InvokeModel` 만 (template.yaml 그대로)
- CloudTrail 활성화 권장 (Lambda Invoke / DynamoDB 변경 추적)

## 7. v2.3 → 다음 변경 시 체크리스트

설계 변경하려면:
1. `MCP_HUB_DESIGN_v2.X.md` 신규 버전 작성 (변경 이력 표 포함)
2. `LOCKED_DECISIONS` 코드 상수가 아니라 `seeds/decisions.json` 또는 `lock_decision` 으로 추가 (B1)
3. tool 추가/변경 시 docstring에 한국어 트리거 명시 (S1)
4. `_validate_recommendation` 같은 sanity check는 룰 결정 아닌 **출력 형식 검증만** (v2.1)
5. `transition_phase` / `apply_premortem_revision` 변경 시 `tests/test_premortem.py` 회귀 추가
6. 검증 파이프 `make verify` 4단계 모두 PASS 후 배포

## 8. 알려진 한계

- **콜드스타트** 첫 호출 2-3초. 빈도 낮으면 무시. Provisioned Concurrency는 월 $5.
- **단일 사용자** 동시 쓰기 락 미구현 — 1인용 전제. 다인 운영하려면 `lock_decision` 등 conditional write 필요.
- **revoke_decision tool 미구현** — 현재 코드 호출만. 사용자가 자주 무효화하면 추가 tool로 노출.
- **모니터링 대시보드 없음** — CloudWatch raw metric만. CloudWatch Dashboard 한 장 만들면 편함.

## 9. 회고 시점에 보면 좋은 것

- `query_mistakes(category="premortem-loop-failure")` — force_pass 자동 학습 누적 확인 (B2)
- `get_premortem_history(project_id)` — 보완 회수·결정 이력
- `list_active_presets()` — 진행 중 프로젝트 전체
- DynamoDB `mcp-hub-decisions-*` scan — `source="user_lock"` 만 필터 → 운영 중 추가된 결정 목록
