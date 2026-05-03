# 사용자 작업 가이드 — 0단계부터 적합 판정까지

> 모바일에서 미리 훑어보고 노트북에서 따라하면 됩니다.
> 막히면 출력 그대로 다음 세션에 공유.

---

## 0. 사전 확인 (5분)

### 0-1. AWS 계정 권한 확인
```bash
aws sts get-caller-identity
```
출력에 `Account` `Arn` 나오면 OK. 안 나오면 `aws configure` 먼저.

다음 권한 있는 IAM user 또는 role 필요:
- `cloudformation:*`
- `iam:*` (SAM이 Lambda 실행 role 만듦)
- `lambda:*`
- `apigateway:*`
- `dynamodb:*`
- `bedrock:InvokeModel`, `bedrock:ListFoundationModels`
- `s3:*` (SAM 빌드 산출물 업로드용)

본인 계정이 admin이면 다 됨. 분리 환경이면 IAM Console에서 위 정책 attach.

### 0-2. 도구 설치 확인
```bash
aws --version           # >= 2.x
sam --version           # >= 1.100
git --version
python3 --version       # >= 3.11 권장 (런타임은 3.12지만 로컬 검증은 3.11도 OK)
```

설치 안 됐으면:
- macOS: `brew install awscli aws-sam-cli git python@3.12`
- Linux: 각 도구 공식 문서 따라

---

## 1. Bedrock Opus 활성화 + modelId 확인 (3분)

### 1-1. Console에서 활성화
1. AWS Console 로그인
2. **우측 상단 리전 → "Asia Pacific (Seoul) ap-northeast-2"** 변경 (반드시!)
3. 검색바 "Bedrock" → Bedrock 서비스 진입
4. 좌측 메뉴 **Model access**
5. 우상단 **Modify model access** (또는 Manage model access)
6. **Anthropic Claude Opus 4.7** 체크 (혹은 그 시점 가장 최신 Opus)
7. **사용 사례 약관** 동의 입력
8. **Submit** → 1-3분 기다리면 status `Access granted`

### 1-2. 정확한 modelId 확인
```bash
aws bedrock list-foundation-models \
  --region ap-northeast-2 \
  --query 'modelSummaries[?contains(modelId, `opus`)].[modelId]' \
  --output table
```
출력 예시:
```
anthropic.claude-opus-4-7-20260315-v1:0
```
이 값을 **메모**해둠 (이 가이드에서 `<OPUS_MODEL_ID>` 로 표시).

> Cross-region inference profile (`apac.anthropic.claude-opus-4-7-...`) 도 보일 수 있음 — Opus는 throughput 위해 이 쪽이 더 권장. 둘 중 어느 거 써도 됨.

---

## 2. 레포 가져오기 + 브랜치 체크아웃 (1분)

```bash
git clone https://github.com/newwonwoo/mymcp.git
cd mymcp
git checkout claude/review-design-docs-NwkJR
```

> 이 브랜치가 메인이 될지 main에 머지할지는 사용자 결정. 운영 전에 머지 원하면 `git checkout main && git merge claude/review-design-docs-NwkJR`.

---

## 3. 로컬 검증 (3분)

```bash
make install      # pytest + moto + pyflakes 등 설치
make verify       # 4단계 — ast.parse / import / pytest / pyflakes
```
끝에 **`Overall: PASS`** 나오면 OK.

실패 나면 출력 그대로 저한테(이 세션) 또는 새 세션에 공유.

---

## 4. SAM 배포 (첫 배포, 5-10분)

### 4-1. API Key 64자 생성 + 보관
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# 출력 예: zxvbnmasdfjkl... (64자 정도)
```
이 값을 **별도 안전한 곳에 저장** (1Password / Bitwarden / 메모 앱). 이걸 `<API_KEY>` 로 표시.

### 4-2. 빌드
```bash
sam build
```
끝에 `Build Succeeded` 확인.

### 4-3. 첫 배포 (대화형)
```bash
sam deploy --guided
```

대화형 프롬프트 답변:

| 질문 | 답 |
|---|---|
| Stack Name | `mcp-hub-dev` |
| AWS Region | `ap-northeast-2` |
| Parameter ApiKey | `<API_KEY>` (위에서 만든 거 붙여넣기) |
| Parameter Stage | `dev` |
| Parameter BedrockModel | `<OPUS_MODEL_ID>` (1-2에서 확인한 정확한 값) |
| Confirm changes before deploy | `y` |
| Allow SAM CLI IAM role creation | `y` |
| Disable rollback | `n` |
| McpHubFunction may not have authorization defined | `y` (인증은 코드 안 X-API-Key로 함) |
| Save arguments to configuration file | `y` |
| SAM configuration file | `samconfig.toml` (기본) |
| SAM configuration environment | `default` |

⏱️ CloudFormation이 9테이블 + Lambda + APIGW + IAM role 만드는 데 5-10분.

### 4-4. URL 확인
배포 끝나면 출력 마지막에:
```
Outputs
-----------------------------------------------------------
ApiEndpoint   https://abc123xyz.execute-api.ap-northeast-2.amazonaws.com/dev/mcp
```
이 URL을 **메모** — `<MCP_URL>`.

확인 안 보이면:
```bash
aws cloudformation describe-stacks --stack-name mcp-hub-dev \
  --query 'Stacks[0].Outputs' --region ap-northeast-2
```

---

## 5. 시드 입력 (30초)

```bash
export AWS_REGION=ap-northeast-2
export STAGE=dev
python scripts/seed_db.py
```

출력:
```
  mcp-hub-roles-dev: 5 items
  mcp-hub-mistakes-dev: 25 items
  mcp-hub-prompts-dev: 50 items
  mcp-hub-decisions-dev: 9 items

seeded 89 items across 4 tables.
```

---

## 6. 헬스체크 — tools/list 응답 20개 (30초)

```bash
URL="<MCP_URL>"
KEY="<API_KEY>"

curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools | length'
```
**출력: `20`** 나오면 OK.

다른 출력 나오면:
- `403` → API Key 불일치 (배포 시 입력값과 동일한지 확인)
- `404` → URL 끝의 `/mcp` 빠졌거나 path 다름
- `500` → CloudWatch Logs 확인: `sam logs -n McpHubFunction --stack-name mcp-hub-dev --tail`

---

## 7. claude.ai 커넥터 등록 (1분)

### 7-1. 데스크톱·웹
1. https://claude.ai 로그인
2. 좌하단 본인 계정 → **Settings**
3. **Connectors** 탭
4. **Add custom connector** 또는 **+ Add MCP server**
5. 입력:
   - **Name**: `mcp-hub`
   - **URL**: `<MCP_URL>`
   - **Authentication**: `API Key` (또는 `Custom Header`)
   - **Header Name**: `X-API-Key`
   - **Header Value**: `<API_KEY>`
6. **Save** → 자동 connect → 도구 목록 펼쳐 **20개** 보이면 OK

### 7-2. 모바일 (iOS / Android)
- 모바일 앱은 데스크톱에서 등록한 커넥터 자동 동기화 — 모바일에서 별도 설정 불필요
- 채팅창 좌하단 ⊕ → "Connectors" → mcp-hub 활성화 토글 ON

### 7-3. Claude Code 웹 (claude.ai/code)
- 같은 계정이면 자동 노출. 작업 시 `mcp__mcp-hub__*` 형태로 보임

### 7-4. Claude Code CLI (선택)
```bash
claude mcp add mcp-hub <MCP_URL> --header "X-API-Key: <API_KEY>"
```

---

## 8. 첫 호출 테스트 (1분)

claude.ai 채팅창에 입력:
```
mcp-hub의 list_roles 호출해서 5개 역할 보여줘
```

응답 안에 `planner` `designer` `architect` `coder` `reviewer` 5개가 색상·서브모드와 함께 나오면 **🎉 정상 연결**.

이어서:
```
resume_context 호출해줘 (project_id는 아직 없어, 일반 호출만)
```
이건 project_id 필요해서 NotFoundError 정상.

```
list_active_presets 호출
```
빈 배열 `[]` 나오면 정상 (아직 프로젝트 0개).

---

## 9. 첫 실제 프로젝트 — 워크플로우 한 바퀴 (1시간)

자기 다음 프로젝트 아이디어로 한 번 돌려봐서 게이트가 발동하는지 확인:

### 9-1. classify_project
```
"<프로젝트 한 줄 설명>" 으로 mcp-hub classify_project 호출해줘
```
→ recommended_roles + scores + draft preset 반환. 출력의 `project_id` 메모 → `<PID>`.

### 9-2. approve_assignment
```
project_id <PID> 로 approve_assignment 호출
```
→ status active + phase=planning 자동 시작.

### 9-3. start_session + planner 작업
```
<PID>, role=planner 로 start_session 호출
이어서 planner workflow requirements_정리 프롬프트 가져와서 요구사항 정리해줘
```

### 9-4. transition_phase("coding") — 게이트 발동 확인
중간 phase 다 거치고 (designing → architecting), 또는 바로 coding 시도:
```
transition_phase project_id=<PID>, new_phase=coding, reason="구현 시작"
```

✅ **게이트 정상**: 응답에 `phase: pending_premortem` + `premortem_report` (stories 3개 / warnings / assumption / revised_plan) + 보완할지 물어봄

❌ **게이트 미작동**: phase=coding 즉시 진입 — 코드 문제. CloudWatch 로그 확인.

### 9-5. apply_premortem_revision
```
mode=pass 로 apply_premortem_revision 호출 (또는 보완하고 싶으면 revise_all)
```
→ phase=coding 진입 → coder 작업 시작 가능.

---

## 10. QA_REPORT 적합 전환 (5분)

`QA_REPORT.md` §6 체크리스트의 ⏳ 8개 항목을 ✅로 갱신:

```bash
# QA_REPORT.md 열어서 §2-4 / §6 의 ⏳ → ✅ 수정
git add QA_REPORT.md
git commit -m "qa: mark deployment items ✅ — adoption complete"
git push
```

§1 판정도 "조건부 적합" → **"적합"** 으로 바꾸면 1.0 GA 완료.

---

## 11. 운영 전환 — prod 분리 (선택, 나중에)

dev에서 충분히 검증되면:
```bash
sam deploy --stack-name mcp-hub-prod \
  --parameter-overrides Stage=prod ApiKey=<NEW_KEY> BedrockModel=<OPUS_MODEL_ID>
```
- prod 별도 URL 발급
- prod API Key는 dev와 다른 거로
- claude.ai에 새 커넥터로 추가 등록 (이름 `mcp-hub-prod`)
- dev는 테스트용으로 유지

---

## 12. 막히는 지점 별 대처

| 증상 | 진단 | 대처 |
|---|---|---|
| `sam build` 실패 | Python 3.12 / pip 오류 | `python3.12 --version` 확인 |
| `sam deploy` IAM 권한 거부 | 0-1 권한 부족 | 권한 추가 또는 admin user로 |
| `Bedrock AccessDeniedException` | 모델 access 미활성 | 1-1 다시 |
| `ResourceNotFoundException model` | modelId 오타 | 1-2 명령으로 정확한 ID 재확인 후 `sam deploy --parameter-overrides BedrockModel=...` 재배포 |
| 시드 스크립트가 `STAGE` 못 읽음 | 환경변수 누락 | `export STAGE=dev` 후 재실행 |
| claude.ai 등록 후 도구 목록 비어있음 | URL 끝 `/mcp` 누락 | URL 확인 |
| 도구 호출 시 `403` | API Key 불일치 | 커넥터 설정의 헤더 값 재확인 |
| 도구 호출 시 `500` | Lambda 에러 | `sam logs -n McpHubFunction --stack-name mcp-hub-dev --tail` |

---

## 예상 총 소요 시간

| 단계 | 시간 |
|---|---|
| 0. 사전 확인 | 5분 |
| 1. Bedrock 활성화 | 3분 (+ Anthropic 승인 대기 0~1분) |
| 2-3. 클론 + 로컬 검증 | 4분 |
| 4. SAM 배포 | 5-10분 |
| 5-6. 시드 + 헬스체크 | 1분 |
| 7-8. claude.ai 등록 + 첫 호출 | 2분 |
| **첫 가동까지** | **약 25분** |
| 9. 첫 프로젝트 워크플로우 (선택) | 1시간 |
| 10. QA 갱신 | 5분 |
