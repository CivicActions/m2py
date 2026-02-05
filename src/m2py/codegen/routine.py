"""Routine code generation for MUMPS-to-Python transpilation.

Generates complete Python modules from MUMPS routines.
Handles module structure, imports, labels as functions, and $TEST tracking.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional

from m2py.asg.elements import MLabel, MRoutine
from m2py.asg.enums import ScopeStrategy
from m2py.analysis.variables import FunctionSignature
from m2py.codegen.emitter import CodeEmitter
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.line_dispatch import (
    generate_line_map,
    generate_line_map_code,
)
from m2py.codegen.names import NameTranslator, translate_name
from m2py.codegen.statements import (
    generate_offset_guarded_statements,
    generate_scope_statements,
)

if TYPE_CHECKING:
    pass


@dataclass
class GeneratorContext:
    """Context passed through code generation.

    Carries state needed by expression and statement generators.
    Extended for Spec 005 with signatures and loop tracking.
    Extended for Spec 006 with strategy and state variable tracking.
    Extended for Spec 017 with dynamic locals support.
    """

    routine: MRoutine
    emitter: CodeEmitter
    name_translator: NameTranslator = field(default_factory=NameTranslator)
    imports: set[str] = field(default_factory=set)
    current_label: Optional[MLabel] = None

    # Spec 005: Function signatures for label code generation
    signatures: Dict[str, FunctionSignature] = field(default_factory=dict)

    # Spec 005: Flag for $TEST save/restore in extrinsic calls
    in_extrinsic_call: bool = False

    # Spec 006: GOTO strategy for cross-label pattern
    strategy: "GotoStrategy" = None  # type: ignore[assignment]

    # Spec 006: Variables stored in RoutineState (for state.VAR access)
    state_vars: set[str] = field(default_factory=set)

    # Spec 006: Array variables (MArray-backed) for subscript access
    array_vars: set[str] = field(default_factory=set)

    # Variables that are read but never written in the routine (input-only from caller).
    # In TRAMPOLINE mode, these need to be read from _scope instead of bare Python vars.
    input_only_vars: set[str] = field(default_factory=set)

    # Spec 011: Name of the NewScopeManager variable when inside a NEW-managed block
    # If set, _generate_new() should use _new_mgr.new_var() instead of _scope.pop()
    new_scope_manager_var: Optional[str] = None

    # Spec 017: True when routine uses dynamic _locals dict instead of static fields
    # This happens when routine contains argumentless KILL or argumentless NEW
    uses_dynamic_locals: bool = False

    # Spec 017 Phase 14 (T075m): True when generating code inside inline XECUTE
    # GOTO/DO inside inline XECUTE should raise _XecuteExit instead of return
    in_inline_xecute: bool = False

    # Spec 017 Phase 11: Counter for generating unique FOR loop variable names
    # Prevents nested FOR loops from clobbering each other's _for_start/_for_step/_for_end
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


def get_scope_strategy_pattern(strategy: ScopeStrategy) -> str:
    """Get the code generation pattern for a scope strategy.

    Args:
        strategy: The ScopeStrategy enum value

    Returns:
        String describing the pattern for documentation/debugging

    Note:
        Actual code generation is handled in _generate_label based on
        the strategy and FunctionSignature details.
    """
    patterns = {
        ScopeStrategy.PURE_FUNCTION: "def label(args) -> return_type: return expr",
        ScopeStrategy.FUNCTION_WITH_OUTPUTS: "def label(args) -> Tuple: return (value, *byref_outputs)",
        ScopeStrategy.SUBROUTINE: "def label(args) -> None: pass",
        ScopeStrategy.REQUIRES_RUNTIME: "# Requires runtime scope - not supported in Spec 005",
    }
    return patterns.get(strategy, "# Unknown strategy")


# T104: Removed _routine_needs_loop_exit_exception() - now using
# MRoutine.needs_loop_exit_exception field populated by classify_gotos()


class RoutineGenerator:
    """Generates Python code for a complete MUMPS routine.

    Transforms an MRoutine ASG into executable Python code with:
    - Required imports for helpers and runtime
    - Module-level runtime instance (_rt)
    - Module-level $TEST tracking (_test)
    - Labels as Python functions

    Spec 006: Strategy selection determines code generation pattern:
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

        Spec 006 (T058): Selects generation pattern based on strategy.
        - SIMPLE_FUNCTIONS: Labels as Python functions (Spec 005 behavior)
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
            # Spec 017: Check if routine needs dynamic _locals dict
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
            # Spec 006: Trampoline pattern with RoutineState
            self._generate_trampoline_code(ctx)
        else:
            # Spec 005: Simple functions pattern
            for label in self._routine.labels:
                self._generate_label(label, ctx)

            # Spec 008 (T089-T092): Generate _line_map for external D/G +N^ROUTINE patterns
            # External routines can call this module with D +N^ROUTINE or D LABEL+N^ROUTINE
            # so we always need _line_map for line dispatch
            self._generate_simple_line_map(ctx)

        # Generate _entry_function for D ^ROUTINE semantics
        # This points to the first label (line 1), which may be preamble or named label
        self._generate_entry_function(ctx)

        # T077: Generate if __name__ == "__main__" entry point block
        self._generate_main_block(ctx)

        code = self._emitter.get_code()

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

        Spec 006: Adds RoutineState imports and class for TRAMPOLINE strategy.
        Spec 012: Adds re import for pattern matching.

        Args:
            ctx: Generator context
        """
        # Imports
        ctx.emitter.line("import re")
        ctx.emitter.line("import time")
        ctx.emitter.line("from decimal import Decimal")
        ctx.emitter.line("from itertools import chain, count")
        ctx.emitter.line(
            "from m2py.codegen.helpers import m_str, m_num, m_truth, m_compare, m_div, m_add, m_sub, m_mul, m_mod, m_range"
        )
        # Spec 009 (T024): Import MArray for subscripted local variable support
        ctx.emitter.line("from m2py.runtime import MUMPSRuntime, MArray")
        # Spec 009: Import LHS function helpers (Phase 3-4) and $DATA helpers (Phase 8)
        # Spec 010: Import $ORDER and $QUERY helpers (Phase 2), $SELECT helper (Phase 3)
        # Spec 010: Import $PIECE and $EXTRACT helpers (Phase 5), $GET helpers (Phase 6)
        # Spec 010: Import $FIND helper (Phase 7), $NAME/$QLENGTH/$QSUBSCRIPT (Phase 9)
        # Spec 010: Import $FNUMBER helper (Phase 10)
        # Spec 011: Import sorts-after helper (Phase 10, uses MUMPS collation), pattern_match (Phase 12)
        # Spec 011: Import NewScopeManager for NEW command scope semantics
        # Spec 011 Phase 20: Import READ command helpers
        # Spec 017 Phase 18: Import m_var_value for cross-routine variable access
        # Spec 017 Phase 19: Import _format_subscript for building var name strings with proper quoting
        # Note: Contains ([) and follows (]) are inlined as Python expressions
        ctx.emitter.line(
            "from m2py.runtime.helpers import m_set_piece, m_set_extract, m_data, m_data_global, m_order, m_order_global, m_query, m_query_global, _raise_select_false, m_piece, m_extract, m_get, m_get_global, m_find, m_name, m_qlength, m_qsubscript, m_justify, m_fnumber, m_sorts_after, m_pattern_match, NewScopeManager, m_read_timeout, m_read_char, m_var_value, _format_subscript"
        )
        # Spec 010: Import $RANDOM helper (Phase 8)
        ctx.emitter.line("from m2py.codegen.expressions import _m_random_checked")

        # Spec 006: Additional imports for trampoline pattern
        if self._strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("from dataclasses import dataclass, field")
            ctx.emitter.line("from typing import Any, Optional, Tuple")
            # T075: Import GotoExternal and run_with_goto_support for cross-routine GOTO handling
            ctx.emitter.line(
                "from m2py.runtime import GotoExternal, run_with_goto_support, resolve_goto_target, LabelNotFoundError"
            )

        ctx.emitter.blank()

        # T078: Remove module-level _rt creation
        # _rt is now passed as a parameter to all label functions
        # Entry point (if __name__ == "__main__") creates the shared instance

        # $TEST tracking
        ctx.emitter.line("_test = False")
        ctx.emitter.blank()

        # Spec 008: Module constants for external call infrastructure
        # _source_lines: Original MUMPS source for $TEXT support
        source_lines = self._routine.source_lines or []
        ctx.emitter.line(f"_source_lines = {source_lines!r}")
        ctx.emitter.blank()

        # _routine_name: Name of this routine for $TEXT(+0) and error messages
        # Falls back to first non-empty label name if routine.name is not set
        # Preserves original case for $TEXT(+0) which returns source-accurate routine name
        routine_name = self._routine.name
        if not routine_name:
            # Find first non-empty label name (skipping labelless preamble)
            for label in self._routine.labels:
                if label.name:
                    routine_name = label.name
                    break
            else:
                routine_name = ""
        ctx.emitter.line(f'_routine_name = "{routine_name}"')
        ctx.emitter.blank()

        # _label_lines: Maps label names to 0-indexed line numbers for $TEXT(LABEL+offset)
        label_lines = {
            label.name: label.line_number - 1
            for label in self._routine.labels
            if label.line_number is not None
        }
        ctx.emitter.line(f"_label_lines = {label_lines!r}")
        ctx.emitter.blank()

        # T078: Removed _rt._current_* initialization
        # Runtime context is now set per-call within label functions that use $TEXT

        # Spec 006: Generate RoutineState class for trampoline pattern
        if self._strategy == GotoStrategy.TRAMPOLINE:
            from m2py.codegen.shared_state import generate_routine_state_class

            state_class = generate_routine_state_class(self._routine)
            for line in state_class.strip().split("\n"):
                ctx.emitter.line(line)
            ctx.emitter.blank()

        # T083: Extrinsic function helper - saves/restores $TEST
        # T076: Accept _rt as first parameter for shared runtime
        # Spec 010 (T020): Handle by-ref parameter unpacking via _byref
        # Spec 011: Set _in_extrinsic flag for $QUIT tracking
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
            # Spec 011: Save/restore _in_extrinsic for $QUIT tracking
            ctx.emitter.line("_saved_extrinsic = _rt._in_extrinsic")
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                # Spec 011: Mark that we're in an extrinsic for $QUIT
                ctx.emitter.line("_rt._in_extrinsic = True")
                # T083: Pass _rt and _scope to external extrinsic
                ctx.emitter.line("if _scope is not None:")
                with ctx.emitter.indented():
                    ctx.emitter.line("_result = _ef(_rt, *args, _scope=_scope)")
                ctx.emitter.line("else:")
                with ctx.emitter.indented():
                    ctx.emitter.line("_result = _ef(_rt, *args)")
                # Spec 010 (T020): Handle by-ref unpacking
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
                ctx.emitter.line("_test = _saved")
                # Spec 011: Restore extrinsic flag for nested calls
                ctx.emitter.line("_rt._in_extrinsic = _saved_extrinsic")
        ctx.emitter.blank()

        # T036: _LoopExit exception for multi-loop exits
        # Only generate if the routine has MULTI_LOOP_EXIT GOTOs
        # FR-018: Accept optional target parameter for cross-label exits
        # T104: Use pre-computed field from classify_gotos()
        if self._routine.needs_loop_exit_exception:
            ctx.emitter.line("class _LoopExit(Exception):")
            with ctx.emitter.indented():
                ctx.emitter.line('"""Exception for multi-loop exit via GOTO."""')
                ctx.emitter.line("def __init__(self, target=None):")
                with ctx.emitter.indented():
                    ctx.emitter.line("self.target = target")
            ctx.emitter.blank()

        # T075m: _XecuteExit exception for GOTO/DO inside inline XECUTE
        # This allows GOTO inside XECUTE to exit just the XECUTE block
        # without returning from the enclosing function
        ctx.emitter.line("class _XecuteExit(Exception):")
        with ctx.emitter.indented():
            ctx.emitter.line(
                '"""Exception for control flow exit from inline XECUTE."""'
            )
            ctx.emitter.line("pass")
        ctx.emitter.blank()

    def _generate_label_docstring(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate Python docstring with MUMPS source info.

        Spec 014 (T065): Generates a docstring for each label function containing:
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

        Spec 006 (T069a): Labels with has_self_loop=True wrap body in while True:
        - Self-loop GOTOs become continue
        - QUIT becomes break (implicit at end of body)
        - Other exits (cross-label GOTO) use return

        Spec 014 (T055): Wraps body in try/except for error handling:
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

        # Spec 012 Phase 3: REQUIRES_RUNTIME strategy is now supported.
        # Labels with indirection/XECUTE use _rt.get_var()/_rt.set_var() at runtime.
        # The strategy is handled the same as SIMPLE_FUNCTIONS for code generation.

        # T076: Add _rt as first parameter for shared runtime across routines
        # T030: Add _scope parameter for cross-routine variable visibility
        # All labels accept _rt and _scope so they can be called externally (D LABEL^ROUTINE)
        # _scope must come AFTER formal params since it has a default value
        # _start_offset allows external callers to pass offset for D LABEL+N^ROUTINE calls
        # Spec 017 Phase 19: Formal params have None default so they can be omitted
        # (MUMPS allows calling with fewer args than defined - undefined params have $D()=0)
        formal_params_with_defaults = [f"{p}=None" for p in formal_params]
        all_params = (
            ["_rt"] + formal_params_with_defaults + ["_scope=None", "_start_offset=0"]
        )
        params_str = ", ".join(all_params)
        ctx.emitter.line(f"def {func_name}({params_str}):")

        with ctx.emitter.indented():
            # Spec 014 (T065): Generate docstring with MUMPS source info
            self._generate_label_docstring(label, ctx)

            # Declare global _test
            ctx.emitter.line("global _test")
            # T030: Initialize _scope if not provided (entry point behavior)
            ctx.emitter.line("_scope = _scope if _scope is not None else {}")
            # T075f: Update runtime context for $TEXT support in external routine calls
            ctx.emitter.line("_rt._current_routine = _routine_name")
            ctx.emitter.line("_rt._current_source_lines = _source_lines")
            ctx.emitter.line("_rt._current_label_lines = _label_lines")

            # T084: Copy formal parameters into _scope for variable reads
            # Use original MUMPS names for _scope keys, translated names for Python vars
            # Spec 009 (T021): Use MArray for consistency with subscripted variables
            # Spec 017: Formal parameters are implicitly NEWed per MUMPS spec
            original_formal_params = label.formal_list or []
            if (
                label.signature
                and label.signature.formal_params
                and not label.formal_list
            ):
                original_formal_params = label.signature.formal_params

            # Spec 014 (T055): Wrap body in try/except for error handling
            # This implements MUMPS $ETRAP error handling at stack frame boundaries
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                # Spec 011/017: Use NewScopeManager if label has:
                # - Explicit NEW statements, OR
                # - Formal parameters (implicitly NEWed per MUMPS spec)
                needs_scope_manager = label.has_new_statements or bool(
                    original_formal_params
                )
                if needs_scope_manager:
                    ctx.emitter.line("with NewScopeManager(_scope) as _new_mgr:")
                    ctx.new_scope_manager_var = "_new_mgr"
                    with ctx.emitter.indented():
                        # Spec 017: NEW formal parameters first (saves caller's values)
                        # Then assign parameter values to _scope
                        # Phase 19: Only assign if parameter was actually passed (not None)
                        # This ensures $D(param)=0 for undefined parameters
                        for orig_name in original_formal_params:
                            ctx.emitter.line(f"_new_mgr.new_var({orig_name!r})")
                            python_name = translate_name(orig_name)
                            ctx.emitter.line(f"if {python_name} is not None:")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    f"_scope[{orig_name!r}] = MArray(value={python_name})"
                                )
                        self._generate_label_body(label, ctx)
                    ctx.new_scope_manager_var = None
                else:
                    self._generate_label_body(label, ctx)

            # Spec 014 (T055): Error handling - invoke $ETRAP if set
            ctx.emitter.line("except Exception as _e:")
            with ctx.emitter.indented():
                ctx.emitter.line("if _rt._handle_etrap(_e, _scope):")
                with ctx.emitter.indented():
                    ctx.emitter.line("return  # $ETRAP cleared $ECODE, implicit QUIT")
                ctx.emitter.line("raise  # Propagate to caller")

        ctx.emitter.blank()
        ctx.current_label = None

    def _generate_label_body(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate the body statements for a label function.

        Factored out to support wrapping with NewScopeManager when needed.

        Spec 013 (T031-T033): Handles fall-through semantics for SIMPLE_FUNCTIONS.
        Labels without explicit exit (QUIT/GOTO/HALT) call the next label
        function directly at the end, implementing MUMPS fall-through behavior.

        T075a: External offset support for SIMPLE_FUNCTIONS strategy.
        Pass label.line_number to generate_scope_statements so it can wrap
        statements with offset guards (if _start_offset <= offset:). This allows
        external callers to enter at any line via D LABEL+N^ROUTINE calls.

        Args:
            label: MLabel ASG node
            ctx: Generator context
        """
        # Get label line for offset support
        label_line = label.line_number

        # Spec 006 (T069a): Check for self-loop pattern
        if label.has_self_loop:
            # Wrap body in while True: for self-loop pattern
            ctx.emitter.line("while True:")
            with ctx.emitter.indented():
                if label.body and label.body.statements:
                    generate_scope_statements(
                        label.body.statements, ctx, label_line=label_line
                    )
                else:
                    ctx.emitter.line("pass")
                # If no explicit exit, add break to prevent infinite loop
                # This handles fall-through at end of label
                if not label.has_explicit_exit:
                    ctx.emitter.line("break")
            # Spec 013: After the while loop, fall through to next label if needed
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

            # Spec 013 (T031): Fall-through to next label if needed
            # For SIMPLE_FUNCTIONS, we call the next label function directly
            # This implements MUMPS implicit fall-through behavior
            if label.needs_fallthrough and label.next_label:
                next_func = translate_name(label.next_label.name)
                ctx.emitter.line(f"return {next_func}(_rt, _scope=_scope)")

    def _generate_simple_line_map(self, ctx: GeneratorContext) -> None:
        """Generate _line_map for SIMPLE_FUNCTIONS strategy.

        Spec 008 (T089-T092): External routines may call this module with
        D +N^ROUTINE or D LABEL+N^ROUTINE patterns, so we always need
        _line_map for line dispatch.

        For SIMPLE_FUNCTIONS, _line_map uses the same format as TRAMPOLINE:
        dict[int, tuple[str, int]] mapping line numbers to (label_name, offset).

        The calling code then uses getattr(module, label_name) to get the function.
        Note: SIMPLE_FUNCTIONS don't support offset entry (always starts from beginning),
        but we need the _line_map for run_with_goto_support() compatibility.

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

        T077: Creates the runtime instance and scope, then calls the entry point.
        This allows the generated module to be run directly as a script.

        Args:
            ctx: Generator context
        """
        entry_label = self._routine.labels[0].name if self._routine.labels else None
        if not entry_label:
            return

        entry_func = translate_name(entry_label)

        ctx.emitter.blank()
        ctx.emitter.line('if __name__ == "__main__":')
        with ctx.emitter.indented():
            # T077: Create runtime and scope at entry point
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

        Spec 006 (T056): Generates:
        1. Label functions prefixed with _ (they return (next_label, state) tuples)
        2. _labels dict mapping label names to functions
        3. Entry point function with trampoline dispatcher (named after first label)

        Spec 014 (T055): Wraps dispatcher loop in try/except for error handling:
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

        # Spec 007 (T010-T012): Generate _line_map when routine has offset calls
        # Uses pre-computed ASG field from classify_gotos() analysis
        has_offsets = self._routine.has_offset_calls
        if has_offsets:
            line_map = generate_line_map(self._routine)
            generate_line_map_code(line_map, ctx.emitter)
            ctx.emitter.blank()

        # Generate trampoline dispatcher entry point
        # Named after the first label so it's the default entry point
        # T076: Accept _rt parameter for shared runtime across routines
        # T030: Accept _scope parameter for cross-routine variable visibility
        entry_label = self._routine.labels[0].name if self._routine.labels else None
        if entry_label:
            entry_func = translate_name(entry_label)
            ctx.emitter.line(f"def {entry_func}(_rt, _scope=None):")
            with ctx.emitter.indented():
                ctx.emitter.line('"""Trampoline dispatcher for routine execution."""')
                # T030: Initialize _scope if not provided (entry point behavior)
                ctx.emitter.line("_scope = _scope if _scope is not None else {}")
                # T075f: Update runtime context for $TEXT support in external routine calls
                # When this routine is called via DO ^ROUTINE, $TEXT should return
                # lines from THIS routine, not the calling routine
                ctx.emitter.line("_rt._current_routine = _routine_name")
                ctx.emitter.line("_rt._current_source_lines = _source_lines")
                ctx.emitter.line("_rt._current_label_lines = _label_lines")
                ctx.emitter.line("state = RoutineState()")
                # T075b: Initialize state from _scope for cross-routine visibility
                # When called from another routine, variables may already exist in _scope
                if ctx.uses_dynamic_locals:
                    # T075j: For dynamic locals, copy _scope into state._locals
                    # Values must be wrapped in MArray if they aren't already,
                    # since the expression codegen expects MArray.value access
                    ctx.emitter.line("for k, v in _scope.items():")
                    with ctx.emitter.indented():
                        ctx.emitter.line("if isinstance(v, MArray):")
                        with ctx.emitter.indented():
                            ctx.emitter.line("state._locals[k] = v")
                        ctx.emitter.line("else:")
                        with ctx.emitter.indented():
                            ctx.emitter.line("_m = MArray()")
                            ctx.emitter.line("_m.value = v")
                            ctx.emitter.line("state._locals[k] = _m")
                else:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        # Check if variable exists in _scope and initialize from it
                        ctx.emitter.line(
                            f"if {var_name!r} in _scope: state.{py_name} = _scope[{var_name!r}].value if isinstance(_scope.get({var_name!r}), MArray) else _scope[{var_name!r}]"
                        )
                # Spec 007 (T018): Target can be str (label) or int (line number)
                ctx.emitter.line(f'target: str | int | None = "{entry_label}"')
                ctx.emitter.blank()
                ctx.emitter.line("while target is not None:")
                with ctx.emitter.indented():
                    # Spec 014 (T055): Wrap dispatcher loop body in try/except
                    # This implements MUMPS $ETRAP error handling at trampoline level
                    ctx.emitter.line("try:")
                    with ctx.emitter.indented():
                        if has_offsets:
                            # Spec 007 (T018-T019): Handle int targets via _line_map
                            ctx.emitter.line("if isinstance(target, int):")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    "label_name, offset = _line_map[target]"
                                )
                                # _line_map stores Python function names (entry points)
                                # Internal trampoline functions have _ prefix, so add it
                                ctx.emitter.line("func = globals()['_' + label_name]")
                                # T076: Pass _rt and _scope to inner functions
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope, _start_offset=offset)"
                                )
                            # T087: Handle (label, offset) tuple targets from G LABEL+N
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
                                # T076: Pass _rt and _scope to inner functions
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope)"
                                )
                        else:
                            # No offsets: simple label dispatch
                            ctx.emitter.line("func = _labels[target]")
                            # T076: Pass _rt and _scope to inner functions
                            ctx.emitter.line("target, state = func(_rt, state, _scope)")
                    # Handle GotoExternal specially - it's control flow, not an error
                    # When a subroutine (DO) does an external GOTO, we run that chain
                    # to completion and then continue the trampoline
                    ctx.emitter.line("except GotoExternal as _goto:")
                    with ctx.emitter.indented():
                        # Run the external GOTO chain to completion
                        ctx.emitter.line("run_with_goto_support(")
                        with ctx.emitter.indented():
                            ctx.emitter.line("resolve_goto_target(_goto), _rt, _scope")
                        ctx.emitter.line(")")
                        # Continue the trampoline - set target to None to exit
                        # (the GOTO chain has completed, so we're done with this call)
                        ctx.emitter.line("target = None")
                    # Spec 014 (T055): Error handling - invoke $ETRAP if set
                    ctx.emitter.line("except Exception as _e:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("if _rt._handle_etrap(_e, _scope):")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "return state  # $ETRAP cleared $ECODE, implicit QUIT"
                            )
                        ctx.emitter.line("raise  # Propagate to caller")
                ctx.emitter.blank()
                # T075b: Sync state back to _scope before returning for cross-routine visibility
                if ctx.uses_dynamic_locals:
                    # For dynamic locals, copy state._locals back to _scope
                    ctx.emitter.line(
                        "_scope.update({k: v for k, v in state._locals.items()})"
                    )
                else:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        ctx.emitter.line(f"_scope[{var_name!r}] = state.{py_name}")
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
                params_str = "_rt, " + ", ".join(formal_params) + ", _scope=None"
                args_str = ", ".join(formal_params)
            else:
                params_str = "_rt, _scope=None"
                args_str = ""

            ctx.emitter.line(f"def {label_name}({params_str}):")
            with ctx.emitter.indented():
                ctx.emitter.line(f'"""Entry point for DO {label.name} calls."""')
                ctx.emitter.line("_scope = _scope if _scope is not None else {}")
                # T075f: Update runtime context for $TEXT support in external routine calls
                ctx.emitter.line("_rt._current_routine = _routine_name")
                ctx.emitter.line("_rt._current_source_lines = _source_lines")
                ctx.emitter.line("_rt._current_label_lines = _label_lines")
                ctx.emitter.line("state = RoutineState()")

                # T075b: Initialize state from _scope for cross-routine visibility
                if ctx.uses_dynamic_locals:
                    # T075j: For dynamic locals, copy _scope into state._locals
                    # Values must be wrapped in MArray if they aren't already,
                    # since the expression codegen expects MArray.value access
                    ctx.emitter.line("for k, v in _scope.items():")
                    with ctx.emitter.indented():
                        ctx.emitter.line("if isinstance(v, MArray):")
                        with ctx.emitter.indented():
                            ctx.emitter.line("state._locals[k] = v")
                        ctx.emitter.line("else:")
                        with ctx.emitter.indented():
                            ctx.emitter.line("_m = MArray()")
                            ctx.emitter.line("_m.value = v")
                            ctx.emitter.line("state._locals[k] = _m")
                else:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        ctx.emitter.line(
                            f"if {var_name!r} in _scope: state.{py_name} = _scope[{var_name!r}].value if isinstance(_scope.get({var_name!r}), MArray) else _scope[{var_name!r}]"
                        )

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

                    # Run trampoline until subroutine returns (target is None)
                    # T075: Handle both int targets (line numbers from GOTO+offset)
                    # and string targets (label names from GOTO label)
                    ctx.emitter.line("while target is not None:")
                    with ctx.emitter.indented():
                        # Only handle int targets if routine has offset calls
                        if self._routine.has_offset_calls:
                            ctx.emitter.line("if isinstance(target, int):")
                            with ctx.emitter.indented():
                                ctx.emitter.line(
                                    "label_name, offset = _line_map[target]"
                                )
                                ctx.emitter.line("func = globals()['_' + label_name]")
                                ctx.emitter.line(
                                    "target, state = func(_rt, state, _scope, _start_offset=offset)"
                                )
                            # T087: Handle (label, offset) tuple targets from G LABEL+N
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
                            ctx.emitter.line("func = _labels[target]")
                            ctx.emitter.line("target, state = func(_rt, state, _scope)")
                # Handle GotoExternal - run the external GOTO chain to completion
                # The subroutine's external GOTO runs to completion, then control
                # returns to the caller of this DO
                ctx.emitter.line("except GotoExternal as _goto:")
                with ctx.emitter.indented():
                    ctx.emitter.line("run_with_goto_support(")
                    with ctx.emitter.indented():
                        ctx.emitter.line("resolve_goto_target(_goto), _rt, _scope")
                    ctx.emitter.line(")")
                    # After external GOTO runs, sync _scope back into state
                    # so state reflects any changes made by the external routine
                    if ctx.uses_dynamic_locals:
                        ctx.emitter.line("for _k, _v in _scope.items():")
                        with ctx.emitter.indented():
                            ctx.emitter.line("if isinstance(_v, MArray):")
                            with ctx.emitter.indented():
                                ctx.emitter.line("state._locals[_k] = _v")
                            ctx.emitter.line("else:")
                            with ctx.emitter.indented():
                                ctx.emitter.line("_m = MArray()")
                                ctx.emitter.line("_m.value = _v")
                                ctx.emitter.line("state._locals[_k] = _m")
                    else:
                        for var_name in sorted(ctx.state_vars):
                            py_name = translate_name(var_name)
                            ctx.emitter.line(
                                f"if {var_name!r} in _scope: state.{py_name} = _scope[{var_name!r}].value if isinstance(_scope.get({var_name!r}), MArray) else _scope[{var_name!r}]"
                            )

                # T075b: Sync state back to _scope before returning
                if ctx.uses_dynamic_locals:
                    # For dynamic locals, copy state._locals back to _scope
                    ctx.emitter.line(
                        "_scope.update({k: v for k, v in state._locals.items()})"
                    )
                else:
                    for var_name in sorted(ctx.state_vars):
                        py_name = translate_name(var_name)
                        ctx.emitter.line(f"_scope[{var_name!r}] = state.{py_name}")
                ctx.emitter.line("return state")
            ctx.emitter.blank()

    def _generate_trampoline_label(
        self, label: MLabel, ctx: GeneratorContext, next_label: str | None = None
    ) -> None:
        """Generate label function for trampoline pattern.

        Spec 006 (T057): Label functions:
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

        # Spec 012 Phase 3: REQUIRES_RUNTIME strategy is now supported for TRAMPOLINE too.
        # Labels with indirection/XECUTE use _rt.get_var()/_rt.set_var() at runtime.

        # Generate function definition with state parameter
        # T076: All labels take _rt as first parameter for shared runtime
        # For trampoline, all labels take _rt, state and _scope; formal params come later
        # Spec 007 (T020): Add _start_offset parameter for offset entry support
        # Spec 008: Add _scope parameter for external call support
        # Uses pre-computed ASG field from classify_gotos() analysis
        # Spec 017 Phase 19: Formal params have None default so they can be omitted
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

        # Return type annotation for trampoline labels
        # Spec 007: return type is str | int | None (can be label name or line number)
        if has_offsets:
            return_type = "Tuple[Optional[str | int], RoutineState]"
        else:
            return_type = "Tuple[Optional[str], RoutineState]"
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

            # Get label line number for offset calculation
            label_line = label.line_number

            # Spec 006 (T069a/T069b): Self-loop labels wrap body in while True:
            # Self-loop GOTOs become continue, QUIT becomes break
            if label.has_self_loop:
                ctx.emitter.line("while True:")
                with ctx.emitter.indented():
                    # Generate body statements
                    if label.body and label.body.statements:
                        # Spec 007: Use offset guards when routine has offset calls
                        if has_offsets and label_line is not None:
                            generate_offset_guarded_statements(
                                label.body.statements, label_line, ctx
                            )
                        else:
                            generate_scope_statements(label.body.statements, ctx)
                    else:
                        ctx.emitter.line("pass")
                    # Implicit break at end if no explicit exit (to prevent infinite loop)
                    if not label.has_explicit_exit:
                        ctx.emitter.line("break")
            else:
                # Generate body statements using scope-aware generator
                # This handles forward GOTO restructuring automatically
                if label.body and label.body.statements:
                    # Spec 007 (T021): Use offset guards when routine has offset calls
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
    "get_scope_strategy_pattern",
    "AnalysisNotCompleteError",
]
