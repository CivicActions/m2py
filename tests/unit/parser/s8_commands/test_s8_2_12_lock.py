"""Tests for LOCK command parsing (§8.2.12).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12
"""

import pytest


@pytest.mark.parser
class TestLockCommandParsing:
    """Parser-level tests for LOCK command (§8.2.12)."""

    def test_lock_basic(self, command_metamodel):
        """L ^GLOBAL - basic lock parses correctly (§8.2.12)."""
        model = command_metamodel.model_from_str("L ^GLOBAL", "LockCommand")
        assert len(model.targets) == 1

    def test_lock_indirection(self, command_metamodel):
        """L @A - single indirection (§8.2.12)."""
        model = command_metamodel.model_from_str("L @A", "LockCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # IndirectChain has var attribute for simple variable
        assert target.indirect.var.name == "A"
        assert target.indirect.nested is None

    def test_lock_double_indirection(self, command_metamodel):
        """L @@A - double indirection (§8.2.12)."""
        model = command_metamodel.model_from_str("L @@A", "LockCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # Nested indirection
        assert target.indirect.nested is not None
        assert target.indirect.nested.var.name == "A"

    def test_lock_indirection_with_timeout(self, command_metamodel):
        """L @A:1 - indirection with timeout (§8.2.12)."""
        model = command_metamodel.model_from_str("L @A:1", "LockCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        assert target.timeout is not None

    def test_lock_paren_with_indirection(self, command_metamodel):
        """L (@A,^B):1 - parenthesized list with indirection (§8.2.12)."""
        model = command_metamodel.model_from_str("L (@A,^B):1", "LockCommand")
        # Parenthesized list uses locklist instead of targets
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        # First item is indirection
        first_item = model.locklist.targets[0]
        assert first_item.indirect is not None
        assert first_item.indirect.var.name == "A"
        # Second item is global
        second_item = model.locklist.targets[1]
        assert second_item.target is not None

    def test_lock_postcond_indirection(self, command_metamodel):
        """L:X=1 @A - postcondition with indirection (§8.2.12)."""
        model = command_metamodel.model_from_str("L:X=1 @A", "LockCommand")
        assert model.postcond is not None
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_lock_increment(self, command_metamodel):
        """L +^A - incremental lock (§8.2.12)."""
        model = command_metamodel.model_from_str("L +^A", "LockCommand")
        assert len(model.targets) == 1
        assert model.targets[0].lockop == "+"

    def test_lock_decrement(self, command_metamodel):
        """L -^A - decremental lock (§8.2.12)."""
        model = command_metamodel.model_from_str("L -^A", "LockCommand")
        assert len(model.targets) == 1
        assert model.targets[0].lockop == "-"

    def test_lock_multiple_increments(self, command_metamodel):
        """L +^A,+^B,+^C - multiple incremental locks (§8.2.12)."""
        model = command_metamodel.model_from_str("L +^A,+^B,+^C", "LockCommand")
        assert len(model.targets) == 3
        assert all(t.lockop == "+" for t in model.targets)

    def test_lock_multiple_decrements(self, command_metamodel):
        """L -^A,-^B,-^C - multiple decremental locks (§8.2.12)."""
        model = command_metamodel.model_from_str("L -^A,-^B,-^C", "LockCommand")
        assert len(model.targets) == 3
        assert all(t.lockop == "-" for t in model.targets)

    def test_lock_mixed_ops(self, command_metamodel):
        """L +^A,-^B,^C - mixed incremental, decremental, and normal locks (§8.2.12)."""
        model = command_metamodel.model_from_str("L +^A,-^B,^C", "LockCommand")
        assert len(model.targets) == 3
        assert model.targets[0].lockop == "+"
        assert model.targets[1].lockop == "-"
        assert model.targets[2].lockop is None

    def test_lock_paren_with_ops(self, command_metamodel):
        """L (+^A,+^B):1 - parenthesized with +/- on each item (§8.2.12)."""
        model = command_metamodel.model_from_str("L (+^A,+^B):1", "LockCommand")
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        assert model.locklist.targets[0].lockop == "+"
        assert model.locklist.targets[1].lockop == "+"

    def test_lock_paren_list_lockop(self, command_metamodel):
        """L +(^A,^B,^C) - list-level lockop applies to all items (§8.2.12)."""
        model = command_metamodel.model_from_str("L +(^A,^B,^C)", "LockCommand")
        assert model.locklist is not None
        assert model.locklist.lockop == "+"
        assert len(model.locklist.targets) == 3

    def test_lock_paren_decremental(self, command_metamodel):
        """L -(^A):1 - decremental lock on parenthesized list with timeout (§8.2.12)."""
        model = command_metamodel.model_from_str("L -(^A):1", "LockCommand")
        assert model.locklist is not None
        assert model.locklist.lockop == "-"
        assert model.locklist.timeout is not None
