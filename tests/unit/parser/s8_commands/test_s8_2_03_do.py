"""Tests for DO command parsing (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
Migrated from:
- tests/unit/test_command_grammar.py
- tests/unit/test_parser.py::TestControlFlowBodyPopulation (DO block tests)
"""

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestDoCommandParsing:
    """Parser-level tests for DO command (§8.2.3)."""

    def test_simple_do(self, command_metamodel):
        """D LABEL - simple DO with label (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL", "DoCommand")
        assert len(model.targets) == 1

    def test_do_with_args(self, command_metamodel):
        """D LABEL(A,B) - DO with arguments (§8.2.3)."""
        model = command_metamodel.model_from_str("D LABEL(A,B)", "DoCommand")
        target = model.targets[0]
        assert target.args is not None

    def test_do_external_routine(self, command_metamodel):
        """D ^ROUTINE - DO with external routine (§8.2.3)."""
        model = command_metamodel.model_from_str("D ^ROUTINE", "DoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_argumentless_do(self, command_metamodel):
        """D (block start) - argumentless DO (§8.2.3)."""
        model = command_metamodel.model_from_str("D", "DoCommand")
        assert model.targets is None or len(model.targets) == 0

    def test_do_arg_postcondition(self, command_metamodel):
        """D LABEL:X=1 - postcondition on target argument (§8.2.3, BUG-004)."""
        model = command_metamodel.model_from_str("D LABEL:X=1", "DoCommand")
        assert model.postcond is None  # Command postcond is None
        assert model.targets[0].postcond is not None  # Target postcond is set
        assert model.targets[0].label.label == "LABEL"

    def test_do_computed_offset_with_bare_global(self, command_metamodel):
        """D 1+^V1A^V1CALLE - computed offset with bare global value (§8.2.3).

        Pattern: label=1, offset=^V1A (global value), routine=V1CALLE
        The bare global ^V1A is part of the offset expression, not a routine ref.
        """
        model = command_metamodel.model_from_str("D 1+^V1A^V1CALLE", "DoCommand")
        target = model.targets[0]
        assert target.label.label == "1"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"

    def test_do_computed_offset_complex_expression(self, command_metamodel):
        """D Z+-20+^V1A+^V1A^V1CALLE - complex computed offset (§8.2.3)."""
        model = command_metamodel.model_from_str(
            "D Z+-20+^V1A+^V1A^V1CALLE", "DoCommand"
        )
        target = model.targets[0]
        assert target.label.label == "Z"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"

    def test_do_computed_offset_with_naked_global(self, command_metamodel):
        """D %0A1B2C3+^V1A(2)-^(3)/10 - offset with subscripted and naked globals (§8.2.3)."""
        model = command_metamodel.model_from_str(
            "D %0A1B2C3+^V1A(2)-^(3)/10", "DoCommand"
        )
        target = model.targets[0]
        assert target.label.label == "%0A1B2C3"
        assert target.label.offset is not None
        # No routine in this case
        assert target.label.routine is None

    def test_do_label_plus_routine_offset_expression(self, command_metamodel):
        """D V1CALLE+7-11+12^V1CALLE - expression offset then routine (§8.2.3)."""
        model = command_metamodel.model_from_str(
            "D V1CALLE+7-11+12^V1CALLE", "DoCommand"
        )
        target = model.targets[0]
        assert target.label.label == "V1CALLE"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"

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
        # Args should parse correctly
        target = model.targets[0]
        assert target.args is not None

    def test_do_mixed_byref_args(self, command_metamodel):
        """DO routine(.@IX,.Y,Z) - mixed args (§8.2.3)."""
        model = command_metamodel.model_from_str("DO routine(.@IX,.Y,Z)", "DoCommand")
        assert model is not None


# =============================================================================
# Phase 12: Control Flow Body Population Tests
# =============================================================================


@pytest.mark.parser
class TestDoBlockPopulation:
    """T349: Tests for DO block body population.

    These tests verify that argumentless DO block bodies are properly populated
    with dot-indented lines.

    Migrated from: tests/unit/test_parser.py::TestControlFlowBodyPopulation
    """

    def test_do_block_simple(self):
        """T349: Argumentless DO collects dot-indented lines in body."""
        from m2py.asg.statements import MDoStatement, MSetStatement, MWriteStatement

        parser = MUMPSParser()
        source = """TEST\tD
 . S X=1
 . W X
 S Y=2
"""
        routine = parser.parse(source)

        # Should have 2 statements: DO block and SET
        assert len(routine.labels[0].body.statements) == 2

        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        assert len(do_stmt.targets) == 0  # Argumentless DO
        assert len(do_stmt.body.statements) == 2
        assert isinstance(do_stmt.body.statements[0], MSetStatement)
        assert isinstance(do_stmt.body.statements[1], MWriteStatement)

        # SET Y=2 should be outside DO block
        assert isinstance(routine.labels[0].body.statements[1], MSetStatement)

    def test_do_block_nested(self):
        """T349: Nested DO blocks are properly structured."""
        from m2py.asg.statements import MDoStatement

        parser = MUMPSParser()
        source = """TEST\tD
 . S X=1
 . D
 . . S Y=2
 . . S Z=3
 . S A=4
 S B=5
"""
        routine = parser.parse(source)

        # Should have 2 statements: outer DO block and SET B=5
        assert len(routine.labels[0].body.statements) == 2

        outer_do = routine.labels[0].body.statements[0]
        assert isinstance(outer_do, MDoStatement)
        # Outer DO has: S X=1, nested DO, S A=4
        assert len(outer_do.body.statements) == 3

        inner_do = outer_do.body.statements[1]
        assert isinstance(inner_do, MDoStatement)
        # Inner DO has: S Y=2, S Z=3
        assert len(inner_do.body.statements) == 2
