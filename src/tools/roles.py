"""역할 조회 tool. (2개)

Trigger phrases (한국어): "역할 목록", "역할 보여줘", "어떤 역할 있어"
Trigger phrases (English): "list roles", "show roles", "what roles"
"""
from src.db.repositories.roles import RolesRepository
from src.lib.errors import NotFoundError
from src.server import mcp


@mcp.tool()
def list_roles() -> list[dict]:
    """모든 역할(5개) 메타데이터 반환.

    Trigger phrases (한국어): "역할 목록", "역할 다 보여줘"
    새 프로젝트 시작 시 가장 먼저 호출하여 사용 가능한 역할을 파악.
    """
    return RolesRepository().list_all()


@mcp.tool()
def get_role(role_name: str) -> dict:
    """특정 역할 상세 정보(서브모드, 색상 포함) 반환.

    Trigger phrases (한국어): "{역할} 역할 알려줘", "{역할} 정보"
    role_name: planner / designer / architect / coder / reviewer 중 하나.
    """
    role = RolesRepository().get(role_name)
    if not role:
        raise NotFoundError(
            f"Unknown role: {role_name}. "
            "Available: planner, designer, architect, coder, reviewer"
        )
    return role
