#!/usr/bin/env python3
"""Test name indirection support in DO/GOTO commands."""

import sys
from m2py.analysis.command_parser import parse_commands_from_line


def test_do_with_name_indirection():
    """Test DO command with name indirection: DO @X@(1)"""
    cmds = parse_commands_from_line(" D @X@(1)")
    assert len(cmds) == 1, f"Expected 1 command, got {len(cmds)}"

    cmd = cmds[0]
    assert cmd.__class__.__name__ == "DoCommand", (
        f"Expected DoCommand, got {cmd.__class__.__name__}"
    )

    # The DO command has targets
    assert len(cmd.targets) > 0, "DO should have at least one target"

    target = cmd.targets[0]
    assert hasattr(target, "indirect"), "DoTarget should have indirect attribute"
    assert target.indirect is not None, "indirect should not be None"

    # The indirect target should have name_subscripts
    indirect = target.indirect
    assert hasattr(indirect, "labelIndirect"), "DoIndirect should have labelIndirect"
    label_indirect = indirect.labelIndirect
    assert label_indirect is not None, "labelIndirect should not be None"
    assert hasattr(label_indirect, "name_subscripts"), (
        "IndirectChain should have name_subscripts attribute"
    )
    assert len(label_indirect.name_subscripts) > 0, (
        f"IndirectChain should have at least one name_subscript, got {len(label_indirect.name_subscripts)}"
    )

    print("✅ test_do_with_name_indirection PASSED")


def test_goto_with_name_indirection():
    """Test GOTO command with name indirection: GOTO @X@(A)"""
    cmds = parse_commands_from_line(" G @X@(A)")
    assert len(cmds) == 1, f"Expected 1 command, got {len(cmds)}"

    cmd = cmds[0]
    assert cmd.__class__.__name__ == "GotoCommand", (
        f"Expected GotoCommand, got {cmd.__class__.__name__}"
    )

    # The GOTO command has targets
    assert len(cmd.targets) > 0, "GOTO should have at least one target"

    target = cmd.targets[0]
    assert hasattr(target, "indirect"), "GotoTarget should have indirect attribute"
    assert target.indirect is not None, "indirect should not be None"

    # The indirect target should have name_subscripts
    indirect = target.indirect
    assert hasattr(indirect, "labelIndirect"), "GotoIndirect should have labelIndirect"
    label_indirect = indirect.labelIndirect
    assert label_indirect is not None, "labelIndirect should not be None"
    assert hasattr(label_indirect, "name_subscripts"), (
        "IndirectChain should have name_subscripts attribute"
    )
    assert len(label_indirect.name_subscripts) > 0, (
        f"IndirectChain should have at least one name_subscript, got {len(label_indirect.name_subscripts)}"
    )

    print("✅ test_goto_with_name_indirection PASSED")


def test_simple_indirection_still_works():
    """Ensure simple indirection without name indirection still works"""
    cmds = parse_commands_from_line(" D @X")
    assert len(cmds) == 1, f"Expected 1 command, got {len(cmds)}"

    cmd = cmds[0]
    assert cmd.__class__.__name__ == "DoCommand"
    assert len(cmd.targets) > 0

    target = cmd.targets[0]
    indirect = target.indirect
    label_indirect = indirect.labelIndirect
    assert label_indirect is not None
    assert hasattr(label_indirect, "name_subscripts"), (
        "IndirectChain should have name_subscripts attribute"
    )
    assert len(label_indirect.name_subscripts) == 0, (
        f"simple indirection should have no name_subscripts, got {len(label_indirect.name_subscripts)}"
    )

    print("✅ test_simple_indirection_still_works PASSED")


def test_chained_name_indirection():
    """Test chained name indirection: DO @X@(1)@(2)"""
    cmds = parse_commands_from_line(" D @X@(1)@(2)")
    assert len(cmds) == 1, f"Expected 1 command, got {len(cmds)}"

    cmd = cmds[0]
    assert cmd.__class__.__name__ == "DoCommand"
    assert len(cmd.targets) > 0

    target = cmd.targets[0]
    indirect = target.indirect
    label_indirect = indirect.labelIndirect
    assert label_indirect is not None
    assert hasattr(label_indirect, "name_subscripts"), (
        "IndirectChain should have name_subscripts attribute"
    )
    assert len(label_indirect.name_subscripts) == 2, (
        f"Expected 2 name_subscripts, got {len(label_indirect.name_subscripts)}"
    )

    print("✅ test_chained_name_indirection PASSED")


if __name__ == "__main__":
    try:
        test_do_with_name_indirection()
        test_goto_with_name_indirection()
        test_simple_indirection_still_works()
        test_chained_name_indirection()
        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
