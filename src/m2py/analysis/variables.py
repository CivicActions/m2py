"""Variable scope and data flow analysis.

Analyzes variable usage across MUMPS routines:
1. Collects variable reads and writes per label
2. Respects NEW command boundaries for scoping
3. Computes input_variables (read before first write)
4. Computes output_variables (written and visible to caller)
5. Supports transitive closure for call chain propagation
6. Computes function signatures for Python code generation

MUMPS MDC Specification References:
-----------------------------------
This module implements variable scoping semantics from ANSI/MDC X11.1-1995:

- MDC 8.1.14 (Parameter Passing): Defines call-by-value and call-by-reference.
  Step 1: Evaluate actual parameters left to right
  Step 2: For each actual with corresponding formal, process per passing mode:
    - For .actualname (by-ref): Establish alias between actual and formal
    - For expr (by-value): NEW formal, SET formal=expr
    - For omitted: NEW formal (creates empty DATA-CELL)
  Step 3: Execute the called code

- MDC 8.1.42 (NEW Command): Four forms supported:
  1. NEW - Exclusive NEW all, creates empty stack level
  2. NEW x,y,z - Selective NEW, saves/clears specified variables
  3. NEW (x,y) - Exclusive NEW except x,y
  4. Implicit NEW via formal parameters

- MDC 8.1.26 (DO Command): Call semantics for subroutines
  - D label - Simple call (no arguments)
  - D label(args) - Call with parameter binding
  - D label^routine - External routine call
  - D +offset - Line offset call

- MDC 7.1.10 (PROCESS-STACK): Scope model
  - Each subroutine/DO level creates a stack frame
  - NEW creates local scope for variables
  - Variables not NEWed are visible from caller scope

These specifications define the MUMPS variable visibility and call semantics
that this module analyzes to enable Python code generation with proper
function signatures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ..asg.elements import MCall, MLabel, MRoutine
from ..asg.expressions import MVariable
from ..asg.statements import (
    MDoStatement,
    MForStatement,
    MIfStatement,
    MKillStatement,
    MNewStatement,
    MQuitStatement,
    MSetStatement,
    MStatement,
    MWriteStatement,
    MXecuteStatement,
)
from ..asg.enums import PassingMode, ScopeStrategy


# =============================================================================
# Data Classes for Variable Analysis
# =============================================================================


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
    formal_params: Set[str] = field(
        default_factory=set
    )  # Formal parameter names (implicit NEW)

    # Computed after analysis
    input_variables: Set[str] = field(default_factory=set)
    output_variables: Set[str] = field(default_factory=set)


@dataclass
class ParameterBinding:
    """Links an actual parameter at a call site to a formal parameter.

    Created during reference resolution to track how arguments flow
    from caller to callee.

    Per MUMPS spec (MDC 8.1.7):
    - Call-by-value: expr evaluated, new DATA-CELL created
    - Call-by-reference: .actualname creates alias to caller's variable
    - Omitted: empty DATA-CELL created

    Attributes:
        formal_name: Name in the callee's formal_list
        actual_expr: The expression passed by caller (may be None for OMITTED)
        passing_mode: How the parameter was passed
        caller_var_name: For BY_REFERENCE, the caller's variable name
    """

    formal_name: str
    actual_expr: Optional[Any] = None  # MExpr
    passing_mode: PassingMode = PassingMode.BY_VALUE
    caller_var_name: Optional[str] = None  # For BY_REFERENCE only


@dataclass
class FunctionSignature:
    """Clean function signature for a label, computed from variable analysis.

    Enables generating Python functions with proper arguments and return values
    instead of runtime get_local()/set_local() patterns.

    Attributes:
        label_name: The label this signature describes
        formal_params: Ordered list of formal parameter names
        required_inputs: Variables that must be provided by caller (not in formal_params)
        optional_inputs: Variables that may come from caller scope or globals
        return_value: Expression type from QUIT value analysis (if any)
        byref_outputs: Variables modified via call-by-reference that affect caller
        side_effect_outputs: Other visible modifications (not by-ref, not NEWed)
        requires_runtime_scope: True if indirection/XECUTE defeats static analysis
        scope_strategy: Classification for code generation approach
        has_value_quit: True if any QUIT has a return value
        has_void_quit: True if any QUIT has no return value
        transitive_inputs: After transitive analysis, inputs including callee needs
        transitive_outputs: After transitive analysis, outputs including callee effects
    """

    label_name: str = ""
    formal_params: List[str] = field(default_factory=list)
    required_inputs: Set[str] = field(default_factory=set)
    optional_inputs: Set[str] = field(default_factory=set)
    return_value: Optional[Any] = None  # MExpr or type description
    byref_outputs: Set[str] = field(default_factory=set)
    side_effect_outputs: Set[str] = field(default_factory=set)
    requires_runtime_scope: bool = False
    scope_strategy: ScopeStrategy = ScopeStrategy.SUBROUTINE
    has_value_quit: bool = False
    has_void_quit: bool = False
    transitive_inputs: Set[str] = field(default_factory=set)
    transitive_outputs: Set[str] = field(default_factory=set)


class RoutineAnalysisCache:
    """Cached analysis results for a routine with incremental update support.

    For IDE scenarios where single labels change, this cache avoids
    recomputing the entire routine analysis.

    The cache is invalidated when:
    - A label is added or removed
    - A label's body changes (detected via source hash)

    When a single label changes, only that label and labels that call it
    need recomputation.

    Usage:
        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed()  # Full analysis on first call

        # After editing label "FOO":
        cache.invalidate_label("FOO")
        cache.ensure_analyzed()  # Only recomputes FOO and callers
    """

    def __init__(self, routine: MRoutine):
        self.routine = routine
        self._label_vars: Dict[str, ScopeVariables] = {}
        self._signatures: Dict[str, FunctionSignature] = {}
        self._transitive_inputs: Dict[str, Set[str]] = {}
        self._transitive_outputs: Dict[str, Set[str]] = {}
        self._call_graph: Dict[str, Set[str]] = {}  # label -> labels it calls
        self._reverse_call_graph: Dict[str, Set[str]] = {}  # label -> callers
        self._label_hashes: Dict[str, int] = {}  # For change detection
        self._valid_labels: Set[str] = set()
        self._fully_analyzed: bool = False

    def ensure_analyzed(self, compute_transitive: bool = True) -> None:
        """Ensure all analysis is complete, doing minimal work if cached."""
        if self._fully_analyzed:
            return

        # Check which labels need (re)analysis
        current_labels = {label.name for label in self.routine.labels}
        stale_labels = current_labels - self._valid_labels

        # If too many labels changed, just recompute everything
        if len(stale_labels) > len(current_labels) // 2:
            self._full_analysis(compute_transitive)
            return

        # Incremental: analyze only stale labels
        for label_name in stale_labels:
            label = self.routine.get_label(label_name)
            if label:
                scope_vars = _analyze_label(label)
                self._label_vars[label_name] = scope_vars
                label.variables_read = scope_vars.reads
                label.variables_written = scope_vars.writes
                label.variables_newed = scope_vars.newed
                label.input_variables = scope_vars.input_variables
                label.output_variables = scope_vars.output_variables
                self._valid_labels.add(label_name)

        # Rebuild call graph
        self._build_call_graph()

        # Recompute signatures for stale labels and their callers
        affected = self._get_affected_labels(stale_labels)
        for label_name in affected:
            label = self.routine.get_label(label_name)
            if label and label_name in self._label_vars:
                sig = compute_function_signature(label, self._label_vars[label_name])
                self._signatures[label_name] = sig

        # Recompute transitive closures (full, since they're cheap)
        if compute_transitive:
            self._transitive_inputs = compute_transitive_inputs(
                self.routine, self._label_vars
            )
            self._transitive_outputs = compute_transitive_outputs(
                self.routine, self._label_vars, self._signatures
            )

            # Update signatures with transitive info
            for name, sig in self._signatures.items():
                sig.transitive_inputs = self._transitive_inputs.get(name, set())
                sig.transitive_outputs = self._transitive_outputs.get(name, set())

        self._fully_analyzed = True

    def _full_analysis(self, compute_transitive: bool = True) -> None:
        """Perform complete analysis from scratch."""
        self._label_vars = analyze_variables(self.routine)
        self._signatures = compute_all_signatures(self.routine)
        self._build_call_graph()

        if compute_transitive:
            self._transitive_inputs = compute_transitive_inputs(
                self.routine, self._label_vars
            )
            self._transitive_outputs = compute_transitive_outputs(
                self.routine, self._label_vars, self._signatures
            )

            # Update signatures with transitive info
            for name, sig in self._signatures.items():
                sig.transitive_inputs = self._transitive_inputs.get(name, set())
                sig.transitive_outputs = self._transitive_outputs.get(name, set())

        self._valid_labels = {label.name for label in self.routine.labels}
        self._fully_analyzed = True

    def _build_call_graph(self) -> None:
        """Build forward and reverse call graphs."""
        self._call_graph = {}
        self._reverse_call_graph = {}

        for label in self.routine.labels:
            callees = set()
            for stmt in label.body.walk_statements():
                if isinstance(stmt, MDoStatement):
                    for target in stmt.targets:
                        if target.name and not target.routine:
                            callees.add(target.name)
            self._call_graph[label.name] = callees

            # Build reverse graph
            for callee in callees:
                if callee not in self._reverse_call_graph:
                    self._reverse_call_graph[callee] = set()
                self._reverse_call_graph[callee].add(label.name)

    def _get_affected_labels(self, changed: Set[str]) -> Set[str]:
        """Get labels affected by changes (changed + transitive callers)."""
        affected = set(changed)
        worklist = list(changed)

        while worklist:
            label = worklist.pop()
            callers = self._reverse_call_graph.get(label, set())
            for caller in callers:
                if caller not in affected:
                    affected.add(caller)
                    worklist.append(caller)

        return affected

    def invalidate_label(self, label_name: str) -> None:
        """Mark a label as needing reanalysis."""
        self._valid_labels.discard(label_name)
        self._fully_analyzed = False

    def invalidate_all(self) -> None:
        """Mark all labels as needing reanalysis."""
        self._valid_labels.clear()
        self._fully_analyzed = False

    @property
    def label_vars(self) -> Dict[str, ScopeVariables]:
        """Get label variable analysis (ensures analysis is done)."""
        self.ensure_analyzed()
        return self._label_vars

    @property
    def signatures(self) -> Dict[str, FunctionSignature]:
        """Get computed signatures (ensures analysis is done)."""
        self.ensure_analyzed()
        return self._signatures


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

    Treats formal parameters as implicitly NEWed per MUMPS spec.

    Per MDC 8.1.14 Step 2, parameter passing performs an implicit NEW on
    formal parameter names, so they create local scope and don't count as
    input variables from the caller's perspective.

    Per MDC 8.1.42, NEW command forms:
    - NEW x,y,z: Saves current values and creates new empty DATA-CELLs
    - NEW (x,y): Exclusive NEW - saves all EXCEPT x,y

    Args:
        label: The MLabel to analyze

    Returns:
        ScopeVariables with reads, writes, newed, formal_params sets populated
    """
    scope_vars = ScopeVariables()

    # Track order of operations for input/output computation
    read_before_write = set()
    written_vars = set()
    newed_vars = set()

    # Formal parameters are implicitly NEWed per MUMPS spec (MDC 8.1.7 step 3)
    # This means they create local scope and don't count as input variables
    formal_params = set(label.formal_list) if label.formal_list else set()
    scope_vars.formal_params = formal_params
    newed_vars.update(formal_params)  # Treat formals as implicitly newed

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

    # Compute input variables: read before first write and not newed (including formal params)
    scope_vars.input_variables = read_before_write - newed_vars

    # Compute output variables: written and not newed (visible to caller)
    # Note: formal params are also excluded since they are implicitly newed
    scope_vars.output_variables = written_vars - newed_vars

    return scope_vars


def _extract_statement_variables(
    stmt: MStatement,
) -> Tuple[Set[str], Set[str], Set[str]]:
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
            if hasattr(assignment, "target") and assignment.target:
                if hasattr(assignment.target, "name"):
                    writes.add(assignment.target.name)
            if hasattr(assignment, "value") and assignment.value:
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

    elif isinstance(stmt, MKillStatement):
        # KILL removes variables
        # - K (no args) kills ALL locals - can't enumerate statically
        # - K X,Y kills specific variables
        # - K (X,Y) is exclusive kill (keep only X,Y) - can't enumerate others
        if not stmt.is_kill_all and not stmt.exclusive:
            # Selective kill: mark specific variables as "killed" (undefined after this)
            for target in stmt.targets:
                if hasattr(target, "name"):
                    name = target.name
                    # For variable analysis, treat KILL as making variable undefined
                    # This is similar to NEW in that subsequent reads see empty/undefined
                    # We track it as a "write" to empty (variable becomes undefined)
                    if name and not name.startswith("^"):
                        writes.add(name)

    elif isinstance(stmt, MForStatement):
        # FOR I=... writes the loop variable
        if stmt.loop_var:
            # loop_var may be a string or an MVariable
            if isinstance(stmt.loop_var, str):
                writes.add(stmt.loop_var)
            elif isinstance(stmt.loop_var, MVariable):
                name = stmt.loop_var.name
                if not name.startswith("^") and not name.startswith("$"):
                    writes.add(name)
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
    from ..asg.expressions import (
        MVariable,
        MBinaryOp,
        MUnaryOp,
        MLiteral,
        MIntrinsicFunction,
        MExtrinsicFunction,
        MSpecialVariable,
        MActualParameter,
    )

    # MVariable has a name
    if isinstance(expr, MVariable):
        name = expr.name
        # Exclude globals (^name) and special variables ($name)
        if name and not name.startswith("^") and not name.startswith("$"):
            vars_found.add(name)
        # Recursively check subscripts
        if hasattr(expr, "subscripts") and expr.subscripts:
            for sub in expr.subscripts:
                vars_found.update(_extract_expression_variables(sub))

    # MBinaryOp has left and right operands
    elif isinstance(expr, MBinaryOp):
        if hasattr(expr, "left") and expr.left:
            vars_found.update(_extract_expression_variables(expr.left))
        if hasattr(expr, "right") and expr.right:
            vars_found.update(_extract_expression_variables(expr.right))

    # MUnaryOp has operand
    elif isinstance(expr, MUnaryOp):
        if hasattr(expr, "operand") and expr.operand:
            vars_found.update(_extract_expression_variables(expr.operand))

    # MLiteral - no variable references
    elif isinstance(expr, MLiteral):
        pass

    # MIntrinsicFunction - extract variables from arguments only, not the function name
    elif isinstance(expr, MIntrinsicFunction):
        # Arguments are extracted below via the 'args' attribute handling
        pass

    # MExtrinsicFunction - extract variables from arguments only
    elif isinstance(expr, MExtrinsicFunction):
        # Arguments are extracted below via the 'args' attribute handling
        pass

    # MSpecialVariable - no variable references (these are $TEST, $HOROLOG, etc.)
    elif isinstance(expr, MSpecialVariable):
        pass

    # MActualParameter - extract variables from the expression field
    elif isinstance(expr, MActualParameter):
        if expr.expression:
            vars_found.update(_extract_expression_variables(expr.expression))

    # Fallback: check generic attributes
    elif hasattr(expr, "name") and isinstance(getattr(expr, "name", None), str):
        name = expr.name
        if name and not name.startswith("^") and not name.startswith("$"):
            vars_found.add(name)

    # Check for nested expressions in lists
    # Note: FunctionArgs is an object with an 'args' list attribute, not a list itself
    # Use isinstance checks for type-safe access
    if isinstance(expr, (MIntrinsicFunction, MExtrinsicFunction)):
        args = getattr(expr, "args", None)
        if args is not None:
            # Handle FunctionArgs object which has an inner 'args' list
            if hasattr(args, "args"):
                args = args.args
            if isinstance(args, list):
                for arg in args:
                    vars_found.update(_extract_expression_variables(arg))

    # Check for arguments attribute on MCall-like objects
    if hasattr(expr, "arguments"):
        arguments = getattr(expr, "arguments", None)
        if isinstance(arguments, list):
            for arg in arguments:
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
            chains[var].append((line, "def"))

        for var in reads:
            if var not in chains:
                chains[var] = []
            chains[var].append((line, "use"))

    return chains


def compute_transitive_inputs(
    routine: MRoutine, label_vars: Dict[str, ScopeVariables]
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
        name: set(vars.input_variables) for name, vars in label_vars.items()
    }

    # Fixed-point iteration
    changed = True
    while changed:
        changed = False
        for label_name, callees in call_graph.items():
            current = transitive_inputs.get(label_name, set())
            for callee in callees:
                callee_inputs = transitive_inputs.get(callee, set())
                # Add callee inputs that aren't provided by caller's writes
                caller_writes = label_vars.get(label_name, ScopeVariables()).writes
                new_inputs = callee_inputs - caller_writes
                if new_inputs - current:
                    current.update(new_inputs)
                    transitive_inputs[label_name] = current
                    changed = True

    return transitive_inputs


# =============================================================================
# Function Signature Computation
# =============================================================================


def analyze_quit_statements(label: MLabel) -> Tuple[bool, bool, Optional[Any]]:
    """Analyze QUIT statements in a label to determine return behavior.

    Per MUMPS spec, extrinsic functions must return a value via QUIT,
    while subroutines have void QUIT or fall through.

    Args:
        label: The MLabel to analyze

    Returns:
        Tuple of (has_value_quit, has_void_quit, first_return_expr)
    """
    has_value_quit = False
    has_void_quit = False
    first_return_expr = None

    for stmt in label.body.walk_statements():
        if isinstance(stmt, MQuitStatement):
            if stmt.return_value is not None:
                has_value_quit = True
                if first_return_expr is None:
                    first_return_expr = stmt.return_value
            else:
                has_void_quit = True

    return has_value_quit, has_void_quit, first_return_expr


def check_requires_runtime_scope(label: MLabel) -> bool:
    """Check if a label requires runtime scope (static analysis insufficient).

    Returns True if the label contains:
    - XECUTE command (executes arbitrary code)
    - Name indirection (@VAR for variable access)
    - Argument indirection (D @VAR, G @VAR)

    These patterns defeat static analysis because the affected variables
    cannot be determined until runtime.

    Args:
        label: The MLabel to analyze

    Returns:
        True if runtime scope is required
    """

    for stmt in label.body.walk_statements():
        # XECUTE defeats static analysis
        if isinstance(stmt, MXecuteStatement):
            return True

        # Check for indirection in DO targets
        if isinstance(stmt, MDoStatement):
            for target in stmt.targets:
                if target.label_is_indirect or target.routine_is_indirect:
                    return True

        # Check for indirection in expressions (name indirection)
        # This is a simplified check - a full check would walk all expressions
        if hasattr(stmt, "targets"):
            for target in getattr(stmt, "targets", []):
                if hasattr(target, "indirection") and target.indirection:
                    return True

    return False


def compute_function_signature(
    label: MLabel, scope_vars: ScopeVariables
) -> FunctionSignature:
    """Compute a clean function signature for a label.

    Combines formal parameters, variable analysis, and QUIT analysis
    to determine the label's interface for Python code generation.

    This function detects by-ref outputs by checking which formal parameters
    are written to within the label's scope. Per MUMPS spec (MDC 8.1.14),
    when a caller passes a variable by reference (.actualname), any writes
    to the formal parameter in the callee modify the caller's variable.

    Args:
        label: The MLabel to compute signature for
        scope_vars: Pre-computed ScopeVariables for the label

    Returns:
        FunctionSignature describing the label's interface

    Example:
        For SWAP(X,Y) with body "N T S T=X,X=Y,Y=T Q", both X and Y are
        written (scope_vars.writes contains X and Y), so byref_outputs = {X, Y}.
        A caller using D SWAP(.A,.B) will have A and B modified.
    """
    sig = FunctionSignature()
    sig.label_name = label.name
    sig.formal_params = list(label.formal_list) if label.formal_list else []

    # Required inputs: input_variables not in formal_params
    # These must be provided by the caller through some mechanism
    formal_set = set(sig.formal_params)
    sig.required_inputs = scope_vars.input_variables - formal_set

    # Side effect outputs: output_variables (visible to caller)
    sig.side_effect_outputs = set(scope_vars.output_variables)

    # Detect formal params that are written (potential by-ref outputs)
    # If a formal parameter is written within the label, and the caller
    # passes a variable by reference, that caller variable gets modified
    for formal_param in sig.formal_params:
        if formal_param in scope_vars.writes:
            sig.byref_outputs.add(formal_param)

    # Analyze QUIT statements
    has_value, has_void, return_expr = analyze_quit_statements(label)
    sig.has_value_quit = has_value
    sig.has_void_quit = has_void
    sig.return_value = return_expr

    # Check if runtime scope is required
    sig.requires_runtime_scope = check_requires_runtime_scope(label)

    # Classify scope strategy
    sig.scope_strategy = classify_scope_strategy(sig)

    return sig


def classify_scope_strategy(sig: FunctionSignature) -> ScopeStrategy:
    """Classify the code generation strategy for a function signature.

    Args:
        sig: The FunctionSignature to classify

    Returns:
        ScopeStrategy enum value
    """
    # If runtime scope required, that takes precedence
    if sig.requires_runtime_scope:
        return ScopeStrategy.REQUIRES_RUNTIME

    # If has return value
    if sig.has_value_quit:
        # If also has by-ref outputs, it's a function with outputs
        if sig.byref_outputs:
            return ScopeStrategy.FUNCTION_WITH_OUTPUTS
        # If no required inputs from caller scope (all via formal params), pure function
        if not sig.required_inputs and not sig.side_effect_outputs:
            return ScopeStrategy.PURE_FUNCTION
        # Has return but also side effects - function with outputs
        if sig.side_effect_outputs or sig.required_inputs:
            return ScopeStrategy.FUNCTION_WITH_OUTPUTS
        return ScopeStrategy.PURE_FUNCTION

    # No return value - it's a subroutine
    return ScopeStrategy.SUBROUTINE


def compute_all_signatures(routine: MRoutine) -> Dict[str, FunctionSignature]:
    """Compute function signatures for all labels in a routine.

    This is the main entry point for signature computation. It:
    1. Runs variable analysis if not already done
    2. Computes signatures for each label
    3. Populates MLabel.signature fields
    4. Sets MRoutine.requires_runtime_eval if any label requires runtime scope

    Args:
        routine: The MRoutine to analyze

    Returns:
        Dictionary mapping label names to FunctionSignatures
    """
    # First, ensure variable analysis is done
    label_vars = analyze_variables(routine)

    # Compute signatures
    signatures = {}
    for label in routine.labels:
        scope_vars = label_vars.get(label.name, ScopeVariables())
        sig = compute_function_signature(label, scope_vars)
        signatures[label.name] = sig

        # Store on label for easy access
        if not hasattr(label, "signature"):
            object.__setattr__(label, "signature", sig)
        else:
            label.signature = sig

    # Roll up requires_runtime_scope from labels to routine
    # If ANY label requires runtime scope, the routine does too
    routine.requires_runtime_eval = any(
        sig.requires_runtime_scope for sig in signatures.values()
    )

    return signatures


def bind_parameters(call: MCall, target_label: MLabel) -> List[ParameterBinding]:
    """Link actual parameters at a call site to formal parameters.

    Creates ParameterBinding objects that track:
    - Which formal gets which actual
    - Whether passed by value or reference
    - For by-ref, the caller's variable name

    Per MDC 8.1.14 (Parameter Passing):
    - Step 1: Evaluate actual parameters left to right
    - Step 2a: For .actualname (by-ref), establish alias
    - Step 2b: For expr (by-value), NEW formal and SET formal=expr
    - Step 2c: For omitted, NEW formal (empty DATA-CELL)
    - The number of actuals must be <= number of formals

    Args:
        call: The MCall representing the call site
        target_label: The target MLabel being called

    Returns:
        List of ParameterBinding objects
    """
    from ..asg.expressions import MVariable, MActualParameter

    bindings = []
    formal_list = target_label.formal_list if target_label.formal_list else []
    arguments = call.arguments if call.arguments else []

    for i, formal_name in enumerate(formal_list):
        binding = ParameterBinding(formal_name=formal_name)

        if i < len(arguments):
            arg = arguments[i]

            # Check if it's an MActualParameter with passing mode
            if isinstance(arg, MActualParameter):
                binding.actual_expr = arg.expression
                binding.passing_mode = arg.passing_mode
                binding.caller_var_name = arg.variable_name
            # Check if it's a plain variable (could be by-ref if detected earlier)
            elif isinstance(arg, MVariable):
                binding.actual_expr = arg
                binding.passing_mode = PassingMode.BY_VALUE
                binding.caller_var_name = arg.name
            elif arg is None:
                # Omitted parameter
                binding.passing_mode = PassingMode.OMITTED
            else:
                # Expression - by value
                binding.actual_expr = arg
                binding.passing_mode = PassingMode.BY_VALUE
        else:
            # Fewer actuals than formals - treat as omitted
            binding.passing_mode = PassingMode.OMITTED

        bindings.append(binding)

    return bindings


def compute_transitive_outputs(
    routine: MRoutine,
    label_vars: Dict[str, ScopeVariables],
    signatures: Dict[str, FunctionSignature],
) -> Dict[str, Set[str]]:
    """Compute transitive closure of output variables through call chains.

    When label A calls label B with by-ref parameter .X bound to formal Y,
    and B modifies Y, then X is in A's transitive outputs.

    Args:
        routine: The MRoutine being analyzed
        label_vars: Result of analyze_variables()
        signatures: Result of compute_all_signatures()

    Returns:
        Dictionary mapping label names to transitive output variable sets
    """
    # Build call graph with parameter info
    call_info = {}  # label_name -> [(callee_name, call_obj)]
    for label in routine.labels:
        calls = []
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MDoStatement):
                for target in stmt.targets:
                    if target.name and not target.routine:  # Local call
                        calls.append((target.name, target))
        call_info[label.name] = calls

    # Initialize with direct outputs
    transitive_outputs = {
        name: set(vars.output_variables) for name, vars in label_vars.items()
    }

    # Fixed-point iteration for by-ref propagation
    changed = True
    iterations = 0
    max_iterations = 100  # Prevent infinite loops

    while changed and iterations < max_iterations:
        changed = False
        iterations += 1

        for label_name, calls in call_info.items():
            current = transitive_outputs.get(label_name, set())

            for callee_name, call_obj in calls:
                callee_label = routine.get_label(callee_name)
                if not callee_label:
                    continue

                # Get parameter bindings
                bindings = bind_parameters(call_obj, callee_label)

                # For each by-ref parameter, if callee modifies formal,
                # add caller's actual to outputs
                callee_vars = label_vars.get(callee_name, ScopeVariables())
                callee_trans = transitive_outputs.get(callee_name, set())

                for binding in bindings:
                    if binding.passing_mode == PassingMode.BY_REFERENCE:
                        # If callee writes to this formal (directly or transitively),
                        # caller's var is affected. Check both direct writes and
                        # transitive outputs (for nested call chains).
                        formal_is_modified = (
                            binding.formal_name in callee_vars.writes
                            or binding.formal_name in callee_trans
                        )
                        if formal_is_modified:
                            if (
                                binding.caller_var_name
                                and binding.caller_var_name not in current
                            ):
                                current.add(binding.caller_var_name)
                                changed = True

            transitive_outputs[label_name] = current

    return transitive_outputs
