"""API Contracts for Spec 005 Code Generation.

These type signatures define the interfaces for structured control flow
code generation. All implementations must conform to these contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Protocol, List, Dict

if TYPE_CHECKING:
    from m2py.asg.elements import MLabel, MRoutine
    from m2py.asg.statements import (
        MForStatement,
        MGotoStatement,
        MQuitStatement,
        MDoStatement,
    )
    from m2py.analysis.variables import FunctionSignature
    from m2py.codegen.emitter import CodeEmitter


# =============================================================================
# Code Generation Context Contracts
# =============================================================================


@dataclass
class GeneratorContextContract:
    """Contract for generator context passed through code generation.

    Extended for Spec 005 to include function signatures and loop tracking.
    """

    routine: "MRoutine"
    emitter: "CodeEmitter"
    current_label: Optional["MLabel"] = None

    # Spec 005 additions
    signatures: Dict[str, "FunctionSignature"] = field(default_factory=dict)
    loop_stack: List["MForStatement"] = field(default_factory=list)


# =============================================================================
# FOR Loop Code Generation Contracts
# =============================================================================


class ForLoopGenerator(Protocol):
    """Protocol for FOR loop code generators."""

    def generate(
        self,
        stmt: "MForStatement",
        ctx: GeneratorContextContract,
    ) -> None:
        """Generate Python code for a FOR loop.

        Pre-conditions:
            - stmt.loop_type is set
            - stmt.loop_var_modified_in_body is set
            - stmt.has_internal_quit is set
            - stmt.has_internal_goto is set
            - ctx.emitter is valid

        Post-conditions:
            - Python code written to ctx.emitter
            - Generated code is syntactically valid
            - Loop semantics match MUMPS behavior

        Generated patterns by loop_type:
            - BOUNDED + not modified: for i in range(...)
            - BOUNDED + modified: while loop
            - OPEN_ENDED: itertools.count or while
            - ARGUMENTLESS: while True
            - STRING_LIST: for i in [...]
            - MIXED: chained iteration
        """
        ...


@dataclass
class ForGenResult:
    """Result contract for FOR loop generation."""

    pattern_used: str  # "for_range", "while_bounded", "while_true", etc.
    uses_break: bool
    uses_continue: bool
    loop_var_name: str


# =============================================================================
# GOTO Code Generation Contracts
# =============================================================================


class GotoGenerator(Protocol):
    """Protocol for GOTO code generators."""

    def generate(
        self,
        stmt: "MGotoStatement",
        ctx: GeneratorContextContract,
    ) -> None:
        """Generate Python code for a GOTO statement.

        Pre-conditions:
            - stmt.goto_type is set
            - stmt.is_cross_label is set
            - stmt.exits_loops is populated (if applicable)
            - ctx.loop_stack reflects current nesting

        Post-conditions:
            - Python code written to ctx.emitter
            - Generated code is syntactically valid
            - Control flow matches MUMPS behavior

        Supported patterns (Spec 005):
            - LOOP_EXIT + is_cross_label=False: generate `break`
            - MULTI_LOOP_EXIT: generate exception raise
            - FORWARD_JUMP + is_cross_label=False: if/else restructure

        Unsupported (raises UnsupportedFeatureError):
            - is_cross_label=True (except LOOP_EXIT)
            - BACKWARD_JUMP + is_cross_label=True
            - EXTERNAL
            - UNRESOLVED

        Note: GOTO cannot create Python `continue` semantics (MDC 3.6.5).
        GOTO terminates all FOR loops on the line containing the GOTO.
        For skip-iteration patterns, MUMPS uses conditional execution.
        """
        ...


@dataclass
class GotoGenResult:
    """Result contract for GOTO generation."""

    pattern_used: str  # "break", "exception", "restructure", "unsupported"
    target_label: Optional[str]
    loops_exited: int


# =============================================================================
# QUIT Code Generation Contracts
# =============================================================================


class QuitGenerator(Protocol):
    """Protocol for QUIT code generators."""

    def generate(
        self,
        stmt: "MQuitStatement",
        ctx: GeneratorContextContract,
    ) -> None:
        """Generate Python code for a QUIT statement.

        Pre-conditions:
            - stmt.exits_for is set
            - stmt.exits_do_block is set
            - stmt.return_value is set (if extrinsic)
            - ctx.current_label is set

        Post-conditions:
            - Python code written to ctx.emitter
            - Generated code is syntactically valid
            - Return semantics match MUMPS behavior

        Generated patterns:
            - exits_for=True: `break`
            - exits_do_block=True: `return`
            - return_value present: `return expr`
            - postcondition present: `if cond: break/return`
        """
        ...


# =============================================================================
# Function Signature Contracts
# =============================================================================


class LabelGenerator(Protocol):
    """Protocol for label-to-function code generators."""

    def generate(
        self,
        label: "MLabel",
        signature: "FunctionSignature",
        ctx: GeneratorContextContract,
    ) -> None:
        """Generate Python function from MUMPS label.

        Pre-conditions:
            - signature.scope_strategy is set
            - signature.formal_params is populated
            - signature.byref_outputs is populated
            - ctx.emitter is valid

        Post-conditions:
            - Python function definition written to ctx.emitter
            - Function signature includes formal parameters
            - Return pattern matches scope_strategy:
              - PURE_FUNCTION: return value
              - FUNCTION_WITH_OUTPUTS: return (value, *byref_outputs)
              - SUBROUTINE: implicit return None
              - REQUIRES_RUNTIME: raise UnsupportedFeatureError
        """
        ...


# =============================================================================
# Call Site Contracts
# =============================================================================


class DoCallGenerator(Protocol):
    """Protocol for DO call site code generators."""

    def generate(
        self,
        stmt: "MDoStatement",
        ctx: GeneratorContextContract,
    ) -> None:
        """Generate Python call from DO statement.

        Pre-conditions:
            - Target label signature in ctx.signatures
            - ctx.emitter is valid

        Post-conditions:
            - Python call written to ctx.emitter
            - If callee has byref_outputs, destructure return:
              `modified_var = callee(args)` or
              `ret, mod1, mod2 = callee(args)`
        """
        ...


class ExtrinsicCallGenerator(Protocol):
    """Protocol for extrinsic function call generators."""

    def generate_call(
        self,
        target_label: str,
        arguments: list,
        ctx: GeneratorContextContract,
    ) -> str:
        """Generate Python expression for extrinsic function call.

        Pre-conditions:
            - Target label signature in ctx.signatures

        Post-conditions:
            - Returns Python expression string
            - $TEST save/restore wrapped around call:
              `(_saved := _test, _test := _saved, result)[2]`
              or separate statements in statement context
        """
        ...


# =============================================================================
# Validation Contracts
# =============================================================================


def validate_for_analysis_complete(stmt: "MForStatement") -> List[str]:
    """Validate FOR statement has all required analysis data.

    Returns list of missing fields.
    """
    errors = []
    if not hasattr(stmt, "loop_type") or stmt.loop_type is None:
        errors.append("loop_type not set")
    if not hasattr(stmt, "loop_var_modified_in_body"):
        errors.append("loop_var_modified_in_body not set")
    if not hasattr(stmt, "has_internal_quit"):
        errors.append("has_internal_quit not set")
    return errors


def validate_goto_analysis_complete(stmt: "MGotoStatement") -> List[str]:
    """Validate GOTO statement has all required analysis data.

    Returns list of missing fields.

    Note: is_loop_continue is NOT validated - GOTO cannot create continue
    semantics per MDC 3.6.5 (GOTO terminates all FOR loops on the line).
    """
    errors = []
    if not hasattr(stmt, "goto_type") or stmt.goto_type is None:
        errors.append("goto_type not set")
    if not hasattr(stmt, "is_cross_label"):
        errors.append("is_cross_label not set")
    return errors


def validate_signature_complete(sig: "FunctionSignature") -> List[str]:
    """Validate function signature has all required data.

    Returns list of missing fields.
    """
    errors = []
    if sig.scope_strategy is None:
        errors.append("scope_strategy not set")
    if sig.formal_params is None:
        errors.append("formal_params not set")
    if sig.byref_outputs is None:
        errors.append("byref_outputs not set")
    return errors


# =============================================================================
# Output Validation
# =============================================================================


def validate_generated_python(code: str) -> tuple[bool, Optional[str]]:
    """Validate generated Python code is syntactically correct.

    Returns (is_valid, error_message).
    """
    import ast

    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)
