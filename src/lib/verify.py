"""코드 검증 4단계 헬퍼.

ast.parse → import → mock 호출 → grep(pyflakes).
scripts/verify_code.py가 디렉토리 단위 실행에 이 모듈을 사용한다.
"""
import ast
import importlib
import subprocess
from pathlib import Path


def stage_ast_parse(py_file: Path) -> tuple[bool, str]:
    """1단계 — 구문 파싱."""
    try:
        ast.parse(py_file.read_text(encoding="utf-8"))
        return True, "PASS"
    except SyntaxError as exc:
        return False, f"FAIL: {exc}"


def stage_import(module_name: str) -> tuple[bool, str]:
    """2단계 — 실제 import 가능 여부."""
    try:
        importlib.import_module(module_name)
        return True, "PASS"
    except Exception as exc:  # noqa: BLE001 — 검증 단계라 모든 예외 캡처
        return False, f"FAIL: {type(exc).__name__}: {exc}"


def stage_pyflakes(target_dir: str) -> tuple[bool, str]:
    """4단계 — 정의되지 않은 변수, 미사용 import 등 grep."""
    result = subprocess.run(
        ["pyflakes", target_dir],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and not result.stdout.strip():
        return True, "PASS"
    return False, f"FAIL:\n{result.stdout}{result.stderr}"


def module_name_from_path(py_file: Path, repo_root: Path) -> str:
    """`src/tools/roles.py` → `src.tools.roles`."""
    rel = py_file.relative_to(repo_root).with_suffix("")
    parts = rel.parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)
