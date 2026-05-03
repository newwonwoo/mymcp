"""API Key 검증. X-API-Key 헤더만 허용 (1인용 단일 키)."""
import hmac

from src.config import get_settings


def verify_api_key(provided: str | None) -> bool:
    """헤더 값이 환경변수의 API_KEY와 일치하면 True.

    상수시간 비교(`hmac.compare_digest`) 사용 — 타이밍 어택 방지.
    """
    expected = get_settings().api_key
    if not expected or not provided:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))
