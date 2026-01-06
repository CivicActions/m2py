"""Tests for ZWRITE command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZWriteStatement


@pytest.mark.asg
@pytest.mark.ydb
class TestZwriteAsg:
    """ASG-level tests for ZWRITE command (YDB)."""

    def test_zwrite_asg_node(self):
        """ZWRITE creates proper ASG node with variable arguments."""
        parser = MUMPSParser()
        source = """TEST
 ZWRITE A
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        assert len(stmt.args) == 1
        # Verify argument contains target variable info
        arg = stmt.args[0]
        assert arg.target is not None
        assert arg.target.name == "A"

    def test_zwrite_variable_analysis(self):
        """ZWRITE variable reference is analyzed with subscripts."""
        parser = MUMPSParser()
        source = """TEST
 ZWRITE X(1,2)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        assert len(stmt.args) == 1
        # Verify subscripted variable is captured
        arg = stmt.args[0]
        assert arg.target.name == "X"
        # The target should have subscript info
        assert len(arg.target.subscripts) == 2


@pytest.mark.asg
@pytest.mark.ydb
class TestZwriteRangesPatterns:
    """Tests for ZWRITE subscript ranges and patterns (YDB, GAP-003i, GAP-004b).

    ZWRITE supports special subscript syntax for filtering output:
    - * (all subscripts)
    - start:end (range)
    - ^?.E (global name pattern)

    This tests the _analyze_MZWriteSubscriptAll, _analyze_MZWriteSubscriptRange,
    and _analyze_ZWriteGlobalPattern paths in semantic_analyzer.py.
    """

    def test_zwrite_wildcard_subscript(self):
        """ZWRITE with wildcard (*) subscript.

        Example: ZWRITE X(*) - show all subscripts of X.
        """
        from m2py.asg.statements import MZWriteSubscriptAll

        parser = MUMPSParser()
        source = """TEST
 ZWRITE X(*)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        assert len(stmt.args) == 1
        arg = stmt.args[0]
        # Target should have a wildcard subscript
        assert len(arg.target.subscripts) == 1
        assert isinstance(arg.target.subscripts[0], MZWriteSubscriptAll)

    def test_zwrite_range_subscript_start_end(self):
        """ZWRITE with range subscript (start:end).

        Example: ZWRITE X(1:10) - show subscripts 1 through 10.
        """
        from m2py.asg.statements import MZWriteSubscriptRange

        parser = MUMPSParser()
        source = """TEST
 ZWRITE X(1:10)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        arg = stmt.args[0]
        assert len(arg.target.subscripts) == 1
        sub = arg.target.subscripts[0]
        assert isinstance(sub, MZWriteSubscriptRange)
        assert sub.start.value == 1
        assert sub.end.value == 10

    def test_zwrite_range_subscript_start_only(self):
        """ZWRITE with start-only range subscript (start:).

        Example: ZWRITE X(5:) - show subscripts from 5 to end.
        """
        from m2py.asg.statements import MZWriteSubscriptRange

        parser = MUMPSParser()
        source = """TEST
 ZWRITE X(5:)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        arg = stmt.args[0]
        sub = arg.target.subscripts[0]
        assert isinstance(sub, MZWriteSubscriptRange)
        assert sub.start.value == 5
        assert sub.end is None

    def test_zwrite_range_subscript_end_only(self):
        """ZWRITE with end-only range subscript (:end).

        Example: ZWRITE X(:10) - show subscripts from beginning to 10.
        """
        from m2py.asg.statements import MZWriteSubscriptRange

        parser = MUMPSParser()
        source = """TEST
 ZWRITE X(:10)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        arg = stmt.args[0]
        sub = arg.target.subscripts[0]
        assert isinstance(sub, MZWriteSubscriptRange)
        assert sub.start is None
        assert sub.end.value == 10

    def test_zwrite_global_name_pattern(self):
        """ZWRITE with global name pattern (^?.E).

        Example: ZWRITE ^?.E - show all globals with single char name ending in E.
        """
        parser = MUMPSParser()
        source = """TEST
 ZWRITE ^?1A
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        arg = stmt.args[0]
        # The target should have a pattern spec, not a name
        assert hasattr(arg.target, "name_pattern")

    def test_zwrite_global_pattern_with_subscripts(self):
        """ZWRITE with global name pattern and subscripts.

        Example: ZWRITE ^?.E(1:10) - pattern match + range subscripts.
        """
        from m2py.asg.statements import MZWriteSubscriptRange

        parser = MUMPSParser()
        source = """TEST
 ZWRITE ^?1A(1:5)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        arg = stmt.args[0]
        # Should have pattern and subscripts
        assert hasattr(arg.target, "name_pattern")
        assert arg.target.subscripts is not None
        assert len(arg.target.subscripts) == 1
        assert isinstance(arg.target.subscripts[0], MZWriteSubscriptRange)
