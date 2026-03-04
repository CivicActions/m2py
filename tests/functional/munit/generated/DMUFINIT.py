from decimal import Decimal
from m2py.codegen.helpers import m_str, m_num, m_truth, m_compare, m_add, m_mod
from m2py.runtime import (
    MUMPSRuntime,
    MArray,
    run_with_goto_support,
    resolve_goto_target,
    GotoExternal,
)
from m2py.runtime.helpers import (
    m_set_piece,
    m_data,
    m_data_global,
    _raise_select_false,
    m_piece,
    m_extract,
    m_get,
    m_var_value,
    unwind_new_stack,
)
from dataclasses import dataclass, field
from typing import Tuple

_test = False

_globals = globals()

_source_lines = [
    "DMUFINIT ;VEN/SMH-FILEMAN UNIT TEST INIT ;2015-01-05  7:53 AM",
    " ;;22.2;MSC Fileman;;Jan 05, 2015;",
    " ;;Submitted to OSEHRA 5 January 2015 by the VISTA Expertise Network.",
    " ;;Based on Medsphere Systems Corporation's MSC Fileman 1051.",
    " ;;Licensed under the terms of the Apache License, Version 2.0.",
    " ;",
    " K DIF,DIFQ,DIFQR,DIFQN,DIK,DDF,DDT,DTO,D0,DLAYGO,DIC,DIDUZ,DIR,DA,DIFROM,DFR,DTN,DIX,DZ,DIRUT,DTOUT,DUOUT",
    ' S DIOVRD=1,U="^",DIFQ=0,DIFROM="0.1" W !,"This version (#0.1) of \'DMUFINIT\' was created on 10-JAN-2013"',
    ' W !?9,"(at FILEMAN.MUMPS.ORG, by VA FILEMAN 22.2)",!',
    ' I $D(^DD("VERSION")),^("VERSION")\'<22.2 G GO',
    ' ;W !,"FIRST, I\'LL FRESHEN UP YOUR VA FILEMAN...." D N^DINIT',
    ' ; I ^DD("VERSION")<22.2 W !,"but I need version 22.2 of the VA FileMan!" G Q ;VEN/SMH',
    "GO ;",
    "EN ; ENTER HERE TO BYPASS THE PRE-INIT PROGRAM",
    " S DIFQ=0 K DIRUT,DTOUT,DUOUT",
    ' F DIFRIR=1:1:1 S DIFRRTN="^DMUFINI"_$E("5",DIFRIR) D @DIFRRTN',
    ' W:1 !,"I AM GOING TO SET UP THE FOLLOWING FILES:" F I=1:2:4 S DIF(I)=^UTILITY("DIF",$J,I) D 1 G Q:DIFQ!$D(DIRUT) K DIF(I)',
    ' S DIFROM="0.1" D PKG:\'$D(DIFROM(0)),^DMUFINI1 G Q:\'$D(DIFQ) S DIK(0)="AB"',
    ' F DIF=1:2:4 S %=^UTILITY("DIF",$J,DIF),DIK=$P(%,";",5),N=$P(%,";",3),D=$P(%,";",4)_U_N D D K DIFQ(N)',
    " K DIFQR D ^DMUFINI2,^DMUFINI3",
    ' L  S DUZ=DIDUZ W:1 !,$C(7),"OK, I\'M DONE.",!,"NO"_$P("TE THAT FILE",U,DSEC)_" SECURITY-CODE PROTECTION HAS BEEN MADE"',
    ' I DIFROM F DIF=1:2:4 S %=^UTILITY("DIF",$J,DIF),N=+$P(%,";",3) I N,$P(%,";",8)="y" S ^DD(N,0,"VR")=DIFROM',
    ' I DIFROM(0)>0 F %="PRE","INI","INIT" S:$D(DIFROM(%)) $P(^DIC(9.4,DIFROM(0),%),U,2)=DIFROM(%)',
    " I $G(DIFQN) S $P(^(0),U,3,4)=$P(DIFQN,U,2)_U_($P(^DIC(0),U,4)+DIFQN) K DIFQN",
    ' I DIFROM,$D(^%ZTSK) S X="DMUFINIS" X ^%ZOSF("TEST") D:$T PAC^DMUFINIS($T(IXF),.DIFROM)',
    ' S:DIFROM(0)>0 ^DIC(9.4,DIFROM(0),"VERSION")=DIFROM G Q^DIFROM0',
    'D S:$D(^DIC(+N,0))[0 ^(0)=D S X=$D(@(DIK_"0)")),^(0)=D_U_$S(X#2:$P(^(0),U,3,9),1:U)',
    ' S DIFQR=DIFQR(+N) I ^DD("VERSION")>17.5,$D(^DD(+N,0,"DIK"))#2 S X=^("DIK"),Y=+N,DMAX=^DD("ROU") D EN^DIKZ',
    ' I DIFQR D IXALL^DIK:$O(@(DIK_"0)")) W "."',
    " Q",
    "R G REP^DMUFINI2",
    " ;",
    '1 S N=+$P(DIF(I),";",3),DIF=$P(DIF(I),";",4),S=$P(DIF(I),";",5)',
    ' W !!?3,N,?13,DIF,$P("  (Partial Definition)",U,$P(DIF(I),";",6)),$P("  (including data)",U,$P(DIF(I),";",13)="y") S Z=$S($D(^DIC(N,0))#2:^(0),1:"")',
    ' I Z="" S DIFQ(N)=1,DIFQN=$G(DIFQN)+1_U_N G S',
    ' I $L($P(Z,DIF)) W $C(7),!,"*BUT YOU ALREADY HAVE \'",$P(Z,U),"\' AS FILE #",N,"!" D R Q:DIFQ  G S:$D(DIFKEP(N)),1',
    ' S DIFQ(N)=$P(DIF(I),";",7)\'="n"',
    ' I $L(Z) W $C(7),!,"Note:  You already have the \'",$P(Z,U),"\' File." S DIFQ(0)=1',
    ' S %=$E(^UTILITY("DIF",$J,I+1),4,245) I %]"" X % S DIFQ(N)=$T W:\'$T !,"Screen on this Data Dictionary did not pass--DD will not be installed!" G S',
    ' I $L(Z),$P(DIF(I),";",10)="y" S DIR("A")="Shall I write over the existing Data Definition",DIR("??")="^D DD^DIFROMH1",DIR("B")="YES",DIR(0)="Y" D ^DIR S DIFQ(N)=Y',
    'S S DIFQR(N)=0 Q:$P(DIF(I),";",13)\'="y"!$D(DIRUT)',
    ' I $P(DIF(I),";",15)="y",$O(@(S_"0)"))>0 S DIF=$P(DIF(I),";",14)="o",DIR("A")="Want my data "_$P("merged with^to overwrite",U,DIF+1)_" yours",DIR("??")="^D DTA^DIFROMH1",DIR(0)="Y" D ^DIR S DIFQR(N)=$S(\'Y:Y,1:Y+DIF) Q',
    ' S %=$P(DIF(I),";",14)="o" W !,$C(7),"I will ",$P("MERGE^OVERWRITE",U,%+1)," your data with mine." S DIFQR(N)=%+1',
    " Q",
    'Q W $C(7),!!,"NO UPDATING HAS OCCURRED!" G Q^DIFROM0',
    " ;",
    'PKG S X=$P($T(IXF),";",3),DIC="^DIC(9.4,",DIC(0)="",DIC("S")="I $P(^(0),U,2)="""_$P(X,U,2)_"""",X=$P(X,U) D ^DIC S DIFROM(0)=+Y K DIC',
    " Q",
    " ;",
    "IXF ;;FILEMAN EXTENSIONS FILES^DMUF;1",
]

_routine_name = "DMUFINIT"

_label_lines = {
    "DMUFINIT": 0,
    "GO": 12,
    "EN": 13,
    "D": 26,
    "R": 30,
    "1": 32,
    "S": 40,
    "Q": 44,
    "PKG": 46,
    "IXF": 49,
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
    _saved_routine = _rt._current_routine
    _saved_source_lines = _rt._current_source_lines
    _saved_label_lines = _rt._current_label_lines
    _rt._extrinsic_stack.append(_rt._in_extrinsic)
    _rt.push_stack_frame("$$", label=getattr(_ef, "__name__", ""))
    try:
        _rt._in_extrinsic = True
        _current_ef = _ef
        _current_args = args
        while True:
            try:
                if _scope is not None:
                    _result = _current_ef(_rt, *_current_args, _scope=_scope)
                else:
                    _result = _current_ef(_rt, *_current_args)
                break
            except GotoExternal as _goto:
                _current_ef = resolve_goto_target(_goto)
                _current_args = ()  # GOTO target receives args via _scope
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
        _rt._current_routine = _saved_routine
        _rt._current_source_lines = _saved_source_lines
        _rt._current_label_lines = _saved_label_lines
        _rt._in_extrinsic = _rt._extrinsic_stack.pop()


class _XecuteExit(Exception):
    """Exception for control flow exit from inline XECUTE."""

    pass


def _DMUFINIT(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    state._locals.get("DIF", MArray()).kill()
    state._locals.get("DIFQ", MArray()).kill()
    state._locals.get("DIFQR", MArray()).kill()
    state._locals.get("DIFQN", MArray()).kill()
    state._locals.get("DIK", MArray()).kill()
    state._locals.get("DDF", MArray()).kill()
    state._locals.get("DDT", MArray()).kill()
    state._locals.get("DTO", MArray()).kill()
    state._locals.get("D0", MArray()).kill()
    state._locals.get("DLAYGO", MArray()).kill()
    state._locals.get("DIC", MArray()).kill()
    state._locals.get("DIDUZ", MArray()).kill()
    state._locals.get("DIR", MArray()).kill()
    state._locals.get("DA", MArray()).kill()
    state._locals.get("DIFROM", MArray()).kill()
    state._locals.get("DFR", MArray()).kill()
    state._locals.get("DTN", MArray()).kill()
    state._locals.get("DIX", MArray()).kill()
    state._locals.get("DZ", MArray()).kill()
    state._locals.get("DIRUT", MArray()).kill()
    state._locals.get("DTOUT", MArray()).kill()
    state._locals.get("DUOUT", MArray()).kill()
    state._locals.setdefault("DIOVRD", MArray()).value = 1
    state._locals.setdefault("U", MArray()).value = "^"
    state._locals.setdefault("DIFQ", MArray()).value = 0
    state._locals.setdefault("DIFROM", MArray()).value = "0.1"
    _rt.write_newline()
    _rt.write("This version (#0.1) of 'DMUFINIT' was created on 10-JAN-2013")
    _rt.write_newline()
    _rt.write_tab(int(m_num(9)))
    _rt.write("(at FILEMAN.MUMPS.ORG, by VA FILEMAN 22.2)")
    _rt.write_newline()
    if (_test := m_truth(m_data_global(_rt.globals, "DD", ("VERSION",)))) and (
        _test := m_truth(
            int(
                not m_compare(
                    (_rt.globals.get(*_rt.globals.resolve_naked(("VERSION",))) or ""),
                    "<",
                    Decimal("22.2"),
                )
            )
        )
    ):
        return ("GO", state)
    _rt._test = _test
    return ("GO", state)


def _GO(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    pass
    return ("EN", state)


def _EN(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    state._locals.setdefault("DIFQ", MArray()).value = 0
    state._locals.get("DIRUT", MArray()).kill()
    state._locals.get("DTOUT", MArray()).kill()
    state._locals.get("DUOUT", MArray()).kill()
    _for_start_0 = m_num(1)
    _for_step_0 = m_num(1)
    _for_end_0 = m_num(1)
    DIFRIR = _for_start_0
    state._locals.setdefault("DIFRIR", MArray()).value = _for_start_0
    while (
        (_for_step_0 > 0 and DIFRIR <= _for_end_0)
        or (_for_step_0 < 0 and DIFRIR >= _for_end_0)
        or (_for_step_0 == 0 and DIFRIR <= _for_end_0)
    ):
        state._locals.setdefault("DIFRIR", MArray()).value = DIFRIR
        state._locals.setdefault("DIFRRTN", MArray()).value = m_str("^DMUFINI") + m_str(
            m_extract(
                m_str("5"),
                int(m_num(m_var_value(state._locals["DIFRIR"]))),
                int(m_num(m_var_value(state._locals["DIFRIR"]))),
            )
        )
        _call_targets = _rt.resolve_do_targets(
            str(m_var_value(state._locals["DIFRRTN"])), state._locals
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
            if _call_target.args_str:
                _xecute_target = _call_target.label or ""
                if _call_target.routine:
                    _xecute_target = _xecute_target + "^" + _call_target.routine
                _xecute_target = _xecute_target + _call_target.args_str
                _rt.execute_mumps("D " + _xecute_target, state._locals)
                for _k, _v in _scope.items():
                    if isinstance(_v, MArray):
                        state._locals[_k] = _v
                    else:
                        _m = MArray()
                        _m.value = _v
                        state._locals[_k] = _m
            elif _call_target.routine and _call_target.routine != _routine_name:
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
                        _rt, _scope=state._locals, _start_offset=_line_offset
                    )
                else:
                    _func(_rt, _scope=state._locals)
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
        DIFRIR = m_add(DIFRIR, _for_step_0)
    if m_truth(1):
        _rt.write_newline()
        _rt.write("I AM GOING TO SET UP THE FOLLOWING FILES:")
    _goto_label = None
    _for_start_1 = m_num(1)
    _for_step_1 = m_num(2)
    _for_end_1 = m_num(4)
    _a_I = _for_start_1
    state._locals.setdefault("_a_I", MArray()).value = _for_start_1
    while (
        (_for_step_1 > 0 and _a_I <= _for_end_1)
        or (_for_step_1 < 0 and _a_I >= _for_end_1)
        or (_for_step_1 == 0 and _a_I <= _for_end_1)
    ):
        state._locals.setdefault("_a_I", MArray()).value = _a_I
        state._locals.setdefault("DIF", MArray())[
            m_var_value(state._locals["_a_I"])
        ] = (
            _rt.globals.get(
                "UTILITY",
                (
                    "DIF",
                    _rt.job(),
                    m_var_value(state._locals["_a_I"]),
                ),
            )
            or ""
        )
        _rt._extrinsic_stack.append(_rt._in_extrinsic)
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="DMUFINIT", label="1")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        _n_1(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _rt._extrinsic_stack.pop()
        if m_truth(
            int(
                m_truth(m_var_value(state._locals["DIFQ"]))
                or m_truth(m_data(state._locals.get("DIRUT", MArray()), ()))
            )
        ):
            _goto_label = "Q"
            break
        state._locals.get("DIF", MArray()).kill(m_var_value(state._locals["_a_I"]))
        _a_I = m_add(_a_I, _for_step_1)
    if _goto_label is not None:
        return (_goto_label, state)
    state._locals.setdefault("DIFROM", MArray()).value = "0.1"
    if m_truth(int(not m_truth(m_data(state._locals.get("DIFROM", MArray()), (0,))))):
        _rt._extrinsic_stack.append(_rt._in_extrinsic)
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="DMUFINIT", label="PKG")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        PKG(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _rt._extrinsic_stack.pop()
    import DMUFINI1

    _saved_routine = _rt._current_routine
    _saved_source_lines = _rt._current_source_lines
    _saved_label_lines = _rt._current_label_lines
    _scope.update({k: v for k, v in state._locals.items()})
    _rt.push_stack_frame("DO", routine="DMUFINI1", label="")
    run_with_goto_support(DMUFINI1._entry_function, _rt, _scope)
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
    if m_truth(int(not m_truth(m_data(state._locals.get("DIFQ", MArray()), ())))):
        return ("Q", state)
    state._locals.setdefault("DIK", MArray())[0] = "AB"
    _for_start_2 = m_num(1)
    _for_step_2 = m_num(2)
    _for_end_2 = m_num(4)
    DIF = _for_start_2
    state._locals.setdefault("DIF", MArray()).value = _for_start_2
    while (
        (_for_step_2 > 0 and DIF <= _for_end_2)
        or (_for_step_2 < 0 and DIF >= _for_end_2)
        or (_for_step_2 == 0 and DIF <= _for_end_2)
    ):
        state._locals.setdefault("DIF", MArray()).value = DIF
        state._locals.setdefault("_pct_", MArray()).value = (
            _rt.globals.get(
                "UTILITY",
                (
                    "DIF",
                    _rt.job(),
                    m_var_value(state._locals["DIF"]),
                ),
            )
            or ""
        )
        state._locals.setdefault("DIK", MArray()).value = m_piece(
            m_str(m_var_value(state._locals["_pct_"])), m_str(";"), int(m_num(5))
        )
        state._locals.setdefault("N", MArray()).value = m_piece(
            m_str(m_var_value(state._locals["_pct_"])), m_str(";"), int(m_num(3))
        )
        state._locals.setdefault("D", MArray()).value = m_str(
            (
                m_str(
                    m_piece(
                        m_str(m_var_value(state._locals["_pct_"])),
                        m_str(";"),
                        int(m_num(4)),
                    )
                )
                + m_str(m_var_value(state._locals["U"]))
            )
        ) + m_str(m_var_value(state._locals["N"]))
        _rt._extrinsic_stack.append(_rt._in_extrinsic)
        _rt._in_extrinsic = False
        _rt.push_stack_frame("DO", routine="DMUFINIT", label="D")
        for _k in list(_scope.keys()):
            if _k not in state._locals:
                del _scope[_k]
        _scope.update({k: v for k, v in state._locals.items()})
        D(_rt, _scope=_scope)
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        _rt.pop_stack_frame()
        _rt._in_extrinsic = _rt._extrinsic_stack.pop()
        state._locals.get("DIFQ", MArray()).kill(m_var_value(state._locals["N"]))
        DIF = m_add(DIF, _for_step_2)
    state._locals.get("DIFQR", MArray()).kill()
    import DMUFINI2

    _saved_routine = _rt._current_routine
    _saved_source_lines = _rt._current_source_lines
    _saved_label_lines = _rt._current_label_lines
    _scope.update({k: v for k, v in state._locals.items()})
    _rt.push_stack_frame("DO", routine="DMUFINI2", label="")
    run_with_goto_support(DMUFINI2._entry_function, _rt, _scope)
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
    import DMUFINI3

    _saved_routine = _rt._current_routine
    _saved_source_lines = _rt._current_source_lines
    _saved_label_lines = _rt._current_label_lines
    _scope.update({k: v for k, v in state._locals.items()})
    _rt.push_stack_frame("DO", routine="DMUFINI3", label="")
    run_with_goto_support(DMUFINI3._entry_function, _rt, _scope)
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
    _rt.globals.unlock_all()
    state._locals.setdefault("DUZ", MArray()).value = m_var_value(
        state._locals["DIDUZ"]
    )
    if m_truth(1):
        _rt.write_newline()
        _rt.write((chr(int(m_num(7))) if int(m_num(7)) >= 0 else ""))
        _rt.write("OK, I'M DONE.")
        _rt.write_newline()
        _rt.write(
            (
                m_str(
                    (
                        m_str("NO")
                        + m_str(
                            m_piece(
                                m_str("TE THAT FILE"),
                                m_str(m_var_value(state._locals["U"])),
                                int(m_num(m_var_value(state._locals["DSEC"]))),
                            )
                        )
                    )
                )
                + m_str(" SECURITY-CODE PROTECTION HAS BEEN MADE")
            )
        )
    _test = m_truth(m_var_value(state._locals["DIFROM"]))
    _rt._test = _test
    if _test:
        _for_start_3 = m_num(1)
        _for_step_3 = m_num(2)
        _for_end_3 = m_num(4)
        DIF = _for_start_3
        state._locals.setdefault("DIF", MArray()).value = _for_start_3
        while (
            (_for_step_3 > 0 and DIF <= _for_end_3)
            or (_for_step_3 < 0 and DIF >= _for_end_3)
            or (_for_step_3 == 0 and DIF <= _for_end_3)
        ):
            state._locals.setdefault("DIF", MArray()).value = DIF
            state._locals.setdefault("_pct_", MArray()).value = (
                _rt.globals.get(
                    "UTILITY",
                    (
                        "DIF",
                        _rt.job(),
                        m_var_value(state._locals["DIF"]),
                    ),
                )
                or ""
            )
            state._locals.setdefault("N", MArray()).value = +m_num(
                m_piece(
                    m_str(m_var_value(state._locals["_pct_"])),
                    m_str(";"),
                    int(m_num(3)),
                )
            )
            if (_test := m_truth(m_var_value(state._locals["N"]))) and (
                _test := m_truth(
                    m_compare(
                        m_piece(
                            m_str(m_var_value(state._locals["_pct_"])),
                            m_str(";"),
                            int(m_num(8)),
                        ),
                        "=",
                        "y",
                    )
                )
            ):
                _rt.globals.set(
                    "DD",
                    (
                        m_var_value(state._locals["N"]),
                        0,
                        "VR",
                    ),
                    m_str(m_var_value(state._locals["DIFROM"])),
                )
            _rt._test = _test
            DIF = m_add(DIF, _for_step_3)
    _test = m_truth(m_compare(state._locals.get("DIFROM", MArray()).get(0), ">", 0))
    _rt._test = _test
    if _test:
        for _pct_ in ["PRE", "INI", "INIT"]:
            state._locals.setdefault("_pct_", MArray()).value = _pct_
            if m_truth(
                m_data(
                    state._locals.get("DIFROM", MArray()),
                    (m_var_value(state._locals["_pct_"]),),
                )
            ):
                m_set_piece(
                    lambda: (
                        _rt.globals.get(
                            "DIC",
                            (
                                str(Decimal("9.4")),
                                str(state._locals.get("DIFROM", MArray()).get(0)),
                                str(m_var_value(state._locals["_pct_"])),
                            ),
                        )
                        or ""
                    ),
                    lambda v: _rt.globals.set(
                        "DIC",
                        (
                            str(Decimal("9.4")),
                            str(state._locals.get("DIFROM", MArray()).get(0)),
                            str(m_var_value(state._locals["_pct_"])),
                        ),
                        v,
                    ),
                    m_str(m_var_value(state._locals["U"])),
                    int(m_num(2)),
                    None,
                    m_str(
                        state._locals.get("DIFROM", MArray()).get(
                            m_var_value(state._locals["_pct_"])
                        )
                    ),
                )
    _test = m_truth(m_get(state._locals.get("DIFQN", MArray()), (), ""))
    _rt._test = _test
    if _test:
        _sp_value = m_str(
            (
                m_str(
                    (
                        m_str(
                            m_piece(
                                m_str(m_var_value(state._locals["DIFQN"])),
                                m_str(m_var_value(state._locals["U"])),
                                int(m_num(2)),
                            )
                        )
                        + m_str(m_var_value(state._locals["U"]))
                    )
                )
                + m_str(
                    m_add(
                        m_piece(
                            m_str((_rt.globals.get("DIC", (0,)) or "")),
                            m_str(m_var_value(state._locals["U"])),
                            int(m_num(4)),
                        ),
                        m_var_value(state._locals["DIFQN"]),
                    )
                )
            )
        )
        _lhs_name_272, _lhs_subs_272 = _rt.globals.resolve_naked((0,))
        m_set_piece(
            lambda: _rt.globals.get(_lhs_name_272, _lhs_subs_272) or "",
            lambda v: _rt.globals.set(_lhs_name_272, _lhs_subs_272, v),
            m_str(m_var_value(state._locals["U"])),
            int(m_num(3)),
            int(m_num(4)),
            _sp_value,
        )
        state._locals.get("DIFQN", MArray()).kill()
    if (_test := m_truth(m_var_value(state._locals["DIFROM"]))) and (
        _test := m_truth(m_data_global(_rt.globals, "%ZTSK", ()))
    ):
        state._locals.setdefault("X", MArray()).value = "DMUFINIS"
        _scope.update({k: v for k, v in state._locals.items()})
        _rt.execute_mumps(
            (_rt.globals.get("%ZOSF", ("TEST",)) or ""), _scope, globals()
        )
        _test = _rt._test
        for _k, _v in _scope.items():
            if isinstance(_v, MArray):
                state._locals[_k] = _v
            else:
                _m = MArray()
                _m.value = _v
                state._locals[_k] = _m
        if m_truth(int(_test)):
            import DMUFINIS

            _saved_routine = _rt._current_routine
            _saved_source_lines = _rt._current_source_lines
            _saved_label_lines = _rt._current_label_lines
            _scope.update({k: v for k, v in state._locals.items()})
            _rt.push_stack_frame("DO", routine="DMUFINIS", label="PAC")
            if not hasattr(DMUFINIS, "PAC"):
                from m2py.runtime import LabelNotFoundError

                raise LabelNotFoundError(
                    "PAC", "DMUFINIS", list(DMUFINIS._label_lines.keys())
                )
            run_with_goto_support(
                lambda _rt, _scope=_scope: getattr(DMUFINIS, "PAC")(
                    _rt,
                    _rt.get_text(offset=0, label="IXF"),
                    _scope.setdefault("DIFROM", MArray()),
                    _scope=_scope,
                ),
                _rt,
                _scope,
            )
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
    _rt._test = _test
    if m_truth(m_compare(state._locals.get("DIFROM", MArray()).get(0), ">", 0)):
        _rt.globals.set(
            "DIC",
            (
                Decimal("9.4"),
                state._locals.get("DIFROM", MArray()).get(0),
                "VERSION",
            ),
            m_str(m_var_value(state._locals["DIFROM"])),
        )
    _scope.update({k: v for k, v in state._locals.items()})
    import DIFROM0

    raise GotoExternal(DIFROM0, "Q", _rt=_rt)
    return ("D", state)


def _D(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    if m_truth(
        int(
            m_str(0)
            in m_str(
                m_data_global(
                    _rt.globals,
                    "DIC",
                    (
                        (+m_num(m_var_value(state._locals["N"]))),
                        0,
                    ),
                )
            )
        )
    ):
        _naked_sub_vals = (0,)
        _naked_value = m_str(m_var_value(state._locals["D"]))
        _name, _subs = _rt.globals.resolve_naked(_naked_sub_vals)
        _rt.globals.set(_name, _subs, _naked_value)
    state._locals.setdefault("X", MArray()).value = _rt.data_indirected(
        str((m_str(m_var_value(state._locals["DIK"])) + m_str("0)"))),
        state._locals,
        levels=0,
    )
    _naked_sub_vals = (0,)
    _naked_value = m_str(
        (
            m_str(
                (
                    m_str(m_var_value(state._locals["D"]))
                    + m_str(m_var_value(state._locals["U"]))
                )
            )
            + m_str(
                (
                    m_piece(
                        m_str(
                            (_rt.globals.get(*_rt.globals.resolve_naked((0,))) or "")
                        ),
                        m_str(m_var_value(state._locals["U"])),
                        int(m_num(3)),
                        int(m_num(9)),
                    )
                    if m_truth(m_mod(m_var_value(state._locals["X"]), 2))
                    else (
                        m_var_value(state._locals["U"])
                        if m_truth(1)
                        else _raise_select_false()
                    )
                )
            )
        )
    )
    _name, _subs = _rt.globals.resolve_naked(_naked_sub_vals)
    _rt.globals.set(_name, _subs, _naked_value)
    state._locals.setdefault("DIFQR", MArray()).value = state._locals.get(
        "DIFQR", MArray()
    ).get((+m_num(m_var_value(state._locals["N"]))))
    if (
        _test := m_truth(
            m_compare((_rt.globals.get("DD", ("VERSION",)) or ""), ">", Decimal("17.5"))
        )
    ) and (
        _test := m_truth(
            m_mod(
                m_data_global(
                    _rt.globals,
                    "DD",
                    (
                        (+m_num(m_var_value(state._locals["N"]))),
                        0,
                        "DIK",
                    ),
                ),
                2,
            )
        )
    ):
        state._locals.setdefault("X", MArray()).value = (
            _rt.globals.get(*_rt.globals.resolve_naked(("DIK",))) or ""
        )
        state._locals.setdefault("Y", MArray()).value = +m_num(
            m_var_value(state._locals["N"])
        )
        state._locals.setdefault("DMAX", MArray()).value = (
            _rt.globals.get("DD", ("ROU",)) or ""
        )
        import DIKZ

        _saved_routine = _rt._current_routine
        _saved_source_lines = _rt._current_source_lines
        _saved_label_lines = _rt._current_label_lines
        _scope.update({k: v for k, v in state._locals.items()})
        _rt.push_stack_frame("DO", routine="DIKZ", label="EN")
        if not hasattr(DIKZ, "EN"):
            from m2py.runtime import LabelNotFoundError

            raise LabelNotFoundError("EN", "DIKZ", list(DIKZ._label_lines.keys()))
        run_with_goto_support(getattr(DIKZ, "EN"), _rt, _scope)
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
    _rt._test = _test
    _test = m_truth(m_var_value(state._locals["DIFQR"]))
    _rt._test = _test
    if _test:
        if m_truth(
            _rt.get_order(
                str((m_str(m_var_value(state._locals["DIK"])) + m_str("0)"))),
                state._locals,
                1,
            )
        ):
            import DIK

            _saved_routine = _rt._current_routine
            _saved_source_lines = _rt._current_source_lines
            _saved_label_lines = _rt._current_label_lines
            _scope.update({k: v for k, v in state._locals.items()})
            _rt.push_stack_frame("DO", routine="DIK", label="IXALL")
            if not hasattr(DIK, "IXALL"):
                from m2py.runtime import LabelNotFoundError

                raise LabelNotFoundError("IXALL", "DIK", list(DIK._label_lines.keys()))
            run_with_goto_support(getattr(DIK, "IXALL"), _rt, _scope)
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
        _rt.write(".")
    return (None, state)
    return ("R", state)


def _R(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    _scope.update({k: v for k, v in state._locals.items()})
    import DMUFINI2

    raise GotoExternal(DMUFINI2, "REP", _rt=_rt)
    return ("1", state)


def __n_1(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    while True:
        state._locals.setdefault("N", MArray()).value = +m_num(
            m_piece(
                m_str(
                    state._locals.get("DIF", MArray()).get(
                        m_var_value(state._locals["_a_I"])
                    )
                ),
                m_str(";"),
                int(m_num(3)),
            )
        )
        state._locals.setdefault("DIF", MArray()).value = m_piece(
            m_str(
                state._locals.get("DIF", MArray()).get(
                    m_var_value(state._locals["_a_I"])
                )
            ),
            m_str(";"),
            int(m_num(4)),
        )
        state._locals.setdefault("S", MArray()).value = m_piece(
            m_str(
                state._locals.get("DIF", MArray()).get(
                    m_var_value(state._locals["_a_I"])
                )
            ),
            m_str(";"),
            int(m_num(5)),
        )
        _rt.write_newline()
        _rt.write_newline()
        _rt.write_tab(int(m_num(3)))
        _rt.write(m_var_value(state._locals["N"]))
        _rt.write_tab(int(m_num(13)))
        _rt.write(m_var_value(state._locals["DIF"]))
        _rt.write(
            m_piece(
                m_str("  (Partial Definition)"),
                m_str(m_var_value(state._locals["U"])),
                int(
                    m_num(
                        m_piece(
                            m_str(
                                state._locals.get("DIF", MArray()).get(
                                    m_var_value(state._locals["_a_I"])
                                )
                            ),
                            m_str(";"),
                            int(m_num(6)),
                        )
                    )
                ),
            )
        )
        _rt.write(
            m_piece(
                m_str("  (including data)"),
                m_str(m_var_value(state._locals["U"])),
                int(
                    m_num(
                        m_compare(
                            m_piece(
                                m_str(
                                    state._locals.get("DIF", MArray()).get(
                                        m_var_value(state._locals["_a_I"])
                                    )
                                ),
                                m_str(";"),
                                int(m_num(13)),
                            ),
                            "=",
                            "y",
                        )
                    )
                ),
            )
        )
        state._locals.setdefault("Z", MArray()).value = (
            (_rt.globals.get(*_rt.globals.resolve_naked((0,))) or "")
            if m_truth(
                m_mod(
                    m_data_global(
                        _rt.globals,
                        "DIC",
                        (
                            m_var_value(state._locals["N"]),
                            0,
                        ),
                    ),
                    2,
                )
            )
            else ("" if m_truth(1) else _raise_select_false())
        )
        _test = m_truth(m_compare(m_var_value(state._locals["Z"]), "=", ""))
        _rt._test = _test
        if _test:
            state._locals.setdefault("DIFQ", MArray())[
                m_var_value(state._locals["N"])
            ] = 1
            state._locals.setdefault("DIFQN", MArray()).value = m_str(
                (
                    m_str(m_add(m_get(state._locals.get("DIFQN", MArray()), (), ""), 1))
                    + m_str(m_var_value(state._locals["U"]))
                )
            ) + m_str(m_var_value(state._locals["N"]))
            return ("S", state)
        _test = m_truth(
            len(
                m_str(
                    m_piece(
                        m_str(m_var_value(state._locals["Z"])),
                        m_str(m_var_value(state._locals["DIF"])),
                        int(m_num(1)),
                    )
                )
            )
        )
        _rt._test = _test
        if _test:
            _rt.write((chr(int(m_num(7))) if int(m_num(7)) >= 0 else ""))
            _rt.write_newline()
            _rt.write("*BUT YOU ALREADY HAVE '")
            _rt.write(
                m_piece(
                    m_str(m_var_value(state._locals["Z"])),
                    m_str(m_var_value(state._locals["U"])),
                    int(m_num(1)),
                )
            )
            _rt.write("' AS FILE #")
            _rt.write(m_var_value(state._locals["N"]))
            _rt.write("!")
            _rt._extrinsic_stack.append(_rt._in_extrinsic)
            _rt._in_extrinsic = False
            _rt.push_stack_frame("DO", routine="DMUFINIT", label="R")
            for _k in list(_scope.keys()):
                if _k not in state._locals:
                    del _scope[_k]
            _scope.update({k: v for k, v in state._locals.items()})
            R(_rt, _scope=_scope)
            for _k, _v in _scope.items():
                if isinstance(_v, MArray):
                    state._locals[_k] = _v
                else:
                    _m = MArray()
                    _m.value = _v
                    state._locals[_k] = _m
            _rt.pop_stack_frame()
            _rt._in_extrinsic = _rt._extrinsic_stack.pop()
            if m_truth(m_var_value(state._locals["DIFQ"])):
                return (None, state)
            if m_truth(
                m_data(
                    state._locals.get("DIFKEP", MArray()),
                    (m_var_value(state._locals["N"]),),
                )
            ):
                return ("S", state)
            else:
                return ("1", state)
        state._locals.setdefault("DIFQ", MArray())[m_var_value(state._locals["N"])] = (
            int(
                not m_compare(
                    m_piece(
                        m_str(
                            state._locals.get("DIF", MArray()).get(
                                m_var_value(state._locals["_a_I"])
                            )
                        ),
                        m_str(";"),
                        int(m_num(7)),
                    ),
                    "=",
                    "n",
                )
            )
        )
        _test = m_truth(len(m_str(m_var_value(state._locals["Z"]))))
        _rt._test = _test
        if _test:
            _rt.write((chr(int(m_num(7))) if int(m_num(7)) >= 0 else ""))
            _rt.write_newline()
            _rt.write("Note:  You already have the '")
            _rt.write(
                m_piece(
                    m_str(m_var_value(state._locals["Z"])),
                    m_str(m_var_value(state._locals["U"])),
                    int(m_num(1)),
                )
            )
            _rt.write("' File.")
            state._locals.setdefault("DIFQ", MArray())[0] = 1
        state._locals.setdefault("_pct_", MArray()).value = m_extract(
            m_str(
                (
                    _rt.globals.get(
                        "UTILITY",
                        (
                            "DIF",
                            _rt.job(),
                            m_add(m_var_value(state._locals["_a_I"]), 1),
                        ),
                    )
                    or ""
                )
            ),
            int(m_num(4)),
            int(m_num(245)),
        )
        _test = m_truth(int(m_str(m_var_value(state._locals["_pct_"])) > m_str("")))
        _rt._test = _test
        if _test:
            _scope.update({k: v for k, v in state._locals.items()})
            _rt.execute_mumps(m_var_value(state._locals["_pct_"]), _scope, globals())
            _test = _rt._test
            for _k, _v in _scope.items():
                if isinstance(_v, MArray):
                    state._locals[_k] = _v
                else:
                    _m = MArray()
                    _m.value = _v
                    state._locals[_k] = _m
            state._locals.setdefault("DIFQ", MArray())[
                m_var_value(state._locals["N"])
            ] = int(_test)
            if m_truth(int(not m_truth(int(_test)))):
                _rt.write_newline()
                _rt.write(
                    "Screen on this Data Dictionary did not pass--DD will not be installed!"
                )
            return ("S", state)
        if (_test := m_truth(len(m_str(m_var_value(state._locals["Z"]))))) and (
            _test := m_truth(
                m_compare(
                    m_piece(
                        m_str(
                            state._locals.get("DIF", MArray()).get(
                                m_var_value(state._locals["_a_I"])
                            )
                        ),
                        m_str(";"),
                        int(m_num(10)),
                    ),
                    "=",
                    "y",
                )
            )
        ):
            state._locals.setdefault("DIR", MArray())["A"] = (
                "Shall I write over the existing Data Definition"
            )
            state._locals.setdefault("DIR", MArray())["??"] = "^D DD^DIFROMH1"
            state._locals.setdefault("DIR", MArray())["B"] = "YES"
            state._locals.setdefault("DIR", MArray())[0] = "Y"
            import DIR

            _saved_routine = _rt._current_routine
            _saved_source_lines = _rt._current_source_lines
            _saved_label_lines = _rt._current_label_lines
            _scope.update({k: v for k, v in state._locals.items()})
            _rt.push_stack_frame("DO", routine="DIR", label="")
            run_with_goto_support(DIR._entry_function, _rt, _scope)
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
            state._locals.setdefault("DIFQ", MArray())[
                m_var_value(state._locals["N"])
            ] = m_var_value(state._locals["Y"])
        _rt._test = _test
        break
    return ("S", state)


def _S(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    state._locals.setdefault("DIFQR", MArray())[m_var_value(state._locals["N"])] = 0
    if m_truth(
        int(
            m_truth(
                int(
                    not m_compare(
                        m_piece(
                            m_str(
                                state._locals.get("DIF", MArray()).get(
                                    m_var_value(state._locals["_a_I"])
                                )
                            ),
                            m_str(";"),
                            int(m_num(13)),
                        ),
                        "=",
                        "y",
                    )
                )
            )
            or m_truth(m_data(state._locals.get("DIRUT", MArray()), ()))
        )
    ):
        return (None, state)
    if (
        _test := m_truth(
            m_compare(
                m_piece(
                    m_str(
                        state._locals.get("DIF", MArray()).get(
                            m_var_value(state._locals["_a_I"])
                        )
                    ),
                    m_str(";"),
                    int(m_num(15)),
                ),
                "=",
                "y",
            )
        )
    ) and (
        _test := m_truth(
            m_compare(
                _rt.get_order(
                    str((m_str(m_var_value(state._locals["S"])) + m_str("0)"))),
                    state._locals,
                    1,
                ),
                ">",
                0,
            )
        )
    ):
        state._locals.setdefault("DIF", MArray()).value = m_compare(
            m_piece(
                m_str(
                    state._locals.get("DIF", MArray()).get(
                        m_var_value(state._locals["_a_I"])
                    )
                ),
                m_str(";"),
                int(m_num(14)),
            ),
            "=",
            "o",
        )
        state._locals.setdefault("DIR", MArray())["A"] = m_str(
            (
                m_str("Want my data ")
                + m_str(
                    m_piece(
                        m_str("merged with^to overwrite"),
                        m_str(m_var_value(state._locals["U"])),
                        int(m_num(m_add(m_var_value(state._locals["DIF"]), 1))),
                    )
                )
            )
        ) + m_str(" yours")
        state._locals.setdefault("DIR", MArray())["??"] = "^D DTA^DIFROMH1"
        state._locals.setdefault("DIR", MArray())[0] = "Y"
        import DIR

        _saved_routine = _rt._current_routine
        _saved_source_lines = _rt._current_source_lines
        _saved_label_lines = _rt._current_label_lines
        _scope.update({k: v for k, v in state._locals.items()})
        _rt.push_stack_frame("DO", routine="DIR", label="")
        run_with_goto_support(DIR._entry_function, _rt, _scope)
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
        state._locals.setdefault("DIFQR", MArray())[m_var_value(state._locals["N"])] = (
            m_var_value(state._locals["Y"])
            if m_truth(int(not m_truth(m_var_value(state._locals["Y"]))))
            else (
                m_add(
                    m_var_value(state._locals["Y"]), m_var_value(state._locals["DIF"])
                )
                if m_truth(1)
                else _raise_select_false()
            )
        )
        return (None, state)
    _rt._test = _test
    state._locals.setdefault("_pct_", MArray()).value = m_compare(
        m_piece(
            m_str(
                state._locals.get("DIF", MArray()).get(
                    m_var_value(state._locals["_a_I"])
                )
            ),
            m_str(";"),
            int(m_num(14)),
        ),
        "=",
        "o",
    )
    _rt.write_newline()
    _rt.write((chr(int(m_num(7))) if int(m_num(7)) >= 0 else ""))
    _rt.write("I will ")
    _rt.write(
        m_piece(
            m_str("MERGE^OVERWRITE"),
            m_str(m_var_value(state._locals["U"])),
            int(m_num(m_add(m_var_value(state._locals["_pct_"]), 1))),
        )
    )
    _rt.write(" your data with mine.")
    state._locals.setdefault("DIFQR", MArray())[m_var_value(state._locals["N"])] = (
        m_add(m_var_value(state._locals["_pct_"]), 1)
    )
    return (None, state)
    return ("Q", state)


def _Q(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    _rt.write((chr(int(m_num(7))) if int(m_num(7)) >= 0 else ""))
    _rt.write_newline()
    _rt.write_newline()
    _rt.write("NO UPDATING HAS OCCURRED!")
    _scope.update({k: v for k, v in state._locals.items()})
    import DIFROM0

    raise GotoExternal(DIFROM0, "Q", _rt=_rt)
    return ("PKG", state)


def _PKG(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    state._locals.setdefault("X", MArray()).value = m_piece(
        m_str(_rt.get_text(offset=0, label="IXF")), m_str(";"), int(m_num(3))
    )
    state._locals.setdefault("DIC", MArray()).value = "^DIC(9.4,"
    state._locals.setdefault("DIC", MArray())[0] = ""
    state._locals.setdefault("DIC", MArray())["S"] = m_str(
        (
            m_str('I $P(^(0),U,2)="')
            + m_str(
                m_piece(
                    m_str(m_var_value(state._locals["X"])),
                    m_str(m_var_value(state._locals["U"])),
                    int(m_num(2)),
                )
            )
        )
    ) + m_str('"')
    state._locals.setdefault("X", MArray()).value = m_piece(
        m_str(m_var_value(state._locals["X"])),
        m_str(m_var_value(state._locals["U"])),
        int(m_num(1)),
    )
    import DIC

    _saved_routine = _rt._current_routine
    _saved_source_lines = _rt._current_source_lines
    _saved_label_lines = _rt._current_label_lines
    _scope.update({k: v for k, v in state._locals.items()})
    _rt.push_stack_frame("DO", routine="DIC", label="")
    run_with_goto_support(DIC._entry_function, _rt, _scope)
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
    state._locals.setdefault("DIFROM", MArray())[0] = +m_num(
        m_var_value(state._locals["Y"])
    )
    state._locals.get("DIC", MArray()).kill()
    return (None, state)
    return ("IXF", state)


def _IXF(_rt, state, _scope) -> Tuple[str | int | None, RoutineState]:
    global _test
    pass
    return (None, state)


_labels = {
    "DMUFINIT": _DMUFINIT,
    "GO": _GO,
    "EN": _EN,
    "D": _D,
    "R": _R,
    "1": __n_1,
    "S": _S,
    "Q": _Q,
    "PKG": _PKG,
    "IXF": _IXF,
}

_line_map: dict[int, tuple[str, int]] = {
    1: ("DMUFINIT", 0),
    7: ("DMUFINIT", 6),
    8: ("DMUFINIT", 7),
    9: ("DMUFINIT", 8),
    10: ("DMUFINIT", 9),
    13: ("GO", 0),
    14: ("EN", 0),
    15: ("EN", 1),
    16: ("EN", 2),
    17: ("EN", 3),
    18: ("EN", 4),
    19: ("EN", 5),
    20: ("EN", 6),
    21: ("EN", 7),
    22: ("EN", 8),
    23: ("EN", 9),
    24: ("EN", 10),
    25: ("EN", 11),
    26: ("EN", 12),
    27: ("D", 0),
    28: ("D", 1),
    29: ("D", 2),
    30: ("D", 3),
    31: ("R", 0),
    33: ("_n_1", 0),
    34: ("_n_1", 1),
    35: ("_n_1", 2),
    36: ("_n_1", 3),
    37: ("_n_1", 4),
    38: ("_n_1", 5),
    39: ("_n_1", 6),
    40: ("_n_1", 7),
    41: ("S", 0),
    42: ("S", 1),
    43: ("S", 2),
    44: ("S", 3),
    45: ("Q", 0),
    47: ("PKG", 0),
    48: ("PKG", 1),
    50: ("IXF", 0),
}


def DMUFINIT(_rt, _scope=None):
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
    target: str | int | None = "DMUFINIT"

    while target is not None:
        try:
            assert isinstance(target, str)
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


def GO(_rt, _scope=None):
    """Entry point for DO GO calls."""
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
        target, state = _GO(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


def EN(_rt, _scope=None):
    """Entry point for DO EN calls."""
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
        target, state = _EN(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


def D(_rt, _scope=None):
    """Entry point for DO D calls."""
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
        target, state = _D(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


def R(_rt, _scope=None):
    """Entry point for DO R calls."""
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
        target, state = _R(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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
            assert isinstance(target, str)
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


def S(_rt, _scope=None):
    """Entry point for DO S calls."""
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
        target, state = _S(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


def Q(_rt, _scope=None):
    """Entry point for DO Q calls."""
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
        target, state = _Q(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


def PKG(_rt, _scope=None):
    """Entry point for DO PKG calls."""
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
        target, state = _PKG(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


def IXF(_rt, _scope=None):
    """Entry point for DO IXF calls."""
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
        target, state = _IXF(_rt, state, _scope)
        while target is not None:
            assert isinstance(target, str)
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


_entry_function = DMUFINIT


if __name__ == "__main__":
    _rt = MUMPSRuntime()
    _scope = {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    DMUFINIT(_rt, _scope=_scope)
