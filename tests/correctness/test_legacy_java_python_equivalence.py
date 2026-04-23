import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.correctness


def _load_shared_vectors() -> list[dict]:
    vectors_path = _repo_root() / "fixtures" / "vectors" / "legacy_calculator_vectors.json"
    with open(vectors_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, list)
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


SHARED_VECTORS = _load_shared_vectors()


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
    java_vector_runner = _read_fixture("fixtures/java/simple/LegacyCalculatorVectorRunner.java")
    java_path = workdir / "LegacyCalculator.java"
    java_runner_path = workdir / "LegacyCalculatorVectorRunner.java"
    java_path.write_text(java_source, encoding="utf-8")
    java_runner_path.write_text(java_vector_runner, encoding="utf-8")

    compile_proc = subprocess.run(
        ["javac", str(java_path), str(java_runner_path)],
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


@pytest.fixture(scope="module")
def java_vector_batch_runner(tmp_path_factory):
    if not shutil.which("javac") or not shutil.which("java"):
        pytest.skip("Java toolchain not available (requires javac and java)")

    workdir = tmp_path_factory.mktemp("legacy_java_vector_batch")
    java_source = _read_fixture("fixtures/java/simple/LegacyCalculator.java")
    java_vector_runner = _read_fixture("fixtures/java/simple/LegacyCalculatorVectorRunner.java")
    java_path = workdir / "LegacyCalculator.java"
    java_runner_path = workdir / "LegacyCalculatorVectorRunner.java"
    java_path.write_text(java_source, encoding="utf-8")
    java_runner_path.write_text(java_vector_runner, encoding="utf-8")

    compile_proc = subprocess.run(
        ["javac", str(java_path), str(java_runner_path)],
        cwd=workdir,
        check=False,
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        pytest.fail(f"Failed compiling Java vector runner fixture: {compile_proc.stderr}")

    def _run(vectors_path: Path) -> dict[str, tuple[int, int]]:
        run_proc = subprocess.run(
            ["java", "-cp", str(workdir), "LegacyCalculatorVectorRunner", str(vectors_path)],
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        if run_proc.returncode != 0:
            pytest.fail(f"Legacy Java vector batch execution failed: {run_proc.stderr}")

        outputs: dict[str, tuple[int, int]] = {}
        for line in run_proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            case_id, actual, expected = line.split(",", 2)
            outputs[case_id] = (int(actual), int(expected))
        return outputs

    return _run


def test_legacy_java_fixture_expected_values(java_legacy_runner):
    for vector in SHARED_VECTORS:
        base = int(vector["input"]["base"])
        multiplier = int(vector["input"]["multiplier"])
        premium = bool(vector["input"]["premium"])
        expected = int(vector["expected"])
        assert java_legacy_runner(base, multiplier, premium) == expected


def test_python_fixture_expected_values():
    calculate_score = _load_python_calculator()
    for vector in SHARED_VECTORS:
        base = int(vector["input"]["base"])
        multiplier = int(vector["input"]["multiplier"])
        premium = bool(vector["input"]["premium"])
        expected = int(vector["expected"])
        assert calculate_score(base, multiplier, premium) == expected


def test_python_matches_legacy_java_outputs(java_legacy_runner):
    calculate_score = _load_python_calculator()
    for vector in SHARED_VECTORS:
        base = int(vector["input"]["base"])
        multiplier = int(vector["input"]["multiplier"])
        premium = bool(vector["input"]["premium"])
        legacy_output = java_legacy_runner(base, multiplier, premium)
        python_output = calculate_score(base, multiplier, premium)
        assert python_output == legacy_output


def test_java_batch_runner_reads_shared_json_vectors(java_vector_batch_runner):
    vectors_path = _repo_root() / "fixtures" / "vectors" / "legacy_calculator_vectors.json"
    outputs = java_vector_batch_runner(vectors_path)
    assert outputs, "Expected java batch runner to produce vector outputs"
    assert len(outputs) == len(SHARED_VECTORS)
    for vector in SHARED_VECTORS:
        case_id = str(vector["id"])
        expected = int(vector["expected"])
        assert case_id in outputs
        actual, runner_expected = outputs[case_id]
        assert runner_expected == expected
        assert actual == expected