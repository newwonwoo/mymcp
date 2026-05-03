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

# Streamable HTTP transport — claude.ai/Claude Code 웹 커넥터 호환
app = mcp.streamable_http_app()
