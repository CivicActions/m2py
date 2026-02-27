"""Routine code generation for MUMPS-to-Python transpilation.

Generates complete Python modules from MUMPS routines.
Handles module structure, imports, labels as functions, and $TEST tracking.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional

from m2py.asg.elements import MLabel, MRoutine
from m2py.asg.enums import ExprResultType
from m2py.asg.statements import MQuitStatement
from m2py.analysis.variables import FunctionSignature
from m2py.codegen.emitter import CodeEmitter
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.line_dispatch import (
    generate_line_map,
    generate_line_map_code,
)
from m2py.codegen.names import NameTranslator, translate_name
from m2py.codegen.statements import (
    _emit_goto_external_handler,
    emit_scope_to_state_sync,
    emit_scope_var_to_state,
    emit_state_to_scope_sync,
    emit_state_var_to_scope,
    generate_offset_guarded_statements,
    generate_scope_statements,
)

if TYPE_CHECKING:
    pass


# Mapping from ExprResultType to Python type annotation strings.
# All return types include None because generated functions can return None
# via $ETRAP error handling paths and fall-through code paths.
_RESULT_TYPE_TO_HINT: Dict[ExprResultType, str] = {
    ExprResultType.STRING: "str | None",
    ExprResultType.NUMERIC: "int | Decimal | None",
    ExprResultType.BOOLEAN_INT: "int | None",
    ExprResultType.NUMERIC_STRING: "str | None",
}


def _infer_return_type(label: MLabel) -> str | None:
    """Infer a consistent return type hint from all QUIT expressions in a label.

    Walks all statements in the label body, collects return_value.result_type
    from every MQuitStatement that has a return value, and returns a type hint
    string if all return types are consistent and non-UNKNOWN.

    Args:
        label: MLabel ASG node to analyze

    Returns:
        Python type annotation string (e.g. "str", "int") or None if
        no consistent type can be determined.
    """
    result_types: set[ExprResultType] = set()

    for stmt in label.body.walk_statements():
        if isinstance(stmt, MQuitStatement) and stmt.return_value is not None:
            rt = stmt.return_value.result_type
            if rt is None or rt == ExprResultType.UNKNOWN:
                # Any unknown return makes the whole function un-annotatable
                return None
            result_types.add(rt)

    if not result_types:
        # No QUIT with return value — not a function, no annotation
        return None

    if len(result_types) == 1:
        rt = next(iter(result_types))
        return _RESULT_TYPE_TO_HINT.get(rt)

    # Multiple different types — cannot annotate consistently
    return None


@dataclass
class GeneratorContext:
    """Context passed through code generation.

    Carries state needed by expression and statement generators.
    """

    routine: MRoutine
    emitter: CodeEmitter
    name_translator: NameTranslator = field(default_factory=NameTranslator)
    imports: set[str] = field(default_factory=set)
    current_label: Optional[MLabel] = None

    # Function signatures for label code generation
    signatures: Dict[str, FunctionSignature] = field(default_factory=dict)

    # Flag for $TEST save/restore in extrinsic calls
    in_extrinsic_call: bool = False

    # GOTO strategy for cross-label pattern
    strategy: "GotoStrategy" = None  # type: ignore[assignment]

    # Variables stored in RoutineState (for state.VAR access)
    state_vars: set[str] = field(default_factory=set)

    # Array variables (MArray-backed) for subscript access
    array_vars: set[str] = field(default_factory=set)

    # Variables that are read but never written in the routine (input-only from caller).
    # In TRAMPOLINE mode, these need to be read from _scope instead of bare Python vars.
    input_only_vars: set[str] = field(default_factory=set)

    # Name of the NewScopeManager variable when inside a NEW-managed block
    # If set, _generate_new() should use _new_mgr.new_var() instead of _scope.pop()
    new_scope_manager_var: Optional[str] = None

    # True when routine uses dynamic _locals dict instead of static fields.
    # This happens when routine contains argumentless KILL or argumentless NEW.
    uses_dynamic_locals: bool = False

    # True when generating code inside inline XECUTE.
    # GOTO/DO inside inline XECUTE should raise _XecuteExit instead of return.
    in_inline_xecute: bool = False

    # Counter for generating unique FOR loop variable names.
    # Prevents nested FOR loops from clobbering each other's _for_start/_for_step/_for_end.
    _for_loop_counter: int = 0

    def next_for_loop_id(self) -> int:
        """Return a unique ID for FOR loop variable names and increment counter."""
        loop_id = self._for_loop_counter
        self._for_loop_counter += 1
        return loop_id


class AnalysisNotCompleteError(ValueError):
    """Raised when code generation is attempted without complete analysis.

    This error indicates that required analysis passes have not been run
    before code generation was attempted. Each analysis pass populates
    specific ASG fields that codegen depends on.

    The 'analysis-first' principle requires:
    - resolve_references(): Resolves label and routine references
    - classify_gotos(): Classifies GOTO patterns and populates exits_loops
    - analyze_for_loops(): Classifies FOR loops and detects modifications
    - analyze_quit_context(): Sets exits_for/exits_do_block on QUITs
    - analyze_variables(): Computes function signatures
    """

    def __init__(self, missing_field: str, required_pass: str, context: str = ""):
        ctx_msg = f" in {context}" if context else ""
        super().__init__(
            f"Analysis field '{missing_field}' not set{ctx_msg}. "
            f"Run {required_pass}() before code generation."
        )
        self.missing_field = missing_field
        self.required_pass = required_pass


def validate_analysis_complete(routine: MRoutine) -> None:
    """Validate that required analysis passes have run before codegen.

    Checks that FOR loop analysis, GOTO analysis, and QUIT context analysis
    have populated the ASG fields needed for proper code generation. This
    enforces the 'analysis-first' principle: codegen reads ASG fields, it
    does not compute semantic properties.

    Args:
        routine: The routine to validate

    Raises:
        AnalysisNotCompleteError: If analysis fields are not populated

    Analysis passes and their outputs:
        - classify_gotos(): MGotoStatement.goto_type, .exits_loops
        - analyze_for_loops(): MForStatement.loop_type, .loop_var_modified_in_body
        - analyze_quit_context(): MQuitStatement.exits_for, .exits_do_block
        - analyze_variables(): MLabel.signature
    """
    from m2py.asg.statements import MForStatement, MGotoStatement
    from m2py.asg.enums import GotoType

    if not routine.labels:
        return  # Empty routine is valid

    for label in routine.labels:
        if label.body is None:
            continue

        # Walk all statements and validate analysis fields
        for stmt in label.body.walk_statements():
            # Validate FOR statement analysis
            if isinstance(stmt, MForStatement):
                if stmt.loop_type is None:
                    raise AnalysisNotCompleteError(
                        "loop_type",
                        "analyze_for_loops",
                        f"MForStatement at line {stmt.line_number}",
                    )

            # Validate GOTO statement analysis
            if isinstance(stmt, MGotoStatement):
                if stmt.goto_type is None:
                    raise AnalysisNotCompleteError(
                        "goto_type",
                        "classify_gotos",
                        f"MGotoStatement at line {stmt.line_number}",
                    )
                # LOOP_EXIT and MULTI_LOOP_EXIT must have exits_loops populated
                if stmt.goto_type in (GotoType.LOOP_EXIT, GotoType.MULTI_LOOP_EXIT):
                    if not stmt.exits_loops:
                        raise AnalysisNotCompleteError(
                            "exits_loops",
                            "classify_gotos",
                            f"MGotoStatement (loop exit) at line {stmt.line_number}",
                        )

            # QUIT validation: exits_for/exits_do_block are Optional and may be
            # None when QUIT is not inside a FOR or DO block. The analysis pass
            # sets them when appropriate, so we don't raise errors for None here.
            # The codegen correctly handles None by generating 'return' statements.


def _fix_empty_blocks(code: str) -> str:
    """Insert 'pass' into empty if/elif/else blocks.

    Scans generated Python for if/elif/else statements whose body is empty
    (next non-blank line is at same or lower indentation). Inserts 'pass'
    to make the block syntactically valid.

    These arise when conditional DO or IF at end-of-line produce
    an if block whose body is at a different scope level.
    """
    lines = code.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith(("if ", "elif ", "else:")) and stripped.endswith(":"):
            indent = len(line) - len(stripped)
            # Look at next non-blank line
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j >= len(lines):
                # End of file — empty block
                result.append(line)
                result.append(" " * (indent + 4) + "pass")
                i += 1
                continue
            next_indent = len(lines[j]) - len(lines[j].lstrip())
            if next_indent <= indent:
                # Next line is at same or lower indentation → empty block
                result.append(line)
                result.append(" " * (indent + 4) + "pass")
                i += 1
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _fix_import_in_elif_chain(code: str) -> str:
    """Move import statements that break if/elif/else chains.

    When codegen emits an ``import X`` between an ``if`` block and an
    ``elif``/``else``, the generated Python is invalid.  This function
    detects this pattern and hoists the import above the ``if`` block.
    """
    lines = code.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Detect: current line is `import X` (or `from X import Y`)
        # and the NEXT non-blank line is `elif` or `else:` at the same indent
        if (
            stripped.startswith("import ") or stripped.startswith("from ")
        ) and i + 1 < len(lines):
            # Find next non-blank line
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                next_stripped = lines[j].lstrip()
                next_indent = len(lines[j]) - len(next_stripped)
                if next_indent == indent and next_stripped.startswith(
                    ("elif ", "else:")
                ):
                    # This import breaks an if/elif chain.
                    # Hoist it above the preceding if block.
                    # Walk backwards to find the `if` at the same indentation.
                    insert_pos = len(result) - 1
                    while insert_pos >= 0:
                        prev = result[insert_pos]
                        prev_stripped = prev.lstrip()
                        prev_indent = len(prev) - len(prev_stripped)
                        if prev_indent == indent and prev_stripped.startswith("if "):
                            break
                        insert_pos -= 1
                    if insert_pos >= 0:
                        result.insert(insert_pos, line)
                        i += 1
                        continue
        result.append(line)
        i += 1
    return "\n".join(result)


class RoutineGenerator:
    """Generates Python code for a complete MUMPS routine.

    Transforms an MRoutine ASG into executable Python code with:
    - Required imports for helpers and runtime
    - Module-level runtime instance (_rt)
    - Module-level $TEST tracking (_test)
    - Labels as Python functions

    Strategy selection determines code generation pattern:
    - SIMPLE_FUNCTIONS: Labels as simple functions (no cross-label GOTOs)
    - TRAMPOLINE: Labels with RoutineState, trampoline dispatch
    """

    def __init__(
        self,
        routine: MRoutine,
        strategy: GotoStrategy = GotoStrategy.SIMPLE_FUNCTIONS,
    ) -> None:
        """Initialize generator with parsed routine.

        Args:
            routine: MRoutine ASG to generate code from
            strategy: Code generation strategy for cross-label GOTOs
        """
        self._routine = routine
        self._strategy = strategy
        self._emitter = CodeEmitter()
        self._name_translator = NameTranslator()

    def generate(self) -> str:
        """Generate complete Python module.

        Selects generation pattern based on strategy:
        - SIMPLE_FUNCTIONS: Labels as Python functions
        - TRAMPOLINE: Labels with RoutineState, trampoline dispatch

        Returns:
            Python source code as string
        """
        # Compute state vars and array vars for trampoline pattern
        state_vars: set[str] = set()
        array_vars: set[str] = set()
        input_only_vars: set[str] = set()
        uses_dynamic_locals = False
        if self._strategy == GotoStrategy.TRAMPOLINE:
            state_vars = self._routine.routine_state_vars or set()
            array_vars = self._routine.array_vars or set()
            input_only_vars = self._routine.routine_input_only_vars or set()
            # Check if routine needs dynamic _locals dict
            from m2py.codegen.shared_state import routine_uses_dynamic_locals

            uses_dynamic_locals = routine_uses_dynamic_locals(self._routine)

        ctx = GeneratorContext(
            routine=self._routine,
            emitter=self._emitter,
            name_translator=self._name_translator,
            strategy=self._strategy,
            state_vars=state_vars,
            array_vars=array_vars,
            input_only_vars=input_only_vars,
            uses_dynamic_locals=uses_dynamic_locals,
        )

        # Generate module preamble
        self._generate_preamble(ctx)

        if self._strategy == GotoStrategy.TRAMPOLINE:
            # Trampoline pattern with RoutineState
            self._generate_trampoline_code(ctx)
        else:
            # Simple functions pattern
            for label in self._routine.labels:
                self._generate_label(label, ctx)

            # Generate _line_map for external D/G +N^ROUTINE patterns.
            # External routines can call this module with D +N^ROUTINE or
            # D LABEL+N^ROUTINE so we always need _line_map for line dispatch.
            self._generate_simple_line_map(ctx)

        # Generate _entry_function for D ^ROUTINE semantics
        # This points to the first label (line 1), which may be preamble or named label
        self._generate_entry_function(ctx)

        # Generate if __name__ == "__main__" entry point block
        self._generate_main_block(ctx)

        code = self._emitter.get_code()

        # Post-processing: fix empty if/elif/else blocks by inserting 'pass'.
        # These arise when conditional DO or IF at end-of-line produce
        # an if block whose body is at a different scope level.
        code = _fix_empty_blocks(code)

        # Post-processing: hoist import statements that break if/elif/else chains.
        # These arise when codegen emits an inline import for DO ^ROUTINE
        # between an if block's body and its elif/else continuation.
        code = _fix_import_in_elif_chain(code)

        # Validate generated Python is syntactically correct
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(
                f"Generated Python has syntax error: {e}\n\nGenerated code:\n{code}"
            ) from e

        return code

    def _generate_preamble(self, ctx: GeneratorContext) -> None:
        """Generate module imports and initialization.

        Adds RoutineState imports and class for TRAMPOLINE strategy.

        Args:
            ctx: Generator context
        """
        # Imports
        # Suppress "too complex" warnings from pyright for large generated functions.
        # Transpiled MUMPS code can produce deeply nested conditional paths that
        # exceed pyright's analysis complexity threshold.
        ctx.emitter.line("# pyright: reportGeneralTypeIssues=false")
        ctx.emitter.line("import re")
        ctx.emitter.line("import time")
        ctx.emitter.line("from decimal import Decimal")
        ctx.emitter.line("from itertools import chain, count")
        ctx.emitter.line(
            "from m2py.codegen.helpers import m_str, m_num, m_truth, m_compare, m_div, m_int_div, m_pow, m_add, m_sub, m_mul, m_mod, m_range"
        )
        # Import MArray for subscripted local variable support
        # run_with_goto_support is needed for any D ^ROUTINE call
        # GotoExternal is needed for cross-routine GOTO and indirect GOTO
        ctx.emitter.line(
            "from m2py.runtime import MUMPSRuntime, MArray, run_with_goto_support, resolve_goto_target, LabelNotFoundError, GotoExternal"
        )
        # Import runtime helpers: LHS functions, $DATA, $ORDER, $QUERY, $SELECT,
        # $PIECE, $EXTRACT, $GET, $FIND, $NAME/$QLENGTH/$QSUBSCRIPT, $FNUMBER,
        # sorts-after, pattern_match, NewScopeManager, READ helpers, m_var_value,
        # _format_subscript, unwind_new_stack, $ZDATE, $ZMESSAGE,
        # IRIS vendor: $REPLACE, $ZBOOLEAN, $ZU, $ZF, $ZCONVERT, stubs.
        # Contains ([) and follows (]) are inlined as Python expressions.
        ctx.emitter.line(
            "from m2py.runtime.helpers import m_set_piece, m_set_extract, m_data, m_data_global, m_order, m_order_global, m_query, m_query_global, _raise_select_false, m_piece, m_extract, m_get, m_get_global, m_increment, m_increment_global, m_find, m_name, m_qlength, m_qsubscript, m_justify, m_fnumber, m_sorts_after, m_pattern_match, m_translate, NewScopeManager, m_var_value, _format_subscript, unwind_new_stack, m_zdate, m_zmessage, m_replace, m_zboolean, m_zu, m_zf, m_zcall_stub, m_view_func_stub, m_zconvert, _rt_os_environ_get, m_zgetjpi, m_zparse, m_zbitand, m_zbitor, m_zbitxor, m_zbitnot, m_zbitstr, m_zabs, m_now, m_ztime, m_zgetsyi, _rt_os_getcwd"
        )
        # Import $RANDOM helper
        ctx.emitter.line("from m2py.codegen.expressions import _m_random_checked")

        # Additional imports for trampoline pattern
        if self._strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("from dataclasses import dataclass, field")
            ctx.emitter.line("from typing import Any, Optional, Tuple")

        ctx.emitter.blank()

        # _rt is passed as a parameter to all label functions.
        # Entry point (if __name__ == "__main__") creates the shared instance.

        # $TEST tracking
        ctx.emitter.line("_test = False")
        ctx.emitter.blank()

        # Capture module globals before any user-defined function can shadow builtin globals()
        ctx.emitter.line("_globals = globals()")
        ctx.emitter.blank()

        # Module constants for external call infrastructure
        # _source_lines: Original MUMPS source for $TEXT support
        source_lines = self._routine.source_lines or []
        ctx.emitter.line(f"_source_lines = {source_lines!r}")
        ctx.emitter.blank()

        # _routine_name: Name of this routine for $TEXT(+0) and error messages
        # Falls back to first non-empty label name if routine.name is not set
        # Preserves original case for $TEXT(+0) which returns source-accurate routine name
        routine_name = self._routine.name
        ctx.emitter.line(f'_routine_name = "{routine_name}"')
        ctx.emitter.blank()

        # _label_lines: Maps label names to 0-indexed line numbers for $TEXT(LABEL+offset)
        # Include both top-level labels and dotted (inline) labels so $TEXT can
        # resolve labels that appear within dot blocks.
        label_lines = {
            label.name: label.line_number - 1
            for label in self._routine.labels
            if label.line_number is not None
        }
        for dlabel in getattr(self._routine, "_dotted_labels", []):
            if dlabel.line_number is not None:
                label_lines[dlabel.name] = dlabel.line_number - 1
        ctx.emitter.line(f"_label_lines = {label_lines!r}")
        ctx.emitter.blank()

        # Runtime context is set per-call within label functions that use $TEXT

        # Generate RoutineState class for trampoline pattern
        if self._strategy == GotoStrategy.TRAMPOLINE:
            from m2py.codegen.shared_state import generate_routine_state_class

            state_class = generate_routine_state_class(self._routine)
            for line in state_class.strip().split("\n"):
                ctx.emitter.line(line)
            ctx.emitter.blank()

        # Extrinsic function helper — saves/restores $TEST, accepts _rt as
        # first parameter for shared runtime, handles by-ref parameter
        # unpacking via _byref, and sets _in_extrinsic flag for $QUIT tracking.
        ctx.emitter.blank()
        ctx.emitter.line(
            "def _call_extrinsic(_rt, _ef, *args, _scope=None, _byref=None):"
        )
        with ctx.emitter.indented():
            ctx.emitter.line(
                '"""Call extrinsic function with $TEST save/restore and by-ref handling.'
            )
            ctx.emitter.blank()
            ctx.emitter.line("Args:")
            ctx.emitter.line("    _rt: Runtime instance")
            ctx.emitter.line("    _ef: The extrinsic function to call")
            ctx.emitter.line("    *args: Positional arguments for the function")
            ctx.emitter.line(
                "    _scope: Variable scope dictionary for cross-routine visibility"
            )
            ctx.emitter.line(
                "    _byref: List of by-ref variable names (or None for by-value)"
            )
            ctx.emitter.line('"""')
            ctx.emitter.line("global _test")
            ctx.emitter.line("_saved = _test")
            # Save runtime context before extrinsic call for $TEXT support
            # (same as external DO — extrinsic callee sets _current_routine
            # to its own name, so we must restore after it returns)
            ctx.emitter.line("_saved_routine = _rt._current_routine")
            ctx.emitter.line("_saved_source_lines = _rt._current_source_lines")
            ctx.emitter.line("_saved_label_lines = _rt._current_label_lines")
            # Save/restore _in_extrinsic for $QUIT tracking
            ctx.emitter.line("_rt._extrinsic_stack.append(_rt._in_extrinsic)")
            # Push $$ stack frame for extrinsic function call
            # Pass label from the function being called for $STACK introspection
            ctx.emitter.line(
                '_rt.push_stack_frame("$$", label=getattr(_ef, "__name__", ""))'
            )
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                # Mark that we're in an extrinsic for $QUIT
                ctx.emitter.line("_rt._in_extrinsic = True")
                # Handle GotoExternal: some extrinsic functions use GOTO to
                # redirect to the actual implementation (e.g., $$CREF^DILF
                # does G ENCREF^DIQGU).  The GOTO target runs in the same
                # extrinsic context and its QUIT value becomes the return.
                ctx.emitter.line("_current_ef = _ef")
                ctx.emitter.line("_current_args = args")
                ctx.emitter.line("while True:")
                with ctx.emitter.indented():
                    ctx.emitter.line("try:")
                    with ctx.emitter.indented():
                        # Pass _rt and _scope to external extrinsic
                        ctx.emitter.line("if _scope is not None:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "_result = _current_ef(_rt, *_current_args, _scope=_scope)"
                            )
                        ctx.emitter.line("else:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "_result = _current_ef(_rt, *_current_args)"
                            )
                        ctx.emitter.line("break")
                    ctx.emitter.line("except GotoExternal as _goto:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_current_ef = resolve_goto_target(_goto)")
                        ctx.emitter.line(
                            "_current_args = ()  # GOTO target receives args via _scope"
                        )
                # Handle by-ref unpacking
                ctx.emitter.line("# Unpack by-ref values if result is a tuple")
                ctx.emitter.line("if isinstance(_result, tuple) and len(_result) > 1:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        "# Only unpack to caller scope if _byref is provided"
                    )
                    ctx.emitter.line("if _byref and _scope is not None:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_byref_idx = 1")
                        ctx.emitter.line("for _name in _byref:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "if _name is not None and _byref_idx < len(_result):"
                            )
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    "_scope.setdefault(_name, MArray()).value = _result[_byref_idx]"
                                )
                            ctx.emitter.line("_byref_idx += 1")
                    ctx.emitter.line(
                        "# Always return just the first element (return value)"
                    )
                    ctx.emitter.line("return _result[0]")
                ctx.emitter.line("return _result")
            ctx.emitter.line("finally:")
            with ctx.emitter.indented():
                # Pop $$ stack frame
                ctx.emitter.line("_rt.pop_stack_frame()")
                ctx.emitter.line("_test = _saved")
                # Sync $TEST to runtime after restore (extrinsic preserves caller's $TEST)
                ctx.emitter.line("_rt._test = _test")
                # Restore runtime context after extrinsic call returns
                ctx.emitter.line("_rt._current_routine = _saved_routine")
                ctx.emitter.line("_rt._current_source_lines = _saved_source_lines")
                ctx.emitter.line("_rt._current_label_lines = _saved_label_lines")
                # Restore extrinsic flag for nested calls
                ctx.emitter.line("_rt._in_extrinsic = _rt._extrinsic_stack.pop()")
        ctx.emitter.blank()

        # _LoopExit exception for multi-loop exit via GOTO.
        # Only generate if the routine has MULTI_LOOP_EXIT GOTOs.
        # Uses pre-computed needs_loop_exit_exception field from classify_gotos().
        # Accepts optional target parameter for cross-label exits.
        if self._routine.needs_loop_exit_exception:
            ctx.emitter.line("class _LoopExit(Exception):")
            with ctx.emitter.indented():
                ctx.emitter.line('"""Exception for multi-loop exit via GOTO."""')
                ctx.emitter.line("def __init__(self, target=None):")
                with ctx.emitter.indented():
                    ctx.emitter.line("self.target = target")
            ctx.emitter.blank()

        # _XecuteExit exception for GOTO/DO inside inline XECUTE.
        # This allows GOTO inside XECUTE to exit just the XECUTE block
        # without returning from the enclosing function.
        ctx.emitter.line("class _XecuteExit(Exception):")
        with ctx.emitter.indented():
            ctx.emitter.line(
                '"""Exception for control flow exit from inline XECUTE."""'
            )
            ctx.emitter.line("pass")
        ctx.emitter.blank()

    def _generate_label_docstring(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate Python docstring with MUMPS source info.

        Generates a docstring for each label function containing:
        - MUMPS label name (original, for debugging/traceability)
        - Source line number (1-indexed)
        - Inline comment from label line (if present)

        Args:
            label: MLabel ASG node
            ctx: Generator context
        """
        # Build docstring content
        parts = []

        # Label name and line number
        line_num = label.line_number if label.line_number else "?"
        parts.append(f"MUMPS label: {label.name} (line {line_num})")

        # Extract inline comment from parsed content if available
        if label._parsed_content and hasattr(label._parsed_content, "comment"):
            comment = label._parsed_content.comment
            if comment and hasattr(comment, "text") and comment.text:
                # Strip leading/trailing whitespace from comment
                comment_text = comment.text.strip()
                if comment_text:
                    # Escape backslashes first, then quotes to prevent breaking the docstring
                    comment_text = comment_text.replace("\\", "\\\\")
                    comment_text = comment_text.replace('"', "'")
                    parts.append(comment_text)

        # Generate the docstring
        docstring = " - ".join(parts) if len(parts) > 1 else parts[0]
        ctx.emitter.line(f'"""{docstring}"""')

    def _generate_label(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate Python function from MUMPS label.

        Uses FunctionSignature to determine:
        - Formal parameters for function definition
        - Return pattern based on scope_strategy

        Labels with has_self_loop=True wrap body in while True:
        - Self-loop GOTOs become continue
        - QUIT becomes break (implicit at end of body)
        - Other exits (cross-label GOTO) use return

        Wraps body in try/except for $ETRAP error handling:
        - Catches exceptions and calls _rt._handle_etrap()
        - If $ETRAP clears $ECODE, performs implicit QUIT (return)
        - If $ECODE not cleared, re-raises exception to propagate

        Args:
            label: MLabel ASG node
            ctx: Generator context

        Raises:
            UnsupportedFeatureError: For REQUIRES_RUNTIME scope strategy
        """

        ctx.current_label = label

        # Translate label name to valid Python identifier
        func_name = translate_name(label.name)

        # Get formal parameters from label or signature
        formal_params = []
        if label.formal_list:
            formal_params = [translate_name(p) for p in label.formal_list]
        elif label.signature and label.signature.formal_params:
            formal_params = [translate_name(p) for p in label.signature.formal_params]

        # REQUIRES_RUNTIME strategy is supported for both SIMPLE_FUNCTIONS and TRAMPOLINE.
        # Labels with indirection/XECUTE use _rt.get_var()/_rt.set_var() at runtime.

        # All labels take _rt as first parameter for shared runtime across routines
        # and _scope for cross-routine variable visibility (D LABEL^ROUTINE).
        # _scope must come AFTER formal params since it has a default value.
        # _start_offset allows external callers to pass offset for D LABEL+N^ROUTINE calls.
        # Formal params have None default so they can be omitted
        # (MUMPS allows calling with fewer args than defined - undefined params have $D()=0).
        formal_params_with_defaults = [f"{p}=None" for p in formal_params]
        all_params = (
            ["_rt"] + formal_params_with_defaults + ["_scope=None", "_start_offset=0"]
        )
        params_str = ", ".join(all_params)

        # Infer return type from QUIT expressions
        # Skip annotation for labels with byref_outputs since those return tuples
        has_byref = bool(label.signature and label.signature.byref_outputs)
        return_hint = None if has_byref else _infer_return_type(label)
        if return_hint:
            ctx.emitter.line(f"def {func_name}({params_str}) -> {return_hint}:")
        else:
            ctx.emitter.line(f"def {func_name}({params_str}):")

        with ctx.emitter.indented():
            # Generate docstring with MUMPS source info
            self._generate_label_docstring(label, ctx)

            # Declare global _test
            ctx.emitter.line("global _test")
            # Sync $TEST from runtime on function entry (cross-module visibility)
            ctx.emitter.line("_test = _rt._test")
            # Initialize _scope if not provided (entry point behavior)
            ctx.emitter.line("_scope = _scope if _scope is not None else {}")
            # Update runtime context for $TEXT support in external routine calls
            ctx.emitter.line("_rt._current_routine = _routine_name")
            ctx.emitter.line("_rt._current_source_lines = _source_lines")
            ctx.emitter.line("_rt._current_label_lines = _label_lines")

            # Copy formal parameters into _scope for variable reads.
            # Use original MUMPS names for _scope keys, translated names for Python vars.
            # Use MArray for consistency with subscripted variables.
            # Formal parameters are implicitly NEWed per MUMPS spec.
            original_formal_params = label.formal_list or []
            if (
                label.signature
                and label.signature.formal_params
                and not label.formal_list
            ):
                original_formal_params = label.signature.formal_params

            # Wrap body in try/except for $ETRAP error handling
            # at stack frame boundaries.
            # IMPORTANT: When NewScopeManager is used (for NEW $ETRAP etc.),
            # the try/except MUST be INSIDE the with block. Otherwise,
            # NewScopeManager.__exit__ restores $ETRAP to "" before
            # _handle_etrap() sees the current $ETRAP value.
            needs_scope_manager = label.has_new_statements or bool(
                original_formal_params
            )
            if needs_scope_manager:
                ctx.emitter.line("with NewScopeManager(_scope) as _new_mgr:")
                ctx.new_scope_manager_var = "_new_mgr"
                with ctx.emitter.indented():
                    # NEW formal parameters first (saves caller's values).
                    # Then assign parameter values to _scope.
                    # Only assign if parameter was actually passed (not None)
                    # to ensure $D(param)=0 for undefined parameters.
                    # If param is an MArray, it's a by-ref alias — use directly.
                    for orig_name in original_formal_params:
                        python_name = translate_name(orig_name)
                        # Use python_name for scope key to match GET/SET in body
                        # (e.g., %1 → _pct_1 so reads/writes use same key)
                        ctx.emitter.line(f"_new_mgr.new_var({python_name!r})")
                        ctx.emitter.line(f"if {python_name} is not None:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(f"if isinstance({python_name}, MArray):")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    f"_scope[{python_name!r}] = {python_name}"
                                )
                            ctx.emitter.line("else:")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    f"_scope[{python_name!r}] = MArray(value={python_name})"
                                )
                    ctx.emitter.line("try:")
                    with ctx.emitter.indented():
                        self._generate_label_body(label, ctx)
                    # Error handling — invoke $ETRAP if set
                    ctx.emitter.line("except Exception as _e:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("if _rt._handle_etrap(_e, _scope):")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "return  # $ETRAP cleared $ECODE, implicit QUIT"
                            )
                        ctx.emitter.line("raise  # Propagate to caller")
                ctx.new_scope_manager_var = None
            else:
                ctx.emitter.line("try:")
                with ctx.emitter.indented():
                    self._generate_label_body(label, ctx)
                # Error handling — invoke $ETRAP if set
                ctx.emitter.line("except Exception as _e:")
                with ctx.emitter.indented():
                    ctx.emitter.line("if _rt._handle_etrap(_e, _scope):")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            "return  # $ETRAP cleared $ECODE, implicit QUIT"
                        )
                    ctx.emitter.line("raise  # Propagate to caller")

        ctx.emitter.blank()
        ctx.current_label = None

    def _generate_label_body(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate the body statements for a label function.

        Factored out to support wrapping with NewScopeManager when needed.

        Handles fall-through semantics for SIMPLE_FUNCTIONS: labels without
        explicit exit (QUIT/GOTO/HALT) call the next label function directly
        at the end, implementing MUMPS fall-through behavior.

        Passes label.line_number to generate_scope_statements for external
        offset support, allowing external callers to enter at any line via
        D LABEL+N^ROUTINE calls.

        Args:
            label: MLabel ASG node
            ctx: Generator context
        """
        # Get label line for offset support
        label_line = label.line_number

        # Check for self-loop pattern
        if label.has_self_loop:
            # Wrap body in while True: for self-loop pattern
            ctx.emitter.line("while True:")
            with ctx.emitter.indented():
                generate_scope_statements(
                    label.body.statements, ctx, label_line=label_line
                )
                # If no explicit exit, add break to prevent infinite loop
                # This handles fall-through at end of label
                if not label.has_explicit_exit:
                    ctx.emitter.line("break")
            # After the while loop, fall through to next label if needed
            if label.needs_fallthrough and label.next_label:
                next_func = translate_name(label.next_label.name)
                ctx.emitter.line(f"return {next_func}(_rt, _scope=_scope)")
        else:
            # Generate body statements using scope-aware generator
            # This handles forward GOTO restructuring and offset guards automatically
            if label.body and label.body.statements:
                generate_scope_statements(
                    label.body.statements, ctx, label_line=label_line
                )
            else:
                # Empty function needs pass
                ctx.emitter.line("pass")

            # Fall-through to next label if needed.
            # For SIMPLE_FUNCTIONS, call the next label function directly
            # to implement MUMPS implicit fall-through behavior.
            if label.needs_fallthrough and label.next_label:
                next_func = translate_name(label.next_label.name)
                ctx.emitter.line(f"return {next_func}(_rt, _scope=_scope)")

    def _generate_simple_line_map(self, ctx: GeneratorContext) -> None:
        """Generate _line_map for SIMPLE_FUNCTIONS strategy.

        External routines may call this module with D +N^ROUTINE or
        D LABEL+N^ROUTINE patterns, so _line_map is always needed for
        line dispatch.

        Uses the same format as TRAMPOLINE:
        dict[int, tuple[str, int]] mapping line numbers to (label_name, offset).

        The calling code uses getattr(module, label_name) to get the function.
        SIMPLE_FUNCTIONS don't support offset entry (always starts from beginning),
        but _line_map is needed for run_with_goto_support() compatibility.

        Args:
            ctx: Generator context
        """
        line_map = generate_line_map(self._routine)

        if not line_map:
            # No line map needed - empty routine
            ctx.emitter.line("_line_map: dict[int, tuple[str, int]] = {}")
            ctx.emitter.blank()
            return

        # Generate _line_map dict (same format as TRAMPOLINE)
        generate_line_map_code(line_map, ctx.emitter)
        ctx.emitter.blank()

    def _generate_entry_function(self, ctx: GeneratorContext) -> None:
        """Generate _entry_function pointer to first label function.

        In MUMPS, D ^ROUTINE starts execution at line 1 of the routine,
        which may be a labelless preamble or a named label. This function
        generates an _entry_function variable pointing to the correct
        entry point for external routine calls.

        This is needed when the first line is labelless (preamble), because
        calling the routine by name (D ^V1LL1) should start at line 1,
        not at the named label (V1LL1) which may be on line 2.

        Args:
            ctx: Generator context
        """
        if not self._routine.labels:
            return

        first_label = self._routine.labels[0]
        entry_func_name = translate_name(first_label.name)

        ctx.emitter.blank()
        ctx.emitter.line(f"_entry_function = {entry_func_name}")
        ctx.emitter.blank()

    def _generate_main_block(self, ctx: GeneratorContext) -> None:
        """Generate if __name__ == "__main__" entry point block.

        Creates the runtime instance and scope, then calls the entry point.
        This allows the generated module to be run directly as a script.

        Args:
            ctx: Generator context
        """
        entry_label = self._routine.labels[0].name if self._routine.labels else None
        if entry_label is None:
            return

        entry_func = translate_name(entry_label)

        ctx.emitter.blank()
        ctx.emitter.line('if __name__ == "__main__":')
        with ctx.emitter.indented():
            # Create runtime and scope at entry point
            ctx.emitter.line("_rt = MUMPSRuntime()")
            ctx.emitter.line("_scope = {}")
            # Set up runtime context for this routine
            ctx.emitter.line("_rt._current_routine = _routine_name")
            ctx.emitter.line("_rt._current_source_lines = _source_lines")
            ctx.emitter.line("_rt._current_label_lines = _label_lines")
            # Call entry function with runtime and scope
            ctx.emitter.line(f"{entry_func}(_rt, _scope=_scope)")

    def _generate_trampoline_code(self, ctx: GeneratorContext) -> None:
        """Generate trampoline pattern code for cross-label GOTOs.

        Generates:
        1. Label functions prefixed with _ (they return (next_label, state) tuples)
        2. _labels dict mapping label names to functions
        3. Entry point function with trampoline dispatcher (named after first label)

        Wraps dispatcher loop in try/except for error handling:
        - Catches exceptions and calls _rt._handle_etrap()
        - If $ETRAP clears $ECODE, returns state (implicit QUIT)
        - If $ECODE not cleared, re-raises exception to propagate

        Args:
            ctx: Generator context
        """
        # Build mapping of label -> next label for fall-through
        labels = self._routine.labels
        next_label_map: dict[str, str | None] = {}
        for i, label in enumerate(labels):
            if i + 1 < len(labels):
                next_label_map[label.name] = labels[i + 1].name
            else:
                next_label_map[label.name] = None  # Last label falls through to exit

        # Generate label functions (they return (next_label, state) tuples)
        # Label functions are prefixed with _ so entry point can use label name
        for label in labels:
            self._generate_trampoline_label(label, ctx, next_label_map.get(label.name))

        # Generate _labels registry dict
        ctx.emitter.line("_labels = {")
        with ctx.emitter.indented():
            for label in self._routine.labels:
                # Use _LABEL for function name (prefixed)
                func_name = "_" + translate_name(label.name)
                ctx.emitter.line(f'"{label.name}": {func_name},')
        ctx.emitter.line("}")
        ctx.emitter.blank()

        # Generate _line_map for external D/G +N^ROUTINE patterns and
        # internal indirection that may resolve to offset calls at runtime.
        # Always emitted to ensure _line_map is defined even when
        # has_offset_calls is False (indirection can generate offset
        # references that pyright needs to see defined).
        line_map = generate_line_map(self._routine)
        if line_map:
            generate_line_map_code(line_map, ctx.emitter)
        else:
            ctx.emitter.line("_line_map: dict[int, tuple[str, int]] = {}")
        ctx.emitter.blank()

        has_offsets = self._routine.has_offset_calls

        # Generate trampoline dispatcher entry point
        # Named after the first label so it's the default entry point
        # Accept _rt parameter for shared runtime across routines
        # Accept _scope parameter for cross-routine variable visibility
        entry_label = self._routine.labels[0].name if self._routine.labels else None
        if entry_label is not None:
            entry_func = translate_name(entry_label)  # "" -> "_preamble"
            ctx.emitter.line(f"def {entry_func}(_rt, _scope=None):")
            with ctx.emitter.indented():
                ctx.emitter.line('"""Trampoline dispatcher for routine execution."""')
                # Initialize _scope if not provided (entry point behavior)
                ctx.emitter.line("_scope = _scope if _scope is not None else {}")
                # Update runtime context for $TEXT support in external routine calls.
                # When this routine is called via DO ^ROUTINE, $TEXT should return
                # lines from THIS routine, not the calling routine.
                ctx.emitter.line("_rt._current_routine = _routine_name")
                ctx.emitter.line("_rt._current_source_lines = _source_lines")
                ctx.emitter.line("_rt._current_label_lines = _label_lines")
                ctx.emitter.line("state = RoutineState()")
                # Initialize state from _scope for cross-routine visibility.
                # When called from another routine, variables may already exist in _scope.
                emit_scope_to_state_sync(ctx)
                if not ctx.uses_dynamic_locals:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        emit_scope_var_to_state(ctx, var_name, py_name)
                # Target can be str (label) or int (line number)
                ctx.emitter.line(f'target: str | int | None = "{entry_label}"')
                ctx.emitter.blank()
                ctx.emitter.line("while target is not None:")
                with ctx.emitter.indented():
                    # Wrap dispatcher loop body in try/except.
                    # This implements MUMPS $ETRAP error handling at trampoline level.
                    ctx.emitter.line("try:")
                    with ctx.emitter.indented():
                        if has_offsets:
                            # Handle int targets via _line_map
                            ctx.emitter.line("if isinstance(target, int):")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    "label_name, offset = _line_map[target]"
                                )
                                # _line_map stores Python function names (entry points)
                                # Internal trampoline functions have _ prefix, so add it
                                ctx.emitter.line("func = _globals['_' + label_name]")
                                # Pass _rt and _scope to inner functions
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope, _start_offset=offset)"
                                )
                            # Handle (label, offset) tuple targets from G LABEL+N
                            ctx.emitter.line("elif isinstance(target, tuple):")
                            with ctx.emitter.indented():
                                ctx.emitter.line("label_name, offset = target")
                                # Use _labels dict which maps MUMPS label names to internal functions
                                ctx.emitter.line("func = _labels[label_name]")
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope, _start_offset=offset)"
                                )
                            ctx.emitter.line("else:")
                            with ctx.emitter.indented():
                                ctx.emitter.line("func = _labels[target]")
                                # Pass _rt and _scope to inner functions
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope)"
                                )
                        else:
                            # No offsets: simple label dispatch
                            # Assert narrowing for type checker - target is str here
                            ctx.emitter.line("assert isinstance(target, str)")
                            ctx.emitter.line("func = _labels[target]")
                            # Pass _rt and _scope to inner functions
                            ctx.emitter.line("target, state = func(_rt, state, _scope)")
                    # Handle GotoExternal specially - it's control flow, not an error
                    # When a subroutine (DO) does an external GOTO, we run that chain
                    # to completion and then continue the trampoline
                    ctx.emitter.line("except GotoExternal as _goto:")
                    with ctx.emitter.indented():
                        # Sync state back to _scope BEFORE transferring control
                        # Static vars need explicit sync when not using dynamic locals
                        if not ctx.uses_dynamic_locals:
                            for var_name in sorted(ctx.state_vars):
                                py_name = translate_name(var_name)
                                emit_state_var_to_scope(ctx, var_name, py_name)
                        # Run the external GOTO chain to completion and sync back
                        _emit_goto_external_handler(ctx)
                        # Static scope→state sync after external call
                        if not ctx.uses_dynamic_locals:
                            for var_name in sorted(ctx.state_vars):
                                py_name = translate_name(var_name)
                                emit_scope_var_to_state(ctx, var_name, py_name)
                        # Continue the trampoline - set target to None to exit
                        # (the GOTO chain has completed, so we're done with this call)
                        ctx.emitter.line("target = None")
                    # Error handling — invoke $ETRAP if set
                    ctx.emitter.line("except Exception as _e:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("if _rt._handle_etrap(_e, _scope):")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "return state  # $ETRAP cleared $ECODE, implicit QUIT"
                            )
                        ctx.emitter.line("raise  # Propagate to caller")
                ctx.emitter.blank()
                # Unwind NEW stack before syncing state back to _scope.
                # This restores variables saved by NEW commands during the subroutine.
                if ctx.uses_dynamic_locals:
                    # Track keys before/after unwind to detect what was removed
                    ctx.emitter.line("_pre_unwind = set(state._locals.keys())")
                    ctx.emitter.line("unwind_new_stack(state)")
                    # Remove from _scope only keys that unwind explicitly removed
                    # (not ALL missing keys — _scope may have vars from called routines)
                    ctx.emitter.line(
                        "for _k in _pre_unwind - set(state._locals.keys()):"
                    )
                    with ctx.emitter.indented():
                        ctx.emitter.line("_scope.pop(_k, None)")
                # Sync state back to _scope before returning for cross-routine visibility
                emit_state_to_scope_sync(ctx)
                if not ctx.uses_dynamic_locals:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        emit_state_var_to_scope(
                            ctx, var_name, py_name, scope_key=var_name
                        )
                ctx.emitter.line("return state")
            ctx.emitter.blank()

        # Generate wrapper functions for all other labels that can be called via DO
        # These wrappers create a new state, call the internal function, and run
        # the trampoline until the subroutine returns (QUIT)
        for label in self._routine.labels[1:]:  # Skip first label, already has wrapper
            label_name = translate_name(label.name)
            internal_func = "_" + label_name

            # Get formal parameters
            formal_params = []
            if label.formal_list:
                formal_params = [translate_name(p) for p in label.formal_list]

            # Build parameter string
            if formal_params:
                formal_with_defaults = [f"{p}=None" for p in formal_params]
                params_str = "_rt, " + ", ".join(formal_with_defaults) + ", _scope=None"
                args_str = ", ".join(formal_params)
            else:
                params_str = "_rt, _scope=None"
                args_str = ""

            ctx.emitter.line(f"def {label_name}({params_str}):")
            with ctx.emitter.indented():
                ctx.emitter.line(f'"""Entry point for DO {label.name} calls."""')
                ctx.emitter.line("_scope = _scope if _scope is not None else {}")
                # Update runtime context for $TEXT support in external routine calls
                ctx.emitter.line("_rt._current_routine = _routine_name")
                ctx.emitter.line("_rt._current_source_lines = _source_lines")
                ctx.emitter.line("_rt._current_label_lines = _label_lines")
                ctx.emitter.line("state = RoutineState()")

                # Initialize state from _scope for cross-routine visibility
                emit_scope_to_state_sync(ctx)
                if not ctx.uses_dynamic_locals:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        emit_scope_var_to_state(ctx, var_name, py_name)

                # Wrap entire execution in try/except GotoExternal
                # This handles GotoExternal from both:
                # 1. The initial call to the internal function
                # 2. The trampoline dispatch loop
                ctx.emitter.line("try:")
                with ctx.emitter.indented():
                    # Call internal function and get next target
                    if args_str:
                        ctx.emitter.line(
                            f"target, state = {internal_func}(_rt, state, _scope, {args_str})"
                        )
                    else:
                        ctx.emitter.line(
                            f"target, state = {internal_func}(_rt, state, _scope)"
                        )

                    # Run trampoline until subroutine returns (target is None).
                    # Handle both int targets (line numbers from GOTO+offset)
                    # and string targets (label names from GOTO label).
                    ctx.emitter.line("while target is not None:")
                    with ctx.emitter.indented():
                        # Only handle int targets if routine has offset calls
                        if self._routine.has_offset_calls:
                            ctx.emitter.line("if isinstance(target, int):")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    "label_name, offset = _line_map[target]"
                                )
                                ctx.emitter.line("func = _globals['_' + label_name]")
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope, _start_offset=offset)"
                                )
                            # Handle (label, offset) tuple targets from G LABEL+N
                            ctx.emitter.line("elif isinstance(target, tuple):")
                            with ctx.emitter.indented():
                                ctx.emitter.line("label_name, offset = target")
                                # Use _labels dict which maps MUMPS label names to internal functions
                                ctx.emitter.line("func = _labels[label_name]")
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope, _start_offset=offset)"
                                )
                            ctx.emitter.line("else:")
                            with ctx.emitter.indented():
                                ctx.emitter.line("func = _labels[target]")
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope)"
                                )
                        else:
                            ctx.emitter.line("assert isinstance(target, str)")
                            ctx.emitter.line("func = _labels[target]")
                            ctx.emitter.line("target, state = func(_rt, state, _scope)")
                # Handle GotoExternal - run the external GOTO chain to completion
                # The subroutine's external GOTO runs to completion, then control
                # returns to the caller of this DO
                ctx.emitter.line("except GotoExternal as _goto:")
                with ctx.emitter.indented():
                    # Static state→scope sync before external call
                    if not ctx.uses_dynamic_locals:
                        for var_name in sorted(ctx.state_vars):
                            py_name = translate_name(var_name)
                            emit_state_var_to_scope(ctx, var_name, py_name)
                    # Run the external GOTO chain to completion and sync back
                    _emit_goto_external_handler(ctx)
                    # Static scope→state sync after external call
                    if not ctx.uses_dynamic_locals:
                        for var_name in sorted(ctx.state_vars):
                            py_name = translate_name(var_name)
                            emit_scope_var_to_state(ctx, var_name, py_name)

                # Unwind NEW stack before syncing state back to _scope
                if ctx.uses_dynamic_locals:
                    # Track keys before/after unwind to detect what was removed
                    ctx.emitter.line("_pre_unwind = set(state._locals.keys())")
                    ctx.emitter.line("unwind_new_stack(state)")
                    # Remove from _scope only keys that unwind explicitly removed
                    ctx.emitter.line(
                        "for _k in _pre_unwind - set(state._locals.keys()):"
                    )
                    with ctx.emitter.indented():
                        ctx.emitter.line("_scope.pop(_k, None)")
                # Sync state back to _scope before returning
                emit_state_to_scope_sync(ctx)
                if not ctx.uses_dynamic_locals:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        emit_state_var_to_scope(ctx, var_name, py_name)
                # Return extrinsic function return value if one was stored
                # Otherwise return state for normal DO calls
                ctx.emitter.line(
                    "return getattr(state, '_return_value', None) if hasattr(state, '_return_value') else state"
                )
            ctx.emitter.blank()

    def _generate_trampoline_label(
        self, label: MLabel, ctx: GeneratorContext, next_label: str | None = None
    ) -> None:
        """Generate label function for trampoline pattern.

        Label functions:
        - Prefixed with _ (e.g., _TEST, _NEXT) so entry point can use label name
        - Receive state parameter
        - Access state_vars via state.VAR
        - Return (next_label, state) or (None, state) for exit
        - Fall-through: return next label name if no explicit exit

        Args:
            label: MLabel ASG node
            ctx: Generator context
            next_label: Name of next label for fall-through (None if last label)

        Raises:
            UnsupportedFeatureError: For REQUIRES_RUNTIME scope strategy
        """

        ctx.current_label = label

        # Translate label name to valid Python identifier and prefix with _
        func_name = "_" + translate_name(label.name)

        # Get formal parameters from label or signature
        formal_params = []
        if label.formal_list:
            formal_params = [translate_name(p) for p in label.formal_list]
        elif label.signature and label.signature.formal_params:
            formal_params = [translate_name(p) for p in label.signature.formal_params]

        # REQUIRES_RUNTIME strategy is supported for TRAMPOLINE too.
        # Labels with indirection/XECUTE use _rt.get_var()/_rt.set_var() at runtime.

        # Generate function definition with state parameter.
        # All trampoline labels take _rt, state and _scope; formal params come after.
        # _start_offset parameter supports offset entry (D LABEL+N).
        # Uses pre-computed ASG field from classify_gotos() analysis.
        # Formal params have None default so they can be omitted
        # (MUMPS allows calling with fewer args than defined).
        has_offsets = self._routine.has_offset_calls
        formal_params_with_defaults = [f"{p}=None" for p in formal_params]
        if formal_params:
            if has_offsets:
                params_str = (
                    "_rt, state, _scope, "
                    + ", ".join(formal_params_with_defaults)
                    + ", _start_offset=0"
                )
            else:
                params_str = "_rt, state, _scope, " + ", ".join(
                    formal_params_with_defaults
                )
        else:
            if has_offsets:
                params_str = "_rt, state, _scope, _start_offset=0"
            else:
                params_str = "_rt, state, _scope"

        # Return type annotation for trampoline labels.
        # Target can be str (label name), int (line number), or None (exit).
        # Line numbers can come from explicit D LABEL+N or from indirection
        # that resolves offsets at runtime, so always include int.
        return_type = "Tuple[str | int | None, RoutineState]"
        ctx.emitter.line(f"def {func_name}({params_str}) -> {return_type}:")

        with ctx.emitter.indented():
            # Declare global _test
            ctx.emitter.line("global _test")

            # Store formal parameters in state if they need to flow across GOTO
            # This handles cases like SUB(X) G SHOW where SHOW needs to read X
            state_vars = ctx.state_vars or set()
            for param in formal_params:
                if param in state_vars:
                    ctx.emitter.line(f"state.{param} = {param}")

            # Initialize formal parameters in state._locals for dynamic locals
            # The wrapper passes formal params as positional args to the internal
            # function, but the body reads variables from state._locals dict.
            # Without this, the initial parameter value is lost.
            # If param is an MArray (by-ref), alias it directly for
            # DATA-CELL semantics. Otherwise wrap the value in a new MArray.
            if ctx.uses_dynamic_locals and formal_params:
                for param in formal_params:
                    ctx.emitter.line(f"if isinstance({param}, MArray):")
                    with ctx.emitter.indented():
                        ctx.emitter.line(f"state._locals[{param!r}] = {param}")
                    ctx.emitter.line("else:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f"state._locals.setdefault({param!r}, MArray()).value = {param}"
                        )

            # Fallback: formal params NOT in state_vars and NOT in dynamic_locals
            # must be placed into _scope so the body can read them via _scope[].
            # This handles TRAMPOLINE labels with static state vars where the
            # formal parameter is local to one label (not shared across GOTOs).
            if not ctx.uses_dynamic_locals and formal_params:
                for param in formal_params:
                    if param not in state_vars:
                        ctx.emitter.line(f"if {param} is not None:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(f"if isinstance({param}, MArray):")
                            with ctx.emitter.indented():
                                ctx.emitter.line(f"_scope[{param!r}] = {param}")
                            ctx.emitter.line("else:")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    f"_scope.setdefault({param!r}, MArray()).value = {param}"
                                )

            # Get label line number for offset calculation
            label_line = label.line_number

            # Self-loop labels wrap body in while True:
            # Self-loop GOTOs become continue, QUIT becomes break
            if label.has_self_loop:
                ctx.emitter.line("while True:")
                with ctx.emitter.indented():
                    # Generate body statements
                    # Use offset guards when routine has offset calls
                    if has_offsets and label_line is not None:
                        generate_offset_guarded_statements(
                            label.body.statements, label_line, ctx
                        )
                    else:
                        generate_scope_statements(label.body.statements, ctx)
                    # Implicit break at end if no explicit exit (to prevent infinite loop)
                    if not label.has_explicit_exit:
                        ctx.emitter.line("break")
            else:
                # Generate body statements using scope-aware generator
                # This handles forward GOTO restructuring automatically
                if label.body and label.body.statements:
                    # Use offset guards when routine has offset calls
                    if has_offsets and label_line is not None:
                        generate_offset_guarded_statements(
                            label.body.statements, label_line, ctx
                        )
                    else:
                        generate_scope_statements(label.body.statements, ctx)
                else:
                    # Empty function needs pass
                    ctx.emitter.line("pass")

            # Fall-through: return next label or None if last label
            # This handles labels that don't end with explicit GOTO or QUIT
            if next_label:
                ctx.emitter.line(f'return ("{next_label}", state)')
            else:
                ctx.emitter.line("return (None, state)")

        ctx.emitter.blank()
        ctx.current_label = None


__all__ = [
    "RoutineGenerator",
    "GeneratorContext",
    "validate_analysis_complete",
    "AnalysisNotCompleteError",
]
