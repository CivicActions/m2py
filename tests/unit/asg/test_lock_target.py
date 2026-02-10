"""Unit tests for MLockTarget dataclass.

Tests the new MLockTarget dataclass that replaces untyped dict objects
in MLockStatement.targets.

Phase 12 (US13): ASG Field Cleanup
"""

import pytest

from m2py.asg.statements import MLockTarget
from m2py.asg.expressions import MLiteral, MVariable


@pytest.mark.asg
class TestMLockTargetBasics:
    """Test basic MLockTarget creation and fields."""

    def test_default_values(self):
        """MLockTarget should have sensible defaults."""
        target = MLockTarget()
        assert target.name is None
        assert target.subscripts == []
        assert target.is_global is False
        assert target.lockop == ""
        assert target.timeout is None
        assert target.postcondition is None
        assert target.is_indirect is False
        assert target.indirection is None
        assert target.indirection_levels == 0

    def test_local_variable_lock(self):
        """MLockTarget can represent a local variable lock."""
        target = MLockTarget(name="X", is_global=False)
        assert target.name == "X"
        assert target.is_global is False
        assert target.is_indirect is False

    def test_global_variable_lock(self):
        """MLockTarget can represent a global variable lock."""
        target = MLockTarget(name="G", is_global=True)
        assert target.name == "G"
        assert target.is_global is True

    def test_subscripted_lock(self):
        """MLockTarget can represent a subscripted lock target."""
        sub1 = MLiteral(value=1)
        sub2 = MLiteral(value=2)
        target = MLockTarget(name="A", subscripts=[sub1, sub2])
        assert target.name == "A"
        assert len(target.subscripts) == 2

    def test_incremental_lock(self):
        """MLockTarget can represent an incremental lock (+)."""
        target = MLockTarget(name="X", lockop="+")
        assert target.lockop == "+"

    def test_decremental_lock(self):
        """MLockTarget can represent a decremental lock (-)."""
        target = MLockTarget(name="X", lockop="-")
        assert target.lockop == "-"

    def test_lock_with_timeout(self):
        """MLockTarget can have a per-target timeout."""
        timeout_expr = MLiteral(value=5)
        target = MLockTarget(name="X", timeout=timeout_expr)
        assert target.timeout is timeout_expr

    def test_lock_with_postcondition(self):
        """MLockTarget can have a per-target postcondition."""
        postcond = MVariable(name="Y", subscripts=[])
        target = MLockTarget(name="X", postcondition=postcond)
        assert target.postcondition is postcond


@pytest.mark.asg
class TestMLockTargetIndirection:
    """Test MLockTarget indirection handling."""

    def test_indirect_lock(self):
        """MLockTarget can represent an indirect lock (@NAME)."""
        ind_expr = MVariable(name="X", subscripts=[])
        target = MLockTarget(
            is_indirect=True,
            indirection=ind_expr,
            indirection_levels=1,
        )
        assert target.is_indirect is True
        assert target.indirection is ind_expr
        assert target.indirection_levels == 1
        # Name is None for indirect targets (resolved at runtime)
        assert target.name is None

    def test_double_indirect_lock(self):
        """MLockTarget can represent double indirection (@@NAME)."""
        ind_expr = MVariable(name="PTR", subscripts=[])
        target = MLockTarget(
            is_indirect=True,
            indirection=ind_expr,
            indirection_levels=2,
        )
        assert target.indirection_levels == 2


@pytest.mark.asg
class TestMLockTargetCombinations:
    """Test combinations of MLockTarget fields."""

    def test_global_subscripted_incremental_with_timeout(self):
        """Complex MLockTarget: L +^G(1,2):5"""
        sub1 = MLiteral(value=1)
        sub2 = MLiteral(value=2)
        timeout = MLiteral(value=5)
        target = MLockTarget(
            name="G",
            is_global=True,
            subscripts=[sub1, sub2],
            lockop="+",
            timeout=timeout,
        )
        assert target.name == "G"
        assert target.is_global is True
        assert len(target.subscripts) == 2
        assert target.lockop == "+"
        assert target.timeout is timeout

    def test_indirect_with_postcondition(self):
        """MLockTarget: L @X:cond"""
        ind_expr = MVariable(name="X", subscripts=[])
        postcond = MVariable(name="Y", subscripts=[])
        target = MLockTarget(
            is_indirect=True,
            indirection=ind_expr,
            indirection_levels=1,
            postcondition=postcond,
        )
        assert target.is_indirect is True
        assert target.postcondition is postcond
