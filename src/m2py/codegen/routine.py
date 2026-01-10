"""Routine code generation for MUMPS-to-Python transpilation.

Generates complete Python modules from MUMPS routines.
Handles module structure, imports, labels as functions, and $TEST tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from m2py.asg.elements import MLabel, MRoutine
from m2py.codegen.emitter import CodeEmitter
from m2py.codegen.names import NameTranslator, translate_name
from m2py.codegen.statements import generate_statement

if TYPE_CHECKING:
    pass


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


__all__ = ["RoutineGenerator", "GeneratorContext"]
