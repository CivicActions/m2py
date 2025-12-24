"""Command parsing using textX grammar.

Provides functions to parse MUMPS commands into ASG nodes using
the textX command grammar.

This module provides the primary parsing interface for MUMPS commands,
converting textX parsed models into the M2PY ASG representation.
"""

from pathlib import Path
from typing import Optional, Any, List
from functools import lru_cache

from textx import metamodel_from_file
from textx.exceptions import TextXSyntaxError

from ..asg.enums import ForLoopType, ForParamType, LiteralType
from ..asg.statements import (
    MForStatement,
    MForParameter,
    MSetStatement,
    MAssignment,
    MWriteStatement,
    MQuitStatement,
    MIfStatement,
    MNewStatement,
    MDoStatement,
    MGotoStatement,
)
from ..asg.expressions import MLiteral, MVariable, MGlobal
from ..asg.elements import MCall


@lru_cache(maxsize=1)
def _get_command_metamodel():
    """Get the cached command grammar metamodel with custom classes."""
    from ..parser.textx_classes import get_expression_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_expression_classes(), skipws=False
    )


@lru_cache(maxsize=1)
def _get_line_metamodel():
    """Get the cached line content grammar metamodel with custom classes."""
    from ..parser.textx_classes import get_expression_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "line.tx", classes=get_expression_classes(), skipws=False
    )


@lru_cache(maxsize=1)
def _get_expression_metamodel():
    """Get the cached expression grammar metamodel with custom classes."""
    from ..parser.textx_classes import get_expression_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "expressions.tx", classes=get_expression_classes(), skipws=False
    )


def parse_line_content(line_content: str) -> Optional[Any]:
    """Parse a MUMPS line content string into a textX model.

    This parses the content after a label or continuation prefix,
    which consists of commands separated by spaces and optionally
    ending with a comment.

    Args:
        line_content: The line content (e.g., "S X=1 W X  ;comment")

    Returns:
        The parsed textX LineContent model or None if parsing fails
    """
    mm = _get_line_metamodel()
    try:
        return mm.model_from_str(line_content)
    except TextXSyntaxError:
        return None


def parse_commands_from_line(line_content: str) -> List[Any]:
    """Parse a line content string and return list of command models.

    Args:
        line_content: The line content string

    Returns:
        List of textX command models (empty if parsing fails)
    """
    model = parse_line_content(line_content)
    if model and model.commands:
        return [lc.cmd for lc in model.commands]
    return []


def get_line_comment(line_content: str) -> Optional[str]:
    """Extract comment from a line content string.

    Args:
        line_content: The line content string

    Returns:
        The comment text (without ';') or None if no comment
    """
    model = parse_line_content(line_content)
    if model and model.comment:
        return model.comment.text
    return None


def detect_quit_after_for(line_content: str) -> bool:
    """Detect if there's a QUIT command after any FOR command on this line.

    In MUMPS, FOR body extends to end of line. If QUIT appears after FOR
    on the same line, it's an exit point for the FOR loop.

    Args:
        line_content: The line content string

    Returns:
        True if QUIT found after FOR, False otherwise
    """
    commands = parse_commands_from_line(line_content)
    if not commands:
        return False

    found_for = False
    for cmd in commands:
        cls_name = cmd.__class__.__name__
        if cls_name == "ForCommand":
            found_for = True
        elif found_for and cls_name == "QuitCommand":
            return True

    return False


def extract_for_commands(line_content: str) -> List[Any]:
    """Extract all FOR commands from a line content string.

    Uses textX grammar to properly parse and identify FOR commands,
    avoiding false positives from string literals or other contexts.

    Args:
        line_content: The line content string

    Returns:
        List of ForCommand textX models found in the line
    """
    cmds = parse_commands_from_line(line_content)
    return [cmd for cmd in cmds if cmd.__class__.__name__ == "ForCommand"]


def classify_for_from_textx(for_cmd) -> tuple:
    """Classify a textX ForCommand into loop type and variable.

    Args:
        for_cmd: A textX ForCommand model

    Returns:
        Tuple of (ForLoopType, loop_var) where loop_var is a string (simple var)
        or LocalVariable (subscripted var) or ""
    """
    from ..asg.enums import ForLoopType, ForParamType

    # Argumentless FOR: no var or params
    if not for_cmd.var or not for_cmd.params:
        return ForLoopType.ARGUMENTLESS, ""

    # For simple variables, return the string name; for subscripted, return the object
    if for_cmd.var.subscripts:
        loop_var = for_cmd.var
    else:
        loop_var = for_cmd.var.name

    # Analyze parameters to determine loop type
    param_types = []
    for param in for_cmd.params:
        if param.step:
            if param.end:
                param_types.append(ForParamType.RANGE)
            else:
                param_types.append(ForParamType.OPEN_RANGE)
        else:
            param_types.append(ForParamType.VALUE)

    # Determine overall loop type
    if not param_types:
        return ForLoopType.ARGUMENTLESS, loop_var

    unique_types = set(param_types)

    if len(for_cmd.params) > 1 and len(unique_types) > 1:
        return ForLoopType.MIXED, loop_var

    if ForParamType.RANGE in unique_types:
        return ForLoopType.BOUNDED, loop_var
    elif ForParamType.OPEN_RANGE in unique_types:
        return ForLoopType.OPEN_ENDED, loop_var
    else:
        return ForLoopType.STRING_LIST, loop_var


def _convert_subscripts_to_asg(subscripts: List[Any]) -> List[Any]:
    """Convert a list of subscript expressions to proper ASG nodes.

    Subscripts may contain raw textX Expr wrapper nodes when they have
    complex expressions (e.g., A+B, $A(X)). This function converts them
    to proper ASG expression nodes.

    Args:
        subscripts: List of expression objects (may be textX or ASG nodes)

    Returns:
        List of ASG expression nodes
    """
    from .semantic_analyzer import analyze_expression
    from ..asg.expressions import MExpr

    result = []
    for sub in subscripts:
        if sub is None:
            continue
        # Already an ASG expression - keep it
        if isinstance(sub, MExpr):
            result.append(sub)
        # textX wrapper - need to convert
        elif hasattr(sub, "__class__") and "textx" in sub.__class__.__module__.lower():
            result.append(analyze_expression(sub))
        # Has 'left' attribute (Expr wrapper from textX)
        elif hasattr(sub, "left"):
            result.append(analyze_expression(sub))
        # Has 'operand' attribute (UnaryExpr wrapper from textX)
        elif hasattr(sub, "operand"):
            result.append(analyze_expression(sub))
        else:
            result.append(sub)
    return result


def _convert_loop_var_to_asg(loop_var: Any) -> Any:
    """Convert a loop variable to proper ASG form with converted subscripts.

    For simple variables (string name), returns the name unchanged.
    For subscripted variables, returns a copy with subscripts converted to ASG.

    Args:
        loop_var: Either a string name or a LocalVariable/GlobalVariable

    Returns:
        String name or variable with ASG subscripts
    """
    from ..asg.expressions import MVariable, MGlobal

    # Simple string name - return as-is
    if isinstance(loop_var, str):
        return loop_var

    # Variable with subscripts - convert subscripts
    if hasattr(loop_var, "subscripts") and loop_var.subscripts:
        converted_subscripts = _convert_subscripts_to_asg(loop_var.subscripts)

        # Create a new variable with converted subscripts
        if isinstance(loop_var, MGlobal):
            new_var = MGlobal()
            new_var.name = loop_var.name
            new_var.subscripts = converted_subscripts
            return new_var
        else:
            new_var = MVariable()
            new_var.name = loop_var.name
            new_var.subscripts = converted_subscripts
            return new_var

    # No subscripts - return as-is
    return loop_var


def _build_for_parameters(params: list) -> list:
    """Build MForParameter list from parsed FOR command parameters.

    This is a shared helper for parse_for_command() and parse_for_command_to_asg().

    Args:
        params: List of textX ForParam models

    Returns:
        List of MForParameter ASG nodes
    """
    parameters = []

    for param in params:
        fp = MForParameter()

        if param.start:
            fp.start = _expr_to_asg_literal(_expr_to_string(param.start))

        if param.step:
            fp.step = _expr_to_asg_literal(_expr_to_string(param.step))
            if param.end:
                fp.end = _expr_to_asg_literal(_expr_to_string(param.end))
                fp.param_type = ForParamType.RANGE
            else:
                fp.param_type = ForParamType.OPEN_RANGE
        else:
            fp.param_type = ForParamType.VALUE
            # For VALUE type, the start IS the value
            if param.start:
                fp.value = fp.start

        parameters.append(fp)

    return parameters


def _extract_loop_var(for_var) -> Any:
    """Extract loop variable from parsed FOR command.

    For simple variables, returns the string name.
    For subscripted variables, returns the full ASG object.

    Args:
        for_var: A textX LocalVariable model (or None)

    Returns:
        String name, subscripted variable object, or None
    """
    if not for_var:
        return None

    # For simple variables, use the string name for backwards compatibility
    # For subscripted variables, convert to proper ASG with clean subscripts
    if for_var.subscripts:
        return _convert_loop_var_to_asg(for_var)
    else:
        return for_var.name


def parse_for_command_to_asg(for_cmd) -> MForStatement:
    """Convert a textX ForCommand model to an MForStatement ASG node.

    Args:
        for_cmd: A textX ForCommand model (from extract_for_commands)

    Returns:
        MForStatement ASG node with parameters populated
    """
    statement = MForStatement()

    # Extract loop variable using shared helper
    statement.loop_var = _extract_loop_var(for_cmd.var)

    # Build parameters using shared helper
    if for_cmd.params:
        statement.parameters = _build_for_parameters(for_cmd.params)

    # Classify the loop type
    statement.loop_type = _classify_for_params(statement.parameters)

    # Detect infinite loops: ARGUMENTLESS or step=0
    if statement.loop_type == ForLoopType.ARGUMENTLESS:
        statement.is_infinite = True
    else:
        # Check for step=0 in any parameter
        for fp in statement.parameters:
            if fp.step is not None:
                # Check if step is numeric literal 0
                # Handle both MLiteral and NumericLiteral (textX) types
                step = fp.step
                step_value = getattr(step, "value", None)
                if step_value == 0 or step_value == "0":
                    statement.is_infinite = True
                    break

    return statement


def _expr_to_asg_literal(expr_str: str) -> MLiteral:
    """Create an MLiteral from an expression string.

    For now, we capture expressions as raw text in an MLiteral.
    A more complete implementation would parse full expressions.

    Args:
        expr_str: Expression string like "1", '"ABC"', or "X+1"

    Returns:
        MLiteral with the raw expression
    """
    literal = MLiteral()
    literal.raw_value = expr_str

    # Determine literal type
    if expr_str.startswith('"') and expr_str.endswith('"'):
        literal.literal_type = LiteralType.STRING
        literal.value = expr_str[1:-1]  # Remove quotes
    else:
        # Try to parse as number
        try:
            if "." in expr_str or "E" in expr_str.upper():
                literal.value = float(expr_str)
                literal.literal_type = LiteralType.DECIMAL
            else:
                literal.value = int(expr_str)
                literal.literal_type = LiteralType.INTEGER
        except ValueError:
            # Not a simple literal - it's an expression
            literal.literal_type = LiteralType.STRING
            literal.value = expr_str

    return literal


def parse_command(command_text: str) -> Optional[Any]:
    """Parse a MUMPS command string into a textX model.

    Args:
        command_text: The command string (e.g., "S X=1" or "W X")

    Returns:
        The parsed textX model or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        return mm.model_from_str(command_text, "Command")
    except TextXSyntaxError:
        return None


def parse_expression(expr_text: str) -> Optional[Any]:
    """Parse a MUMPS expression string into a textX model.

    Args:
        expr_text: The expression string (e.g., "X+Y*Z")

    Returns:
        The parsed textX model or None if parsing fails
    """
    mm = _get_expression_metamodel()
    try:
        return mm.model_from_str(expr_text, "Expr")
    except TextXSyntaxError:
        return None


def convert_to_literal(textx_model) -> MLiteral:
    """Convert a textX NumericLiteral or StringLiteral to MLiteral.

    Args:
        textx_model: The textX literal model

    Returns:
        An MLiteral ASG node
    """
    cls_name = textx_model.__class__.__name__

    if cls_name == "NumericLiteral":
        value_str = textx_model.value
        # Determine if integer or float
        if "." in value_str or "e" in value_str.lower():
            return MLiteral(value=float(value_str), literal_type=LiteralType.DECIMAL)
        else:
            return MLiteral(value=int(value_str), literal_type=LiteralType.INTEGER)
    elif cls_name == "StringLiteral":
        # Remove quotes and handle "" escaping
        raw = textx_model.value
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        value = raw.replace('""', '"')
        return MLiteral(value=value, literal_type=LiteralType.STRING)
    else:
        # Fallback
        return MLiteral(value=str(textx_model), literal_type=LiteralType.STRING)


def convert_to_variable(textx_model):
    """Convert a textX LocalVariable, GlobalVariable, or NakedGlobal to ASG.

    Args:
        textx_model: The textX variable model

    Returns:
        An MVariable, MGlobal, or MNakedGlobal ASG node
    """
    cls_name = textx_model.__class__.__name__

    if cls_name == "LocalVariable":
        return MVariable(name=textx_model.name)
    elif cls_name == "GlobalVariable":
        return MGlobal(name=textx_model.name)
    elif cls_name == "NakedGlobal":
        # NakedGlobal inherits from MNakedGlobal, so we can return it directly
        # The textX custom class already has subscripts populated
        return textx_model
    else:
        # Fallback - try to get name attribute
        name = getattr(textx_model, "name", str(textx_model))
        return MVariable(name=name)


def parse_set_command(set_text: str) -> Optional[MSetStatement]:
    """Parse a SET command using textX grammar.

    Args:
        set_text: The SET command (e.g., "S X=1" or "SET A=B,C=D")

    Returns:
        MSetStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(set_text, "SetCommand")
    except TextXSyntaxError:
        return None

    statement = MSetStatement()

    for assign in model.assignments:
        targets = []
        value_str = ""

        # Handle targets (single or parenthesized list)
        if hasattr(assign.targets, "targets"):
            # ParenTargets
            for t in assign.targets.targets:
                targets.append(convert_to_variable(t))
        else:
            # SingleTarget
            targets.append(convert_to_variable(assign.targets))

        # Get value expression as string for now
        # Full expression conversion would be more complex
        if assign.value:
            value_str = _expr_to_string(assign.value)

        for target in targets:
            assignment = MAssignment(target=target, value=value_str)
            statement.assignments.append(assignment)

    return statement


def parse_write_command(write_text: str) -> Optional[MWriteStatement]:
    """Parse a WRITE command using textX grammar.

    Args:
        write_text: The WRITE command (e.g., "W X" or 'W "Hello",!')

    Returns:
        MWriteStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(write_text, "WriteCommand")
    except TextXSyntaxError:
        return None

    statement = MWriteStatement()

    for write_arg in model.args:
        # WriteArg has postcond and arg attributes
        arg_val = write_arg.arg if hasattr(write_arg, "arg") else write_arg

        # Check if arg_val is a FormatControl variant
        if arg_val is None:
            continue

        cls_name = arg_val.__class__.__name__

        # FormatControl types
        if cls_name == "Newline":
            statement.arguments.append({"type": "newline"})
        elif cls_name == "FormFeed":
            statement.arguments.append({"type": "formfeed"})
        elif cls_name == "Tab":
            statement.arguments.append(
                {
                    "type": "tab",
                    "value": _expr_to_string(arg_val.expr) if arg_val.expr else "",
                }
            )
        elif cls_name == "CharCode":
            statement.arguments.append(
                {
                    "type": "charcode",
                    "value": _expr_to_string(arg_val.expr) if arg_val.expr else "",
                }
            )
        else:
            # Regular expression
            statement.arguments.append(
                {"type": "expr", "value": _expr_to_string(arg_val)}
            )

    return statement


def parse_quit_command(quit_text: str) -> Optional[MQuitStatement]:
    """Parse a QUIT command using textX grammar.

    Args:
        quit_text: The QUIT command (e.g., "Q" or "Q X+1" or "Q:cond")

    Returns:
        MQuitStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(quit_text, "QuitCommand")
    except TextXSyntaxError:
        return None

    statement = MQuitStatement()

    if model.postcond:
        statement.postcondition = _expr_to_string(model.postcond.condition)

    if model.value:
        statement.return_value = _expr_to_string(model.value)

    return statement


def parse_if_command(if_text: str) -> Optional[MIfStatement]:
    """Parse an IF command using textX grammar.

    Args:
        if_text: The IF command (e.g., "I X=1" or "IF X>0" or "I A=1,B=2")

    Returns:
        MIfStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(if_text, "IfCommand")
    except TextXSyntaxError:
        return None

    statement = MIfStatement()

    # Handle new grammar: conditions is a list
    if hasattr(model, "conditions") and model.conditions:
        statement.conditions = [_expr_to_string(c) for c in model.conditions]
        # For backwards compatibility, also set single condition if only one
        if len(statement.conditions) == 1:
            statement.condition = statement.conditions[0]

    return statement


def parse_for_command(for_text: str) -> Optional[MForStatement]:
    """Parse a FOR command using textX grammar.

    Args:
        for_text: The FOR command (e.g., "F I=1:1:10")

    Returns:
        MForStatement ASG node with MLiteral fields, or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(for_text, "ForCommand")
    except TextXSyntaxError:
        return None

    statement = MForStatement()

    # Extract loop variable using shared helper
    statement.loop_var = _extract_loop_var(model.var)

    # Build parameters using shared helper
    if model.params:
        statement.parameters = _build_for_parameters(model.params)

    # Classify the loop type
    statement.loop_type = _classify_for_params(statement.parameters)

    return statement


def parse_goto_command(goto_text: str) -> Optional[MGotoStatement]:
    """Parse a GOTO command using textX grammar.

    Args:
        goto_text: The GOTO command (e.g., "G LABEL" or "GOTO LABEL^ROUTINE")

    Returns:
        MGotoStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(goto_text, "GotoCommand")
    except TextXSyntaxError:
        return None

    statement = MGotoStatement()

    # Handle command-level postcondition (e.g., G:condition LABEL)
    if hasattr(model, "postcond") and model.postcond:
        statement.postcondition = _expr_to_string(model.postcond.condition)

    if model.targets:
        for target in model.targets:
            call = MCall()
            label_ref = target.label

            if label_ref:
                call.name = label_ref.label or ""
                if hasattr(label_ref, "offset") and label_ref.offset:
                    call.offset = _expr_to_string(label_ref.offset)
                if hasattr(label_ref, "routine") and label_ref.routine:
                    call.routine = label_ref.routine

            # Handle target-level postcondition if present
            if hasattr(target, "postcond") and target.postcond:
                call.postcondition = _expr_to_string(target.postcond.condition)

            statement.targets.append(call)

    return statement


def parse_new_command(new_text: str) -> Optional[MNewStatement]:
    """Parse a NEW command using textX grammar.

    Args:
        new_text: The NEW command (e.g., "N X,Y,Z" or "NEW (X)")

    Returns:
        MNewStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(new_text, "NewCommand")
    except TextXSyntaxError:
        return None

    statement = MNewStatement()

    # Check for exclusive NEW
    if hasattr(model, "exclusive") and model.exclusive:
        statement.exclusive = True
        # ExclusiveNew uses 'except' attribute, not 'except_'
        except_list = getattr(model.exclusive, "except", None) or getattr(
            model.exclusive, "except_", None
        )
        if except_list:
            statement.except_list = list(except_list)
    elif model.vars:
        # Extract variable names - NewVar objects have a 'name' attribute
        statement.variables = [
            v.name if hasattr(v, "name") else str(v) for v in model.vars
        ]

    return statement


def parse_do_command(do_text: str) -> Optional[MDoStatement]:
    """Parse a DO command using textX grammar.

    Args:
        do_text: The DO command (e.g., "D LABEL" or "DO LABEL^ROUTINE(args)")

    Returns:
        MDoStatement ASG node or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        model = mm.model_from_str(do_text, "DoCommand")
    except TextXSyntaxError:
        return None

    statement = MDoStatement()

    if model.targets:
        for target in model.targets:
            call = MCall()
            label_ref = target.label

            if label_ref:
                call.name = label_ref.label or ""
                if hasattr(label_ref, "offset") and label_ref.offset:
                    call.offset = _expr_to_string(label_ref.offset)
                if hasattr(label_ref, "routine") and label_ref.routine:
                    call.routine = label_ref.routine

            # Handle arguments if present
            if hasattr(target, "args") and target.args and target.args.args:
                call.arguments = [_expr_to_string(arg) for arg in target.args.args]

            # Handle postcondition if present
            if hasattr(target, "postcond") and target.postcond:
                call.postcondition = _expr_to_string(target.postcond.condition)

            statement.targets.append(call)

    return statement


def _classify_for_params(params: list) -> ForLoopType:
    """Classify FOR loop type from parameters."""
    if not params:
        return ForLoopType.ARGUMENTLESS

    types = set()
    for p in params:
        types.add(p.param_type)

    if len(params) > 1 and len(types) > 1:
        return ForLoopType.MIXED

    if ForParamType.RANGE in types:
        return ForLoopType.BOUNDED
    elif ForParamType.OPEN_RANGE in types:
        return ForLoopType.OPEN_ENDED
    else:
        return ForLoopType.STRING_LIST


# =============================================================================
# Expression to String Conversion (dispatch pattern)
# =============================================================================


def _format_subscripts(subscripts) -> str:
    """Format subscripts for variable or function arguments."""
    if hasattr(subscripts, "args"):
        return ",".join(_expr_to_string(s) for s in subscripts.args)
    return ",".join(_expr_to_string(s) for s in subscripts)


def _expr_numeric_literal(expr) -> str:
    """Handle NumericLiteral."""
    return str(expr.value)


def _expr_string_literal(expr) -> str:
    """Handle StringLiteral."""
    val = expr.value
    if isinstance(val, str) and not (val.startswith('"') and val.endswith('"')):
        return f'"{val}"'
    return str(val)


def _expr_local_variable(expr) -> str:
    """Handle LocalVariable."""
    name = expr.name
    if expr.subscripts:
        subs = _format_subscripts(expr.subscripts)
        return f"{name}({subs})"
    return name


def _expr_global_variable(expr) -> str:
    """Handle GlobalVariable."""
    name = f"^{expr.name}"
    if expr.subscripts:
        subs = _format_subscripts(expr.subscripts)
        return f"{name}({subs})"
    return name


def _expr_intrinsic_function(expr) -> str:
    """Handle IntrinsicFunction."""
    name = f"${expr.name}"
    if expr.arguments:
        args = ",".join(_expr_to_string(a) for a in expr.arguments)
        return f"{name}({args})"
    return name


def _expr_extrinsic_function(expr) -> str:
    """Handle ExtrinsicFunction."""
    if hasattr(expr, "target"):
        name = f"$${expr.target.name}"
        if expr.target.routine:
            name += f"^{expr.target.routine}"
    else:
        name = f"$${expr.label}"
        if hasattr(expr, "routine") and expr.routine:
            name += f"^{expr.routine}"
    if expr.arguments:
        args = ",".join(_expr_to_string(a) for a in expr.arguments)
        return f"{name}({args})"
    return name


def _expr_special_variable(expr) -> str:
    """Handle SpecialVariable."""
    return f"${expr.name}"


def _expr_indirection(expr) -> str:
    """Handle Indirection."""
    ind = f"@{_expr_to_string(expr.expr)}"
    if expr.subscripts:
        subs = ",".join(_expr_to_string(s) for s in expr.subscripts.args)
        return f"{ind}({subs})"
    return ind


def _expr_paren(expr) -> str:
    """Handle ParenExpr and OffsetParenExpr."""
    return f"({_expr_to_string(expr.expr)})"


def _expr_binary(expr) -> str:
    """Handle Expr and OffsetExpr (binary expressions with operators).

    Note: textX can misparse "1-2-3" as ops=['-'], right=[2, -3]
    where the second '-' becomes a unary operator on '3'.
    We handle this by treating unary +/- on subsequent operands as binary ops.
    """
    if not (hasattr(expr, "left") and expr.left):
        return str(expr)

    result = _expr_to_string(expr.left)

    if not (hasattr(expr, "right") and expr.right):
        return result

    ops = list(expr.ops) if hasattr(expr, "ops") and expr.ops else []

    for i, right_expr in enumerate(expr.right):
        if i < len(ops):
            # Explicit binary operator
            op = ops[i]
            op_str = op.op if hasattr(op, "op") else str(op)
            result += op_str
            result += _expr_to_string(right_expr)
        else:
            # No explicit binary op - check for leading unary +/-
            leading_ops = []
            if hasattr(right_expr, "operators") and right_expr.operators:
                leading_ops = list(right_expr.operators)
            elif hasattr(right_expr, "operator") and right_expr.operator:
                leading_ops = [right_expr.operator]

            if leading_ops:
                first_op = leading_ops[0]
                op_char = first_op.op if hasattr(first_op, "op") else str(first_op)
                if op_char in ("+", "-"):
                    result += op_char
                    for remaining_op in leading_ops[1:]:
                        result += (
                            remaining_op.op
                            if hasattr(remaining_op, "op")
                            else str(remaining_op)
                        )
                    result += _expr_to_string(right_expr.operand)
                else:
                    for uop in leading_ops:
                        result += uop.op if hasattr(uop, "op") else str(uop)
                    result += _expr_to_string(right_expr.operand)
            else:
                result += _expr_to_string(right_expr)

    return result


def _expr_unary(expr) -> str:
    """Handle UnaryExpr and OffsetUnaryExpr."""
    ops_str = ""
    if hasattr(expr, "operators") and expr.operators:
        for op_obj in expr.operators:
            ops_str += op_obj.op if hasattr(op_obj, "op") else str(op_obj)
    elif hasattr(expr, "operator") and expr.operator:
        ops_str = (
            expr.operator.op if hasattr(expr.operator, "op") else str(expr.operator)
        )
    return f"{ops_str}{_expr_to_string(expr.operand)}"


# Dispatch table for expression types
_EXPR_HANDLERS = {
    "NumericLiteral": _expr_numeric_literal,
    "StringLiteral": _expr_string_literal,
    "LocalVariable": _expr_local_variable,
    "GlobalVariable": _expr_global_variable,
    "IntrinsicFunction": _expr_intrinsic_function,
    "ExtrinsicFunction": _expr_extrinsic_function,
    "SpecialVariable": _expr_special_variable,
    "Indirection": _expr_indirection,
    "ParenExpr": _expr_paren,
    "OffsetParenExpr": _expr_paren,
    "Expr": _expr_binary,
    "OffsetExpr": _expr_binary,
    "UnaryExpr": _expr_unary,
    "OffsetUnaryExpr": _expr_unary,
}


def _expr_to_string(expr) -> str:
    """Convert a textX expression model to a string representation.

    This function extracts the string form of an expression from textX models.
    It is used as an intermediate step before creating MLiteral ASG nodes via
    _expr_to_asg_literal(). For complex expressions (variables, binary ops),
    the string is captured and wrapped in an MLiteral.

    Args:
        expr: The textX expression model

    Returns:
        String representation of the expression
    """
    if expr is None:
        return ""

    cls_name = expr.__class__.__name__
    handler = _EXPR_HANDLERS.get(cls_name)

    if handler:
        return handler(expr)
    return str(expr)


# =============================================================================
# Command Extraction Functions
# =============================================================================


def classify_for_loop_textx(for_content: str) -> tuple:
    """Classify a FOR loop from its content string using textX grammar.

    Args:
        for_content: The content after 'FOR ' or 'F ' command

    Returns:
        Tuple of (ForLoopType, loop_variable_name or None)

    Examples:
        >>> classify_for_loop_textx("I=1:1:10 W I")
        (ForLoopType.BOUNDED, "I")
        >>> classify_for_loop_textx("I=1:1 W I")
        (ForLoopType.OPEN_ENDED, "I")
        >>> classify_for_loop_textx(' W "hello"')
        (ForLoopType.ARGUMENTLESS, None)
    """
    from ..asg.enums import ForLoopType
    import re

    content = for_content.strip()

    # Empty or whitespace-only content = argumentless FOR
    if not content or content[0] in (" ", "\t") or content.startswith(";"):
        return ForLoopType.ARGUMENTLESS, None

    # Check if it starts with a variable assignment
    var_match = re.match(r"^([A-Za-z%][A-Za-z0-9]*|[A-Za-z%])=", content)
    if not var_match:
        # No variable assignment = argumentless FOR (body only)
        return ForLoopType.ARGUMENTLESS, None

    loop_var = var_match.group(1)

    # Extract just the forparams portion (up to the first space that's followed by a command)
    # This needs to handle cases like "I=1:1:10 W I" vs "I=1:1:10"
    after_var = content[len(var_match.group(0)) :]

    # Try to find where the forparams end - either at end of string or at a space followed by command
    # Use the grammar to parse just the forparams portion
    # First, try parsing with just "F var=params"
    for_params_str = f"F {content}"
    statement = parse_for_command(for_params_str)

    if statement and statement.loop_var:
        return statement.loop_type, statement.loop_var

    # If full parsing failed, try parsing just the params part
    # Find where params end - look for space followed by letter (command start)
    # But need to skip spaces inside expressions like "I=A B" shouldn't split
    # Simplest heuristic: split at first space that's not inside parens/quotes
    params_end = _find_for_params_end(after_var)

    if params_end is not None:
        params_only = after_var[:params_end]
        statement = parse_for_command(f"F {loop_var}={params_only}")
        if statement:
            return statement.loop_type, statement.loop_var

    # Fallback: try parsing just the variable assignment without body
    # At this point we know there's a var=, so let's try to classify from the params
    statement = parse_for_command(
        f"F {loop_var}={after_var.split()[0] if after_var.split() else ''}"
    )
    if statement:
        return statement.loop_type, statement.loop_var

    # Last resort: if we have a var but can't parse, treat as STRING_LIST
    return ForLoopType.STRING_LIST, loop_var


def _find_for_params_end(params_str: str) -> Optional[int]:
    """Find where FOR params end and body begins.

    Args:
        params_str: String after var= in FOR command

    Returns:
        Index where body starts, or None if no body found
    """
    in_parens = 0
    in_quotes = False

    for i, ch in enumerate(params_str):
        if ch == '"' and not in_quotes:
            in_quotes = True
        elif ch == '"' and in_quotes:
            in_quotes = False
        elif ch == "(" and not in_quotes:
            in_parens += 1
        elif ch == ")" and not in_quotes:
            in_parens -= 1
        elif ch == " " and not in_quotes and in_parens == 0:
            # Found space outside quotes/parens - this is where body starts
            # But verify next char looks like a command (letter)
            rest = params_str[i + 1 :].lstrip()
            if rest and rest[0].isalpha():
                return i

    return None


def extract_for_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract FOR command info from line content using textX grammar.

    This is a textX-based replacement for classifier.extract_for_from_line().

    Args:
        line_rest: Line content (typically after label)

    Returns:
        Tuple of (ForLoopType, loop_var, for_content) or None if no FOR found
    """
    for_commands = extract_for_commands(line_rest)
    if not for_commands:
        return None

    # Use the first FOR command found
    for_cmd = for_commands[0]
    loop_type, loop_var = classify_for_from_textx(for_cmd)

    # Build the "for_content" string that matches old API
    # This is everything after "FOR " or "F "
    for_content = ""
    if for_cmd.var:
        # Convert LocalVariable to string representation
        var_str = _expr_to_string(for_cmd.var)
        for_content = f"{var_str}="
        if for_cmd.params:
            param_strs = []
            for p in for_cmd.params:
                ps = _expr_to_string(p.start) if p.start else ""
                if p.step:
                    ps += f":{_expr_to_string(p.step)}"
                    if p.end:
                        ps += f":{_expr_to_string(p.end)}"
                param_strs.append(ps)
            for_content += ",".join(param_strs)

    return (loop_type, loop_var or "", for_content)


def extract_goto_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract GOTO command info from line content using textX grammar.

    This is a textX-based replacement for classifier.extract_goto_from_line().

    Args:
        line_rest: Line content

    Returns:
        Tuple of (label, routine, offset) or None if no GOTO found
        - label: The target label name (e.g., "LABEL" or "00000000")
        - routine: External routine name if ^routine syntax used, else None
        - offset: Offset expression string if +offset used, else None
    """
    cmds = parse_commands_from_line(line_rest)

    for cmd in cmds:
        if cmd.__class__.__name__ == "GotoCommand":
            # Extract first target info
            if cmd.targets:
                target = cmd.targets[0]
                label_ref = target.label
                # LabelRef has: label (label name), offset, routine
                label = label_ref.label if label_ref else None
                routine = (
                    label_ref.routine
                    if label_ref and hasattr(label_ref, "routine")
                    else None
                )
                offset = (
                    _expr_to_string(label_ref.offset)
                    if label_ref and hasattr(label_ref, "offset") and label_ref.offset
                    else None
                )

                return (label, routine, offset)

    return None


def extract_do_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract DO command info from line content using textX grammar.

    This is a textX-based replacement for classifier.extract_do_from_line().

    Args:
        line_rest: Line content

    Returns:
        Tuple of (do_content, target_label) or None if no DO found
    """
    cmds = parse_commands_from_line(line_rest)

    for cmd in cmds:
        if cmd.__class__.__name__ == "DoCommand":
            # Check for argumentless DO
            if not cmd.targets:
                return ("", None)

            # Extract first target info
            target = cmd.targets[0]
            label_ref = target.label
            # LabelRef has: label (label name), offset, routine
            label = label_ref.label if label_ref else None
            routine = (
                label_ref.routine
                if label_ref and hasattr(label_ref, "routine")
                else None
            )

            # Build do_content string
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


def extract_set_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract SET command info from line content using textX grammar.

    Args:
        line_rest: Line content

    Returns:
        Tuple of (set_content, first_target) or None if no SET found
    """
    cmds = parse_commands_from_line(line_rest)

    for cmd in cmds:
        if cmd.__class__.__name__ == "SetCommand":
            first_target = None
            if cmd.assignments:
                assign = cmd.assignments[0]
                if hasattr(assign, "targets") and assign.targets:
                    targets = assign.targets
                    if hasattr(targets, "targets"):  # ParenTargets
                        first_target = (
                            targets.targets[0].name
                            if hasattr(targets.targets[0], "name")
                            else None
                        )
                    else:
                        first_target = (
                            targets.name if hasattr(targets, "name") else None
                        )
            return ("", first_target)

    return None


def extract_quit_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract QUIT command info from line content using textX grammar.

    Args:
        line_rest: Line content

    Returns:
        Tuple of (has_value, is_conditional) or None if no QUIT found
    """
    cmds = parse_commands_from_line(line_rest)

    for cmd in cmds:
        if cmd.__class__.__name__ == "QuitCommand":
            has_value = hasattr(cmd, "value") and cmd.value is not None
            is_conditional = hasattr(cmd, "postcond") and cmd.postcond is not None
            return (has_value, is_conditional)

    return None


def extract_if_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract IF command info from line content using textX grammar.

    Args:
        line_rest: Line content

    Returns:
        Tuple of (condition_str,) or None if no IF found
    """
    cmds = parse_commands_from_line(line_rest)

    for cmd in cmds:
        if cmd.__class__.__name__ == "IfCommand":
            condition_str = (
                _expr_to_string(cmd.condition)
                if hasattr(cmd, "condition") and cmd.condition
                else ""
            )
            return (condition_str,)

    return None


def extract_new_from_line_textx(line_rest: str) -> Optional[tuple]:
    """Extract NEW command info from line content using textX grammar.

    Args:
        line_rest: Line content

    Returns:
        Tuple of (new_content, first_var) or None if no NEW found
    """
    cmds = parse_commands_from_line(line_rest)

    for cmd in cmds:
        if cmd.__class__.__name__ == "NewCommand":
            first_var = None
            if cmd.vars:
                # NewVar objects have a 'name' attribute
                first_var = (
                    cmd.vars[0].name
                    if hasattr(cmd.vars[0], "name")
                    else str(cmd.vars[0])
                )

            # Build new_content from variable names
            if cmd.vars:
                var_names = [v.name if hasattr(v, "name") else str(v) for v in cmd.vars]
                new_content = ",".join(var_names)
            else:
                new_content = ""
            return (new_content, first_var)

    return None


def detect_unreachable_code(lines: list) -> list:
    """Detect unreachable code after unconditional GOTO or QUIT using textX.

    Scans a list of MUMPS lines and identifies lines that cannot be
    reached because they follow an unconditional GOTO or QUIT command.

    Args:
        lines: List of MUMPS source lines

    Returns:
        List of (line_number, reason) tuples for unreachable lines
        Line numbers are 1-indexed
    """
    unreachable = []
    after_unconditional_exit = False
    unconditional_exit_line = 0

    for i, line in enumerate(lines, start=1):
        line_stripped = line.strip()

        # Skip empty lines and comment lines
        if not line_stripped or line_stripped.startswith(";"):
            continue

        # Check if this is a label line (starts with non-space)
        # Labels reset reachability since they can be GOTO targets
        if line and line[0] not in " \t":
            after_unconditional_exit = False
            continue

        # If we're after an unconditional exit, this code is unreachable
        if after_unconditional_exit:
            unreachable.append(
                (
                    i,
                    f"unreachable after unconditional exit on line {unconditional_exit_line}",
                )
            )
            continue

        # Parse commands from the line
        cmds = parse_commands_from_line(line_stripped)
        if not cmds:
            continue

        # Check the last command on the line
        last_cmd = cmds[-1]
        cmd_name = last_cmd.__class__.__name__

        # Check for unconditional GOTO
        if cmd_name == "GotoCommand":
            # Unconditional if no postcondition
            if not hasattr(last_cmd, "postcond") or not last_cmd.postcond:
                # Also check if targets have postconditions
                has_postcond = False
                if hasattr(last_cmd, "targets"):
                    for target in last_cmd.targets:
                        if hasattr(target, "postcond") and target.postcond:
                            has_postcond = True
                            break
                if not has_postcond:
                    after_unconditional_exit = True
                    unconditional_exit_line = i
                    continue

        # Check for unconditional QUIT
        if cmd_name == "QuitCommand":
            # Unconditional if no postcondition
            if not hasattr(last_cmd, "postcond") or not last_cmd.postcond:
                after_unconditional_exit = True
                unconditional_exit_line = i
                continue

    return unreachable


# =============================================================================
# Statement Parsing (Content-Only API)
# =============================================================================
# These functions accept content-only (without command word).


def parse_set_statement(content: str) -> Optional[MSetStatement]:
    """Parse SET content into MSetStatement (backward-compatible API).

    Args:
        content: Content after 'SET ' command (e.g., "X=1")

    Returns:
        MSetStatement ASG node or None
    """
    if not content or not content.strip():
        return MSetStatement()
    return parse_set_command(f"S {content}")


def parse_write_statement(content: str) -> Optional[MWriteStatement]:
    """Parse WRITE content into MWriteStatement (backward-compatible API).

    Args:
        content: Content after 'WRITE ' command (e.g., '"Hello"')

    Returns:
        MWriteStatement ASG node or None
    """
    if not content or not content.strip():
        return MWriteStatement()
    return parse_write_command(f"W {content}")


def parse_quit_statement(content: str) -> Optional[MQuitStatement]:
    """Parse QUIT content into MQuitStatement (backward-compatible API).

    Args:
        content: Content after 'QUIT ' command (e.g., "X*2" or ":X>10")

    Returns:
        MQuitStatement ASG node or None
    """
    if not content or not content.strip():
        return MQuitStatement()
    # Handle postcondition - content starts with ":"
    if content.strip().startswith(":"):
        return parse_quit_command(f"Q{content}")
    return parse_quit_command(f"Q {content}")


def parse_if_statement(content: str) -> Optional[MIfStatement]:
    """Parse IF content into MIfStatement (backward-compatible API).

    Args:
        content: Content after 'IF ' command (e.g., "X=1")

    Returns:
        MIfStatement ASG node or None
    """
    if not content or not content.strip():
        return MIfStatement()
    return parse_if_command(f"I {content}")


def parse_for_statement(content: str) -> Optional[MForStatement]:
    """Parse FOR content into MForStatement (backward-compatible API).

    Args:
        content: Content after 'FOR ' command (e.g., "I=1:1:10")

    Returns:
        MForStatement ASG node or None
    """
    if not content or not content.strip():
        stmt = MForStatement()
        stmt.loop_type = ForLoopType.ARGUMENTLESS
        return stmt
    return parse_for_command(f"F {content}")


def parse_goto_statement(content: str) -> Optional[MGotoStatement]:
    """Parse GOTO content into MGotoStatement (backward-compatible API).

    Args:
        content: Content after 'GOTO ' command (e.g., "LABEL")

    Returns:
        MGotoStatement ASG node or None
    """
    if not content or not content.strip():
        return MGotoStatement()
    return parse_goto_command(f"G {content}")


def parse_new_statement(content: str) -> Optional[MNewStatement]:
    """Parse NEW content into MNewStatement (backward-compatible API).

    Args:
        content: Content after 'NEW ' command (e.g., "X,Y,Z")

    Returns:
        MNewStatement ASG node or None
    """
    if not content or not content.strip():
        return MNewStatement()
    return parse_new_command(f"N {content}")


def parse_do_statement(content: str) -> Optional[MDoStatement]:
    """Parse DO content into MDoStatement (backward-compatible API).

    Args:
        content: Content after 'DO ' command (e.g., "LABEL")

    Returns:
        MDoStatement ASG node or None
    """
    if not content or not content.strip():
        return MDoStatement()
    return parse_do_command(f"D {content}")
