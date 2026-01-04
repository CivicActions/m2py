"""Tests for MERGE command ASG analysis (§8.2.13).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.13
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MMergeStatement, MGlobal


@pytest.mark.asg
class TestMergeCommandAnalysis:
    """ASG-level tests for MERGE command analysis (§8.2.13)."""

    def test_merge_variable_tracking(self):
        """MERGE dest variable is tracked (§8.2.13)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M ^DEST=^SRC\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination is not None

    def test_merge_source_analysis(self):
        """MERGE source tree is analyzed (§8.2.13)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M ^DEST=^SRC\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert stmt.merges[0].source is not None

    def test_merge_global_impact(self):
        """MERGE ^GLOBAL impact is tracked (§8.2.13)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M ^A=^B,^C=^D\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 2

        assert isinstance(stmt.merges[0].destination, MGlobal)
        assert stmt.merges[0].destination.name == "A"
        assert isinstance(stmt.merges[1].destination, MGlobal)
        assert stmt.merges[1].destination.name == "C"


@pytest.mark.asg
class TestMergeStatementASG:
    """Tests for MERGE command ASG field population - additional coverage."""

    def test_merge_command_with_postcondition(self):
        """MERGE:condition dest=source handles postcondition."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M:X>0 ^DEST=^SRC\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MMergeStatement)
        assert stmt.postcondition is not None
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination is not None
        assert stmt.merges[0].source is not None

    def test_merge_with_local_variables(self):
        """MERGE can merge local variable trees."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M LOCAL1=LOCAL2\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination is not None
        assert stmt.merges[0].source is not None


@pytest.mark.asg
class TestMultiMerge:
    """Tests for MERGE command with multiple merge pairs."""

    def test_single_merge(self):
        """Single MERGE pair works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M X=Y\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination.name == "X"
        assert stmt.merges[0].source.name == "Y"

    def test_multi_merge(self):
        """MERGE with multiple pairs captures all pairs.

        This is the key fix - previously only the last pair was kept.
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M X=Y,Z=W\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 2

        # First pair: X=Y
        assert stmt.merges[0].destination.name == "X"
        assert stmt.merges[0].source.name == "Y"

        # Second pair: Z=W
        assert stmt.merges[1].destination.name == "Z"
        assert stmt.merges[1].source.name == "W"

    def test_vista_ztmon_pattern(self):
        """Test VistA ZTMON.m pattern with two merge pairs.

        This pattern appears in 210+ VistA files.
        """
        parser = MUMPSParser()
        # Simplified version of ZTMON pattern
        routine = parser.parse(
            'TEST\n M ZTC("S")=^ZTS("STATUS"),ZTC("L")=^ZTS("LOADA")\n'
        )

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 2

        # First merge: ZTC("S")=^ZTS("STATUS")
        assert stmt.merges[0].destination.name == "ZTC"
        assert stmt.merges[0].source.name == "ZTS"

        # Second merge: ZTC("L")=^ZTS("LOADA")
        assert stmt.merges[1].destination.name == "ZTC"
        assert stmt.merges[1].source.name == "ZTS"
