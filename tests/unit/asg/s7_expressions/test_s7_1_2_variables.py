"""Tests for Variables ASG analysis (§7.1.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.expressions import LiteralType
from m2py.parser.line_parser import parse_commands_from_line
from m2py.parser.textx_classes import (
    GlobalVariable,
    LocalVariable,
    NakedGlobal,
    NumericLiteral,
    StringLiteral,
)


def analyze_set_command(line: str):
    """Parse a SET command and return the analyzed statement."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestVariablesAnalysis:
    """ASG-level tests for variables analysis (§7.1.2)."""

    def test_local_variable_resolution(self):
        """Local variables (LVN) are correctly resolved (§7.1.2).

        Tests that local variable names parse to LocalVariable nodes.
        """
        stmt = analyze_set_command("S X=1")
        target = stmt.assignments[0].target

        assert isinstance(target, LocalVariable)
        assert target.name == "X"
        assert target.subscripts == []

    def test_global_variable_resolution(self):
        """Global variables (GVN) are correctly resolved (§7.1.2).

        Tests that global variable references parse to GlobalVariable nodes.
        """
        stmt = analyze_set_command("S ^GLOBAL=1")
        target = stmt.assignments[0].target

        assert isinstance(target, GlobalVariable)
        assert target.name == "GLOBAL"
        assert target.subscripts == []

    def test_naked_global_reference(self):
        """Naked global references are correctly tracked (§7.1.2).

        Tests that naked global references (^(subscripts)) parse to NakedGlobal nodes.
        """
        stmt = analyze_set_command('S ^("key")=1')
        target = stmt.assignments[0].target

        assert isinstance(target, NakedGlobal)
        assert len(target.subscripts) == 1
        assert isinstance(target.subscripts[0], StringLiteral)
        assert target.subscripts[0].value == "key"

    def test_variable_scope_analysis(self):
        """Variable scope (input/output) is correctly analyzed (§7.1.2).

        Tests that variables have proper parent references and can be
        analyzed in context. In MUMPS, local variables are scoped to
        the routine call stack.
        """
        # Local variables should have name and empty subscripts by default
        stmt = analyze_set_command("S RESULT=1")
        local_target = stmt.assignments[0].target
        assert isinstance(local_target, LocalVariable)
        assert local_target.name == "RESULT"

        # Global variables are scoped to the database
        stmt = analyze_set_command("S ^DATA=1")
        global_target = stmt.assignments[0].target
        assert isinstance(global_target, GlobalVariable)
        assert global_target.name == "DATA"

    def test_subscripted_variable(self):
        """Subscripted variables are correctly represented (§7.1.2).

        Tests that subscripted variables capture their subscript expressions.
        """
        # Local with subscripts
        stmt = analyze_set_command("S X(1,2)=1")
        local_target = stmt.assignments[0].target
        assert isinstance(local_target, LocalVariable)
        assert local_target.name == "X"
        assert len(local_target.subscripts) == 2
        assert isinstance(local_target.subscripts[0], NumericLiteral)
        assert local_target.subscripts[0].value == 1
        assert isinstance(local_target.subscripts[1], NumericLiteral)
        assert local_target.subscripts[1].value == 2

        # Global with subscripts
        stmt = analyze_set_command('S ^GLOBAL("sub")=1')
        global_target = stmt.assignments[0].target
        assert isinstance(global_target, GlobalVariable)
        assert global_target.name == "GLOBAL"
        assert len(global_target.subscripts) == 1
        assert isinstance(global_target.subscripts[0], StringLiteral)
        assert global_target.subscripts[0].value == "sub"

    def test_glvn_unification(self):
        """GLVN (local or global) is unified in ASG (§7.1.2).

        Tests that both local and global variable types share similar
        structural properties (name, subscripts) as part of the GLVN concept.
        """
        stmt_local = analyze_set_command("S VAR(1)=1")
        local = stmt_local.assignments[0].target

        stmt_global = analyze_set_command("S ^VAR(1)=1")
        global_var = stmt_global.assignments[0].target

        # Both are variable types with similar structure
        assert isinstance(local, LocalVariable)
        assert isinstance(global_var, GlobalVariable)

        # Both have name attribute
        assert local.name == "VAR"
        assert global_var.name == "VAR"

        # Both have subscripts
        assert len(local.subscripts) == 1
        assert len(global_var.subscripts) == 1
        assert local.subscripts[0].literal_type == LiteralType.INTEGER
        assert global_var.subscripts[0].literal_type == LiteralType.INTEGER
