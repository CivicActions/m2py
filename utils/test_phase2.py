#!/usr/bin/env python3
"""Test script for Spec 008 Phase 2 infrastructure."""

import types

from m2py.runtime import MUMPSRuntime, GotoExternal, LabelNotFoundError


def test_goto_external():
    """Test GotoExternal exception class."""
    # Create a mock module for testing
    mock_module = types.ModuleType("mymodule")
    mock_module._routine_name = "MYMODULE"

    try:
        raise GotoExternal(mock_module, "MYLABEL", 0)
    except GotoExternal as e:
        assert e.module is mock_module
        assert e.label == "MYLABEL"
        assert e.offset == 0
        assert "GOTO MYLABEL^MYMODULE" in str(e)
        print("✓ GotoExternal exception works correctly")


def test_label_not_found_error():
    """Test LabelNotFoundError exception class."""
    try:
        raise LabelNotFoundError("MISSING", "myroutine", ["LABEL1", "LABEL2"])
    except LabelNotFoundError as e:
        assert e.label == "MISSING"
        assert e.routine == "myroutine"
        assert e.available_labels == ["LABEL1", "LABEL2"]
        assert "MISSING" in str(e)
        assert "myroutine" in str(e)
        print("✓ LabelNotFoundError exception works correctly")


def test_get_text():
    """Test get_text() method in MUMPSRuntime."""
    rt = MUMPSRuntime()
    rt._current_routine = "TEST"
    rt._current_source_lines = [
        "TEST",
        ' W "Hello"',
        " Q",
        "LABEL2",
        ' W "World"',
        " Q",
    ]
    rt._current_label_lines = {"TEST": 0, "LABEL2": 3}

    # $TEXT(+0) - returns routine name
    assert rt.get_text(0) == "TEST", f"Expected 'TEST', got {rt.get_text(0)!r}"
    print("✓ $TEXT(+0) returns routine name")

    # $TEXT(+1) - returns first line
    assert rt.get_text(1) == "TEST", f"Expected 'TEST', got {rt.get_text(1)!r}"
    print("✓ $TEXT(+1) returns first line")

    # $TEXT(+4) - returns fourth line
    assert rt.get_text(4) == "LABEL2", f"Expected 'LABEL2', got {rt.get_text(4)!r}"
    print("✓ $TEXT(+4) returns fourth line")

    # $TEXT(+100) - out of bounds returns empty string
    assert rt.get_text(100) == "", f"Expected '', got {rt.get_text(100)!r}"
    print("✓ $TEXT(+100) returns empty string for out of bounds")

    # $TEXT(LABEL2+0) - returns label line
    assert rt.get_text(0, "LABEL2") == "LABEL2"
    print("✓ $TEXT(LABEL2+0) returns label line")

    # $TEXT(LABEL2+1) - returns line after label
    assert rt.get_text(1, "LABEL2") == ' W "World"'
    print("✓ $TEXT(LABEL2+1) returns line after label")

    # $TEXT(MISSING+0) - unknown label returns empty string
    assert rt.get_text(0, "MISSING") == ""
    print("✓ $TEXT(MISSING+0) returns empty string for unknown label")


def test_codegen_module_constants():
    """Test that codegen generates the module constants."""
    from m2py.parser.parser import MUMPSParser
    from m2py.codegen.routine import RoutineGenerator
    from m2py.analysis import (
        classify_gotos,
        analyze_for_loops,
        analyze_quit_context,
        analyze_variables,
    )

    source = """TEST
 W "Hello"
 Q
LABEL2(X)
 W X
 Q
"""

    parser = MUMPSParser()
    routine = parser.parse(source)
    classify_gotos(routine)
    analyze_for_loops(routine)
    analyze_quit_context(routine)
    analyze_variables(routine)

    gen = RoutineGenerator(routine)
    code = gen.generate()

    # Check that module constants are generated
    assert "_source_lines = " in code, "Missing _source_lines"
    assert "_routine_name = " in code, "Missing _routine_name"
    assert "_label_lines = " in code, "Missing _label_lines"
    assert "_rt._current_routine = _routine_name" in code, "Missing context init"
    assert "_rt._current_source_lines = _source_lines" in code, (
        "Missing source_lines init"
    )
    assert "_rt._current_label_lines = _label_lines" in code, "Missing label_lines init"

    print("✓ Codegen generates all module constants and context initialization")


def main():
    """Run all Phase 2 tests."""
    print("Testing Spec 008 Phase 2 - Foundational Infrastructure\n")

    test_goto_external()
    test_label_not_found_error()
    test_get_text()
    test_codegen_module_constants()

    print("\n✓ All Phase 2 tests passed!")


if __name__ == "__main__":
    main()
