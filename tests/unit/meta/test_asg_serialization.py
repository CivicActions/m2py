"""Tests for ASG serialization.

Verifies JSON serialization of ASG nodes for debugging and persistence.

MUMPS 1995 Reference: §6.1 Routine Structure
"""

import json


from m2py.parser import MUMPSParser, dump_asg_json


class TestASGSerialization:
    """Test ASG JSON serialization functionality."""

    def test_dump_asg_json_returns_string(self):
        """dump_asg_json should return a JSON string."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tS X=1\n")
        json_str = dump_asg_json(routine)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_dump_asg_json_is_valid_json(self):
        """dump_asg_json output should be valid JSON."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tS X=1 W X Q\n")
        json_str = dump_asg_json(routine)
        # Should parse without error
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_dump_asg_json_includes_routine_name(self):
        """JSON output should include routine name."""
        parser = MUMPSParser()
        routine = parser.parse("MAIN\tQ\n", filename="TESTRTN.m")
        routine.name = "TESTRTN"
        json_str = dump_asg_json(routine)
        parsed = json.loads(json_str)
        assert parsed.get("name") == "TESTRTN"

    def test_dump_asg_json_includes_labels(self):
        """JSON output should include labels array."""
        parser = MUMPSParser()
        routine = parser.parse("FIRST\n\tQ\nSECOND\n\tQ\n")
        json_str = dump_asg_json(routine)
        parsed = json.loads(json_str)
        labels = parsed.get("labels", [])
        assert len(labels) == 2

    def test_dump_asg_json_includes_statements(self):
        """JSON output should include statement information."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tS X=1 W X\n")
        json_str = dump_asg_json(routine)
        parsed = json.loads(json_str)
        # Labels should have body with statements
        labels = parsed.get("labels", [])
        assert len(labels) > 0
        body = labels[0].get("body", {})
        statements = body.get("statements", [])
        assert len(statements) >= 2

    def test_dump_asg_json_indent(self):
        """dump_asg_json should produce indented output by default."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tS X=1\n")
        json_str = dump_asg_json(routine)
        # Indented JSON has newlines
        assert "\n" in json_str
