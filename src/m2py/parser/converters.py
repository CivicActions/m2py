"""Convert textX command models to ASG statement nodes.

This module provides converters for transforming textX parsed command objects
into their corresponding ASG statement representations.
"""

from typing import Any, List, Optional

from m2py.asg.statements import (
    MStatement,
    MSetStatement,
    MWriteStatement,
    MReadStatement,
    MQuitStatement,
    MIfStatement,
    MElseStatement,
    MForStatement,
    MGotoStatement,
    MDoStatement,
    MNewStatement,
    MKillStatement,
    MHangStatement,
    MHaltStatement,
    MBreakStatement,
    MLockStatement,
    MMergeStatement,
    MViewStatement,
    MXecuteStatement,
    MAssignment,
    MForParameter,
)
from m2py.asg.elements import MCall
from m2py.asg.expressions import (
    MExpr,
    MLiteral,
    MVariable,
    MGlobal,
    MIntrinsicFunction,
    MExtrinsicFunction,
    MSpecialVariable,
    MIndirection,
    MBinaryOp,
    MUnaryOp,
)
from m2py.asg.enums import ForParamType, ForLoopType, LiteralType


# =============================================================================
# Main Converter Entry Point
# =============================================================================

def textx_cmd_to_statement(cmd) -> Optional[MStatement]:
    """Convert a textX command model to an ASG MStatement.
    
    This is the main entry point for command conversion. It dispatches
    to the appropriate converter based on the command type.
    
    Args:
        cmd: A textX command model (SetCommand, WriteCommand, etc.)
        
    Returns:
        The corresponding ASG MStatement, or None if unsupported
    """
    if cmd is None:
        return None
    
    cls_name = cmd.__class__.__name__
    
    converter = _CONVERTERS.get(cls_name)
    if converter:
        return converter(cmd)
    
    # Log unknown command types (could be extended later)
    return None


def textx_cmds_to_statements(commands: List[Any]) -> List[MStatement]:
    """Convert a list of textX commands to ASG statements.
    
    Args:
        commands: List of textX command models
        
    Returns:
        List of converted ASG statements (skipping None results)
    """
    statements = []
    for cmd in commands:
        stmt = textx_cmd_to_statement(cmd)
        if stmt is not None:
            statements.append(stmt)
    return statements


# =============================================================================
# Expression Converters
# =============================================================================

def _convert_expr(expr) -> Optional[MExpr]:
    """Convert a textX expression model to an ASG MExpr.
    
    For now, creates a wrapper that holds the raw expression string.
    Full expression tree building is a separate phase.
    
    Args:
        expr: A textX expression model
        
    Returns:
        An MExpr ASG node
    """
    if expr is None:
        return None
    
    cls_name = expr.__class__.__name__
    
    # Handle atomic types
    if cls_name == 'NumericLiteral':
        literal = MLiteral()
        try:
            if '.' in expr.value or 'E' in expr.value.upper():
                literal.value = float(expr.value)
                literal.literal_type = LiteralType.DECIMAL
            else:
                literal.value = int(expr.value)
                literal.literal_type = LiteralType.INTEGER
        except ValueError:
            literal.value = expr.value
            literal.literal_type = LiteralType.STRING
        return literal
    
    elif cls_name == 'StringLiteral':
        literal = MLiteral()
        literal.literal_type = LiteralType.STRING
        # Remove surrounding quotes
        if expr.value.startswith('"') and expr.value.endswith('"'):
            literal.value = expr.value[1:-1]
        else:
            literal.value = expr.value
        return literal
    
    elif cls_name == 'LocalVariable':
        var = MVariable()
        var.name = expr.name
        if expr.subscripts:
            var.subscripts = [_convert_expr(s) for s in expr.subscripts.args]
        return var
    
    elif cls_name == 'GlobalVariable':
        glob = MGlobal()
        glob.name = expr.name
        if expr.subscripts:
            glob.subscripts = [_convert_expr(s) for s in expr.subscripts.args]
        return glob
    
    elif cls_name == 'IntrinsicFunction':
        func = MIntrinsicFunction()
        func.name = expr.name
        if expr.args:
            func.arguments = [_convert_expr(a) for a in expr.args.args]
        return func
    
    elif cls_name == 'ExtrinsicFunction':
        func = MExtrinsicFunction()
        # Create MCall for the target
        call = MCall()
        call.name = expr.label if hasattr(expr, 'label') else ""
        call.routine = expr.routine if hasattr(expr, 'routine') else None
        func.target = call
        if expr.args:
            func.arguments = [_convert_expr(a) for a in expr.args.args]
        return func
    
    elif cls_name == 'SpecialVariable':
        sv = MSpecialVariable()
        sv.name = expr.name
        return sv
    
    elif cls_name == 'Indirection':
        ind = MIndirection()
        ind.expression = _convert_expr(expr.expr)
        # Note: MIndirection doesn't have subscripts field, they're handled differently
        return ind
    
    elif cls_name == 'ParenExpr':
        # Unwrap parenthesized expression
        return _convert_expr(expr.expr)
    
    elif cls_name == 'UnaryExpr':
        if hasattr(expr, 'operator') and expr.operator:
            unary = MUnaryOp()
            unary.operator = expr.operator.op if hasattr(expr.operator, 'op') else str(expr.operator)
            unary.operand = _convert_expr(expr.operand)
            return unary
        return _convert_expr(expr.operand)
    
    elif cls_name == 'Expr':
        # Full expression with potential binary operators
        return _convert_full_expr(expr)
    
    else:
        # Fallback: wrap as literal with string representation
        literal = MLiteral()
        literal.value = _expr_to_string(expr)
        literal.literal_type = LiteralType.STRING
        return literal


def _convert_full_expr(expr) -> Optional[MExpr]:
    """Convert a full Expr with binary operations.
    
    The textX Expr rule is: UnaryExpr (BinaryOp UnaryExpr)*
    This creates a nested binary tree structure.
    """
    if not hasattr(expr, 'unary_expr'):
        # Fallback to string representation
        literal = MLiteral()
        literal.value = _expr_to_string(expr)
        literal.literal_type = LiteralType.STRING
        return literal
    
    # Start with the first unary expression
    result = _convert_expr(expr.unary_expr)
    
    # Handle binary operators
    if hasattr(expr, 'ops') and expr.ops:
        for i, op in enumerate(expr.ops):
            binary = MBinaryOp()
            binary.operator = op.op if hasattr(op, 'op') else str(op)
            binary.left = result
            
            if hasattr(expr, 'operands') and len(expr.operands) > i:
                binary.right = _convert_expr(expr.operands[i])
            
            result = binary
    
    return result


def _expr_to_string(expr) -> str:
    """Convert textX expression to string representation.
    
    Used as fallback when full conversion isn't yet implemented.
    """
    if expr is None:
        return ""
    
    cls_name = expr.__class__.__name__
    
    if cls_name == 'NumericLiteral':
        return expr.value
    elif cls_name == 'StringLiteral':
        return expr.value
    elif cls_name == 'LocalVariable':
        name = expr.name
        if expr.subscripts:
            subs = ','.join(_expr_to_string(s) for s in expr.subscripts.args)
            return f"{name}({subs})"
        return name
    elif cls_name == 'GlobalVariable':
        name = f"^{expr.name}"
        if expr.subscripts:
            subs = ','.join(_expr_to_string(s) for s in expr.subscripts.args)
            return f"{name}({subs})"
        return name
    elif cls_name == 'IntrinsicFunction':
        name = f"${expr.name}"
        if expr.args:
            args = ','.join(_expr_to_string(a) for a in expr.args.args)
            return f"{name}({args})"
        return name
    elif cls_name == 'ExtrinsicFunction':
        name = f"$${expr.label}"
        if expr.routine:
            name += f"^{expr.routine}"
        if expr.args:
            args = ','.join(_expr_to_string(a) for a in expr.args.args)
            return f"{name}({args})"
        return name
    elif cls_name == 'SpecialVariable':
        return f"${expr.name}"
    elif cls_name == 'Indirection':
        ind = f"@{_expr_to_string(expr.expr)}"
        if expr.subscripts:
            subs = ','.join(_expr_to_string(s) for s in expr.subscripts.args)
            return f"{ind}({subs})"
        return ind
    elif cls_name == 'ParenExpr':
        return f"({_expr_to_string(expr.expr)})"
    elif cls_name == 'UnaryExpr':
        op = ""
        if hasattr(expr, 'operator') and expr.operator:
            op = expr.operator.op if hasattr(expr.operator, 'op') else str(expr.operator)
        return f"{op}{_expr_to_string(expr.operand)}"
    else:
        return str(expr)


# =============================================================================
# Command Converters
# =============================================================================

def _convert_set_command(cmd) -> MSetStatement:
    """Convert SetCommand textX model to MSetStatement ASG."""
    stmt = MSetStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert each assignment
    if hasattr(cmd, 'assignments') and cmd.assignments:
        for assign in cmd.assignments:
            asg_assign = MAssignment()
            
            # Handle targets (single or parenthesized list)
            if hasattr(assign, 'targets') and assign.targets:
                targets = assign.targets
                if targets.__class__.__name__ == 'ParenTargets':
                    # Multiple targets: (A,B)=value
                    asg_assign.target = [_convert_expr(t) for t in targets.targets]
                elif targets.__class__.__name__ == 'SingleTarget':
                    # Single target
                    asg_assign.target = _convert_single_target(targets)
                else:
                    # Try direct access
                    asg_assign.target = _convert_expr(targets)
            
            # Convert value expression
            if hasattr(assign, 'value') and assign.value:
                asg_assign.value = _convert_expr(assign.value)
            
            # Individual assignment postcondition
            if hasattr(assign, 'postcond') and assign.postcond:
                asg_assign.postcondition = _convert_expr(assign.postcond.condition)
            
            stmt.assignments.append(asg_assign)
    
    return stmt


def _convert_single_target(target) -> Optional[MExpr]:
    """Convert a SetTarget to expression."""
    cls_name = target.__class__.__name__
    
    if cls_name == 'SingleTarget':
        # SingleTarget wraps GlobalVariable, LocalVariable, or Indirection
        # Access the actual content
        for attr in ['global_var', 'local_var', 'indirection']:
            if hasattr(target, attr):
                val = getattr(target, attr)
                if val:
                    return _convert_expr(val)
        # Fallback: try treating it as expression
        return _convert_expr(target)
    
    return _convert_expr(target)


def _convert_write_command(cmd) -> MWriteStatement:
    """Convert WriteCommand textX model to MWriteStatement ASG."""
    stmt = MWriteStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert arguments
    if hasattr(cmd, 'args') and cmd.args:
        for arg in cmd.args:
            # WriteArg has postcond and arg attributes
            if hasattr(arg, 'arg') and arg.arg:
                arg_val = arg.arg
                # Handle format controls and expressions
                cls_name = arg_val.__class__.__name__
                
                if cls_name in ('Newline', 'FormFeed', 'Tab', 'CharCode'):
                    # Format control - store as special marker
                    stmt.arguments.append(_convert_format_control(arg_val))
                else:
                    # Expression
                    stmt.arguments.append(_convert_expr(arg_val))
    
    return stmt


def _convert_format_control(fc) -> MLiteral:
    """Convert a format control to a special literal marker."""
    literal = MLiteral()
    cls_name = fc.__class__.__name__
    
    if cls_name == 'Newline':
        literal.value = '!'  # Store format character as value
        literal.literal_type = LiteralType.STRING
    elif cls_name == 'FormFeed':
        literal.value = '#'
        literal.literal_type = LiteralType.STRING
    elif cls_name == 'Tab':
        # Tab column position - store the expression value
        literal.value = ('?', _convert_expr(fc.expr))
        literal.literal_type = LiteralType.STRING
    elif cls_name == 'CharCode':
        # Character code - store the expression value
        literal.value = ('*', _convert_expr(fc.expr))
        literal.literal_type = LiteralType.STRING
    
    return literal


def _convert_read_command(cmd) -> MReadStatement:
    """Convert ReadCommand textX model to MReadStatement ASG."""
    stmt = MReadStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert arguments
    if hasattr(cmd, 'args') and cmd.args:
        for arg in cmd.args:
            # ReadArg has format, prompt, target, timeout attributes
            read_info = {}
            
            if hasattr(arg, 'format') and arg.format:
                read_info['format'] = _convert_format_control(arg.format)
            
            if hasattr(arg, 'prompt') and arg.prompt:
                read_info['prompt'] = _convert_expr(arg.prompt)
            
            if hasattr(arg, 'target') and arg.target:
                target = arg.target
                if target.__class__.__name__ == 'CharRead':
                    # Single character read: *VAR
                    read_info['char_read'] = True
                    read_info['target'] = _convert_expr(target.var)
                else:
                    read_info['target'] = _convert_expr(target)
            
            if hasattr(arg, 'timeout') and arg.timeout:
                read_info['timeout'] = _convert_expr(arg.timeout)
            
            stmt.arguments.append(read_info)
    
    return stmt


def _convert_quit_command(cmd) -> MQuitStatement:
    """Convert QuitCommand textX model to MQuitStatement ASG."""
    stmt = MQuitStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert return value if present
    if hasattr(cmd, 'value') and cmd.value:
        stmt.return_value = _convert_expr(cmd.value)
    
    return stmt


def _convert_if_command(cmd) -> MIfStatement:
    """Convert IfCommand textX model to MIfStatement ASG."""
    stmt = MIfStatement()
    
    # Convert condition
    if hasattr(cmd, 'condition') and cmd.condition:
        stmt.condition = _convert_expr(cmd.condition)
    
    return stmt


def _convert_else_command(cmd) -> MElseStatement:
    """Convert ElseCommand textX model to MElseStatement ASG."""
    return MElseStatement()


def _convert_for_command(cmd) -> MForStatement:
    """Convert ForCommand textX model to MForStatement ASG."""
    stmt = MForStatement()
    
    # Loop variable
    if hasattr(cmd, 'var') and cmd.var:
        stmt.loop_var = cmd.var
    
    # Convert parameters
    if hasattr(cmd, 'params') and cmd.params:
        for param in cmd.params:
            fp = MForParameter()
            
            if hasattr(param, 'start') and param.start:
                fp.start = _convert_expr(param.start)
            
            if hasattr(param, 'step') and param.step:
                fp.step = _convert_expr(param.step)
                if hasattr(param, 'end') and param.end:
                    fp.end = _convert_expr(param.end)
                    fp.param_type = ForParamType.RANGE
                else:
                    fp.param_type = ForParamType.OPEN_RANGE
            else:
                fp.param_type = ForParamType.VALUE
                # For VALUE type, the start IS the value
                if param.start:
                    fp.value = fp.start
            
            stmt.parameters.append(fp)
    
    # Classify the loop type
    stmt.loop_type = _classify_for_params(stmt.parameters)
    
    return stmt


def _classify_for_params(params: List[MForParameter]) -> ForLoopType:
    """Classify FOR loop type from parameters."""
    if not params:
        return ForLoopType.ARGUMENTLESS
    
    types = {p.param_type for p in params}
    
    if ForParamType.RANGE in types:
        return ForLoopType.BOUNDED
    elif ForParamType.OPEN_RANGE in types:
        return ForLoopType.OPEN_ENDED
    else:
        return ForLoopType.STRING_LIST


def _convert_goto_command(cmd) -> MGotoStatement:
    """Convert GotoCommand textX model to MGotoStatement ASG."""
    stmt = MGotoStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert targets (using MCall)
    if hasattr(cmd, 'targets') and cmd.targets:
        for target in cmd.targets:
            call = MCall()
            
            if hasattr(target, 'postcond') and target.postcond:
                call.postcondition = _convert_expr(target.postcond.condition)
            
            if hasattr(target, 'label') and target.label:
                label_ref = target.label
                call.name = label_ref.label if hasattr(label_ref, 'label') and label_ref.label else ""
                call.routine = label_ref.routine if hasattr(label_ref, 'routine') else None
                if hasattr(label_ref, 'offset') and label_ref.offset:
                    call.offset = _convert_expr(label_ref.offset)
            
            stmt.targets.append(call)
    
    return stmt


def _convert_do_command(cmd) -> MDoStatement:
    """Convert DoCommand textX model to MDoStatement ASG."""
    stmt = MDoStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert targets (using MCall)
    if hasattr(cmd, 'targets') and cmd.targets:
        for target in cmd.targets:
            call = MCall()
            
            if hasattr(target, 'postcond') and target.postcond:
                call.postcondition = _convert_expr(target.postcond.condition)
            
            if hasattr(target, 'label') and target.label:
                label_ref = target.label
                call.name = label_ref.label if hasattr(label_ref, 'label') and label_ref.label else ""
                call.routine = label_ref.routine if hasattr(label_ref, 'routine') else None
                if hasattr(label_ref, 'offset') and label_ref.offset:
                    call.offset = _convert_expr(label_ref.offset)
            
            # Arguments
            if hasattr(target, 'args') and target.args:
                if hasattr(target.args, 'args') and target.args.args:
                    call.arguments = [_convert_expr(a) for a in target.args.args]
            
            stmt.targets.append(call)
    
    return stmt


def _convert_new_command(cmd) -> MNewStatement:
    """Convert NewCommand textX model to MNewStatement ASG."""
    stmt = MNewStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Exclusive NEW
    if hasattr(cmd, 'exclusive') and cmd.exclusive:
        stmt.exclusive = True
        exc = cmd.exclusive
        if hasattr(exc, 'except_'):
            stmt.except_list = list(exc.except_)
        elif hasattr(exc, 'except'):
            stmt.except_list = list(getattr(exc, 'except'))
    
    # Regular NEW variables (stored as strings)
    elif hasattr(cmd, 'vars') and cmd.vars:
        for var in cmd.vars:
            if hasattr(var, 'name') and var.name:
                stmt.variables.append(var.name)
    
    return stmt


def _convert_kill_command(cmd) -> MKillStatement:
    """Convert KillCommand textX model to MKillStatement ASG."""
    stmt = MKillStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Exclusive KILL
    if hasattr(cmd, 'exclusive') and cmd.exclusive:
        stmt.exclusive = True
        exc = cmd.exclusive
        if hasattr(exc, 'except_'):
            stmt.except_list = list(exc.except_)
        elif hasattr(exc, 'except'):
            stmt.except_list = list(getattr(exc, 'except'))
    
    # Regular KILL targets
    elif hasattr(cmd, 'vars') and cmd.vars:
        for var in cmd.vars:
            stmt.targets.append(_convert_expr(var))
    
    return stmt


def _convert_hang_command(cmd) -> MHangStatement:
    """Convert HangCommand textX model to MHangStatement ASG."""
    stmt = MHangStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Convert duration expression
    if hasattr(cmd, 'seconds') and cmd.seconds:
        stmt.duration = _convert_expr(cmd.seconds)
    
    return stmt


def _convert_halt_command(cmd) -> MHaltStatement:
    """Convert HaltCommand textX model to MHaltStatement ASG."""
    stmt = MHaltStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    return stmt


def _convert_break_command(cmd) -> MBreakStatement:
    """Convert BreakCommand textX model to MBreakStatement ASG."""
    stmt = MBreakStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    return stmt


def _convert_lock_command(cmd) -> MLockStatement:
    """Convert LockCommand textX model to MLockStatement ASG."""
    stmt = MLockStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # Lock type (+/-)
    if hasattr(cmd, 'lockop') and cmd.lockop:
        stmt.lock_type = str(cmd.lockop)
    
    # Lock targets
    if hasattr(cmd, 'targets') and cmd.targets:
        for target in cmd.targets:
            lock_info = {}
            
            if hasattr(target, 'postcond') and target.postcond:
                lock_info['postcondition'] = _convert_expr(target.postcond.condition)
            
            if hasattr(target, 'target') and target.target:
                lock_info['target'] = _convert_expr(target.target)
            
            if hasattr(target, 'timeout') and target.timeout:
                lock_info['timeout'] = _convert_expr(target.timeout)
            
            stmt.targets.append(lock_info)
    
    return stmt


def _convert_merge_command(cmd) -> MMergeStatement:
    """Convert MergeCommand textX model to MMergeStatement ASG."""
    stmt = MMergeStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # MERGE has destination=source pairs
    if hasattr(cmd, 'merges') and cmd.merges:
        for merge in cmd.merges:
            if hasattr(merge, 'dest') and merge.dest:
                stmt.destination = _convert_expr(merge.dest)
            if hasattr(merge, 'src') and merge.src:
                stmt.source = _convert_expr(merge.src)
    
    return stmt


def _convert_view_command(cmd) -> MViewStatement:
    """Convert ViewCommand textX model to MViewStatement ASG."""
    stmt = MViewStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # View arguments
    if hasattr(cmd, 'args') and cmd.args:
        stmt.arguments = [_convert_expr(a) for a in cmd.args]
    
    return stmt


def _convert_xecute_command(cmd) -> MXecuteStatement:
    """Convert XecuteCommand textX model to MXecuteStatement ASG."""
    stmt = MXecuteStatement()
    
    # Handle postcondition on the command
    if hasattr(cmd, 'postcond') and cmd.postcond:
        stmt.postcondition = _convert_expr(cmd.postcond.condition)
    
    # XECUTE code expressions
    if hasattr(cmd, 'args') and cmd.args:
        for arg in cmd.args:
            if hasattr(arg, 'expr') and arg.expr:
                stmt.code_expressions.append(_convert_expr(arg.expr))
            else:
                # arg might be the expression directly
                stmt.code_expressions.append(_convert_expr(arg))
    
    return stmt


# =============================================================================
# Converter Registry
# =============================================================================

_CONVERTERS = {
    'SetCommand': _convert_set_command,
    'WriteCommand': _convert_write_command,
    'ReadCommand': _convert_read_command,
    'QuitCommand': _convert_quit_command,
    'IfCommand': _convert_if_command,
    'ElseCommand': _convert_else_command,
    'ForCommand': _convert_for_command,
    'GotoCommand': _convert_goto_command,
    'DoCommand': _convert_do_command,
    'NewCommand': _convert_new_command,
    'KillCommand': _convert_kill_command,
    'HangCommand': _convert_hang_command,
    'HaltCommand': _convert_halt_command,
    'BreakCommand': _convert_break_command,
    'LockCommand': _convert_lock_command,
    'MergeCommand': _convert_merge_command,
    'ViewCommand': _convert_view_command,
    'XecuteCommand': _convert_xecute_command,
}
