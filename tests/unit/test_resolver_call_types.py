"""Regression tests for call_type population during reference resolution."""
from pathlib import Path

from m2py.parser.parser import MUMPSParser
from m2py.asg.enums import CallType


def test_local_do_call_is_resolved_with_label_call_type():
    parser = MUMPSParser()
    routine = parser.parse_file(Path("tests/functional/mugj/inref/V1BOA1.m"))
    parser.resolve_references(routine)

    label = routine.get_label("22")
    first_do = next(
        stmt for stmt in label.body.walk_statements() if stmt.__class__.__name__ == "MDoStatement"
    )
    call = first_do.targets[0]

    assert call.is_resolved is True
    assert call.target is not None
    assert call.target.name == "EXAMINER"
    assert call.call_type == CallType.LABEL_CALL


def test_external_do_call_marks_routine_call_type():
    parser = MUMPSParser()
    routine = parser.parse_file(Path("tests/functional/mugj/inref/V1BOA1.m"))
    parser.resolve_references(routine)

    end_label = routine.get_label("END")
    ext_do = next(
        stmt for stmt in end_label.body.walk_statements() if stmt.__class__.__name__ == "MDoStatement"
    )
    call = ext_do.targets[0]

    assert call.routine == "VREPORT"
    assert call.is_resolved is False
    assert call.call_type == CallType.ROUTINE_CALL
