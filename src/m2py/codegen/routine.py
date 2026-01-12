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
from m2py.codegen.names import NameTranslator, translate_name
from m2py.codegen.statements import generate_scope_statements

if TYPE_CHECKING:
    pass


@dataclass
class GeneratorContext:
    """Context passed through code generation.

    Carries state needed by expression and statement generators.
    Extended for Spec 005 with signatures and loop tracking.
    Extended for Spec 006 with strategy and state variable tracking.
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
        if self._strategy == GotoStrategy.TRAMPOLINE:
            state_vars = self._routine.routine_state_vars or set()
            array_vars = self._routine.array_vars or set()

        ctx = GeneratorContext(
            routine=self._routine,
            emitter=self._emitter,
            name_translator=self._name_translator,
            strategy=self._strategy,
            state_vars=state_vars,
            array_vars=array_vars,
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

        Args:
            ctx: Generator context
        """
        # Imports
        ctx.emitter.line("from itertools import chain, count")
        ctx.emitter.line("from m2py.codegen.helpers import m_num, m_truth, m_compare")
        ctx.emitter.line("from m2py.runtime import MUMPSRuntime")

        # Spec 006: Additional imports for trampoline pattern
        if self._strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("from dataclasses import dataclass, field")
            ctx.emitter.line("from typing import Any, Optional, Tuple")
            # Check if we have array variables
            array_vars = self._routine.array_vars or set()
            if array_vars:
                ctx.emitter.line("from m2py.runtime import MArray")

        ctx.emitter.blank()

        # Runtime instance
        ctx.emitter.line("_rt = MUMPSRuntime()")
        ctx.emitter.blank()

        # $TEST tracking
        ctx.emitter.line("_test = False")
        ctx.emitter.blank()

        # Spec 006: Generate RoutineState class for trampoline pattern
        if self._strategy == GotoStrategy.TRAMPOLINE:
            from m2py.codegen.shared_state import generate_routine_state_class

            state_class = generate_routine_state_class(self._routine)
            for line in state_class.strip().split("\n"):
                ctx.emitter.line(line)
            ctx.emitter.blank()

        # T066: Extrinsic function helper - saves/restores $TEST
        ctx.emitter.blank()
        ctx.emitter.line("def _call_extrinsic(_ef, *args):")
        with ctx.emitter.indented():
            ctx.emitter.line('"""Call extrinsic function with $TEST save/restore."""')
            ctx.emitter.line("global _test")
            ctx.emitter.line("_saved = _test")
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                ctx.emitter.line("return _ef(*args)")
            ctx.emitter.line("finally:")
            with ctx.emitter.indented():
                ctx.emitter.line("_test = _saved")
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

    def _generate_label(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate Python function from MUMPS label.

        Uses FunctionSignature to determine:
        - Formal parameters for function definition
        - Return pattern based on scope_strategy

        Spec 006 (T069a): Labels with has_self_loop=True wrap body in while True:
        - Self-loop GOTOs become continue
        - QUIT becomes break (implicit at end of body)
        - Other exits (cross-label GOTO) use return

        Args:
            label: MLabel ASG node
            ctx: Generator context

        Raises:
            UnsupportedFeatureError: For REQUIRES_RUNTIME scope strategy
        """
        from m2py.codegen import UnsupportedFeatureError

        ctx.current_label = label

        # Translate label name to valid Python identifier
        func_name = translate_name(label.name)

        # Get formal parameters from label or signature
        formal_params = []
        if label.formal_list:
            formal_params = [translate_name(p) for p in label.formal_list]
        elif label.signature and label.signature.formal_params:
            formal_params = [translate_name(p) for p in label.signature.formal_params]

        # Check for REQUIRES_RUNTIME strategy
        if (
            label.signature
            and label.signature.scope_strategy == ScopeStrategy.REQUIRES_RUNTIME
        ):
            raise UnsupportedFeatureError(
                f"Label '{label.name}' requires runtime scope (indirection/XECUTE). "
                "This is not supported in Spec 005. See Spec 006/007."
            )

        # Generate function definition with formal parameters
        params_str = ", ".join(formal_params)
        ctx.emitter.line(f"def {func_name}({params_str}):")

        with ctx.emitter.indented():
            # Declare global _test
            ctx.emitter.line("global _test")

            # Spec 006 (T069a): Check for self-loop pattern
            if label.has_self_loop:
                # Wrap body in while True: for self-loop pattern
                ctx.emitter.line("while True:")
                with ctx.emitter.indented():
                    if label.body and label.body.statements:
                        generate_scope_statements(label.body.statements, ctx)
                    else:
                        ctx.emitter.line("pass")
                    # If no explicit exit, add break to prevent infinite loop
                    # This handles fall-through at end of label
                    if not label.has_explicit_exit:
                        ctx.emitter.line("break")
            else:
                # Generate body statements using scope-aware generator
                # This handles forward GOTO restructuring automatically
                if label.body and label.body.statements:
                    generate_scope_statements(label.body.statements, ctx)
                else:
                    # Empty function needs pass
                    ctx.emitter.line("pass")

        ctx.emitter.blank()
        ctx.current_label = None

    def _generate_trampoline_code(self, ctx: GeneratorContext) -> None:
        """Generate trampoline pattern code for cross-label GOTOs.

        Spec 006 (T056): Generates:
        1. Label functions prefixed with _ (they return (next_label, state) tuples)
        2. _labels dict mapping label names to functions
        3. Entry point function with trampoline dispatcher (named after first label)

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

        # Generate trampoline dispatcher entry point
        # Named after the first label so it's the default entry point
        entry_label = self._routine.labels[0].name if self._routine.labels else None
        if entry_label:
            entry_func = translate_name(entry_label)
            ctx.emitter.line(f"def {entry_func}():")
            with ctx.emitter.indented():
                ctx.emitter.line('"""Trampoline dispatcher for routine execution."""')
                ctx.emitter.line("state = RoutineState()")
                ctx.emitter.line(f'label = "{entry_label}"')
                ctx.emitter.blank()
                ctx.emitter.line("while label is not None:")
                with ctx.emitter.indented():
                    ctx.emitter.line("func = _labels[label]")
                    ctx.emitter.line("label, state = func(state)")
                ctx.emitter.blank()
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
        from m2py.codegen import UnsupportedFeatureError

        ctx.current_label = label

        # Translate label name to valid Python identifier and prefix with _
        func_name = "_" + translate_name(label.name)

        # Get formal parameters from label or signature
        formal_params = []
        if label.formal_list:
            formal_params = [translate_name(p) for p in label.formal_list]
        elif label.signature and label.signature.formal_params:
            formal_params = [translate_name(p) for p in label.signature.formal_params]

        # Check for REQUIRES_RUNTIME strategy
        if (
            label.signature
            and label.signature.scope_strategy == ScopeStrategy.REQUIRES_RUNTIME
        ):
            raise UnsupportedFeatureError(
                f"Label '{label.name}' requires runtime scope (indirection/XECUTE). "
                "This is not supported in Spec 005. See Spec 006/007."
            )

        # Generate function definition with state parameter
        # For trampoline, all labels take state; formal params come later
        if formal_params:
            params_str = "state, " + ", ".join(formal_params)
        else:
            params_str = "state"

        # Return type annotation for trampoline labels
        ctx.emitter.line(
            f"def {func_name}({params_str}) -> Tuple[Optional[str], RoutineState]:"
        )

        with ctx.emitter.indented():
            # Declare global _test
            ctx.emitter.line("global _test")

            # Spec 006 (T069a/T069b): Self-loop labels wrap body in while True:
            # Self-loop GOTOs become continue, QUIT becomes break
            if label.has_self_loop:
                ctx.emitter.line("while True:")
                with ctx.emitter.indented():
                    # Generate body statements
                    if label.body and label.body.statements:
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
