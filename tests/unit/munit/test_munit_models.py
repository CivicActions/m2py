"""Unit tests for M-Unit models — round-trip serialization, status derivation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.functional.munit.lib.models import (
    BaselineData,
    FailureDetail,
    MUnitResult,
    PackageBaseline,
    TestRoutineConfig,
)


class TestFailureDetail:
    def test_chkeq_failure(self):
        fd = FailureDetail(
            entry_tag="T1",
            routine="%utt1",
            test_name="Test CHKEQ",
            message="Values differ",
            kind="failure",
            expected="hello",
            actual="world",
        )
        assert fd.kind == "failure"
        assert fd.expected == "hello"
        assert fd.actual == "world"

    def test_chktf_failure_no_expected_actual(self):
        fd = FailureDetail(
            entry_tag="T2",
            routine="%utt1",
            test_name="Test CHKTF",
            message="Expected TRUE but got FALSE",
            kind="failure",
        )
        assert fd.expected is None
        assert fd.actual is None

    def test_error_detail(self):
        fd = FailureDetail(
            entry_tag="T3",
            routine="%utt1",
            test_name="Test Error",
            message="150374082,Z,%utt1+5^%utt1",
            kind="error",
        )
        assert fd.kind == "error"


class TestMUnitResult:
    def test_round_trip(self):
        original = MUnitResult(
            routine="%utt1",
            package="MASH Utilities",
            total_tests=9,
            failures=1,
            errors=0,
            entry_tags=5,
            routines_ran=1,
            status="fail",
            failure_details=[
                FailureDetail(
                    entry_tag="T1",
                    routine="%utt1",
                    test_name="Test 1",
                    message="Expected TRUE",
                    kind="failure",
                )
            ],
            raw_output="some output",
            duration_seconds=1.5,
        )
        d = original.to_dict()
        restored = MUnitResult.from_dict(d)
        assert restored.routine == original.routine
        assert restored.package == original.package
        assert restored.total_tests == original.total_tests
        assert restored.failures == original.failures
        assert restored.errors == original.errors
        assert restored.status == original.status
        assert restored.duration_seconds == 1.5
        assert len(restored.failure_details) == 1
        assert restored.failure_details[0].entry_tag == "T1"
        assert restored.failure_details[0].kind == "failure"

    def test_round_trip_no_failures(self):
        original = MUnitResult(
            routine="MXMLBLD",
            package="M XML Parser",
            total_tests=13,
            failures=0,
            errors=0,
            status="pass",
        )
        d = original.to_dict()
        restored = MUnitResult.from_dict(d)
        assert restored.status == "pass"
        assert restored.failure_details == []

    def test_json_serializable(self):
        result = MUnitResult(
            routine="test",
            package="pkg",
            total_tests=5,
            status="pass",
            error_message=None,
        )
        # to_dict must produce JSON-serializable output
        s = json.dumps(result.to_dict())
        assert '"total_tests": 5' in s
        assert '"error_message": null' in s

    def test_from_dict_with_chkeq_details(self):
        data = {
            "routine": "%utt1",
            "package": "MASH Utilities",
            "total_tests": 1,
            "failures": 1,
            "errors": 0,
            "entry_tags": 1,
            "routines_ran": 1,
            "status": "fail",
            "failure_details": [
                {
                    "entry_tag": "T1",
                    "routine": "%utt1",
                    "test_name": "Test 1",
                    "message": "Values differ",
                    "kind": "failure",
                    "expected": "hello",
                    "actual": "world",
                }
            ],
            "raw_output": "",
            "duration_seconds": None,
            "error_message": None,
        }
        result = MUnitResult.from_dict(data)
        assert result.failure_details[0].expected == "hello"
        assert result.failure_details[0].actual == "world"


class TestBaselineData:
    def test_json_round_trip(self):
        baseline = BaselineData(
            version="1.0",
            captured_at="2025-07-22T12:00:00Z",
            docker_image="worldvista/osehravista:latest",
        )
        baseline.packages["MASH Utilities"] = PackageBaseline(
            package_name="MASH Utilities",
            test_list_path="",
            routines={
                "%utt1": MUnitResult(
                    routine="%utt1",
                    package="MASH Utilities",
                    total_tests=9,
                    failures=0,
                    errors=0,
                    status="pass",
                ),
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "baseline.json"
            baseline.to_json(path)

            # File should exist
            assert path.exists()

            # JSON should be valid
            with open(path) as f:
                raw = json.load(f)
            assert raw["version"] == "1.0"
            assert "%utt1" in raw["packages"]["MASH Utilities"]["routines"]

            # Round-trip
            restored = BaselineData.from_json(path)
            assert restored.version == "1.0"
            assert restored.captured_at == "2025-07-22T12:00:00Z"
            assert "%utt1" in restored.packages["MASH Utilities"].routines
            r = restored.packages["MASH Utilities"].routines["%utt1"]
            assert r.total_tests == 9
            assert r.status == "pass"

    def test_empty_baseline(self):
        baseline = BaselineData()
        d = baseline.to_dict()
        assert d["packages"] == {}

        restored = BaselineData.from_dict(d)
        assert restored.packages == {}

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "deep" / "nested" / "baseline.json"
            baseline = BaselineData()
            baseline.to_json(path)
            assert path.exists()


class TestTestRoutineConfig:
    def test_basic_fields(self):
        config = TestRoutineConfig(
            routine_name="MXMLBLD",
            package_name="M XML Parser",
            invocation="D TEST^MXMLBLD",
            source_path="/path/to/MXMLBLD.m",
            tier=2,
        )
        assert config.routine_name == "MXMLBLD"
        assert config.tier == 2
        assert config.dependencies == []

    def test_with_dependencies(self):
        config = TestRoutineConfig(
            routine_name="ZZRGUT",
            package_name="Problem List",
            invocation="D ^ZZRGUT",
            source_path="/path/to/ZZRGUT.m",
            tier=4,
            dependencies=["GMPLAPI2", "GMPLAPI3"],
        )
        assert len(config.dependencies) == 2
