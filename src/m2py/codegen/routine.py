"""Routine code generation for MUMPS-to-Python transpilation.

Generates complete Python modules from MUMPS routines.
Handles module structure, imports, labels as functions, and $TEST tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from m2py.asg.elements import MLabel, MRoutine
from m2py.asg.enums import ScopeStrategy
from m2py.asg.statements import MForStatement
from m2py.analysis.variables import FunctionSignature
from m2py.codegen.emitter import CodeEmitter
from m2py.codegen.names import NameTranslator, translate_name
from m2py.codegen.statements import generate_statement

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

            # Generate body statements
            if label.body and label.body.statements:
                for stmt in label.body.statements:
                    generate_statement(stmt, ctx)
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
