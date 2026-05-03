"""DynamoDB resource 싱글톤. boto3 세션을 모듈 레벨에 캐시.

테스트에서 moto로 가짜 DynamoDB를 띄울 때도 같은 함수 통해 접근하도록 통일.
"""
import boto3

from src.config import get_settings

_resource = None


def get_dynamodb():
    global _resource
    if _resource is None:
        _resource = boto3.resource("dynamodb", region_name=get_settings().region)
    return _resource


def get_table(name: str):
    return get_dynamodb().Table(name)


def reset_for_tests() -> None:
    """moto fixture에서 boto3 세션을 새로 잡을 때 호출."""
    global _resource
    _resource = None
