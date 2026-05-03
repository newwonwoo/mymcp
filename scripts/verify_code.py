"""코드 검증 4단계 자동화.

조정승 님 원칙: syntax check만으로 NameError 못 잡음 → 4단계 모두 통과해야 함.

    python scripts/verify_code.py [target_dir]

target_dir 기본값은 src/.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.lib.verify import (  # noqa: E402
    module_name_from_path,
    stage_ast_parse,
    stage_import,
    stage_pyflakes,
)


def run(target_dir: str = "src/") -> int:
    target = REPO_ROOT / target_dir
    py_files = sorted(p for p in target.rglob("*.py") if "__pycache__" not in p.parts)

    print(f"=== Stage 1: ast.parse ({len(py_files)} files) ===")
    ast_pass = True
    for py in py_files:
        ok, msg = stage_ast_parse(py)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {py.relative_to(REPO_ROOT)}: {msg}")
        ast_pass &= ok

    print("\n=== Stage 2: import validation ===")
    import_pass = True
    for py in py_files:
        if py.name == "run.sh":
            continue
        mod = module_name_from_path(py, REPO_ROOT)
        if not mod:
            continue
        ok, msg = stage_import(mod)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {mod}: {msg}")
        import_pass &= ok

    print("\n=== Stage 3: mock execution (pytest + moto) ===")
    import subprocess

    pytest_result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    mock_pass = pytest_result.returncode == 0
    print(f"  [{'PASS' if mock_pass else 'FAIL'}]")
    print(pytest_result.stdout.strip().splitlines()[-1] if pytest_result.stdout.strip() else "")
    if not mock_pass:
        print(pytest_result.stdout)
        print(pytest_result.stderr)

    print("\n=== Stage 4: pyflakes (undefined vars / unused imports) ===")
    grep_ok, grep_msg = stage_pyflakes(target_dir)
    print(f"  [{'PASS' if grep_ok else 'FAIL'}] {grep_msg}")

    overall = ast_pass and import_pass and mock_pass and grep_ok
    print("\n=== Overall: " + ("PASS" if overall else "FAIL") + " ===")
    return 0 if overall else 1


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "src/"
    raise SystemExit(run(target))
