"""AWS Bedrock Claude 3.5 Sonnet 호출 래퍼.

`classify_project`, `run_failure_story` 등이 사용.
응답이 ```json 코드펜스를 포함할 수 있으므로 호출자에서 한번 더 정제.
"""
import json

import boto3

from src.config import get_settings


_client = None


def get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=get_settings().region)
    return _client


def reset_for_tests() -> None:
    global _client
    _client = None


def invoke_claude(prompt: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
    """Claude 3.5 Sonnet 단일 메시지 호출. 텍스트 본문만 반환."""
    settings = get_settings()
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = get_client().invoke_model(
        modelId=settings.bedrock_model,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    return payload["content"][0]["text"]
