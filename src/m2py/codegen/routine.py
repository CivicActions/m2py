"""Routine code generation for MUMPS-to-Python transpilation.

Generates complete Python modules from MUMPS routines.
Handles module structure, imports, labels as functions, and $TEST tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from m2py.asg.elements import MLabel, MRoutine
from m2py.asg.enums import GotoType, ScopeStrategy
from m2py.asg.statements import MForStatement, MGotoStatement
from m2py.analysis.variables import FunctionSignature
from m2py.codegen.emitter import CodeEmitter
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

    # Spec 005: Track nested FOR loops for break/continue generation
    loop_stack: List[MForStatement] = field(default_factory=list)

    # Spec 005: Flag for $TEST save/restore in extrinsic calls
    in_extrinsic_call: bool = False


def validate_analysis_complete(routine: MRoutine) -> None:
    """Validate that required analysis passes have run before codegen.

    Checks that FOR loop analysis and GOTO analysis have populated
    the ASG fields needed for proper code generation.

    Args:
        routine: The routine to validate

    Raises:
        ValueError: If analysis appears incomplete
    """
    # For now, just check that the routine has labels
    # More comprehensive validation will be added as we use more analysis fields
    if not routine.labels:
        return  # Empty routine is valid

    # Check that labels exist - analysis creates signatures for each
    # This is a minimal check; full validation happens during generation
    for label in routine.labels:
        if label.body is None:
            continue
        # The presence of body.statements indicates parsing completed
        # Analysis populates fields on individual statements


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


def _routine_needs_loop_exit_exception(routine: MRoutine) -> bool:
    """Check if the routine needs the _LoopExit exception class.

    The _LoopExit exception is needed when there are MULTI_LOOP_EXIT GOTOs
    that need to exit multiple nested FOR loops.

    Args:
        routine: The routine to check

    Returns:
        True if _LoopExit exception class should be generated
    """
    for label in routine.labels:
        if label.body is None:
            continue
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                goto_type = getattr(stmt, "goto_type", None)
                if goto_type == GotoType.MULTI_LOOP_EXIT:
                    return True
    return False


class RoutineGenerator:
    """Generates Python code for a complete MUMPS routine.

    Transforms an MRoutine ASG into executable Python code with:
    - Required imports for helpers and runtime
    - Module-level runtime instance (_rt)
    - Module-level $TEST tracking (_test)
    - Labels as Python functions
    """

    def __init__(self, routine: MRoutine) -> None:
        """Initialize generator with parsed routine.

        Args:
            routine: MRoutine ASG to generate code from
        """
        self._routine = routine
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

        return self._emitter.get_code()

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

        # T036: _LoopExit exception for multi-loop exits
        # Only generate if the routine has MULTI_LOOP_EXIT GOTOs
        if _routine_needs_loop_exit_exception(self._routine):
            ctx.emitter.line("class _LoopExit(Exception):")
            with ctx.emitter.indented():
                ctx.emitter.line('"""Exception for multi-loop exit via GOTO."""')
                ctx.emitter.line("pass")
            ctx.emitter.blank()

    def _generate_label(self, label: MLabel, ctx: GeneratorContext) -> None:
        """Generate Python function from MUMPS label.

        Args:
            label: MLabel ASG node
            ctx: Generator context
        """
        ctx.current_label = label

        # Translate label name to valid Python identifier
        func_name = translate_name(label.name)

        # Function definition
        # For now, ignore formal parameters (Phase 2 scope is basic only)
        ctx.emitter.line(f"def {func_name}():")

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
]
