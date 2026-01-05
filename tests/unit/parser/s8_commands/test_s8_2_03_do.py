"""Tests for DO command parsing (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar metamodel with custom classes."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestDoCommandParsing:
    """Parser-level tests for DO command (§8.2.3)."""

    def test_do_with_label(self, command_metamodel):
        """D LABEL parses DO to label (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL", "DoCommand")
        assert len(model.targets) == 1

    def test_do_external_routine(self, command_metamodel):
        """D ^ROUTINE parses DO to external routine (§8.2.3)."""
        model = command_metamodel.model_from_str("D ^ROUTINE", "DoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_do_with_arguments(self, command_metamodel):
        """D LABEL(A,B) parses DO with arguments (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL(A,B)", "DoCommand")
        target = model.targets[0]
        assert target.args is not None

    def test_do_with_offset(self, command_metamodel):
        """D 1+^V1A^V1CALLE parses DO with computed offset (§8.2.3)."""
        model = command_metamodel.model_from_str("D 1+^V1A^V1CALLE", "DoCommand")
        target = model.targets[0]
        assert target.label.label == "1"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"

    def test_do_argumentless_block(self, command_metamodel):
        """D parses argumentless DO (block start) (§8.2.3)."""
        model = command_metamodel.model_from_str("D", "DoCommand")
        assert model.targets is None or len(model.targets) == 0

    def test_do_with_postcondition(self, command_metamodel):
        """D:condition LABEL parses correctly (§8.2.3)."""
        model = command_metamodel.model_from_str("D:X LABEL", "DoCommand")
        assert model.postcond is not None
        assert len(model.targets) == 1
        assert model.targets[0].label.label == "LABEL"

    def test_do_pass_by_reference(self, command_metamodel):
        """D LABEL(.VAR) parses DO with pass by reference (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL(.VAR)", "DoCommand")
        target = model.targets[0]
        assert target.args is not None

    def test_do_multiple_targets(self, command_metamodel):
        """D LABEL1,LABEL2 parses DO with multiple targets (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL1,LABEL2", "DoCommand")
        assert len(model.targets) == 2

    def test_do_routine_only(self, command_metamodel):
        """D ^ROUTINE parses DO to routine entry (§8.2.3)."""
        model = command_metamodel.model_from_str("D ^ROUTINE", "DoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_do_arg_postcondition(self, command_metamodel):
        """D LABEL:X=1 - postcondition on target argument (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL:X=1", "DoCommand")
        assert model.postcond is None  # Command postcond is None
        assert model.targets[0].postcond is not None  # Target postcond is set
        assert model.targets[0].label.label == "LABEL"

    def test_do_external_simple(self, command_metamodel):
        """DO &func(a,b) - external function call (§8.2.3)."""
        model = command_metamodel.model_from_str("DO &func(a,b)", "DoCommand")
        assert model is not None
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.external is not None
        assert target.external.name == "func"

    def test_do_external_package(self, command_metamodel):
        """DO &pkg.func(x) - external with package (§8.2.3)."""
        model = command_metamodel.model_from_str("DO &pkg.func(x)", "DoCommand")
        target = model.targets[0]
        assert target.external.package == "pkg"
        assert target.external.name == "func"

    def test_do_byref_indirection(self, command_metamodel):
        """DO routine(.@X) - pass-by-ref with indirection (§8.2.3)."""
        model = command_metamodel.model_from_str("DO routine(.@X)", "DoCommand")
        assert model is not None
        target = model.targets[0]
        assert target.args is not None

    def test_do_mixed_byref_args(self, command_metamodel):
        """DO routine(.@IX,.Y,Z) - mixed args (§8.2.3)."""
        model = command_metamodel.model_from_str("DO routine(.@IX,.Y,Z)", "DoCommand")
        assert model is not None
