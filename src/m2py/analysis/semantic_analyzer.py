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
        
        UnaryExpr: operator=UnaryOp? operand=PrimaryExpr
        
        If there's no operator, just return the operand.
        If there's an operator, create an MUnaryOp.
        """
        operand = self.analyze(unary.operand, parent)
        
        if hasattr(unary, 'operator') and unary.operator:
            # Create MUnaryOp
            op = MUnaryOp()
            op_str = unary.operator.op if hasattr(unary.operator, 'op') else str(unary.operator)
            object.__setattr__(op, 'operator', op_str)
            object.__setattr__(op, 'operand', operand)
            object.__setattr__(op, 'parent', parent)
            # Update operand's parent
            object.__setattr__(operand, 'parent', op)
            return op
        
        return operand
    
    def _analyze_Expr(self, expr: Any, parent: Any) -> MExpr:
        """Unwrap Expr and build binary operation tree if needed.
        
        Expr: left=UnaryExpr (ops+=BinaryOp right+=UnaryExpr)*
        
        Note: This requires the grammar to be updated to capture ops/right.
        For now, handle the current grammar structure.
        """
        # Current grammar: Expr: UnaryExpr (BinaryOp UnaryExpr)*
        # This doesn't capture the binary part, so we just get UnaryExpr
        
        # If grammar is updated to have named parts:
        if hasattr(expr, 'left'):
            result = self.analyze(expr.left, parent)
            
            if hasattr(expr, 'ops') and expr.ops:
                for i, op in enumerate(expr.ops):
                    binary = MBinaryOp()
                    op_str = op.op if hasattr(op, 'op') else str(op)
                    object.__setattr__(binary, 'operator', op_str)
                    object.__setattr__(binary, 'left', result)
                    
                    if hasattr(expr, 'right') and len(expr.right) > i:
                        right = self.analyze(expr.right[i], binary)
                        object.__setattr__(binary, 'right', right)
                    
                    object.__setattr__(binary, 'parent', parent)
                    object.__setattr__(result, 'parent', binary)
                    result = binary
            
            return result
        
        # Fallback for current grammar (Expr IS UnaryExpr due to match rule)
        return self._analyze_generic(expr, parent)
    
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
        """Analyze READ command into MReadStatement."""
        stmt = MReadStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'postcond') and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)
        
        if hasattr(cmd, 'args') and cmd.args:
            for arg in cmd.args:
                if hasattr(arg, 'target') and arg.target:
                    target = self.analyze(arg.target, stmt)
                    stmt.arguments.append(target)
                    # Track variable being set
                    if hasattr(arg.target, 'name'):
                        self._track_variable(arg.target.name, arg.target, is_set=True)
        
        return stmt
    
    def _analyze_IfCommand(self, cmd: Any, parent: Any) -> MIfStatement:
        """Analyze IF command into MIfStatement."""
        stmt = MIfStatement()
        object.__setattr__(stmt, 'parent', parent)
        
        if hasattr(cmd, 'condition') and cmd.condition:
            stmt.condition = self.analyze(cmd.condition, stmt)
        
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
            stmt.loop_var = cmd.var
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
                
                if hasattr(target, 'label') and target.label:
                    label_ref = target.label
                    call.name = label_ref.label if hasattr(label_ref, 'label') else ""
                    if hasattr(label_ref, 'routine') and label_ref.routine:
                        call.routine = label_ref.routine
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
                
                if hasattr(target, 'label') and target.label:
                    label_ref = target.label
                    call.name = label_ref.label if hasattr(label_ref, 'label') else ""
                    if hasattr(label_ref, 'routine') and label_ref.routine:
                        call.routine = label_ref.routine
                    if hasattr(label_ref, 'offset') and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)
                    
                    self._track_label_call(call.name, call.routine)
                
                if hasattr(target, 'args') and target.args:
                    if hasattr(target.args, 'args') and target.args.args:
                        call.arguments = [self.analyze(a, call) for a in target.args.args]
                
                stmt.targets.append(call)
        
        return stmt
    
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
        """Analyze KILL command into MKillStatement."""
        stmt = MKillStatement()
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
