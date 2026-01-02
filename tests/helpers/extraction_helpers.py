"""Test helpers for command extraction.

These utilities wrap production parsing functions to provide convenient
test interfaces for extracting command information from line content.

For production code, use:
- parse_commands_from_line() + filter by class name
- extract_for_commands() + classify_for_command()
- analyze_command() for full ASG nodes
"""

from typing import Optional

from m2py.parser.line_parser import (
    parse_commands_from_line,
    extract_for_commands,
    classify_for_command,
)


def has_for_command(line_content: str) -> bool:
    """Check if line contains a FOR command.

    Args:
        line_content: The line content string

    Returns:
        True if FOR command found, False otherwise
    """
    for_cmds = extract_for_commands(line_content)
    return len(for_cmds) > 0


def get_for_info(line_content: str) -> Optional[tuple]:
    """Get FOR command info from a line (for testing).

    Args:
        line_content: The line content string

    Returns:
        Tuple of (ForLoopType, loop_var_name) or None if no FOR found
    """
    for_cmds = extract_for_commands(line_content)
    if not for_cmds:
        return None

    for_cmd = for_cmds[0]
    loop_type, loop_var = classify_for_command(for_cmd)

    # Get variable name as string
    var_name = ""
    if loop_var:
        if hasattr(loop_var, "name"):
            var_name = loop_var.name
        else:
            var_name = str(loop_var)

    return (loop_type, var_name)


def has_goto_command(line_content: str) -> bool:
    """Check if line contains a GOTO command.

    Args:
        line_content: The line content string

    Returns:
        True if GOTO command found, False otherwise
    """
    from m2py.asg.elements import MParseError

    cmds = parse_commands_from_line(line_content)
    if isinstance(cmds, MParseError):
        return False
    return any(cmd.__class__.__name__ == "GotoCommand" for cmd in cmds)


def get_goto_info(line_content: str) -> Optional[tuple]:
    """Get GOTO command info from a line (for testing).

    Args:
        line_content: The line content string

    Returns:
        Tuple of (label, routine, offset) or None if no GOTO found
    """
    from m2py.asg.elements import MParseError

    cmds = parse_commands_from_line(line_content)
    if isinstance(cmds, MParseError):
        return None

    for cmd in cmds:
        if cmd.__class__.__name__ == "GotoCommand":
            if cmd.targets:
                target = cmd.targets[0]
                label_ref = target.label
                label = label_ref.label if label_ref else None
                routine = (
                    label_ref.routine
                    if label_ref and hasattr(label_ref, "routine")
                    else None
                )
                offset = None
                if label_ref and hasattr(label_ref, "offset") and label_ref.offset:
                    offset = _expr_to_string(label_ref.offset)
                return (label, routine, offset)

    return None


def has_do_command(line_content: str) -> bool:
    """Check if line contains a DO command.

    Args:
        line_content: The line content string

    Returns:
        True if DO command found, False otherwise
    """
    from m2py.asg.elements import MParseError

    cmds = parse_commands_from_line(line_content)
    if isinstance(cmds, MParseError):
        return False
    return any(cmd.__class__.__name__ == "DoCommand" for cmd in cmds)


def get_do_info(line_content: str) -> Optional[tuple]:
    """Get DO command info from a line (for testing).

    Args:
        line_content: The line content string

    Returns:
        Tuple of (do_content, target_label) or None if no DO found
    """
    from m2py.asg.elements import MParseError

    cmds = parse_commands_from_line(line_content)
    if isinstance(cmds, MParseError):
        return None

    for cmd in cmds:
        if cmd.__class__.__name__ == "DoCommand":
            if not cmd.targets:
                return ("", None)

            target = cmd.targets[0]
            label_ref = target.label
            label = label_ref.label if label_ref else None
            routine = (
                label_ref.routine
                if label_ref and hasattr(label_ref, "routine")
                else None
            )

            do_content = ""
            if label:
                do_content = label
                if hasattr(label_ref, "offset") and label_ref.offset:
                    do_content += f"+{_expr_to_string(label_ref.offset)}"
                if routine:
                    do_content += f"^{routine}"
            elif routine:
                do_content = f"^{routine}"

            return (do_content, label)

    return None


# =============================================================================
# Expression to String Conversion (for test helpers only)
# =============================================================================


def _format_subscripts(subscripts) -> str:
    """Format subscripts for variable or function arguments."""
    if hasattr(subscripts, "args"):
        return ",".join(_expr_to_string(s) for s in subscripts.args)
    return ",".join(_expr_to_string(s) for s in subscripts)


def _expr_to_string(expr) -> str:
    """Convert a textX expression model to a string representation.

    Args:
        expr: The textX expression model

    Returns:
        String representation of the expression
    """
    if expr is None:
        return ""

    cls_name = expr.__class__.__name__

    if cls_name == "NumericLiteral":
        return str(expr.value)
    elif cls_name == "StringLiteral":
        val = expr.value
        if isinstance(val, str) and not (val.startswith('"') and val.endswith('"')):
            return f'"{val}"'
        return str(val)
    elif cls_name == "LocalVariable":
        name = expr.name
        if expr.subscripts:
            subs = _format_subscripts(expr.subscripts)
            return f"{name}({subs})"
        return name
    elif cls_name == "GlobalVariable":
        name = f"^{expr.name}"
        if expr.subscripts:
            subs = _format_subscripts(expr.subscripts)
            return f"{name}({subs})"
        return name
    elif cls_name == "IntrinsicFunction":
        name = f"${expr.name}"
        if expr.arguments:
            args = ",".join(_expr_to_string(a) for a in expr.arguments)
            return f"{name}({args})"
        return name
    elif cls_name == "SpecialVariable":
        return f"${expr.name}"
    elif cls_name in ("ParenExpr", "OffsetParenExpr"):
        return f"({_expr_to_string(expr.expr)})"
    elif cls_name in ("UnaryExpr", "OffsetUnaryExpr"):
        ops_str = ""
        if hasattr(expr, "operators") and expr.operators:
            for op_obj in expr.operators:
                ops_str += op_obj.op if hasattr(op_obj, "op") else str(op_obj)
        elif hasattr(expr, "operator") and expr.operator:
            ops_str = (
                expr.operator.op if hasattr(expr.operator, "op") else str(expr.operator)
            )
        return f"{ops_str}{_expr_to_string(expr.operand)}"
    elif cls_name in ("Expr", "OffsetExpr"):
        if not (hasattr(expr, "left") and expr.left):
            return str(expr)
        result = _expr_to_string(expr.left)
        if hasattr(expr, "tail") and expr.tail:
            for tail_item in expr.tail:
                if hasattr(tail_item, "right") and tail_item.right:
                    op = tail_item.op
                    op_str = op.op if hasattr(op, "op") else str(op)
                    result += op_str
                    result += _expr_to_string(tail_item.right)
        return result

    return str(expr)
