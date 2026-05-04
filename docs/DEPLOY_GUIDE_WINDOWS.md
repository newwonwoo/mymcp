# Windows / PowerShell 배포 가이드

> bash 버전은 [`DEPLOY_GUIDE.md`](./DEPLOY_GUIDE.md). 이 문서는 PowerShell 환경(Windows 10/11) 전용.
> Windows PowerShell 5.1 / PowerShell 7 둘 다 동작.

## bash → PowerShell 핵심 변환

| bash | PowerShell |
|---|---|
| `export X=Y` | `$env:X = "Y"` |
| `"$URL"` | `$URL` 또는 `"$URL"` |
| `curl` | **`curl.exe`** (Windows 10+ 내장) 또는 `Invoke-RestMethod` |
| `jq '.x'` | `ConvertFrom-Json` 후 `.x` |
| `&&` | `;` (PS 5.1) / `&&` (PS 7+) |
| `python3` | `python` |
| `make` | Makefile 명령을 직접 풀어 실행 |
| `brew install` | `winget install` |
| heredoc `<<EOF` | here-string `@" ... "@` |

---

# 5블록 (총 ~22분)

## A. AWS 준비 (5분)

### A-1. 도구 설치 (없으면)
```powershell
winget install Amazon.AWSCLI
winget install Amazon.SAM-CLI
winget install Python.Python.3.12
winget install Git.Git
```
설치 후 PowerShell **새 창** 열기 (PATH 갱신).

### A-2. 자격증명 확인
```powershell
aws sts get-caller-identity
```
없으면:
```powershell
aws configure
# AWS Access Key ID: <키>
# AWS Secret Access Key: <시크릿>
# Default region: ap-northeast-2
# Default output format: json
```

### A-3. Bedrock Opus 활성화 (Console — OS 무관)
1. https://console.aws.amazon.com → 우상단 리전 **Asia Pacific (Seoul) ap-northeast-2**
2. Bedrock → Model access → Modify → **Anthropic Claude Opus 4.7** → Submit
3. status `Access granted` (1-3분)

### A-4. modelId 메모
```powershell
aws bedrock list-foundation-models `
  --region ap-northeast-2 `
  --query "modelSummaries[?contains(modelId, 'opus')].[modelId]" `
  --output table
```
출력 예: `anthropic.claude-opus-4-7-20260315-v1:0` → 메모 `<OPUS_MODEL_ID>`

> PowerShell 멀티라인: 줄 끝에 backtick `` ` `` (한 줄로 써도 됨)

---

## B. 코드 검증 (4분)

### B-1. clone
```powershell
git clone https://github.com/newwonwoo/mymcp.git
cd mymcp
git checkout claude/review-design-docs-NwkJR
```

### B-2. 의존성 + 4단계 검증 (make 없이)
```powershell
pip install -r requirements-dev.txt
python scripts/verify_code.py src/
```
✅ 마지막 줄 `=== Overall: PASS ===`
✅ pytest: `21 passed`

---

## C. AWS 배포 (10분)

### C-1. API Key 64자 생성 + 안전한 곳에 저장
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
출력 한 줄을 1Password / Bitwarden / Notion 등에 저장 → `<API_KEY>`

### C-2. 빌드 + 배포
```powershell
sam build
sam deploy --guided
```

대화형 답변:

| 질문 | 답 |
|---|---|
| Stack Name | **mcp-hub-dev** |
| AWS Region | **ap-northeast-2** |
| Parameter ApiKey | `<API_KEY>` 붙여넣기 |
| Parameter Stage | **dev** |
| Parameter BedrockModel | `<OPUS_MODEL_ID>` (A-4의 정확한 값) |
| Confirm changes before deploy | **y** |
| Allow SAM CLI IAM role creation | **y** |
| Disable rollback | **n** |
| McpHubFunction may not have authorization defined | **y** |
| Save arguments to configuration file | **y** |
| SAM configuration file | (Enter — `samconfig.toml`) |
| SAM configuration environment | (Enter — `default`) |

⏱️ CloudFormation이 9 DynamoDB + Lambda + APIGW + IAM role 5-10분 만듦.

### C-3. URL 추출
배포 끝 출력의 `ApiEndpoint` 값을 메모 → `<MCP_URL>`

안 보이면:
```powershell
aws cloudformation describe-stacks `
  --stack-name mcp-hub-dev `
  --region ap-northeast-2 `
  --query "Stacks[0].Outputs" --output table
```

---

## D. 시드 + 헬스체크 (1분)

### D-1. 시드 89개 입력
```powershell
$env:AWS_REGION = "ap-northeast-2"
$env:STAGE = "dev"
python scripts/seed_db.py
```
✅ 출력:
```
  mcp-hub-roles-dev: 5 items
  mcp-hub-mistakes-dev: 25 items
  mcp-hub-prompts-dev: 50 items
  mcp-hub-decisions-dev: 9 items

seeded 89 items across 4 tables.
```

### D-2. 헬스체크 — PowerShell native (jq 없이)
```powershell
$URL = "<MCP_URL>"   # C-3의 값
$KEY = "<API_KEY>"   # C-1의 값

$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/list"
} | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = $KEY
}

$response = Invoke-RestMethod -Uri $URL -Method Post -Body $body -Headers $headers
$response.result.tools.Count
```
✅ 출력: **20** (또는 21 — `revoke_decision` 포함 시)

❌ 다른 출력:
- `401 unauthorized` → API Key 불일치 (`$KEY` 값 vs 배포 시 입력값)
- `404` → URL 끝 `/mcp` 누락
- `500` → Lambda 로그 확인:
  ```powershell
  sam logs -n McpHubFunction --stack-name mcp-hub-dev --tail
  ```

### D-3. (대안) curl.exe
```powershell
curl.exe -s -X POST $URL `
  -H "Content-Type: application/json" `
  -H "X-API-Key: $KEY" `
  -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}'
```
> Windows curl.exe는 따옴표 escape에 백슬래시 필요. **`Invoke-RestMethod` 권장**.

---

## E. claude.ai 등록 + 첫 호출 (2분)

OS 무관 — 브라우저 + Claude 앱.

### E-1. 데스크톱 등록 (모바일은 자동 동기화)
1. https://claude.ai 로그인
2. 좌하단 본인 계정 → **Settings**
3. **Connectors** 탭
4. **+ Add custom connector** 또는 **Add MCP server**
5. 입력:

| 필드 | 값 |
|---|---|
| Name | `mcp-hub` |
| URL | `<MCP_URL>` |
| Authentication | API Key (또는 Custom Header) |
| Header Name | `X-API-Key` |
| Header Value | `<API_KEY>` |

6. **Save** → 자동 connect → 도구 **20-21개** 보이면 OK

### E-2. 모바일 (등록 후)
- 데스크톱 등록 자동 동기화
- 채팅창 좌하단 ⊕ → "Connectors" → mcp-hub 토글 ON

### E-3. 첫 호출 — 시동
claude.ai 채팅창에:
```
mcp-hub의 list_roles 호출해서 5개 역할 보여줘
```
✅ `planner` `designer` `architect` `coder` `reviewer` 5개 응답 = **🎉 첫 가동 완료**

---

## PowerShell 특이 주의

### 실행 정책 막힘 (스크립트 실행 거부)
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### PATH 안 잡힘 (winget 설치 직후)
- PowerShell **새 창** 열기
- 또는: `$env:Path += ";C:\Program Files\Amazon\AWSCLIV2"` 등 수동 추가

### 한글 깨짐 (출력에서)
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

### PowerShell 7 권장 — `&&` 체이닝 + 더 빠름
```powershell
winget install Microsoft.PowerShell
```
설치 후 `pwsh` 명령으로 진입.

### Python `pip` 권한 오류
```powershell
pip install --user -r requirements-dev.txt
```

### `python` vs `python3`
- Windows는 보통 `python`
- 둘 다 안 되면 `py -3` 또는 `py -3.12`

---

## 변수 메모 템플릿 (작업 시작 시 메모장에 박아두기)

```
<OPUS_MODEL_ID> = anthropic.claude-opus-4-7-...
<API_KEY>       = <python -c secrets 출력값>
<MCP_URL>       = https://....execute-api.ap-northeast-2.amazonaws.com/dev/mcp
```

---

## 막히면

- 명령어 출력 그대로 다음 세션에 던지면 진단 가능
- AWS 권한 부족이면 IAM에 다음 추가:
  - `cloudformation:*` `iam:*` `lambda:*` `apigateway:*` `dynamodb:*`
  - `bedrock:InvokeModel` `bedrock:ListFoundationModels` `s3:*`
- 수정 후 재배포 (`samconfig.toml` 저장돼있어 한 줄):
  ```powershell
  sam build; sam deploy
  ```
  (PS 7+이면 `sam build && sam deploy`)

---

## 예상 총 소요 시간

| 단계 | 시간 |
|---|---|
| A. AWS 준비 | 5분 |
| B. 코드 검증 | 4분 |
| C. SAM 배포 | 10분 |
| D. 시드 + 헬스체크 | 1분 |
| E. 등록 + 첫 호출 | 2분 |
| **첫 가동까지** | **~22분** |

지금 PowerShell 켜고 **A-1**부터.
