"""Tests for JOB command parsing (§8.2.10).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.10
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for JOB command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestJobCommandParsing:
    """Parser-level tests for JOB command (§8.2.10)."""

    def test_job_basic(self, command_metamodel):
        """JOB ROUTINE parses correctly (§8.2.10)."""
        model = command_metamodel.model_from_str("J ^ROUTINE", "JobCommand")
        assert len(model.targets) == 1
        assert model.targets[0].label.routine == "ROUTINE"

    def test_job_with_label(self, command_metamodel):
        """JOB LABEL^ROUTINE parses correctly (§8.2.10)."""
        model = command_metamodel.model_from_str("JOB LABEL^ROUTINE", "JobCommand")
        t = model.targets[0]
        assert t.label.label == "LABEL"
        assert t.label.routine == "ROUTINE"

    def test_job_with_arguments(self, command_metamodel):
        """JOB LABEL(args) parses correctly (§8.2.10)."""
        model = command_metamodel.model_from_str("J LABEL^ROUTINE(A,B)", "JobCommand")
        t = model.targets[0]
        assert t.label.label == "LABEL"
        assert t.label.routine == "ROUTINE"
        assert t.args is not None

    def test_job_with_timeout(self, command_metamodel):
        """JOB ROUTINE::timeout parses correctly (§8.2.10)."""
        model = command_metamodel.model_from_str("J ^ROUTINE::5", "JobCommand")
        t = model.targets[0]
        assert t.label.routine == "ROUTINE"
        assert t.timeout is not None

    def test_job_with_process_params(self, command_metamodel):
        """JOB ROUTINE:(params):timeout parses correctly (§8.2.10)."""
        model = command_metamodel.model_from_str("J ^ROUTINE:(params):10", "JobCommand")
        t = model.targets[0]
        assert t.label.routine == "ROUTINE"
        assert t.timeout is not None
