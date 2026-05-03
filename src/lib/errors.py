"""커스텀 예외. tool 호출 시 의미 있는 에러를 raise한다."""


class McpHubError(Exception):
    """모든 MCP 허브 예외의 베이스."""


class RoleNotActiveError(McpHubError):
    """비활성 역할 prompt 호출 시 발생. unlock_role 안내 문구 포함."""


class NotFoundError(McpHubError):
    """존재하지 않는 리소스 조회 시."""


class ValidationError(McpHubError):
    """입력 검증 실패."""


class AuthError(McpHubError):
    """API Key 누락 또는 불일치."""
