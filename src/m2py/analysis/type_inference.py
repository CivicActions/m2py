"""Expression-level type inference for the MUMPS ASG.

Performs a single bottom-up pass over all expressions in a routine,
populating MExpr.result_type with the inferred ExprResultType. This
information is used by codegen to emit Python type annotations.

Pipeline position: After compute_signatures (step 6), as step 7.

Key design decisions:
- No recursive fixpoint: MUMPS operator output types depend only on the
  operator, not operand types. A single bottom-up pass suffices.
- Variables are UNKNOWN: MUMPS variables can be retyped across assignments.
- $SELECT is UNKNOWN: Heterogeneous return values.
- MFormatControl/MDeviceControl are skipped (not value expressions).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from m2py.asg.enums import ExprResultType, LiteralType
from m2py.asg.expressions import (
    MActualParameter,
    MBinaryOp,
    MDeviceControl,
    MExternalFunction,
    MExtrinsicFunction,
    MExpr,
    MFormatControl,
    MGlobal,
    MIndirection,
    MIntrinsicFunction,
    MLiteral,
    MNakedGlobal,
    MPatternMatch,
    MSelectArg,
    MSpecialVariable,
    MStructuredSystemVariable,
    MUnaryOp,
    MVariable,
)

if TYPE_CHECKING:
    from m2py.asg.elements import MRoutine

# ── Operator → ResultType mappings ──────────────────────────────────────

_ARITHMETIC_OPS = frozenset({"+", "-", "*", "/", "\\", "#", "**"})
_COMPARISON_OPS = frozenset({"=", "<", ">", "'=", "'<", "'>", "[", "]", "]]"})
_LOGICAL_OPS = frozenset({"&", "!"})

# ── Intrinsic function → ResultType mappings ────────────────────────────

_NUMERIC_FUNCTIONS = frozenset(
    {
        "LENGTH",
        "ASCII",
        "FIND",
        "RANDOM",
        "DATA",
        "QLENGTH",
        "INCREMENT",
        "L",
        "A",
        "F",
        "R",
        "D",
        "QL",  # abbreviated forms
    }
)
_STRING_FUNCTIONS = frozenset(
    {
        "PIECE",
        "EXTRACT",
        "CHAR",
        "TRANSLATE",
        "REVERSE",
        "TEXT",
        "NAME",
        "QUERY",
        "QSUBSCRIPT",
        "ZDATE",
        "P",
        "E",
        "C",
        "TR",
        "RE",
        "T",
        "NA",
        "Q",
        "QS",
        "ZD",  # abbreviated
    }
)
_NUMERIC_STRING_FUNCTIONS = frozenset(
    {
        "JUSTIFY",
        "FNUMBER",
        "J",
        "FN",  # abbreviated
    }
)
_UNKNOWN_FUNCTIONS = frozenset(
    {
        "GET",
        "SELECT",
        "ORDER",
        "G",
        "S",
        "O",  # abbreviated
    }
)

# ── Special variable → ResultType mappings ──────────────────────────────

_BOOLEAN_SVARS = frozenset({"TEST", "TLEVEL", "T", "TL"})
_STRING_SVARS = frozenset(
    {
        "HOROLOG",
        "JOB",
        "IO",
        "STORAGE",
        "SYSTEM",
        "PRINCIPAL",
        "PRINCIPLE",
        "DEVICE",
        "KEY",
        "NAMESPACE",
        "H",
        "J",
        "I",
        "S",
        "P",
        "D",
        "K",  # abbreviated
        # YDB extensions
        "ZSTATUS",
        "ZPOSITION",
        "ZRO",
        "ZJOB",
        "ZS",
        "ZP",
    }
)


def _infer_expr(node: MExpr) -> ExprResultType:
    """Infer the result type of a single expression node.

    Assumes children have already been processed (bottom-up).
    """
    # ── Literals ─────────────────────────────────────────────────────
    if isinstance(node, MLiteral):
        if node.literal_type == LiteralType.STRING:
            return ExprResultType.STRING
        return ExprResultType.NUMERIC  # INTEGER or DECIMAL

    # ── Variables (always UNKNOWN — can be retyped) ──────────────────
    if isinstance(node, (MVariable, MGlobal, MNakedGlobal)):
        return ExprResultType.UNKNOWN

    # ── Binary operators ─────────────────────────────────────────────
    if isinstance(node, MBinaryOp):
        op = node.operator
        if op == "_":
            return ExprResultType.STRING
        if op in _ARITHMETIC_OPS:
            return ExprResultType.NUMERIC
        if op in _COMPARISON_OPS:
            return ExprResultType.BOOLEAN_INT
        if op in _LOGICAL_OPS:
            return ExprResultType.BOOLEAN_INT
        return ExprResultType.UNKNOWN

    # ── Unary operators ──────────────────────────────────────────────
    if isinstance(node, MUnaryOp):
        op = node.operator
        if op == "'":
            return ExprResultType.BOOLEAN_INT
        if op in {"+", "-"}:
            return ExprResultType.NUMERIC
        return ExprResultType.UNKNOWN

    # ── Pattern match ────────────────────────────────────────────────
    if isinstance(node, MPatternMatch):
        return ExprResultType.BOOLEAN_INT

    # ── Intrinsic functions ──────────────────────────────────────────
    if isinstance(node, MIntrinsicFunction):
        name = node.name.upper()
        if name in _NUMERIC_FUNCTIONS:
            return ExprResultType.NUMERIC
        if name in _STRING_FUNCTIONS:
            return ExprResultType.STRING
        if name in _NUMERIC_STRING_FUNCTIONS:
            return ExprResultType.NUMERIC_STRING
        if name in _UNKNOWN_FUNCTIONS:
            return ExprResultType.UNKNOWN
        # $STACK: polymorphic — 1-arg → NUMERIC, 2-arg → STRING
        if name in {"STACK", "ST"}:
            if len(node.arguments) >= 2:
                return ExprResultType.STRING
            return ExprResultType.NUMERIC
        return ExprResultType.UNKNOWN

    # ── Extrinsic / External functions ───────────────────────────────
    if isinstance(node, (MExtrinsicFunction, MExternalFunction)):
        return ExprResultType.UNKNOWN

    # ── Indirection ──────────────────────────────────────────────────
    if isinstance(node, MIndirection):
        return ExprResultType.UNKNOWN

    # ── Special variables ────────────────────────────────────────────
    if isinstance(node, MSpecialVariable):
        name = node.name.upper()
        if name in _BOOLEAN_SVARS:
            return ExprResultType.BOOLEAN_INT
        if name in _STRING_SVARS:
            return ExprResultType.STRING
        return ExprResultType.UNKNOWN

    # ── Structured system variables ──────────────────────────────────
    if isinstance(node, MStructuredSystemVariable):
        return ExprResultType.UNKNOWN

    # ── Non-value expressions (skip) ─────────────────────────────────
    if isinstance(node, (MFormatControl, MDeviceControl)):
        return ExprResultType.UNKNOWN  # Will not be set on these

    return ExprResultType.UNKNOWN


def _walk_and_infer(node: object) -> None:
    """Recursively walk an expression tree bottom-up, setting result_type.

    For MExpr nodes: recurse into children first, then infer own type.
    For non-MExpr containers: recurse into expression-bearing fields.
    """
    if node is None:
        return

    if isinstance(node, MExpr):
        # ── Recurse into children first (bottom-up) ──────────────────
        if isinstance(node, MBinaryOp):
            _walk_and_infer(node.left)
            _walk_and_infer(node.right)
        elif isinstance(node, MUnaryOp):
            _walk_and_infer(node.operand)
        elif isinstance(node, MPatternMatch):
            _walk_and_infer(node.subject)
            _walk_and_infer(node.pattern_indirect)
        elif isinstance(node, MIntrinsicFunction):
            for arg in node.arguments:
                _walk_and_infer(arg)
        elif isinstance(node, MExtrinsicFunction):
            for arg in node.arguments:
                _walk_and_infer(arg)
        elif isinstance(node, MExternalFunction):
            for arg in node.arguments:
                _walk_and_infer(arg)
        elif isinstance(node, MIndirection):
            _walk_and_infer(node.expression)
            if node.subscripts:
                for sub in node.subscripts:
                    _walk_and_infer(sub)
            if node.name_indirection_subscripts:
                for sub_list in node.name_indirection_subscripts:
                    for sub in sub_list:
                        _walk_and_infer(sub)
        elif isinstance(node, (MVariable, MGlobal, MNakedGlobal)):
            for sub in node.subscripts:
                _walk_and_infer(sub)
            if isinstance(node, MGlobal) and node.environment:
                _walk_and_infer(node.environment)
        elif isinstance(node, MStructuredSystemVariable):
            for sub in node.subscripts:
                _walk_and_infer(sub)

        # Skip MFormatControl/MDeviceControl — not value expressions
        if isinstance(node, (MFormatControl, MDeviceControl)):
            # Leave result_type as None for non-value expressions
            return

        # ── Infer type for this node ─────────────────────────────────
        node.result_type = _infer_expr(node)

    elif isinstance(node, MActualParameter):
        # Delegate to wrapped expression
        _walk_and_infer(node.expression)

    elif isinstance(node, MSelectArg):
        _walk_and_infer(node.condition)
        _walk_and_infer(node.value)

    elif isinstance(node, list):
        for item in node:
            _walk_and_infer(item)


def _walk_statement_exprs(stmt: object) -> None:
    """Walk all expression-bearing fields of a statement."""
    if stmt is None:
        return

    # Use the same attribute-scanning approach as variables.walk_expressions
    # for broad statement coverage.
    from m2py.asg.statements import MSetStatement, MForStatement

    # Handle postcondition (common to all statements)
    if hasattr(stmt, "postcondition") and getattr(stmt, "postcondition") is not None:
        _walk_and_infer(getattr(stmt, "postcondition"))

    # SET statement — assignments with target/value
    if isinstance(stmt, MSetStatement):
        for assign in stmt.assignments:
            _walk_and_infer(assign.target)
            _walk_and_infer(assign.value)
        return

    # FOR statement — loop var and parameters
    if isinstance(stmt, MForStatement):
        if isinstance(stmt.loop_var, MExpr):
            _walk_and_infer(stmt.loop_var)
        if stmt.parameters:
            for param in stmt.parameters:
                _walk_and_infer(param.value)
                _walk_and_infer(param.start)
                _walk_and_infer(param.end)
                _walk_and_infer(param.step)
        return

    # Generic expression-bearing attributes
    _EXPR_ATTRS = (
        "conditions",
        "condition",
        "value",
        "expression",
        "return_value",
        "arguments",
        "timeout",
        "parameters",
        "expressions",
        "device_expr",
        "format_expr",
        "code",
        "targets",
        "durations",
        "merges",
        "args",
        "exitcode",
        "action",
        "level",
        "restart_vars",
        "devices",
    )
    for attr in _EXPR_ATTRS:
        val = getattr(stmt, attr, None)
        if val is not None:
            _walk_and_infer(val)

    # Handle assignments if present (for non-MSetStatement that might have them)
    assignments = getattr(stmt, "assignments", None)
    if assignments:
        for assign in assignments:
            _walk_and_infer(getattr(assign, "target", None))
            _walk_and_infer(getattr(assign, "value", None))

    # Handle loop_var if present (for non-MForStatement that might have it)
    loop_var = getattr(stmt, "loop_var", None)
    if loop_var is not None and isinstance(loop_var, MExpr):
        _walk_and_infer(loop_var)


def infer_expression_types(routine: "MRoutine") -> None:
    """Walk all MExpr nodes in the routine and populate result_type.

    This is the public API for the type inference pass. It should be called
    after all prior analysis passes (resolution, scoping, signatures) and
    before code generation.

    Preconditions:
        - All prior analysis passes have completed
        - MExpr.result_type is None for all nodes

    Postconditions:
        - Every MExpr subclass representing a value expression has
          result_type set to a non-None ExprResultType
        - MFormatControl and MDeviceControl retain result_type = None
        - MActualParameter delegates to its wrapped expression

    Side effects:
        Mutates result_type field on MExpr nodes. No other ASG modifications.

    Error handling:
        Never raises. Unknown or unrecognized expressions get UNKNOWN.
    """
    for label in routine.labels:
        if label.body is None:
            continue
        for stmt in label.body.walk_statements():
            _walk_statement_exprs(stmt)
