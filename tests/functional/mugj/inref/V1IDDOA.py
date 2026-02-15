# pyright: reportGeneralTypeIssues=false
from m2py.codegen.helpers import m_str, m_num, m_truth, m_compare, m_add, m_sub
from m2py.runtime import (
    MUMPSRuntime,
    MArray,
    run_with_goto_support,
    resolve_goto_target,
    GotoExternal,
)
from m2py.runtime.helpers import m_var_value, unwind_new_stack
from dataclasses import dataclass, field
from typing import Tuple

_test = False

_globals = globals()

_source_lines = [
    "V1IDDOA\t;INDIRECTION IN DO COMMAND -1-;KO-TS,V1IDDO,VALIDATION VERSION 7.1;31-AUG-1987;",
    "\t;COPYRIGHT MUMPS SYSTEM LABORATORY 1978",
    "\tS PASS=0,FAIL=0",
    '\tW !!,"V1IDDOA: TEST OF INDIRECTION IN DO ARGUMENTS -1-",!',
    '461\tW !,"I-461  indirection of dlabel"',
    '\tS ITEM="I-461  ",VCOMP=""',
    "\tS A=1 DO @A",
    '\tS VCORR="1 " D EXAMINER',
    "\t;",
    '462\tW !,"I-462  indirection of dlabel, while dlabel contains indirection"',
    '\tS ITEM="I-462  ",VCOMP=""',
    '\tS L="@L(1)",L(1)="@$P(""ONE/TWO/THREE"",""/"",2)"',
    "\tD @L",
    '\tS VCORR="TWO " D EXAMINER',
    "\t;",
    '463\tW !,"I-463  indirection of dlabel+intexpr"',
    '\tS ITEM="I-463  ",VCOMP=""',
    '\tS A="ENTRY" DO @A+00002+(2+3)-04 ;ENTRY+3',
    '\tS VCORR="ENTRY3 " D EXAMINER',
    "\t;",
    '464\tW !,"I-464  indirection of dlabel+intexpr, while intexpr contains indirection"',
    '\tS ITEM="I-464  ",VCOMP=""',
    '\tS A=1,B="A" DO @A+@B  ;1+1',
    '\tS VCORR="2 " D EXAMINER',
    "\t;",
    '465\tW !,"I-465  indirection of dlabel+intexpr, while dlabel and intexpr contains"',
    '\tS ITEM="I-465  ",VCOMP=""',
    '\tS A="A(I)",I=02,A(2)="000001",^V1A="@B^@B(1)",B="0098",B(1)="V1IDDO1"',
    "\tD @@A+A(2),@^V1A",
    '\tS VCORR="000001+1 0098 " D EXAMINER',
    "\t;",
    '466\tW !,"I-466  indirection of routine name"',
    '\tS ITEM="I-466  ",VCOMP=""',
    '\tS A="V1IDDO1" D ^@A',
    '\tS B="^V1IDDO1" D @B',
    '\tS A="^V1IDDO1,^@B",B="V1IDDO1" D @A',
    '\tS VCORR="^V1IDDO1 ^V1IDDO1 ^V1IDDO1 ^V1IDDO1 " D EXAMINER',
    "\t;",
    '467\tW !,"I-467  indirection of routine name, while routine name contains indirection"',
    '\tS ITEM="I-467  ",VCOMP=""',
    '\tS ^V1IDDO1="A",A=10,C="V1IDDO1",V1IDDO1="V1IDDO1"',
    "\tD @A^@C,V1IDDO+-5+@^V1IDDO1^@@C",
    '\tS VCORR="10 98 " D EXAMINER',
    "\t;",
    'END\tW !!,"END OF V1IDDOA",!',
    '\tS ROUTINE="V1IDDOA",TESTS=7,AUTO=7,VISUAL=0 D ^VREPORT',
    "\tK  K ^V1A,^V1IDO1 Q",
    "\t;",
    'EXAMINER\tI VCORR=VCOMP S PASS=PASS+1 W !,"   PASS  ",ITEM W:$Y>55 # Q',
    '\tS FAIL=FAIL+1 W !,"** FAIL  ",ITEM W:$Y>55 #',
    '\tW !,"           COMPUTED =""",VCOMP,"""" W:$Y>55 #',
    '\tW !,"           CORRECT  =""",VCORR,"""" W:$Y>55 #',
    "\tQ",
    '98\tS VCOMP=VCOMP_"98 " Q',
    '00980\tS VCOMP=VCOMP_"00980 " Q  ;470',
    '0098\tS VCOMP=VCOMP_"0098 " Q  ;470',
    'ROUTINE\tS VCOMP=VCOMP_"ROUTINE " Q  ;474',
    '1\tS VCOMP=VCOMP_"1 " Q  ;461,473',
    '\tS VCOMP=VCOMP_"2 " Q  ;464,473',
    'DREI\tS VCOMP=VCOMP_"3 " Q  ;473',
    "SIEBEN7\tS VCOMP=VCOMP_7 Q",
    '\tS VCOMP=VCOMP_"SIEBEN7+1 " Q  ;472',
    '%BREAK\tS VCOMP=VCOMP_"%BREAK " Q  ;472',
    'ENTRY\tS VCOMP=VCOMP_"ENTRY " Q',
    '\tS VCOMP=VCOMP_"ENTRY1 " Q',
    'ENTRY2\tS VCOMP=VCOMP_"ENTRY2 " Q',
    '\tS VCOMP=VCOMP_"ENTRY3 " Q  ;463',
    "\tQUIT",
    'ONE\tS VCOMP=VCOMP_"ONE " Q',
    'TWO\tS VCOMP=VCOMP_"TWO " Q  ;462',
    'THREE\tS VCOMP=VCOMP_"THREE " Q',
    '%\tS VCOMP=VCOMP_"% " Q',
    '0123\tS VCOMP=VCOMP_"0123 " Q',
    '012\tS VCOMP=VCOMP_"012 " Q',
    '000001\tS VCOMP=VCOMP_"000001 " Q',
    '\tS VCOMP=VCOMP_"000001+1 " Q  ;465',
]

_routine_name = "V1IDDOA"

_label_lines = {
    "V1IDDOA": 0,
    "461": 4,
    "462": 9,
    "463": 15,
    "464": 20,
    "465": 25,
    "466": 31,
    "467": 38,
    "END": 44,
    "EXAMINER": 48,
    "98": 53,
    "00980": 54,
    "0098": 55,
    "ROUTINE": 56,
    "1": 57,
    "DREI": 59,
    "SIEBEN7": 60,
    "%BREAK": 62,
    "ENTRY": 63,
    "ENTRY2": 65,
    "ONE": 68,
    "TWO": 69,
    "THREE": 70,
    "%": 71,
    "0123": 72,
    "012": 73,
    "000001": 74,
}


@dataclass
class RoutineState:
    """Shared state with dynamic locals for argumentless KILL/NEW support.

    _locals: Dictionary holding all local variable values. Variable names
             are keys, values are the variable values. Supports argumentless
             KILL (clear all) and dynamic variable access.

    _new_stack: Stack of saved _locals snapshots for argumentless NEW.
                Each NEW pushes a copy, QUIT pops and restores.
    """

    _locals: dict = field(default_factory=dict)
    _new_stack: list = field(default_factory=list)


def _call_extrinsic(_rt, _ef, *args, _scope=None, _byref=None):
    """Call extrinsic function with $TEST save/restore and by-ref handling.

    Args:
        _rt: Runtime instance
        _ef: The extrinsic function to call
        *args: Positional arguments for the function
        _scope: Variable scope dictionary for cross-routine visibility
        _byref: List of by-ref variable names (or None for by-value)
    """
    global _test
    _saved = _test
    _saved_extrinsic = _rt._in_extrinsic
    _rt.push_stack_frame("$$", label=getattr(_ef, "__name__", ""))
    try:
        _rt._in_extrinsic = True
        if _scope is not None:
            _result = _ef(_rt, *args, _scope=_scope)
        else:
            _result = _ef(_rt, *args)
        # Unpack by-ref values if result is a tuple
        if isinstance(_result, tuple) and len(_result) > 1:
            # Only unpack to caller scope if _byref is provided
            if _byref and _scope is not None:
                _byref_idx = 1
                for _name in _byref:
                    if _name is not None and _byref_idx < len(_result):
                        _scope.setdefault(_name, MArray()).value = _result[_byref_idx]
                    _byref_idx += 1
            # Always return just the first element (return value)
            return _result[0]
        return _result
    finally:
        _rt.pop_stack_frame()
        _test = _saved
        _rt._test = _test
        _rt._in_extrinsic = _saved_extrinsic


class _XecuteExit(Exception):
    """Exception for control flow exit from inline XECUTE."""

    pass


def _V1IDDOA(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 2:
        state._locals.setdefault("PASS", MArray()).value = 0  # noqa: F841
        state._locals.setdefault("FAIL", MArray()).value = 0  # noqa: F841
    if _start_offset <= 3:
        _rt.write_newline()
        _rt.write_newline()
        _rt.write("V1IDDOA: TEST OF INDIRECTION IN DO ARGUMENTS -1-")
        _rt.write_newline()
    return ("461", state)


def __n_461(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write("I-461  indirection of dlabel")
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-461  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        state._locals.setdefault("A", MArray()).value = 1  # noqa: F841
    if _start_offset <= 2:
        _call_targets = _rt.resolve_do_targets(
            str(m_var_value(state._locals.get("A"))), state._locals
        )
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 3:
        state._locals.setdefault("VCORR", MArray()).value = "1 "  # noqa: F841
    if _start_offset <= 3:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("462", state)


def __n_462(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write("I-462  indirection of dlabel, while dlabel contains indirection")
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-462  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        state._locals.setdefault("L", MArray()).value = "@L(1)"  # noqa: F841
        state._locals.setdefault("L", MArray())[1] = '@$P("ONE/TWO/THREE","/",2)'
    if _start_offset <= 3:
        _call_targets = _rt.resolve_do_targets(
            str(m_var_value(state._locals.get("L"))), state._locals
        )
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 4:
        state._locals.setdefault("VCORR", MArray()).value = "TWO "  # noqa: F841
    if _start_offset <= 4:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("463", state)


def __n_463(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write("I-463  indirection of dlabel+intexpr")
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-463  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        # ENTRY+3
        state._locals.setdefault("A", MArray()).value = "ENTRY"  # noqa: F841
    if _start_offset <= 2:
        _indirect_label = str(str(m_var_value(state._locals.get("A"))))
        _indirect_offset = int(m_num(m_sub(m_add(2, m_add(2, 3)), 4)))
        _indirect_target = _indirect_label + "+" + str(_indirect_offset)
        _call_targets = _rt.resolve_do_targets(_indirect_target, state._locals)
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 3:
        state._locals.setdefault("VCORR", MArray()).value = "ENTRY3 "  # noqa: F841
    if _start_offset <= 3:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("464", state)


def __n_464(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write(
            "I-464  indirection of dlabel+intexpr, while intexpr contains indirection"
        )
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-464  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        # 1+1
        state._locals.setdefault("A", MArray()).value = 1  # noqa: F841
        state._locals.setdefault("B", MArray()).value = "A"  # noqa: F841
    if _start_offset <= 2:
        _indirect_label = str(str(m_var_value(state._locals.get("A"))))
        _indirect_offset = int(m_num(_rt.get_indirected("B", state._locals, levels=1)))
        _indirect_target = _indirect_label + "+" + str(_indirect_offset)
        _call_targets = _rt.resolve_do_targets(_indirect_target, state._locals)
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 3:
        state._locals.setdefault("VCORR", MArray()).value = "2 "  # noqa: F841
    if _start_offset <= 3:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("465", state)


def __n_465(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write(
            "I-465  indirection of dlabel+intexpr, while dlabel and intexpr contains"
        )
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-465  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        state._locals.setdefault("A", MArray()).value = "A(I)"  # noqa: F841
        state._locals.setdefault("_a_I", MArray()).value = 2  # noqa: F841
        state._locals.setdefault("A", MArray())[2] = "000001"
        _rt.globals.set("V1A", (), m_str("@B^@B(1)"))
        state._locals.setdefault("B", MArray()).value = "0098"  # noqa: F841
        state._locals.setdefault("B", MArray())[1] = "V1IDDO1"
    if _start_offset <= 3:
        _indirect_label = str("@" + str(m_var_value(state._locals.get("A"))))
        _indirect_offset = int(m_num(state._locals.get("A", MArray()).get(2)))
        _indirect_target = _indirect_label + "+" + str(_indirect_offset)
        _call_targets = _rt.resolve_do_targets(_indirect_target, state._locals)
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
        _call_targets = _rt.resolve_do_targets(
            str((_rt.globals.get("V1A", ()) or "")), state._locals
        )
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 4:
        state._locals.setdefault("VCORR", MArray()).value = "000001+1 0098 "  # noqa: F841
    if _start_offset <= 4:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("466", state)


def __n_466(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write("I-466  indirection of routine name")
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-466  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        state._locals.setdefault("A", MArray()).value = "V1IDDO1"  # noqa: F841
    if _start_offset <= 2:
        _indirect_label = str("")
        _indirect_target = _indirect_label
        _indirect_routine = str(str(m_var_value(state._locals.get("A"))))
        _indirect_target = _indirect_target + "^" + _indirect_routine
        _call_targets = _rt.resolve_do_targets(_indirect_target, state._locals)
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 3:
        state._locals.setdefault("B", MArray()).value = "^V1IDDO1"  # noqa: F841
    if _start_offset <= 3:
        _call_targets = _rt.resolve_do_targets(
            str(m_var_value(state._locals.get("B"))), state._locals
        )
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 4:
        state._locals.setdefault("A", MArray()).value = "^V1IDDO1,^@B"  # noqa: F841
        state._locals.setdefault("B", MArray()).value = "V1IDDO1"  # noqa: F841
    if _start_offset <= 4:
        _call_targets = _rt.resolve_do_targets(
            str(m_var_value(state._locals.get("A"))), state._locals
        )
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 5:
        state._locals.setdefault(
            "VCORR", MArray()
        ).value = "^V1IDDO1 ^V1IDDO1 ^V1IDDO1 ^V1IDDO1 "  # noqa: F841
    if _start_offset <= 5:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("467", state)


def __n_467(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write(
            "I-467  indirection of routine name, while routine name contains indirection"
        )
    if _start_offset <= 1:
        state._locals.setdefault("ITEM", MArray()).value = "I-467  "  # noqa: F841
        state._locals.setdefault("VCOMP", MArray()).value = ""  # noqa: F841
    if _start_offset <= 2:
        _rt.globals.set("V1IDDO1", (), m_str("A"))
        state._locals.setdefault("A", MArray()).value = 10  # noqa: F841
        state._locals.setdefault("C", MArray()).value = "V1IDDO1"  # noqa: F841
        state._locals.setdefault("V1IDDO1", MArray()).value = "V1IDDO1"  # noqa: F841
    if _start_offset <= 3:
        _indirect_label = str(str(m_var_value(state._locals.get("A"))))
        _indirect_target = _indirect_label
        _indirect_routine = str(str(m_var_value(state._locals.get("C"))))
        _indirect_target = _indirect_target + "^" + _indirect_routine
        _call_targets = _rt.resolve_do_targets(_indirect_target, state._locals)
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
        _indirect_label = str("V1IDDO")
        _indirect_offset = int(
            m_num(
                m_add(
                    (-m_num(5)), _rt.get_indirected("^V1IDDO1", state._locals, levels=1)
                )
            )
        )
        _indirect_target = _indirect_label + "+" + str(_indirect_offset)
        _indirect_routine = str("@" + str(m_var_value(state._locals.get("C"))))
        _indirect_target = _indirect_target + "^" + _indirect_routine
        _call_targets = _rt.resolve_do_targets(_indirect_target, state._locals)
        for _call_target in _call_targets:
            if _call_target.postcondition:
                _pc_temp_var = "ZPOSTCOND"
                _pc_scope = dict(state._locals)
                _rt.execute_mumps(
                    f"S {_pc_temp_var}={_call_target.postcondition}", _pc_scope
                )
                _pc_result = _pc_scope.get(_pc_temp_var)
                if isinstance(_pc_result, MArray):
                    _pc_result = _pc_result.value
                if _pc_result in (0, "", "0", None):
                    continue
            if _call_target.routine and _call_target.routine != _routine_name:
                import importlib
                from m2py.core.names import NameTranslator

                _module = importlib.import_module(_call_target.routine)
                if _call_target.label:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.label), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.label,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                else:
                    _func = getattr(
                        _module, NameTranslator.to_python(_call_target.routine), None
                    )
                    if _func is None:
                        from m2py.runtime import LabelNotFoundError

                        raise LabelNotFoundError(
                            _call_target.routine,
                            _call_target.routine,
                            list(getattr(_module, "_label_lines", {}).keys()),
                        )
                if _call_target.offset is not None:
                    _label_line = _module._label_lines.get(
                        _call_target.label or _call_target.routine, 0
                    )
                    _target_line = (_label_line + 1) + _call_target.offset
                    _label_name, _line_offset = _module._line_map[_target_line]
                    getattr(_module, _label_name)(
                        _rt, _scope=_scope, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=_scope)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            else:
                _func = _labels.get(_call_target.label)
                if _func is None:
                    from m2py.runtime import LabelNotFoundError

                    raise LabelNotFoundError(
                        _call_target.label, _routine_name, list(_label_lines.keys())
                    )
                if _call_target.offset is not None:
                    _label_line = _label_lines.get(_call_target.label, 0)
                    _target_line = (_label_line + 1) + _call_target.offset
                    if _target_line in _line_map:
                        _label_name, _line_offset = _line_map[_target_line]
                        try:
                            _do_target, state = _globals["_" + _label_name](
                                _rt, state, _scope, _start_offset=_line_offset
                            )
                        except GotoExternal as _goto:
                            _scope.update({k: v for k, v in state._locals.items()})
                            run_with_goto_support(
                                resolve_goto_target(_goto), _rt, _scope
                            )
                            for _k, _v in _scope.items():
                                if isinstance(_v, MArray):
                                    state._locals[_k] = _v
                                else:
                                    _m = MArray()
                                    _m.value = _v
                                    state._locals[_k] = _m
                            _do_target = None
                        else:
                            while _do_target is not None:
                                try:
                                    assert isinstance(_do_target, str)
                                    _do_func = _labels[_do_target]
                                    _do_target, state = _do_func(_rt, state, _scope)
                                except GotoExternal as _goto:
                                    _scope.update(
                                        {k: v for k, v in state._locals.items()}
                                    )
                                    run_with_goto_support(
                                        resolve_goto_target(_goto), _rt, _scope
                                    )
                                    for _k, _v in _scope.items():
                                        if isinstance(_v, MArray):
                                            state._locals[_k] = _v
                                        else:
                                            _m = MArray()
                                            _m.value = _v
                                            state._locals[_k] = _m
                                    _do_target = None
                    else:
                        raise ValueError(
                            f"Entry point {_call_target.label}+{_call_target.offset} not valid"
                        )
                else:
                    try:
                        _do_target, state = _func(_rt, state, _scope)
                    except GotoExternal as _goto:
                        _scope.update({k: v for k, v in state._locals.items()})
                        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                        for _k, _v in _scope.items():
                            if isinstance(_v, MArray):
                                state._locals[_k] = _v
                            else:
                                _m = MArray()
                                _m.value = _v
                                state._locals[_k] = _m
                        _do_target = None
                    else:
                        while _do_target is not None:
                            try:
                                assert isinstance(_do_target, str)
                                _do_func = _labels[_do_target]
                                _do_target, state = _do_func(_rt, state, _scope)
                            except GotoExternal as _goto:
                                _scope.update({k: v for k, v in state._locals.items()})
                                run_with_goto_support(
                                    resolve_goto_target(_goto), _rt, _scope
                                )
                                for _k, _v in _scope.items():
                                    if isinstance(_v, MArray):
                                        state._locals[_k] = _v
                                    else:
                                        _m = MArray()
                                        _m.value = _v
                                        state._locals[_k] = _m
                                _do_target = None
    if _start_offset <= 4:
        state._locals.setdefault("VCORR", MArray()).value = "10 98 "  # noqa: F841
    if _start_offset <= 4:
        _saved_extrinsic = _rt._in_extrinsic
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="V1IDDOA", label="EXAMINER")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        EXAMINER(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _saved_extrinsic
    return ("END", state)


def _END(_rt, state, _scope, _start_offset=0) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write_newline()
        _rt.write_newline()
        _rt.write("END OF V1IDDOA")
        _rt.write_newline()
    if _start_offset <= 1:
        state._locals.setdefault("ROUTINE", MArray()).value = "V1IDDOA"  # noqa: F841
        state._locals.setdefault("TESTS", MArray()).value = 7  # noqa: F841
        state._locals.setdefault("AUTO", MArray()).value = 7  # noqa: F841
        state._locals.setdefault("VISUAL", MArray()).value = 0  # noqa: F841
    if _start_offset <= 1:
        import VREPORT

        _saved_routine = _rt._current_routine
        _saved_source_lines = _rt._current_source_lines
        _saved_label_lines = _rt._current_label_lines
        _scope.update({k: v for k, v in state._locals.items()})
        _rt.push_stack_frame("DO", routine="VREPORT", label="")
        run_with_goto_support(VREPORT._entry_function, _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt._current_routine = _saved_routine
        _rt._current_source_lines = _saved_source_lines
        _rt._current_label_lines = _saved_label_lines
        _rt.pop_stack_frame()
        _test = _rt._test
    if _start_offset <= 2:
        state._locals.clear()
    if _start_offset <= 2:
        _rt.globals.kill("V1A", ())
        _rt.globals.kill("V1IDO1", ())
    if _start_offset <= 2:
        return (None, state)
    return ("EXAMINER", state)


def _EXAMINER(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        _test = m_truth(
            m_compare(
                m_var_value(state._locals.get("VCORR")),
                "=",
                m_var_value(state._locals.get("VCOMP")),
            )
        )
        _rt._test = _test
        if _test:
            state._locals.setdefault("PASS", MArray()).value = m_add(
                m_var_value(state._locals.get("PASS")), 1
            )  # noqa: F841
            _rt.write_newline()
            _rt.write("   PASS  ")
            _rt.write(m_var_value(state._locals.get("ITEM")))
            if m_truth(m_compare(_rt.y(), ">", 55)):
                _rt.write_formfeed()
            return (None, state)
    if _start_offset <= 1:
        state._locals.setdefault("FAIL", MArray()).value = m_add(
            m_var_value(state._locals.get("FAIL")), 1
        )  # noqa: F841
    if _start_offset <= 1:
        _rt.write_newline()
        _rt.write("** FAIL  ")
        _rt.write(m_var_value(state._locals.get("ITEM")))
    if _start_offset <= 1:
        if m_truth(m_compare(_rt.y(), ">", 55)):
            _rt.write_formfeed()
    if _start_offset <= 2:
        _rt.write_newline()
        _rt.write('           COMPUTED ="')
        _rt.write(m_var_value(state._locals.get("VCOMP")))
        _rt.write('"')
    if _start_offset <= 2:
        if m_truth(m_compare(_rt.y(), ">", 55)):
            _rt.write_formfeed()
    if _start_offset <= 3:
        _rt.write_newline()
        _rt.write('           CORRECT  ="')
        _rt.write(m_var_value(state._locals.get("VCORR")))
        _rt.write('"')
    if _start_offset <= 3:
        if m_truth(m_compare(_rt.y(), ">", 55)):
            _rt.write_formfeed()
    if _start_offset <= 4:
        return (None, state)
    return ("98", state)


def __n_98(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("98 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("00980", state)


def __n_00980(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 470
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("00980 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("0098", state)


def __n_0098(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 470
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("0098 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("ROUTINE", state)


def _ROUTINE(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 474
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("ROUTINE ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("1", state)


def __n_1(_rt, state, _scope, _start_offset=0) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 461,473
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("1 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    if _start_offset <= 1:
        # 464,473
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("2 ")  # noqa: F841
    if _start_offset <= 1:
        return (None, state)
    return ("DREI", state)


def _DREI(_rt, state, _scope, _start_offset=0) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 473
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("3 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("SIEBEN7", state)


def _SIEBEN7(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str(7)  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    if _start_offset <= 1:
        # 472
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("SIEBEN7+1 ")  # noqa: F841
    if _start_offset <= 1:
        return (None, state)
    return ("%BREAK", state)


def __pct_BREAK(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 472
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("%BREAK ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("ENTRY", state)


def _ENTRY(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("ENTRY ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    if _start_offset <= 1:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("ENTRY1 ")  # noqa: F841
    if _start_offset <= 1:
        return (None, state)
    return ("ENTRY2", state)


def _ENTRY2(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("ENTRY2 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    if _start_offset <= 1:
        # 463
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("ENTRY3 ")  # noqa: F841
    if _start_offset <= 1:
        return (None, state)
    if _start_offset <= 2:
        return (None, state)
    return ("ONE", state)


def _ONE(_rt, state, _scope, _start_offset=0) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("ONE ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("TWO", state)


def _TWO(_rt, state, _scope, _start_offset=0) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        # 462
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("TWO ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("THREE", state)


def _THREE(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("THREE ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("%", state)


def __pct_(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("% ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("0123", state)


def __n_0123(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("0123 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("012", state)


def __n_012(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("012 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    return ("000001", state)


def __n_000001(
    _rt, state, _scope, _start_offset=0
) -> Tuple[str | int | None, RoutineState]:
    global _test
    if _start_offset <= 0:
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("000001 ")  # noqa: F841
    if _start_offset <= 0:
        return (None, state)
    if _start_offset <= 1:
        # 465
        state._locals.setdefault("VCOMP", MArray()).value = m_str(
            m_var_value(state._locals.get("VCOMP"))
        ) + m_str("000001+1 ")  # noqa: F841
    if _start_offset <= 1:
        return (None, state)
    return (None, state)


_labels = {
    "V1IDDOA": _V1IDDOA,
    "461": __n_461,
    "462": __n_462,
    "463": __n_463,
    "464": __n_464,
    "465": __n_465,
    "466": __n_466,
    "467": __n_467,
    "END": _END,
    "EXAMINER": _EXAMINER,
    "98": __n_98,
    "00980": __n_00980,
    "0098": __n_0098,
    "ROUTINE": _ROUTINE,
    "1": __n_1,
    "DREI": _DREI,
    "SIEBEN7": _SIEBEN7,
    "%BREAK": __pct_BREAK,
    "ENTRY": _ENTRY,
    "ENTRY2": _ENTRY2,
    "ONE": _ONE,
    "TWO": _TWO,
    "THREE": _THREE,
    "%": __pct_,
    "0123": __n_0123,
    "012": __n_012,
    "000001": __n_000001,
}

_line_map: dict[int, tuple[str, int]] = {
    1: ("V1IDDOA", 0),
    3: ("V1IDDOA", 2),
    4: ("V1IDDOA", 3),
    5: ("_n_461", 0),
    6: ("_n_461", 1),
    7: ("_n_461", 2),
    8: ("_n_461", 3),
    10: ("_n_462", 0),
    11: ("_n_462", 1),
    12: ("_n_462", 2),
    13: ("_n_462", 3),
    14: ("_n_462", 4),
    16: ("_n_463", 0),
    17: ("_n_463", 1),
    18: ("_n_463", 2),
    19: ("_n_463", 3),
    21: ("_n_464", 0),
    22: ("_n_464", 1),
    23: ("_n_464", 2),
    24: ("_n_464", 3),
    26: ("_n_465", 0),
    27: ("_n_465", 1),
    28: ("_n_465", 2),
    29: ("_n_465", 3),
    30: ("_n_465", 4),
    32: ("_n_466", 0),
    33: ("_n_466", 1),
    34: ("_n_466", 2),
    35: ("_n_466", 3),
    36: ("_n_466", 4),
    37: ("_n_466", 5),
    39: ("_n_467", 0),
    40: ("_n_467", 1),
    41: ("_n_467", 2),
    42: ("_n_467", 3),
    43: ("_n_467", 4),
    45: ("END", 0),
    46: ("END", 1),
    47: ("END", 2),
    49: ("EXAMINER", 0),
    50: ("EXAMINER", 1),
    51: ("EXAMINER", 2),
    52: ("EXAMINER", 3),
    53: ("EXAMINER", 4),
    54: ("_n_98", 0),
    55: ("_n_00980", 0),
    56: ("_n_0098", 0),
    57: ("ROUTINE", 0),
    58: ("_n_1", 0),
    59: ("_n_1", 1),
    60: ("DREI", 0),
    61: ("SIEBEN7", 0),
    62: ("SIEBEN7", 1),
    63: ("_pct_BREAK", 0),
    64: ("ENTRY", 0),
    65: ("ENTRY", 1),
    66: ("ENTRY2", 0),
    67: ("ENTRY2", 1),
    68: ("ENTRY2", 2),
    69: ("ONE", 0),
    70: ("TWO", 0),
    71: ("THREE", 0),
    72: ("_pct_", 0),
    73: ("_n_0123", 0),
    74: ("_n_012", 0),
    75: ("_n_000001", 0),
    76: ("_n_000001", 1),
}


def V1IDDOA(_rt, _scope=None):
    """Trampoline dispatcher for routine execution."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    target: str | int | None = "V1IDDOA"

    while target is not None:
        try:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
        except GotoExternal as _goto:
            _scope.update({k: v for k, v in state._locals.items()})
            run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
            for _k, _v in _scope.items():
                if isinstance(_v, MArray):
                    state._locals[_k] = _v
                else:
                    _m = MArray()
                    _m.value = _v
                    state._locals[_k] = _m
            target = None
        except Exception as _e:
            if _rt._handle_etrap(_e, _scope):
                return state  # $ETRAP cleared $ECODE, implicit QUIT
            raise  # Propagate to caller

    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return state


def _n_461(_rt, _scope=None):
    """Entry point for DO 461 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_461(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_462(_rt, _scope=None):
    """Entry point for DO 462 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_462(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_463(_rt, _scope=None):
    """Entry point for DO 463 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_463(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_464(_rt, _scope=None):
    """Entry point for DO 464 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_464(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_465(_rt, _scope=None):
    """Entry point for DO 465 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_465(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_466(_rt, _scope=None):
    """Entry point for DO 466 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_466(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_467(_rt, _scope=None):
    """Entry point for DO 467 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_467(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def END(_rt, _scope=None):
    """Entry point for DO END calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _END(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def EXAMINER(_rt, _scope=None):
    """Entry point for DO EXAMINER calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _EXAMINER(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_98(_rt, _scope=None):
    """Entry point for DO 98 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_98(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_00980(_rt, _scope=None):
    """Entry point for DO 00980 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_00980(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_0098(_rt, _scope=None):
    """Entry point for DO 0098 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_0098(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def ROUTINE(_rt, _scope=None):
    """Entry point for DO ROUTINE calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _ROUTINE(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_1(_rt, _scope=None):
    """Entry point for DO 1 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_1(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def DREI(_rt, _scope=None):
    """Entry point for DO DREI calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _DREI(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def SIEBEN7(_rt, _scope=None):
    """Entry point for DO SIEBEN7 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _SIEBEN7(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _pct_BREAK(_rt, _scope=None):
    """Entry point for DO %BREAK calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __pct_BREAK(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def ENTRY(_rt, _scope=None):
    """Entry point for DO ENTRY calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _ENTRY(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def ENTRY2(_rt, _scope=None):
    """Entry point for DO ENTRY2 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _ENTRY2(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def ONE(_rt, _scope=None):
    """Entry point for DO ONE calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _ONE(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def TWO(_rt, _scope=None):
    """Entry point for DO TWO calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _TWO(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def THREE(_rt, _scope=None):
    """Entry point for DO THREE calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = _THREE(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _pct_(_rt, _scope=None):
    """Entry point for DO % calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __pct_(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_0123(_rt, _scope=None):
    """Entry point for DO 0123 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_0123(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_012(_rt, _scope=None):
    """Entry point for DO 012 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_012(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


def _n_000001(_rt, _scope=None):
    """Entry point for DO 000001 calls."""
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    state = RoutineState()
    for _k, _v in _scope.items():
        if isinstance(_v, MArray):
            state._locals[_k] = _v
        else:
            _m = MArray()
            _m.value = _v
            state._locals[_k] = _m
    try:
        target, state = __n_000001(_rt, state, _scope)
        while target is not None:
            if isinstance(target, int):
                label_name, offset = _line_map[target]
                func = _globals["_" + label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            elif isinstance(target, tuple):
                label_name, offset = target
                func = _labels[label_name]
                target, state = func(_rt, state, _scope, _start_offset=offset)
            else:
                func = _labels[target]
                target, state = func(_rt, state, _scope)
    except GotoExternal as _goto:
        _scope.update({k: v for k, v in state._locals.items()})
        run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
    _pre_unwind = set(state._locals.keys())
    unwind_new_stack(state)
    for _k in _pre_unwind - set(state._locals.keys()):
        _scope.pop(_k, None)
    _scope.update({k: v for k, v in state._locals.items()})
    return (
        getattr(state, "_return_value", None)
        if hasattr(state, "_return_value")
        else state
    )


_entry_function = V1IDDOA


if __name__ == "__main__":
    _rt = MUMPSRuntime()
    _scope = {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    V1IDDOA(_rt, _scope=_scope)
