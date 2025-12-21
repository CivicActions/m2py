"""Semantic Analyzer for MUMPS ASG.

This module transforms the textX-parsed Concrete Syntax Tree (CST) into
a properly structured Abstract Semantic Graph (ASG) with:

1. Proper parent-child relationships (not textX grammar-based)
2. Unwrapped expressions (no UnaryExpr/Expr wrappers)
3. Semantic context (scope, variable classification)
4. MUMPS-specific annotations

Architecture:
    Source Code → textX Parser → CST (with custom classes) → SemanticAnalyzer → ASG
    
The CST uses our custom classes (LocalVariable, NumericLiteral, etc.) which
inherit from ASG classes. The analyzer walks this tree and:
- Sets proper `parent` references
- Replaces textX wrapper nodes with semantic equivalents
- Builds symbol tables and scope chains
- Classifies variables (local vs parameter vs return)
- Identifies control flow patterns
"""

from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field

from m2py.asg.expressions import (
    MExpr,
    MLiteral,
    MVariable,
    MGlobal,
    MNakedGlobal,
    MIntrinsicFunction,
    MExtrinsicFunction,
    MSpecialVariable,
    MIndirection,
    MBinaryOp,
    MUnaryOp,
)
from m2py.asg.statements import (
    MStatement,
    MSetStatement, MAssignment,
    MWriteStatement, MReadStatement,
    MIfStatement, MElseStatement,
    MForStatement, MForParameter,
    MGotoStatement, MDoStatement,
    MQuitStatement, MNewStatement,
    MKillStatement, MHangStatement, MHaltStatement,
    MBreakStatement, MXecuteStatement, MLockStatement,
    MMergeStatement,
)
from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
from m2py.asg.enums import LiteralType, ForLoopType, ForParamType


# =============================================================================
# Semantic Context
# =============================================================================

@dataclass
class SemanticScope:
    """Represents a semantic scope during analysis.
    
    Tracks variables, their classifications, and nesting context.
    """
    parent_scope: Optional["SemanticScope"] = None
    variables: Dict[str, "ScopeVariableInfo"] = field(default_factory=dict)
    globals_accessed: Set[str] = field(default_factory=set)
    labels_called: Set[str] = field(default_factory=set)
    
    # Scope metadata
    label_name: Optional[str] = None
    routine_name: Optional[str] = None
    is_for_body: bool = False
    nesting_level: int = 0


@dataclass 
class ScopeVariableInfo:
    """Information about a variable encountered during semantic analysis."""
    name: str
    first_reference: Any = None  # The ASG node where first seen
    is_newed: bool = False
    is_set: bool = False
    is_read: bool = False
    is_passed_by_ref: bool = False
    subscript_patterns: List[int] = field(default_factory=list)  # Number of subscripts seen


# =============================================================================
# Semantic Analyzer
# =============================================================================

class SemanticAnalyzer:
    """Transforms textX CST into enriched ASG.
    
    The analyzer walks the textX-parsed tree and:
    1. Unwraps expression wrappers (UnaryExpr, Expr)
    2. Sets proper parent-child relationships
    3. Builds semantic context (scopes, variables)
    4. Creates a clean ASG suitable for code generation
    
    Usage:
        analyzer = SemanticAnalyzer()
        asg = analyzer.analyze(textx_model)
    """
    
    def __init__(self):
        self.current_scope: Optional[SemanticScope] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def analyze(self, model: Any, parent: Any = None) -> Any:
        """Analyze a textX model and return enriched ASG.
        
        This is the main entry point. It dispatches based on the
        type of the model node.
        """
        if model is None:
            return None
        
        cls_name = model.__class__.__name__
        
        # Dispatch to specific handlers
        handler = getattr(self, f'_analyze_{cls_name}', None)
        if handler:
            return handler(model, parent)
        
        # Check if it's already an ASG type (from custom classes)
        if isinstance(model, MExpr):
            return self._analyze_expression(model, parent)
        
        # Fallback: try to unwrap common textX patterns
        return self._analyze_generic(model, parent)
    
    def _analyze_expression(self, expr: MExpr, parent: Any) -> MExpr:
        """Set parent on an already-converted expression and recurse."""
        # Set parent reference
        object.__setattr__(expr, 'parent', parent)
        
        # Handle specific expression types
        if isinstance(expr, MVariable):
            self._track_variable(expr.name, expr, is_read=True)
            # Analyze subscripts
            new_subscripts = []
            for sub in expr.subscripts:
                new_subscripts.append(self.analyze(sub, expr))
            object.__setattr__(expr, 'subscripts', new_subscripts)
        
        elif isinstance(expr, MGlobal):
            self._track_global(expr.name, expr)
            new_subscripts = []
            for sub in expr.subscripts:
                new_subscripts.append(self.analyze(sub, expr))
            object.__setattr__(expr, 'subscripts', new_subscripts)
        
        elif isinstance(expr, MIntrinsicFunction):
            new_args = []
            for arg in expr.arguments:
                new_args.append(self.analyze(arg, expr))
            object.__setattr__(expr, 'arguments', new_args)
        
        elif isinstance(expr, MExtrinsicFunction):
            new_args = []
            for arg in expr.arguments:
                new_args.append(self.analyze(arg, expr))
            object.__setattr__(expr, 'arguments', new_args)
            if expr.target:
                self._track_label_call(expr.target.name, expr.target.routine)
        
        elif isinstance(expr, MBinaryOp):
            object.__setattr__(expr, 'left', self.analyze(expr.left, expr))
            object.__setattr__(expr, 'right', self.analyze(expr.right, expr))
        
        elif isinstance(expr, MUnaryOp):
            object.__setattr__(expr, 'operand', self.analyze(expr.operand, expr))
        
        elif isinstance(expr, MIndirection):
            object.__setattr__(expr, 'expression', self.analyze(expr.expression, expr))
        
        return expr
    
    def _analyze_UnaryExpr(self, unary: Any, parent: Any) -> MExpr:
        """Unwrap UnaryExpr to get the underlying expression.
        
        UnaryExpr: operators*=UnaryOp operand=PrimaryExpr
        
        If there are no operators, just return the operand.
        If there are operators, create nested MUnaryOp nodes (innermost first).
        Example: --X becomes MUnaryOp('-', MUnaryOp('-', X))
        """
        operand = self.analyze(unary.operand, parent)
        
        # Handle chained unary operators (new grammar uses 'operators' list)
        operators = []
        if hasattr(unary, 'operators') and unary.operators:
            operators = list(unary.operators)
        elif hasattr(unary, 'operator') and unary.operator:
            # Backwards compatibility for old grammar
            operators = [unary.operator]
        
        if operators:
            # Apply operators from right to left (innermost first)
            # E.g., --X means -(-(X)), so we apply inner - first
            result = operand
            for op_obj in reversed(operators):
                op = MUnaryOp()
                op_str = op_obj.op if hasattr(op_obj, 'op') else str(op_obj)
                object.__setattr__(op, 'operator', op_str)
                object.__setattr__(op, 'operand', result)
                object.__setattr__(op, 'parent', parent)
                # Update child's parent
                object.__setattr__(result, 'parent', op)
                result = op
            return result
        
        return operand
    
    def _analyze_Expr(self, expr: Any, parent: Any) -> MExpr:
        """Unwrap Expr and build binary operation tree if needed.
        
        Expr: left=UnaryExpr (ops+=BinaryOp right+=UnaryExpr)*
        
        Note: textX's PEG parser can misparse expressions like "1-2-3" when
        operators like +/- can also be unary. It parses as:
        - left=1, ops=['-'], right=[2, -3] (where -3 has unary -)
        Instead of: left=1, ops=['-', '-'], right=[2, 3]
        
        This handler compensates by treating unary +/- on subsequent operands
        as the binary operator, but ONLY when there are more right operands than
        ops (indicating the ambiguous case).
        """
        if hasattr(expr, 'left'):
            result = self.analyze(expr.left, parent)
            
            if hasattr(expr, 'right') and expr.right:
                ops = list(expr.ops) if hasattr(expr, 'ops') and expr.ops else []
                
                for i, right_expr in enumerate(expr.right):
                    binary = MBinaryOp()
                    
                    # Get the binary operator
                    if i < len(ops):
                        # Use explicit binary operator
                        op = ops[i]
                        op_str = op.op if hasattr(op, 'op') else str(op)
                    else:
                        # No explicit binary op - check if right_expr has leading unary +/-
                        # that should be treated as the binary operator (textX parsing quirk)
                        # Handle both new 'operators' list and old 'operator' single value
                        leading_ops = []
                        if hasattr(right_expr, 'operators') and right_expr.operators:
                            leading_ops = list(right_expr.operators)
                        elif hasattr(right_expr, 'operator') and right_expr.operator:
                            leading_ops = [right_expr.operator]
                        
                        if leading_ops:
                            first_op = leading_ops[0]
                            op_char = first_op.op if hasattr(first_op, 'op') else str(first_op)
                            if op_char in ('+', '-'):
                                # Use first unary as binary operator
                                op_str = op_char
                                # Remove the first operator from the list
                                if hasattr(right_expr, 'operators'):
                                    object.__setattr__(right_expr, 'operators', leading_ops[1:])
                                else:
                                    object.__setattr__(right_expr, 'operator', None)
                            else:
                                # Not +/-, skip
                                continue
                        else:
                            # No operator available - this shouldn't happen for valid expressions
                            # Just skip this operand (it may be part of pattern syntax)
                            continue
                    
                    object.__setattr__(binary, 'operator', op_str)
                    object.__setattr__(binary, 'left', result)
                    
                    right = self.analyze(right_expr, binary)
                    object.__setattr__(binary, 'right', right)
                    
                    object.__setattr__(binary, 'parent', parent)
                    object.__setattr__(result, 'parent', binary)
                    result = binary
            
            return result
        
        # Fallback for current grammar (Expr IS UnaryExpr due to match rule)
        return self._analyze_generic(expr, parent)
    
    # OffsetExpr has the same structure as Expr, just excludes GlobalVariable
    _analyze_OffsetExpr = _analyze_Expr
    
    # OffsetUnaryExpr has the same structure as UnaryExpr
    _analyze_OffsetUnaryExpr = _analyze_UnaryExpr
    
    def _analyze_generic(self, model: Any, parent: Any) -> Any:
        """Generic handler for unknown textX types.
        
        Tries common patterns for unwrapping.
        """
        # If it has 'operand', likely a wrapper
        if hasattr(model, 'operand'):
            return self.analyze(model.operand, parent)
        
        # If it has 'expr', likely a paren wrapper
        if hasattr(model, 'expr'):
            return self.analyze(model.expr, parent)
        
        # If it has 'unary_expr', it's the old Expr structure
        if hasattr(model, 'unary_expr'):
            return self.analyze(model.unary_expr, parent)
        
        # Can't unwrap, return as-is with parent set if possible
        if hasattr(model, '__setattr__'):
            try:
                object.__setattr__(model, 'parent', parent)
            except (TypeError, AttributeError):
                pass
        
        return model
    
    # =========================================================================
    # Command Analysis Methods (textX Command → ASG Statement)
    # =========================================================================
    
    def _analyze_SetCommand(self, cmd: Any, parent: Any) -> MSetStatement:
        """Analyze SET command into MSetStatement."""
        stmt = MSetStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'assignments') and cmd.assignments:
            for assign in cmd.assignments:
                asg_assign = MAssignment()
                
                # Handle targets
                if hasattr(assign, 'targets') and assign.targets:
                    targets = assign.targets
                    if targets.__class__.__name__ == 'ParenTargets':
                        asg_assign.target = [self.analyze(t, asg_assign) for t in targets.targets]
                        # Track variables being set
                        for t in targets.targets:
                            if hasattr(t, 'name'):
                                self._track_variable(t.name, t, is_set=True)
                    else:
                        asg_assign.target = self.analyze(targets, asg_assign)
                        if hasattr(targets, 'name'):
                            self._track_variable(targets.name, targets, is_set=True)
                
                if hasattr(assign, 'value') and assign.value:
                    asg_assign.value = self.analyze(assign.value, asg_assign)
                
                stmt.assignments.append(asg_assign)
        
        return stmt
    
    def _analyze_WriteCommand(self, cmd: Any, parent: Any) -> MWriteStatement:
        """Analyze WRITE command into MWriteStatement."""
        stmt = MWriteStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'args') and cmd.args:
            for arg in cmd.args:
                if hasattr(arg, 'arg') and arg.arg:
                    stmt.arguments.append(self.analyze(arg.arg, stmt))
        
        return stmt
    
    def _analyze_ReadCommand(self, cmd: Any, parent: Any) -> MReadStatement:
        """Analyze READ command into MReadStatement.
        
        READ arguments can be:
        - Format controls: !, #, ?n (output to device)
        - Prompts: "string" (output to device)
        - Targets: VAR or VAR:timeout (input from device)
        """
        stmt = MReadStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'args') and cmd.args:
            for arg in cmd.args:
                # Handle format controls (!, #, ?n)
                if hasattr(arg, 'format') and arg.format:
                    # Keep format control as-is (textX object)
                    stmt.arguments.append(arg.format)
                # Handle prompts ("string")
                elif hasattr(arg, 'prompt') and arg.prompt:
                    prompt_expr = self.analyze(arg.prompt, stmt)
                    stmt.arguments.append(prompt_expr)
                # Handle targets (VAR or VAR:timeout)
                elif hasattr(arg, 'target') and arg.target:
                    target = self.analyze(arg.target, stmt)
                    stmt.arguments.append(target)
                    # Track variable being set
                    if hasattr(arg.target, 'name'):
                        self._track_variable(arg.target.name, arg.target, is_set=True)
        
        return stmt
    
    def _analyze_IfCommand(self, cmd: Any, parent: Any) -> MIfStatement:
        """Analyze IF command into MIfStatement.
        
        MUMPS allows comma-separated conditions which act as AND:
        IF cond1,cond2 is equivalent to IF cond1 IF cond2
        """
        stmt = MIfStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        # Handle new grammar: conditions+=Expr[/,/]
        if hasattr(cmd, 'conditions') and cmd.conditions:
            analyzed_conditions = [self.analyze(c, stmt) for c in cmd.conditions]
            stmt.conditions = analyzed_conditions
            # For backwards compatibility, also set single condition if only one
            if len(analyzed_conditions) == 1:
                stmt.condition = analyzed_conditions[0]
        # Handle old grammar for backwards compatibility: condition=Expr
        elif hasattr(cmd, 'condition') and cmd.condition:
            stmt.condition = self.analyze(cmd.condition, stmt)
            stmt.conditions = [stmt.condition]
        
        return stmt
    
    def _analyze_ElseCommand(self, cmd: Any, parent: Any) -> MElseStatement:
        """Analyze ELSE command into MElseStatement."""
        stmt = MElseStatement()
        object.__setattr__(stmt, 'parent', parent)
        return stmt
    
    def _analyze_ForCommand(self, cmd: Any, parent: Any) -> MForStatement:
        """Analyze FOR command into MForStatement."""
        stmt = MForStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'var') and cmd.var:
            # For simple variables, use the string name; for subscripted, use the full object
            if hasattr(cmd.var, 'subscripts') and cmd.var.subscripts:
                # Convert subscripts to proper ASG expressions
                stmt.loop_var = self._convert_loop_var_subscripts(cmd.var)
            else:
                stmt.loop_var = cmd.var.name if hasattr(cmd.var, 'name') else cmd.var
            self._track_variable(cmd.var, cmd, is_set=True)
        
        if hasattr(cmd, 'params') and cmd.params:
            for param in cmd.params:
                fp = MForParameter()
                
                if hasattr(param, 'start') and param.start:
                    fp.start = self.analyze(param.start, fp)
                
                if hasattr(param, 'step') and param.step:
                    fp.step = self.analyze(param.step, fp)
                    if hasattr(param, 'end') and param.end:
                        fp.end = self.analyze(param.end, fp)
                        fp.param_type = ForParamType.RANGE
                    else:
                        fp.param_type = ForParamType.OPEN_RANGE
                else:
                    fp.param_type = ForParamType.VALUE
                    fp.value = fp.start
                
                stmt.parameters.append(fp)
        
        # Classify loop type
        stmt.loop_type = self._classify_for_params(stmt.parameters)
        
        return stmt
    
    def _convert_loop_var_subscripts(self, var: Any) -> Any:
        """Convert a loop variable's subscripts to proper ASG expressions.
        
        Args:
            var: A LocalVariable or GlobalVariable with subscripts
            
        Returns:
            A new variable with subscripts converted to ASG expressions
        """
        converted_subscripts = []
        for sub in var.subscripts:
            if sub is None:
                continue
            # Already an MExpr - keep it
            if isinstance(sub, MExpr):
                converted_subscripts.append(sub)
            else:
                # Convert via analyze
                converted_subscripts.append(self.analyze(sub, var))
        
        # Create new variable with converted subscripts
        if isinstance(var, MGlobal):
            new_var = MGlobal()
            new_var.name = var.name
            new_var.subscripts = converted_subscripts
            return new_var
        else:
            new_var = MVariable()
            new_var.name = var.name
            new_var.subscripts = converted_subscripts
            return new_var
    
    def _classify_for_params(self, params: List[MForParameter]) -> ForLoopType:
        """Classify FOR loop type from parameters."""
        if not params:
            return ForLoopType.ARGUMENTLESS
        
        types = {p.param_type for p in params}
        
        if len(params) > 1 and len(types) > 1:
            return ForLoopType.MIXED
        
        if ForParamType.RANGE in types:
            return ForLoopType.BOUNDED
        elif ForParamType.OPEN_RANGE in types:
            return ForLoopType.OPEN_ENDED
        else:
            return ForLoopType.STRING_LIST
    
    def _analyze_GotoCommand(self, cmd: Any, parent: Any) -> MGotoStatement:
        """Analyze GOTO command into MGotoStatement."""
        stmt = MGotoStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'targets') and cmd.targets:
            for target in cmd.targets:
                call = MCall()
                
                if hasattr(target, 'postcond') and target.postcond:
                    call.postcondition = self.analyze(target.postcond.condition, call)
                
                # Handle indirection: G @VAR, G @@VAR, G @VAR+offset, G @VAR^@routine
                if hasattr(target, 'indirect') and target.indirect:
                    indirect = target.indirect
                    call.name = ""  # Indirection target - no static name
                    call.label_is_indirect = True
                    
                    # Process the IndirectChain for the label part
                    if hasattr(indirect, 'labelIndirect') and indirect.labelIndirect:
                        indirection_expr, levels = self._analyze_indirect_chain(indirect.labelIndirect, call)
                        call.indirection = indirection_expr
                        call.indirection_levels = levels
                    
                    # Process offset if present: @VAR+offset
                    if hasattr(indirect, 'offset') and indirect.offset:
                        call.offset = self.analyze(indirect.offset, call)
                    
                    # Process routine part: ^routine or ^@routine
                    if hasattr(indirect, 'routine') and indirect.routine:
                        call.routine = indirect.routine
                    elif hasattr(indirect, 'routineIndirect') and indirect.routineIndirect:
                        routine_expr, _ = self._analyze_indirect_chain(indirect.routineIndirect, call)
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True
                
                elif hasattr(target, 'label') and target.label:
                    label_ref = target.label
                    call.name = label_ref.label or ""
                    
                    # Handle routine: either literal name or indirect (@VAR, @@VAR)
                    if hasattr(label_ref, 'routine') and label_ref.routine:
                        call.routine = label_ref.routine
                    elif hasattr(label_ref, 'routineIndirect') and label_ref.routineIndirect:
                        routine_expr, _ = self._analyze_indirect_chain(label_ref.routineIndirect, call)
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True
                    
                    if hasattr(label_ref, 'offset') and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)
                    
                    self._track_label_call(call.name, call.routine)
                
                stmt.targets.append(call)
        
        return stmt
    
    def _analyze_DoCommand(self, cmd: Any, parent: Any) -> MDoStatement:
        """Analyze DO command into MDoStatement."""
        stmt = MDoStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'targets') and cmd.targets:
            for target in cmd.targets:
                call = MCall()
                
                if hasattr(target, 'postcond') and target.postcond:
                    call.postcondition = self.analyze(target.postcond.condition, call)
                
                # Handle indirection: D @VAR, D @@VAR, D @VAR+offset, D @VAR^@routine
                if hasattr(target, 'indirect') and target.indirect:
                    indirect = target.indirect
                    call.name = ""  # Indirection target - no static name
                    call.label_is_indirect = True
                    
                    # Process the IndirectChain for the label part
                    if hasattr(indirect, 'labelIndirect') and indirect.labelIndirect:
                        indirection_expr, levels = self._analyze_indirect_chain(indirect.labelIndirect, call)
                        call.indirection = indirection_expr
                        call.indirection_levels = levels
                    
                    # Process offset if present: @VAR+offset
                    if hasattr(indirect, 'offset') and indirect.offset:
                        call.offset = self.analyze(indirect.offset, call)
                    
                    # Process routine part: ^routine or ^@routine
                    if hasattr(indirect, 'routine') and indirect.routine:
                        call.routine = indirect.routine
                    elif hasattr(indirect, 'routineIndirect') and indirect.routineIndirect:
                        routine_expr, _ = self._analyze_indirect_chain(indirect.routineIndirect, call)
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True
                    
                    # Process arguments if present
                    if hasattr(indirect, 'args') and indirect.args:
                        if hasattr(indirect.args, 'args') and indirect.args.args:
                            call.arguments = [self.analyze(a, call) for a in indirect.args.args]
                
                elif hasattr(target, 'label') and target.label:
                    label_ref = target.label
                    call.name = label_ref.label or ""
                    
                    # Handle routine: either literal name or indirect (@VAR, @@VAR)
                    if hasattr(label_ref, 'routine') and label_ref.routine:
                        call.routine = label_ref.routine
                    elif hasattr(label_ref, 'routineIndirect') and label_ref.routineIndirect:
                        routine_expr, _ = self._analyze_indirect_chain(label_ref.routineIndirect, call)
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True
                    
                    if hasattr(label_ref, 'offset') and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)
                    
                    self._track_label_call(call.name, call.routine)
                
                if hasattr(target, 'args') and target.args:
                    if hasattr(target.args, 'args') and target.args.args:
                        call.arguments = [self.analyze(a, call) for a in target.args.args]
                
                stmt.targets.append(call)
        
        return stmt
    
    def _analyze_indirect_chain(self, chain: Any, parent: Any) -> tuple:
        """Analyze an IndirectChain and return (expression, indirection_levels).
        
        IndirectChain can be nested: @@VAR means @(@VAR)
        Returns the innermost expression and count of @ levels.
        """
        levels = 1
        current = chain
        
        # Walk through nested indirection to count levels
        while hasattr(current, 'nested') and current.nested:
            levels += 1
            current = current.nested
        
        # Now 'current' is the innermost IndirectChain - get its expression
        # Note: 'global' is a Python keyword, so we use getattr
        if hasattr(current, 'var') and current.var:
            expr = self.analyze(current.var, parent)
        elif hasattr(current, 'global') and getattr(current, 'global', None):
            expr = self.analyze(getattr(current, 'global'), parent)
        elif hasattr(current, 'expr') and current.expr:
            expr = self.analyze(current.expr, parent)
        else:
            expr = None
        
        # If there were nested levels, wrap in MIndirection objects
        # to represent the structure: @@A becomes Indirection(Indirection(var=A))
        for _ in range(levels - 1):
            inner = MIndirection(expression=expr, indirection_type="nested")
            expr = inner
        
        return expr, levels
    
    def _analyze_QuitCommand(self, cmd: Any, parent: Any) -> MQuitStatement:
        """Analyze QUIT command into MQuitStatement."""
        stmt = MQuitStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'value') and cmd.value:
            stmt.return_value = self.analyze(cmd.value, stmt)
        
        return stmt
    
    def _analyze_NewCommand(self, cmd: Any, parent: Any) -> MNewStatement:
        """Analyze NEW command into MNewStatement."""
        stmt = MNewStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'exclusive') and cmd.exclusive:
            stmt.exclusive = True
            exc = cmd.exclusive
            except_list = getattr(exc, 'except', None) or getattr(exc, 'except_', None)
            if except_list:
                stmt.except_list = list(except_list)
        elif hasattr(cmd, 'vars') and cmd.vars:
            for v in cmd.vars:
                var_name = v.name if hasattr(v, 'name') else str(v)
                stmt.variables.append(var_name)
                self._track_variable(var_name, v, is_newed=True)
        
        return stmt
    
    def _analyze_KillCommand(self, cmd: Any, parent: Any) -> MKillStatement:
        """Analyze KILL command into MKillStatement.
        
        Handles:
        - K (no args) - kill all locals
        - K X,Y - selective kill of X and Y
        - K (X,Y) - exclusive kill (keep only X,Y)
        - K (X,Y,Z),(X,W) - multiple exclusive groups (keep intersection)
        - K (X,W),Z - mixed: exclusive then selective
        """
        stmt = MKillStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        # New grammar structure: args is a list of KillArgument
        if hasattr(cmd, 'args') and cmd.args:
            exclusive_groups = []
            selective_targets = []
            
            for arg in cmd.args:
                # Check if this is an exclusive group (has 'exclusive' flag and 'except' list)
                if hasattr(arg, 'exclusive') and arg.exclusive:
                    # This is an exclusive group: (X,Y,Z)
                    except_list = getattr(arg, 'except', None) or getattr(arg, 'except_', None)
                    if except_list:
                        exclusive_groups.append(list(except_list))
                elif hasattr(arg, 'target') and arg.target:
                    # This is a selective target
                    selective_targets.append(self.analyze(arg.target, stmt))
            
            # Process exclusive groups
            if exclusive_groups:
                stmt.exclusive = True
                stmt.except_groups = exclusive_groups
                
                # Compute intersection of all exclusive groups
                if len(exclusive_groups) == 1:
                    stmt.except_list = exclusive_groups[0]
                else:
                    # Intersection: keep only vars that appear in ALL groups
                    result = set(exclusive_groups[0])
                    for group in exclusive_groups[1:]:
                        result &= set(group)
                    stmt.except_list = sorted(list(result))
            
            # Add selective targets (these are killed AFTER exclusive processing)
            stmt.targets = selective_targets
        
        # Legacy support: old grammar structure with 'exclusive' attribute
        elif hasattr(cmd, 'exclusive') and cmd.exclusive:
            stmt.exclusive = True
            exc = cmd.exclusive
            except_list = getattr(exc, 'except', None) or getattr(exc, 'except_', None)
            if except_list:
                stmt.except_list = list(except_list)
                stmt.except_groups = [list(except_list)]
        elif hasattr(cmd, 'vars') and cmd.vars:
            for v in cmd.vars:
                stmt.targets.append(self.analyze(v, stmt))
        
        return stmt
    
    def _analyze_HangCommand(self, cmd: Any, parent: Any) -> MHangStatement:
        """Analyze HANG command into MHangStatement."""
        stmt = MHangStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'seconds') and cmd.seconds:
            stmt.duration = self.analyze(cmd.seconds, stmt)
        
        return stmt
    
    def _analyze_HaltCommand(self, cmd: Any, parent: Any) -> MHaltStatement:
        """Analyze HALT command into MHaltStatement."""
        stmt = MHaltStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        return stmt
    
    def _analyze_BreakCommand(self, cmd: Any, parent: Any) -> MBreakStatement:
        """Analyze BREAK command into MBreakStatement."""
        stmt = MBreakStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        return stmt
    
    def _analyze_XecuteCommand(self, cmd: Any, parent: Any) -> MXecuteStatement:
        """Analyze XECUTE command into MXecuteStatement."""
        stmt = MXecuteStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'args') and cmd.args:
            for arg in cmd.args:
                if hasattr(arg, 'expr') and arg.expr:
                    stmt.code_expressions.append(self.analyze(arg.expr, stmt))
                else:
                    stmt.code_expressions.append(self.analyze(arg, stmt))
        
        return stmt
    
    def _analyze_LockCommand(self, cmd: Any, parent: Any) -> MLockStatement:
        """Analyze LOCK command into MLockStatement."""
        stmt = MLockStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'lockop') and cmd.lockop:
            stmt.lock_type = str(cmd.lockop)
        
        if hasattr(cmd, 'targets') and cmd.targets:
            for target in cmd.targets:
                lock_info = {}
                if hasattr(target, 'target') and target.target:
                    lock_info['target'] = self.analyze(target.target, stmt)
                if hasattr(target, 'timeout') and target.timeout:
                    lock_info['timeout'] = self.analyze(target.timeout, stmt)
                stmt.targets.append(lock_info)
        
        return stmt
    
    def _analyze_MergeCommand(self, cmd: Any, parent: Any) -> MMergeStatement:
        """Analyze MERGE command into MMergeStatement."""
        stmt = MMergeStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'merges') and cmd.merges:
            for merge in cmd.merges:
                if hasattr(merge, 'dest') and merge.dest:
                    stmt.destination = self.analyze(merge.dest, stmt)
                if hasattr(merge, 'src') and merge.src:
                    stmt.source = self.analyze(merge.src, stmt)
        
        return stmt
    
    def _analyze_OpenCommand(self, cmd: Any, parent: Any) -> "MOpenStatement":
        """Analyze OPEN command into MOpenStatement."""
        from m2py.asg.statements import MOpenStatement
        
        stmt = MOpenStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        # OPEN device(:parameters)(:timeout)
        if hasattr(cmd, 'args') and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            if len(args) > 0:
                stmt.device_expr = self.analyze(args[0], stmt)
            # Additional parameters could be parsed from device expr subscripts
        
        return stmt
    
    def _analyze_CloseCommand(self, cmd: Any, parent: Any) -> "MCloseStatement":
        """Analyze CLOSE command into MCloseStatement."""
        from m2py.asg.statements import MCloseStatement
        
        stmt = MCloseStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        # CLOSE device(:parameters)
        if hasattr(cmd, 'args') and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            if len(args) > 0:
                stmt.device_expr = self.analyze(args[0], stmt)
        
        return stmt
    
    def _analyze_UseCommand(self, cmd: Any, parent: Any) -> "MUseStatement":
        """Analyze USE command into MUseStatement."""
        from m2py.asg.statements import MUseStatement
        
        stmt = MUseStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        # USE device(:parameters)
        if hasattr(cmd, 'args') and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            if len(args) > 0:
                stmt.device_expr = self.analyze(args[0], stmt)
        
        return stmt
    
    def _analyze_JobCommand(self, cmd: Any, parent: Any) -> "MJobStatement":
        """Analyze JOB command into MJobStatement."""
        from m2py.asg.statements import MJobStatement
        
        stmt = MJobStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        # JOB uses targets like DO command (label^routine)
        if hasattr(cmd, 'targets') and cmd.targets:
            for target in cmd.targets:
                call = MCall()
                
                if hasattr(target, 'postcond') and target.postcond:
                    call.postcondition = self.analyze(target.postcond.condition, call)
                
                if hasattr(target, 'label') and target.label:
                    label_ref = target.label
                    call.name = label_ref.label or ""
                    if hasattr(label_ref, 'routine') and label_ref.routine:
                        call.routine = label_ref.routine
                    if hasattr(label_ref, 'offset') and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)
                    
                    self._track_label_call(call.name, call.routine)
                
                if hasattr(target, 'args') and target.args:
                    if hasattr(target.args, 'args') and target.args.args:
                        call.arguments = [self.analyze(a, call) for a in target.args.args]
                
                stmt.call = call
                break  # Take first target for now
        
        return stmt
    
    def _analyze_ViewCommand(self, cmd: Any, parent: Any) -> "MViewStatement":
        """Analyze VIEW command into MViewStatement."""
        from m2py.asg.statements import MViewStatement
        
        stmt = MViewStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        # VIEW arguments (implementation-specific parameters)
        if hasattr(cmd, 'args') and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            stmt.arguments = [self.analyze(arg, stmt) for arg in args]
        
        return stmt
    
    # =========================================================================
    # Scope and Variable Tracking
    # =========================================================================
    
    def _push_scope(self, label_name: Optional[str] = None, 
                    routine_name: Optional[str] = None,
                    is_for_body: bool = False) -> SemanticScope:
        """Create and enter a new scope."""
        new_scope = SemanticScope(
            parent_scope=self.current_scope,
            label_name=label_name,
            routine_name=routine_name,
            is_for_body=is_for_body,
            nesting_level=(self.current_scope.nesting_level + 1) if self.current_scope else 0
        )
        self.current_scope = new_scope
        return new_scope
    
    def _pop_scope(self) -> Optional[SemanticScope]:
        """Exit current scope and return it."""
        old_scope = self.current_scope
        if old_scope:
            self.current_scope = old_scope.parent_scope
        return old_scope
    
    def _track_variable(self, name: str, node: Any, 
                        is_read: bool = False, 
                        is_set: bool = False,
                        is_newed: bool = False):
        """Track variable usage in current scope."""
        if not self.current_scope:
            return
        
        if name not in self.current_scope.variables:
            self.current_scope.variables[name] = ScopeVariableInfo(
                name=name,
                first_reference=node
            )
        
        info = self.current_scope.variables[name]
        if is_read:
            info.is_read = True
        if is_set:
            info.is_set = True
        if is_newed:
            info.is_newed = True
    
    def _track_global(self, name: str, node: Any):
        """Track global variable access."""
        if self.current_scope:
            self.current_scope.globals_accessed.add(name)
    
    def _track_label_call(self, label: str, routine: Optional[str]):
        """Track label/routine calls."""
        if self.current_scope:
            call_target = f"{label}^{routine}" if routine else label
            self.current_scope.labels_called.add(call_target)


# =============================================================================
# Convenience Functions
# =============================================================================

def analyze_expression(textx_expr: Any, parent: Any = None) -> MExpr:
    """Analyze a single expression and return clean ASG node."""
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(textx_expr, parent)


def analyze_command(textx_cmd: Any, parent: Any = None) -> Optional[MStatement]:
    """Analyze a textX command and return ASG statement.
    
    Args:
        textx_cmd: A textX command model (SetCommand, WriteCommand, etc.)
        parent: Optional parent ASG node
        
    Returns:
        The corresponding MStatement ASG node, or None if not recognized
    """
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(textx_cmd, parent)


def unwrap_expression(textx_expr: Any) -> Any:
    """Simple unwrap without full semantic analysis.
    
    Use this when you just need to get the underlying expression
    without tracking variables/scopes.
    """
    if textx_expr is None:
        return None
    
    # Already an MExpr
    if isinstance(textx_expr, MExpr):
        return textx_expr
    
    # Expr with left attribute (new grammar)
    if hasattr(textx_expr, 'left'):
        # If no binary ops, just unwrap the left
        if not hasattr(textx_expr, 'ops') or not textx_expr.ops:
            return unwrap_expression(textx_expr.left)
        # Has binary ops - needs full analysis
        return textx_expr
    
    # UnaryExpr without operator
    if hasattr(textx_expr, 'operand'):
        op = getattr(textx_expr, 'operator', None)
        if op is None:
            return unwrap_expression(textx_expr.operand)
    
    # ParenExpr
    if hasattr(textx_expr, 'expr'):
        return unwrap_expression(textx_expr.expr)
    
    return textx_expr
