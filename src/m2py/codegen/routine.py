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

        Returns:
            Python source code as string
        """
        ctx = GeneratorContext(
            routine=self._routine,
            emitter=self._emitter,
            name_translator=self._name_translator,
        )

        # Generate module preamble
        self._generate_preamble(ctx)

        # Generate each label as a function
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

        Args:
            ctx: Generator context
        """
        # Imports
        ctx.emitter.line("from itertools import chain, count")
        ctx.emitter.line("from m2py.codegen.helpers import m_num, m_truth, m_compare")
        ctx.emitter.line("from m2py.runtime import MUMPSRuntime")
        ctx.emitter.blank()

        # Runtime instance
        ctx.emitter.line("_rt = MUMPSRuntime()")
        ctx.emitter.blank()

        # $TEST tracking
        ctx.emitter.line("_test = False")
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

            # Generate body statements using scope-aware generator
            # This handles forward GOTO restructuring automatically
            if label.body and label.body.statements:
                generate_scope_statements(label.body.statements, ctx)
            else:
                # Empty function needs pass
                ctx.emitter.line("pass")

        ctx.emitter.blank()
        ctx.current_label = None


__all__ = [
    "RoutineGenerator",
    "GeneratorContext",
    "validate_analysis_complete",
    "get_scope_strategy_pattern",
    "AnalysisNotCompleteError",
]
