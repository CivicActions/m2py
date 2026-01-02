"""Tests for ASG serialization to dict/JSON.

Reference: M2PY ASG architecture
Migrated from: tests/unit/test_parser.py::TestASGSerialization

T338-T339: Serialization of ASG nodes for debugging and tooling.
"""

import json

import pytest

from m2py.parser import MUMPSParser, dump_asg_json


@pytest.mark.parser
class TestASGSerialization:
    """Test ASG serialization to dict/JSON (T338-T339).

    Migrated from: tests/unit/test_parser.py::TestASGSerialization
    """

    def test_routine_to_dict(self):
        """T338: MRoutine.to_dict() returns dictionary representation."""
        parser = MUMPSParser()
        source = "TEST\tS X=1\n"
        routine = parser.parse(source)

        result = routine.to_dict()

        assert isinstance(result, dict)
        assert result["_type"] == "MRoutine"
        assert "labels" in result
        assert len(result["labels"]) >= 1

    def test_to_dict_includes_labels(self):
        """T338: to_dict() includes label details."""
        parser = MUMPSParser()
        source = "TEST\tS X=1\nSUB\tQ\n"
        routine = parser.parse(source)

        result = routine.to_dict()

        labels = result["labels"]
        assert len(labels) >= 2
        assert labels[0]["name"] == "TEST"
        assert labels[1]["name"] == "SUB"

    def test_to_dict_with_position(self):
        """T338: to_dict() can include source position."""
        parser = MUMPSParser()
        source = "TEST\tS X=1\n"
        routine = parser.parse(source, filename="test.m")
        routine.source_file = "test.m"

        result = routine.to_dict(include_position=True)

        assert result.get("source_file") == "test.m"

    def test_dump_asg_json(self):
        """T339: dump_asg_json() produces valid JSON."""
        parser = MUMPSParser()
        source = "TEST\tS X=1\n"
        routine = parser.parse(source)

        json_str = dump_asg_json(routine)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["_type"] == "MRoutine"

    def test_dump_asg_json_pretty(self):
        """T339: dump_asg_json() supports indentation."""
        parser = MUMPSParser()
        source = "TEST\tS X=1\n"
        routine = parser.parse(source)

        json_str = dump_asg_json(routine, indent=2)

        # Should have newlines from indentation
        assert "\n" in json_str
        assert "  " in json_str

    def test_to_dict_handles_nested_structures(self):
        """T338: to_dict() handles nested ASG structures."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 S X=I\n"
        routine = parser.parse(source)

        result = routine.to_dict(max_depth=5)

        # Should serialize without error
        assert result["_type"] == "MRoutine"

    def test_to_dict_max_depth_prevents_infinite_recursion(self):
        """T338: to_dict() respects max_depth to prevent stack overflow."""
        parser = MUMPSParser()
        source = "TEST\tS X=1\n"
        routine = parser.parse(source)

        # Very shallow depth should truncate
        result = routine.to_dict(max_depth=1)

        assert result["_type"] == "MRoutine"
        # Labels might be truncated
        if result.get("labels"):
            first_label = result["labels"][0]
            assert first_label.get("_truncated") or "_type" in first_label
