"""FastMCP 서버 진입점. Lambda Web Adapter가 HTTP 요청을 이 ASGI 앱으로 프록시.

Phase 1: FastMCP 인스턴스만 노출. tool 등록은 Phase 2에서.
Phase 2부터는 src.tools.* 가 import 시 @mcp.tool() 데코레이터로 자동 등록된다.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="mcp-hub",
    instructions=(
        "개인용 역할 조율 MCP 허브 (v2.3). "
        "새 세션 시작 시 resume_context(project_id) 먼저 호출. "
        "작업 시작 전 query_mistakes(role=...) 호출 권장. "
        "비활성 역할 prompt 호출 시 unlock_role 먼저 필요. "
        "코딩 단계 진입 시 실패스토리 자동 트리거(transition_phase('coding'))."
    ),
)


def _register_tools() -> None:
    """src.tools 패키지의 모든 모듈을 import해서 @mcp.tool() 등록을 트리거."""
    import importlib

    for name in (
        "roles",
        "prompts",
        "mistakes",
        "handoffs",
        "sessions",
        "phases",
        "presets",
        "projects",
        "premortem",
        "decisions",
    ):
        importlib.import_module(f"src.tools.{name}")


_register_tools()


# ── X-API-Key 인증 미들웨어 ────────────────────────────────────────────
# claude.ai 커넥터 측에서도 헤더를 보내지만, 서버에서도 강제 검증해야
# 키 모르는 직접 호출(curl 등)을 차단할 수 있다.
from starlette.responses import JSONResponse  # noqa: E402

from src.lib.auth import verify_api_key  # noqa: E402


async def _api_key_middleware(scope, receive, send):
    """ASGI 미들웨어. CORS preflight(OPTIONS)와 헬스 경로는 통과."""
    if scope["type"] != "http":
        await _inner_app(scope, receive, send)
        return
    method = scope.get("method", "")
    path = scope.get("path", "")
    if method == "OPTIONS" or path in ("/health", "/"):
        await _inner_app(scope, receive, send)
        return

    headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
    provided = headers.get("x-api-key") or headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not verify_api_key(provided):
        response = JSONResponse(
            {"error": "unauthorized", "message": "Invalid or missing X-API-Key"},
            status_code=401,
        )
        await response(scope, receive, send)
        return
    await _inner_app(scope, receive, send)


# 내부 앱(FastMCP의 streamable HTTP) — 미들웨어가 통과시킨 요청만 도달
_inner_app = mcp.streamable_http_app()
app = _api_key_middleware
