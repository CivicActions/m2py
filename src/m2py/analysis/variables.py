"""Variable scope and data flow analysis.

Analyzes variable usage across MUMPS routines:
1. Collects variable reads and writes per label
2. Respects NEW command boundaries for scoping
3. Computes input_variables (read before first write)
4. Computes output_variables (written and visible to caller)
5. Supports transitive closure for call chain propagation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from ..asg.elements import MRoutine, MLabel, MScope
from ..asg.statements import (
    MStatement, MSetStatement, MNewStatement, 
    MForStatement, MIfStatement, MDoStatement,
    MWriteStatement, MQuitStatement,
)


@dataclass
class VariableInfo:
    """Information about a variable's usage in a scope."""
    name: str
    is_read: bool = False
    is_written: bool = False
    is_newed: bool = False
    first_read_line: Optional[int] = None
    first_write_line: Optional[int] = None


@dataclass
class ScopeVariables:
    """Variable information for a single scope (label or block)."""
    reads: Set[str] = field(default_factory=set)
    writes: Set[str] = field(default_factory=set)
    newed: Set[str] = field(default_factory=set)
    
    # Computed after analysis
    input_variables: Set[str] = field(default_factory=set)
    output_variables: Set[str] = field(default_factory=set)


def analyze_variables(routine: MRoutine) -> Dict[str, ScopeVariables]:
    """Analyze variable usage across all labels in a routine.
    
    This is the main entry point for variable analysis. It:
    1. Scans each label for variable reads and writes
    2. Tracks NEW commands to understand scope boundaries
    3. Computes input variables (read before first write)
    4. Computes output variables (written and visible to caller)
    
    Args:
        routine: The MRoutine to analyze
        
    Returns:
        Dictionary mapping label names to ScopeVariables
        
    Side Effects:
        Populates MLabel.variables_read, variables_written, variables_newed,
        input_variables, and output_variables
    """
    result = {}
    
    for label in routine.labels:
        scope_vars = _analyze_label(label)
        result[label.name] = scope_vars
        
        # Populate MLabel fields
        label.variables_read = scope_vars.reads
        label.variables_written = scope_vars.writes
        label.variables_newed = scope_vars.newed
        label.input_variables = scope_vars.input_variables
        label.output_variables = scope_vars.output_variables
    
    return result


def _analyze_label(label: MLabel) -> ScopeVariables:
    """Analyze variable usage in a single label.
    
    Args:
        label: The MLabel to analyze
        
    Returns:
        ScopeVariables with reads, writes, newed sets populated
    """
    scope_vars = ScopeVariables()
    
    # Track order of operations for input/output computation
    read_before_write = set()
    written_vars = set()
    newed_vars = set()
    
    # Walk through statements in order
    for stmt in label.body.walk_statements():
        stmt_reads, stmt_writes, stmt_news = _extract_statement_variables(stmt)
        
        # Update newed set (these create new local scope)
        for var in stmt_news:
            newed_vars.add(var)
            scope_vars.newed.add(var)
        
        # Track reads - only count as input if not yet written or newed
        for var in stmt_reads:
            scope_vars.reads.add(var)
            if var not in written_vars and var not in newed_vars:
                read_before_write.add(var)
        
        # Track writes
        for var in stmt_writes:
            scope_vars.writes.add(var)
            written_vars.add(var)
    
    # Compute input variables: read before first write and not newed
    scope_vars.input_variables = read_before_write - newed_vars
    
    # Compute output variables: written and not newed (visible to caller)
    scope_vars.output_variables = written_vars - newed_vars
    
    return scope_vars


def _extract_statement_variables(stmt: MStatement) -> Tuple[Set[str], Set[str], Set[str]]:
    """Extract variable reads, writes, and NEWS from a statement.
    
    Args:
        stmt: The statement to analyze
        
    Returns:
        Tuple of (reads, writes, news) sets
    """
    reads = set()
    writes = set()
    news = set()
    
    if isinstance(stmt, MSetStatement):
        # SET X=expr writes X, may read variables in expr
        for assignment in stmt.assignments:
            if hasattr(assignment, 'target') and assignment.target:
                if hasattr(assignment.target, 'name'):
                    writes.add(assignment.target.name)
            if hasattr(assignment, 'value') and assignment.value:
                reads.update(_extract_expression_variables(assignment.value))
    
    elif isinstance(stmt, MNewStatement):
        # NEW X,Y,Z creates new local scope for these variables
        for var in stmt.variables:
            news.add(var)
        # Exclusive NEW (X) means all EXCEPT X get newed
        # We can't enumerate all, so we just note the exception
        if stmt.exclusive:
            # Store exception list but don't add to news
            # (would need runtime knowledge of all variables)
            pass
    
    elif isinstance(stmt, MForStatement):
        # FOR I=... writes the loop variable
        if stmt.loop_var:
            writes.add(stmt.loop_var)
        # Parameters may reference variables
        for param in stmt.parameters:
            if param.start:
                reads.update(_extract_expression_variables(param.start))
            if param.step:
                reads.update(_extract_expression_variables(param.step))
            if param.end:
                reads.update(_extract_expression_variables(param.end))
            if param.value:
                reads.update(_extract_expression_variables(param.value))
    
    elif isinstance(stmt, MIfStatement):
        # IF condition reads variables in condition
        if stmt.condition:
            reads.update(_extract_expression_variables(stmt.condition))
    
    elif isinstance(stmt, MDoStatement):
        # DO label(args) - args are reads
        for target in stmt.targets:
            for arg in target.arguments:
                reads.update(_extract_expression_variables(arg))
    
    elif isinstance(stmt, MWriteStatement):
        # WRITE reads variables in arguments
        for arg in stmt.arguments:
            reads.update(_extract_expression_variables(arg))
    
    elif isinstance(stmt, MQuitStatement):
        # QUIT value reads the return value
        if stmt.return_value:
            reads.update(_extract_expression_variables(stmt.return_value))
    
    return reads, writes, news


def _extract_expression_variables(expr) -> Set[str]:
    """Extract variable names referenced in an expression.
    
    Args:
        expr: An expression (MLiteral, MVariable, MBinaryOp, etc.)
        
    Returns:
        Set of variable names referenced
    """
    vars_found = set()
    
    if expr is None:
        return vars_found
    
    # Import here to avoid circular imports
    from ..asg.expressions import MVariable, MBinaryOp, MUnaryOp, MLiteral
    
    # MVariable has a name
    if isinstance(expr, MVariable):
        name = expr.name
        # Exclude globals (^name) and special variables ($name)
        if name and not name.startswith('^') and not name.startswith('$'):
            vars_found.add(name)
        # Recursively check subscripts
        if hasattr(expr, 'subscripts') and expr.subscripts:
            for sub in expr.subscripts:
                vars_found.update(_extract_expression_variables(sub))
    
    # MBinaryOp has left and right operands
    elif isinstance(expr, MBinaryOp):
        if hasattr(expr, 'left') and expr.left:
            vars_found.update(_extract_expression_variables(expr.left))
        if hasattr(expr, 'right') and expr.right:
            vars_found.update(_extract_expression_variables(expr.right))
    
    # MUnaryOp has operand
    elif isinstance(expr, MUnaryOp):
        if hasattr(expr, 'operand') and expr.operand:
            vars_found.update(_extract_expression_variables(expr.operand))
    
    # MLiteral - no variable references
    elif isinstance(expr, MLiteral):
        pass
    
    # Fallback: check generic attributes
    elif hasattr(expr, 'name') and isinstance(getattr(expr, 'name', None), str):
        name = expr.name
        if name and not name.startswith('^') and not name.startswith('$'):
            vars_found.add(name)
    
    # Check for nested expressions in lists
    if hasattr(expr, 'args') and expr.args:
        for arg in expr.args:
            vars_found.update(_extract_expression_variables(arg))
    
    if hasattr(expr, 'arguments') and expr.arguments:
        for arg in expr.arguments:
            vars_found.update(_extract_expression_variables(arg))
    
    return vars_found


def get_def_use_chains(label: MLabel) -> Dict[str, List[Tuple[int, str]]]:
    """Build def-use chains for variables in a label.
    
    A def-use chain tracks where variables are defined (written)
    and where they are used (read).
    
    Args:
        label: The MLabel to analyze
        
    Returns:
        Dictionary mapping variable names to list of (line_number, 'def'|'use') tuples
    """
    chains = {}
    
    for stmt in label.body.walk_statements():
        line = stmt.line_number or 0
        reads, writes, _ = _extract_statement_variables(stmt)
        
        for var in writes:
            if var not in chains:
                chains[var] = []
            chains[var].append((line, 'def'))
        
        for var in reads:
            if var not in chains:
                chains[var] = []
            chains[var].append((line, 'use'))
    
    return chains


def compute_transitive_inputs(
    routine: MRoutine,
    label_vars: Dict[str, ScopeVariables]
) -> Dict[str, Set[str]]:
    """Compute transitive closure of input variables through call chains.
    
    When label A calls label B, A's inputs include B's inputs that A
    doesn't already provide.
    
    Args:
        routine: The MRoutine being analyzed
        label_vars: Result of analyze_variables()
        
    Returns:
        Dictionary mapping label names to transitive input variable sets
    """
    # Build call graph
    call_graph = {}
    for label in routine.labels:
        callees = set()
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MDoStatement):
                for target in stmt.targets:
                    if target.name and not target.routine:  # Local call
                        callees.add(target.name)
        call_graph[label.name] = callees
    
    # Initialize with direct inputs
    transitive_inputs = {
        name: set(vars.input_variables)
        for name, vars in label_vars.items()
    }
    
    # Fixed-point iteration
    changed = True
    while changed:
        changed = False
        for label_name, callees in call_graph.items():
            current = transitive_inputs.get(label_name, set())
            for callee in callees:
                callee_inputs = transitive_inputs.get(callee, set())
                callee_outputs = label_vars.get(callee, ScopeVariables()).output_variables
                # Add callee inputs that aren't provided by caller's writes
                caller_writes = label_vars.get(label_name, ScopeVariables()).writes
                new_inputs = callee_inputs - caller_writes
                if new_inputs - current:
                    current.update(new_inputs)
                    transitive_inputs[label_name] = current
                    changed = True
    
    return transitive_inputs
