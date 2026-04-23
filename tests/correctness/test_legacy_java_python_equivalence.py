import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.correctness


TEST_VECTORS: list[tuple[int, int, bool, int]] = [
    (5, 10, False, 50),
    (5, 10, True, 75),
    (8, 12, True, 100),
    (1, 1, False, 1),
    (-4, 10, False, 0),
    (0, 999, True, 25),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_fixture(relative_path: str) -> str:
    return (_repo_root() / relative_path).read_text(encoding="utf-8")


def _load_python_calculator():
    module_path = _repo_root() / "fixtures" / "expected_python" / "legacy_calculator.py"
    spec = importlib.util.spec_from_file_location("legacy_calculator", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.calculate_score


@pytest.fixture(scope="module")
def java_legacy_runner(tmp_path_factory):
    if not shutil.which("javac") or not shutil.which("java"):
        pytest.skip("Java toolchain not available (requires javac and java)")

    workdir = tmp_path_factory.mktemp("legacy_java_calc")
    java_source = _read_fixture("fixtures/java/simple/LegacyCalculator.java")
    java_path = workdir / "LegacyCalculator.java"
    java_path.write_text(java_source, encoding="utf-8")

    compile_proc = subprocess.run(
        ["javac", str(java_path)],
        cwd=workdir,
        check=False,
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        pytest.fail(f"Failed compiling legacy Java fixture: {compile_proc.stderr}")

    def _run(base: int, multiplier: int, premium: bool) -> int:
        run_proc = subprocess.run(
            ["java", "-cp", str(workdir), "LegacyCalculator", str(base), str(multiplier), str(premium).lower()],
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        if run_proc.returncode != 0:
            pytest.fail(f"Legacy Java fixture execution failed: {run_proc.stderr}")
        return int(run_proc.stdout.strip())

    return _run


def test_legacy_java_fixture_expected_values(java_legacy_runner):
    for base, multiplier, premium, expected in TEST_VECTORS:
        assert java_legacy_runner(base, multiplier, premium) == expected


def test_python_fixture_expected_values():
    calculate_score = _load_python_calculator()
    for base, multiplier, premium, expected in TEST_VECTORS:
        assert calculate_score(base, multiplier, premium) == expected


def test_python_matches_legacy_java_outputs(java_legacy_runner):
    calculate_score = _load_python_calculator()
    for base, multiplier, premium, _expected in TEST_VECTORS:
        legacy_output = java_legacy_runner(base, multiplier, premium)
        python_output = calculate_score(base, multiplier, premium)
        assert python_output == legacy_output