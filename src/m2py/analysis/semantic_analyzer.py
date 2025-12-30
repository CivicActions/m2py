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

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from m2py.asg.expressions import (
    MExpr,
    MLiteral,
    MVariable,
    MGlobal,
    MIntrinsicFunction,
    MExtrinsicFunction,
    MIndirection,
    MBinaryOp,
    MUnaryOp,
    MFormatControl,
    MPatternMatch,
    MActualParameter,
)
from m2py.asg.statements import (
    MStatement,
    MSetStatement,
    MAssignment,
    MWriteStatement,
    MReadStatement,
    MReadTarget,
    MIfStatement,
    MElseStatement,
    MForStatement,
    MForParameter,
    MGotoStatement,
    MDoStatement,
    MQuitStatement,
    MNewStatement,
    MKillStatement,
    MHangStatement,
    MHaltStatement,
    MBreakStatement,
    MXecuteStatement,
    MLockStatement,
    MMergeStatement,
    MMergePair,
    MOpenStatement,
    MOpenDevice,
    MCloseStatement,
    MCloseDevice,
    MUseStatement,
    MUseDevice,
    MJobStatement,
    MViewStatement,
)
from m2py.asg.elements import MCall
from m2py.asg.enums import (
    LiteralType,
    ForLoopType,
    ForParamType,
    FormatControlType,
    IndirectionType,
    PassingMode,
)
from m2py.analysis.pattern_compiler import compile_pattern_to_regex, PatternCompileError


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
    subscript_patterns: List[int] = field(
        default_factory=list
    )  # Number of subscripts seen


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
        handler = getattr(self, f"_analyze_{cls_name}", None)
        if handler:
            return handler(model, parent)

        # Check if it's already an ASG type (from custom classes)
        if isinstance(model, MExpr):
            return self._analyze_expression(model, parent)

        # Fallback for unhandled textX dynamic objects: try to unwrap common
        # patterns (operand, expr, unary_expr). This handles edge cases where
        # grammar rules produce wrapper objects without explicit handlers.
        return self._analyze_generic(model, parent)

    def _analyze_expression(self, expr: MExpr, parent: Any) -> MExpr:
        """Set parent on an already-converted expression and recurse."""
        # Set parent reference
        object.__setattr__(expr, "parent", parent)

        # Handle specific expression types
        if isinstance(expr, MVariable):
            self._track_variable(expr.name, expr, is_read=True)
            # Analyze subscripts
            new_subscripts = []
            for sub in expr.subscripts:
                new_subscripts.append(self.analyze(sub, expr))
            object.__setattr__(expr, "subscripts", new_subscripts)

        elif isinstance(expr, MGlobal):
            self._track_global(expr.name, expr)
            new_subscripts = []
            for sub in expr.subscripts:
                new_subscripts.append(self.analyze(sub, expr))
            object.__setattr__(expr, "subscripts", new_subscripts)

        elif isinstance(expr, MIntrinsicFunction):
            new_args = []
            for arg in expr.arguments:
                new_args.append(self.analyze(arg, expr))
            object.__setattr__(expr, "arguments", new_args)

        elif isinstance(expr, MExtrinsicFunction):
            new_args = []
            for arg in expr.arguments:
                new_args.append(self.analyze(arg, expr))
            object.__setattr__(expr, "arguments", new_args)
            if expr.target:
                self._track_label_call(expr.target.name, expr.target.routine)

        elif isinstance(expr, MBinaryOp):
            object.__setattr__(expr, "left", self.analyze(expr.left, expr))
            object.__setattr__(expr, "right", self.analyze(expr.right, expr))

        elif isinstance(expr, MUnaryOp):
            object.__setattr__(expr, "operand", self.analyze(expr.operand, expr))

        elif isinstance(expr, MIndirection):
            object.__setattr__(expr, "expression", self.analyze(expr.expression, expr))
            # Analyze direct subscripts for @X(1,2) form
            if expr.subscripts:
                new_subs = [self.analyze(s, expr) for s in expr.subscripts]
                object.__setattr__(expr, "subscripts", new_subs)
            # Analyze name indirection subscripts for @X@(1,2) form
            if expr.name_indirection_subscripts:
                new_name_subs = [
                    [self.analyze(s, expr) for s in sub_list]
                    for sub_list in expr.name_indirection_subscripts
                ]
                object.__setattr__(expr, "name_indirection_subscripts", new_name_subs)
            # Classify indirection type based on context
            self._classify_indirection(expr, parent)

        return expr

    def _analyze_function_arg(self, arg: Any, parent: Any) -> MActualParameter:
        """Analyze a FunctionArg into an MActualParameter.

        Handles three cases:
        1. By-reference: .VAR passes variable by reference
        2. By-value: Expression is evaluated and passed by value
        3. Omitted: Empty parameter position (nothing between commas)

        Args:
            arg: A FunctionArg textX object with byref or expr attributes
            parent: Parent ASG node for setting parent reference

        Returns:
            MActualParameter with appropriate passing mode
        """
        # Check for by-reference argument: .VAR
        if hasattr(arg, "byref") and arg.byref:
            byref = arg.byref
            var = byref.var
            # Get variable name and subscripts
            var_name = var.name
            # Analyze the variable as an expression to track it
            var_expr = self.analyze(var, parent)
            return MActualParameter(
                passing_mode=PassingMode.BY_REFERENCE,
                expression=var_expr,
                variable_name=var_name,
            )

        # Check for by-value argument: expression
        if hasattr(arg, "expr") and arg.expr:
            expr = self.analyze(arg.expr, parent)
            return MActualParameter(
                passing_mode=PassingMode.BY_VALUE,
                expression=expr,
                variable_name=None,
            )

        # Omitted argument (empty between commas)
        return MActualParameter(
            passing_mode=PassingMode.OMITTED,
            expression=None,
            variable_name=None,
        )

    def _analyze_function_args(
        self, args_obj: Any, parent: Any
    ) -> list[MActualParameter]:
        """Analyze FunctionArgs into a list of MActualParameter nodes.

        Args:
            args_obj: A FunctionArgs textX object with args list
            parent: Parent ASG node

        Returns:
            List of MActualParameter nodes
        """
        if not args_obj or not hasattr(args_obj, "args") or not args_obj.args:
            return []
        return [self._analyze_function_arg(a, parent) for a in args_obj.args]

    def _classify_indirection(self, indirection: MIndirection, parent: Any) -> None:
        """Classify indirection type and attempt static resolution.

        Context-based classification:
        - In pattern match context: PATTERN
        - In subscript context: SUBSCRIPT
        - In DO/GOTO context: ARGUMENT (handled separately in call analysis)
        - Otherwise: NAME (variable indirection)

        Static resolution is attempted for constant string expressions.
        """
        # Default to NAME unless we can determine otherwise
        if indirection.indirection_type == IndirectionType.UNKNOWN:
            object.__setattr__(indirection, "indirection_type", IndirectionType.NAME)

        # Try static resolution for constant string expressions
        inner_expr = indirection.expression
        if (
            isinstance(inner_expr, MLiteral)
            and inner_expr.literal_type == LiteralType.STRING
        ):
            object.__setattr__(indirection, "can_resolve_statically", True)
            object.__setattr__(indirection, "resolved_value", inner_expr.value)

    def _analyze_UnaryExpr(self, unary: Any, parent: Any) -> MExpr:
        """Unwrap UnaryExpr to get the underlying expression.

        UnaryExpr: operators*=UnaryOp operand=PrimaryExpr

        If there are no operators, just return the operand.
        If there are operators, create nested MUnaryOp nodes (innermost first).
        Example: --X becomes MUnaryOp('-', MUnaryOp('-', X))
        """
        operand = self.analyze(unary.operand, parent)

        # Handle chained unary operators (grammar uses 'operators' list)
        operators = []
        if hasattr(unary, "operators") and unary.operators:
            operators = list(unary.operators)

        if operators:
            # Apply operators from right to left (innermost first)
            # E.g., --X means -(-(X)), so we apply inner - first
            result = operand
            for op_obj in reversed(operators):
                op = MUnaryOp()
                op_str = op_obj.op if hasattr(op_obj, "op") else str(op_obj)
                object.__setattr__(op, "operator", op_str)
                object.__setattr__(op, "operand", result)
                object.__setattr__(op, "parent", parent)
                # Update child's parent
                object.__setattr__(result, "parent", op)
                result = op
            return result

        return operand

    def _analyze_Expr(self, expr: Any, parent: Any) -> MExpr:
        """Unwrap Expr and build binary operation tree if needed.

        Grammar structure:
            Expr: left=UnaryExpr (tail+=ExprTail)*

        Where ExprTail is either:
        - PatternMatchTail: op=PatternMatchOp pattern=PatternSpec
        - BinaryOpTail: op=BinaryOp right=UnaryExpr

        Note: textX's PEG parser can misparse expressions like "1-2-3" when
        operators like +/- can also be unary. The handler compensates by
        treating unary +/- on subsequent operands as binary operators.
        """
        if hasattr(expr, "left"):
            result = self.analyze(expr.left, parent)

            # Handle tail-based structure (ExprTail list)
            if hasattr(expr, "tail") and expr.tail:
                for tail_item in expr.tail:
                    tail_type = type(tail_item).__name__

                    # Check for pattern match: either by type name or having pattern/indirect_expr
                    is_pattern_match = (
                        tail_type == "PatternMatchTail"
                        or (hasattr(tail_item, "pattern") and tail_item.pattern)
                        or (
                            hasattr(tail_item, "indirect_expr")
                            and tail_item.indirect_expr
                        )
                    )

                    if is_pattern_match:
                        # Pattern match: create MPatternMatch node
                        op = tail_item.op
                        op_str = op.op if hasattr(op, "op") else str(op)

                        pattern_match = MPatternMatch()
                        object.__setattr__(pattern_match, "operator", op_str)
                        object.__setattr__(pattern_match, "subject", result)

                        # Handle indirect patterns (e.g., X?@PAT) vs literal patterns (e.g., X?3N)
                        if (
                            hasattr(tail_item, "indirect_expr")
                            and tail_item.indirect_expr
                        ):
                            # Indirect pattern: store the expression, leave pattern empty
                            indirect_analyzed = self.analyze(
                                tail_item.indirect_expr, pattern_match
                            )
                            object.__setattr__(
                                pattern_match, "pattern_indirect", indirect_analyzed
                            )
                            object.__setattr__(pattern_match, "pattern", "")
                            # compiled_regex stays None for indirect patterns (runtime evaluation)
                        else:
                            # Literal pattern: store the pattern string
                            pattern_str = self._pattern_to_string(tail_item.pattern)
                            object.__setattr__(pattern_match, "pattern", pattern_str)

                            # Pre-compile pattern to regex for code generation
                            if pattern_str:
                                try:
                                    compiled = compile_pattern_to_regex(pattern_str)
                                    object.__setattr__(
                                        pattern_match, "compiled_regex", compiled
                                    )
                                except PatternCompileError:
                                    pass  # Leave compiled_regex as None for complex patterns

                        object.__setattr__(pattern_match, "parent", parent)
                        object.__setattr__(result, "parent", pattern_match)
                        result = pattern_match

                    elif tail_type == "BinaryOpTail" or (
                        hasattr(tail_item, "right") and tail_item.right
                    ):
                        # Regular binary operation
                        op = tail_item.op
                        op_str = op.op if hasattr(op, "op") else str(op)

                        binary = MBinaryOp()
                        object.__setattr__(binary, "operator", op_str)
                        object.__setattr__(binary, "left", result)

                        right = self.analyze(tail_item.right, binary)
                        object.__setattr__(binary, "right", right)

                        object.__setattr__(binary, "parent", parent)
                        object.__setattr__(result, "parent", binary)
                        result = binary

                return result

            return result

        # Fallback for simple expressions: When Expr has no tail operators,
        # it's equivalent to UnaryExpr. Process via generic analysis which
        # handles UnaryExpr unwrapping.
        return self._analyze_generic(expr, parent)

    def _pattern_to_string(self, pattern_spec: Any) -> str:
        """Convert a textX PatternSpec to a pattern string.

        PatternSpec has atoms, each with repcount and (patcode or strlit or alternation).
        """
        if pattern_spec is None:
            return ""

        parts = []
        if hasattr(pattern_spec, "atoms") and pattern_spec.atoms:
            for atom in pattern_spec.atoms:
                part = self._pattern_atom_to_string(atom)
                parts.append(part)

        return "".join(parts)

    def _pattern_atom_to_string(self, atom: Any) -> str:
        """Convert a single pattern atom to string."""
        result = ""

        # Add repcount
        if hasattr(atom, "repcount") and atom.repcount:
            rc = atom.repcount
            # Check class name to distinguish range from exact
            rc_type = type(rc).__name__
            if rc_type == "RangeRepCount":
                # Range form: min.max, .max, min., or just .
                min_val = str(rc.min) if hasattr(rc, "min") and rc.min else ""
                max_val = str(rc.max) if hasattr(rc, "max") and rc.max else ""
                result += f"{min_val}.{max_val}"
            elif rc_type == "ExactRepCount":
                # Exact form: just the number
                result += str(rc.exact)
            elif hasattr(rc, "exact") and rc.exact is not None:
                # Fallback for textX dynamic objects: check for exact attribute
                # when class name doesn't match expected patterns
                result += str(rc.exact)

        # Add patcode or strlit or alternation
        if hasattr(atom, "patcode") and atom.patcode:
            result += (
                atom.patcode.codes
                if hasattr(atom.patcode, "codes")
                else str(atom.patcode)
            )
        elif hasattr(atom, "strlit") and atom.strlit:
            result += atom.strlit
        elif hasattr(atom, "alternation") and atom.alternation:
            alt_parts = [self._pattern_atom_to_string(a) for a in atom.alternation]
            result += "(" + ",".join(alt_parts) + ")"

        return result

    # OffsetExpr has the same structure as Expr, just excludes GlobalVariable
    _analyze_OffsetExpr = _analyze_Expr

    # OffsetUnaryExpr has the same structure as UnaryExpr
    _analyze_OffsetUnaryExpr = _analyze_UnaryExpr

    def _analyze_SubscriptedGlobal(self, model: Any, parent: Any) -> MGlobal:
        """Convert SubscriptedGlobal textX object to MGlobal ASG node.

        SubscriptedGlobal is used in offset expressions (OffsetPrimaryExpr)
        to distinguish ^NAME(subscripts) from routine names. It has the same
        structure as GlobalVariable but is a separate grammar rule.

        Grammar: SubscriptedGlobal: '^' name=VARNAME subscripts=Subscripts;
        """
        result = MGlobal()
        object.__setattr__(result, "parent", parent)
        object.__setattr__(result, "name", model.name)

        # Convert subscripts
        subscripts = []
        if hasattr(model, "subscripts") and model.subscripts:
            if hasattr(model.subscripts, "args"):
                for sub in model.subscripts.args:
                    subscripts.append(self.analyze(sub, result))
        object.__setattr__(result, "subscripts", subscripts)

        self._track_global(model.name, result)
        return result

    def _analyze_generic(self, model: Any, parent: Any) -> Any:
        """Generic handler for unknown textX types.

        Tries common patterns for unwrapping textX wrapper nodes.
        """
        # If it has 'operand', likely a UnaryExpr wrapper
        if hasattr(model, "operand"):
            return self.analyze(model.operand, parent)

        # If it has 'expr', likely a ParenExpr wrapper
        if hasattr(model, "expr"):
            return self.analyze(model.expr, parent)

        # Can't unwrap, return as-is with parent set if possible
        if hasattr(model, "__setattr__"):
            try:
                object.__setattr__(model, "parent", parent)
            except (TypeError, AttributeError):
                pass

        return model

    # =========================================================================
    # Format Control Analysis (textX FormatControl → MFormatControl)
    # =========================================================================

    def _analyze_Newline(self, node: Any, parent: Any) -> MFormatControl:
        """Analyze ! (newline) format control."""
        fc = MFormatControl()
        object.__setattr__(fc, "parent", parent)
        object.__setattr__(fc, "control_type", FormatControlType.NEWLINE)
        return fc

    def _analyze_FormFeed(self, node: Any, parent: Any) -> MFormatControl:
        """Analyze # (formfeed) format control."""
        fc = MFormatControl()
        object.__setattr__(fc, "parent", parent)
        object.__setattr__(fc, "control_type", FormatControlType.FORMFEED)
        return fc

    def _analyze_Tab(self, node: Any, parent: Any) -> MFormatControl:
        """Analyze ?n (tab to column) format control."""
        fc = MFormatControl()
        object.__setattr__(fc, "parent", parent)
        object.__setattr__(fc, "control_type", FormatControlType.TAB)
        if hasattr(node, "expr") and node.expr:
            object.__setattr__(fc, "expression", self.analyze(node.expr, fc))
        return fc

    def _analyze_CharCode(self, node: Any, parent: Any) -> MFormatControl:
        """Analyze *n (output character code) format control."""
        fc = MFormatControl()
        object.__setattr__(fc, "parent", parent)
        object.__setattr__(fc, "control_type", FormatControlType.CHARCODE)
        if hasattr(node, "expr") and node.expr:
            object.__setattr__(fc, "expression", self.analyze(node.expr, fc))
        return fc

    # =========================================================================
    # Command Analysis Methods (textX Command → ASG Statement)
    # =========================================================================

    def _analyze_SetCommand(self, cmd: Any, parent: Any) -> MSetStatement:
        """Analyze SET command into MSetStatement."""
        stmt = MSetStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "assignments") and cmd.assignments:
            for assign in cmd.assignments:
                # Handle targets
                if hasattr(assign, "targets") and assign.targets:
                    targets = assign.targets
                    if targets.__class__.__name__ == "ParenTargets":
                        # Multi-assignment: S (A,B,C)=value
                        # Expand into separate MAssignment objects, one per target
                        analyzed_value = None
                        if hasattr(assign, "value") and assign.value:
                            # Analyze value once (will be shared by all assignments)
                            analyzed_value = self.analyze(assign.value, stmt)

                        for t in targets.targets:
                            asg_assign = MAssignment()
                            asg_assign.target = self.analyze(t, asg_assign)
                            asg_assign.value = analyzed_value
                            # Track variables being set
                            if hasattr(t, "name"):
                                self._track_variable(t.name, t, is_set=True)
                            stmt.assignments.append(asg_assign)
                    else:
                        # Single target assignment
                        asg_assign = MAssignment()
                        asg_assign.target = self.analyze(targets, asg_assign)
                        if hasattr(targets, "name"):
                            self._track_variable(targets.name, targets, is_set=True)

                        if hasattr(assign, "value") and assign.value:
                            asg_assign.value = self.analyze(assign.value, asg_assign)

                        stmt.assignments.append(asg_assign)

        return stmt

    def _analyze_WriteCommand(self, cmd: Any, parent: Any) -> MWriteStatement:
        """Analyze WRITE command into MWriteStatement."""
        stmt = MWriteStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                if hasattr(arg, "arg") and arg.arg:
                    stmt.arguments.append(self.analyze(arg.arg, stmt))

        return stmt

    def _analyze_ReadCommand(self, cmd: Any, parent: Any) -> MReadStatement:
        """Analyze READ command into MReadStatement.

        READ arguments can be:
        - Format controls: !, #, ?n (output to device)
        - Prompts: "string" (output to device)
        - Targets: VAR or VAR:timeout (input from device)
        - CharRead: *VAR or *VAR:timeout (single character read)

        Grammar structure:
        ReadArg: /,/? postcond=Postcondition? arg=ReadArgValue
        ReadArgValue: ReadFormat | StringLiteral | ReadTargetWithTimeout
        ReadTargetWithTimeout: target=ReadTarget (':' timeout=Expr)?
        ReadTarget: CharRead | GlobalVariable | LocalVariable | Indirection
        CharRead: /\\*/ var=LocalVariable
        """
        stmt = MReadStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                # ReadArg grammar: /,/? postcond=Postcondition? arg=ReadArgValue
                arg_value = getattr(arg, "arg", arg)

                # Check what type of ReadArgValue this is
                arg_cls = arg_value.__class__.__name__

                # Handle ReadTargetWithTimeout (has target attribute)
                if hasattr(arg_value, "target") and arg_value.target:
                    target_node = arg_value.target
                    target_cls = target_node.__class__.__name__

                    # Check for CharRead (*VAR)
                    is_char_read = target_cls == "CharRead"

                    # Get the actual variable (unwrap CharRead if needed)
                    if is_char_read:
                        actual_var = self.analyze(target_node.var, stmt)
                        var_name = (
                            target_node.var.name
                            if hasattr(target_node.var, "name")
                            else None
                        )
                    else:
                        actual_var = self.analyze(target_node, stmt)
                        var_name = (
                            target_node.name if hasattr(target_node, "name") else None
                        )

                    # Get timeout if present
                    timeout_expr = None
                    if hasattr(arg_value, "timeout") and arg_value.timeout:
                        timeout_expr = self.analyze(arg_value.timeout, stmt)

                    # Get fixed_length if present (VAR#length syntax)
                    fixed_length_expr = None
                    if hasattr(arg_value, "fixed_length") and arg_value.fixed_length:
                        fixed_length_expr = self.analyze(arg_value.fixed_length, stmt)

                    # Create MReadTarget with all information
                    read_target = MReadTarget(
                        variable=actual_var,
                        is_char_read=is_char_read,
                        timeout=timeout_expr,
                        fixed_length=fixed_length_expr,
                    )
                    stmt.arguments.append(read_target)

                    # Track variable being set
                    if var_name:
                        self._track_variable(var_name, target_node, is_set=True)

                # Handle format controls (Newline, FormFeed, Tab, CharCode)
                elif arg_cls in ("Newline", "FormFeed", "Tab", "CharCode"):
                    fc = self.analyze(arg_value, stmt)
                    stmt.arguments.append(fc)
                # Handle StringLiteral (prompt)
                elif arg_cls == "StringLiteral" or isinstance(arg_value, MLiteral):
                    prompt_expr = self.analyze(arg_value, stmt)
                    stmt.arguments.append(prompt_expr)
                else:
                    # Unknown - try to analyze it
                    analyzed = self.analyze(arg_value, stmt)
                    if analyzed:
                        stmt.arguments.append(analyzed)

        return stmt

    def _analyze_IfCommand(self, cmd: Any, parent: Any) -> MIfStatement:
        """Analyze IF command into MIfStatement.

        MUMPS allows comma-separated conditions which act as AND:
        IF cond1,cond2 is equivalent to IF cond1 IF cond2
        """
        stmt = MIfStatement()
        object.__setattr__(stmt, "parent", parent)

        # Grammar: conditions+=Expr[/,/] (comma-separated AND conditions)
        if hasattr(cmd, "conditions") and cmd.conditions:
            analyzed_conditions = [
                self.analyze(c, stmt) for c in cmd.conditions if c is not None
            ]
            # Filter out any None results
            stmt.conditions = [c for c in analyzed_conditions if c is not None]
            # Convenience: also set single condition if only one
            if len(stmt.conditions) == 1:
                stmt.condition = stmt.conditions[0]

        return stmt

    def _analyze_ElseCommand(self, cmd: Any, parent: Any) -> MElseStatement:
        """Analyze ELSE command into MElseStatement."""
        stmt = MElseStatement()
        object.__setattr__(stmt, "parent", parent)
        return stmt

    def _analyze_ForCommand(self, cmd: Any, parent: Any) -> MForStatement:
        """Analyze FOR command into MForStatement."""
        stmt = MForStatement()
        object.__setattr__(stmt, "parent", parent)

        # Handle indirection in loop variable: FOR @A=1:1:10
        if hasattr(cmd, "indirect") and cmd.indirect:
            # Indirection in loop variable
            stmt.loop_var = self.analyze(cmd.indirect, stmt)
            stmt.loop_var_indirect = True
        elif hasattr(cmd, "var") and cmd.var:
            # Always convert to ASG node (MVariable or MGlobal)
            # For subscripted variables, analyze subscripts semantically
            if hasattr(cmd.var, "subscripts") and cmd.var.subscripts:
                stmt.loop_var = self._convert_loop_var_subscripts(cmd.var)
            else:
                # Simple variable - convert to ASG node (MVariable or MGlobal)
                stmt.loop_var = self._simple_var_to_asg(cmd.var)
            self._track_variable(cmd.var, cmd, is_set=True)

        if hasattr(cmd, "params") and cmd.params:
            for param in cmd.params:
                fp = MForParameter()

                if hasattr(param, "start") and param.start:
                    fp.start = self.analyze(param.start, fp)

                if hasattr(param, "step") and param.step:
                    fp.step = self.analyze(param.step, fp)
                    if hasattr(param, "end") and param.end:
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

        # Detect infinite loops: ARGUMENTLESS or step=0
        if stmt.loop_type == ForLoopType.ARGUMENTLESS:
            stmt.is_infinite = True
        else:
            # Check for step=0 in any parameter
            for fp in stmt.parameters:
                if fp.step is not None:
                    # Check if step is numeric literal 0
                    # Handle both MLiteral and NumericLiteral (textX) types
                    step_value = getattr(fp.step, "value", None)
                    if step_value == 0 or step_value == "0":
                        stmt.is_infinite = True
                        break

        return stmt

    def _simple_var_to_asg(self, var: Any) -> Any:
        """Convert a simple variable (no subscripts) to ASG form.

        Args:
            var: A LocalVariable, GlobalVariable, or string name

        Returns:
            MVariable or MGlobal ASG node
        """
        from ..asg.expressions import MVariable, MGlobal

        # Handle string names
        if isinstance(var, str):
            if var.startswith("^"):
                new_var = MGlobal()
                new_var.name = var.lstrip("^")
            else:
                new_var = MVariable()
                new_var.name = var
            return new_var

        # Handle variable objects
        var_name = var.name if hasattr(var, "name") else str(var)

        if var_name.startswith("^") or isinstance(var, MGlobal):
            new_var = MGlobal()
            new_var.name = (
                var_name.lstrip("^") if var_name.startswith("^") else var_name
            )
        else:
            new_var = MVariable()
            new_var.name = var_name

        return new_var

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
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                call = MCall()

                if hasattr(target, "postcond") and target.postcond:
                    call.postcondition = self.analyze(target.postcond.condition, call)

                # Handle indirection: G @VAR, G @@VAR, G @VAR+offset, G @VAR^@routine
                if hasattr(target, "indirect") and target.indirect:
                    indirect = target.indirect
                    call.name = ""  # Indirection target - no static name
                    call.label_is_indirect = True

                    # Process the IndirectChain for the label part
                    if hasattr(indirect, "labelIndirect") and indirect.labelIndirect:
                        indirection_expr, levels = self._analyze_indirect_chain(
                            indirect.labelIndirect, call
                        )
                        call.indirection = indirection_expr
                        call.indirection_levels = levels

                    # Process offset if present: @VAR+offset
                    if hasattr(indirect, "offset") and indirect.offset:
                        call.offset = self.analyze(indirect.offset, call)

                    # Process routine part: ^routine or ^@routine
                    if hasattr(indirect, "routine") and indirect.routine:
                        call.routine = indirect.routine
                    elif (
                        hasattr(indirect, "routineIndirect")
                        and indirect.routineIndirect
                    ):
                        routine_expr, _ = self._analyze_indirect_chain(
                            indirect.routineIndirect, call
                        )
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True

                elif hasattr(target, "label") and target.label:
                    label_ref = target.label
                    call.name = label_ref.label or ""

                    # Handle routine: either literal name or indirect (@VAR, @@VAR)
                    if hasattr(label_ref, "routine") and label_ref.routine:
                        call.routine = label_ref.routine
                    elif (
                        hasattr(label_ref, "routineIndirect")
                        and label_ref.routineIndirect
                    ):
                        routine_expr, _ = self._analyze_indirect_chain(
                            label_ref.routineIndirect, call
                        )
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True

                    if hasattr(label_ref, "offset") and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)

                    self._track_label_call(call.name, call.routine)

                stmt.targets.append(call)

        return stmt

    def _analyze_DoCommand(self, cmd: Any, parent: Any) -> MDoStatement:
        """Analyze DO command into MDoStatement."""
        stmt = MDoStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                call = MCall()

                if hasattr(target, "postcond") and target.postcond:
                    call.postcondition = self.analyze(target.postcond.condition, call)

                # Handle indirection: D @VAR, D @@VAR, D @VAR+offset, D @VAR^@routine
                if hasattr(target, "indirect") and target.indirect:
                    indirect = target.indirect
                    call.name = ""  # Indirection target - no static name
                    call.label_is_indirect = True

                    # Process the IndirectChain for the label part
                    if hasattr(indirect, "labelIndirect") and indirect.labelIndirect:
                        indirection_expr, levels = self._analyze_indirect_chain(
                            indirect.labelIndirect, call
                        )
                        call.indirection = indirection_expr
                        call.indirection_levels = levels

                    # Process offset if present: @VAR+offset
                    if hasattr(indirect, "offset") and indirect.offset:
                        call.offset = self.analyze(indirect.offset, call)

                    # Process routine part: ^routine or ^@routine
                    if hasattr(indirect, "routine") and indirect.routine:
                        call.routine = indirect.routine
                    elif (
                        hasattr(indirect, "routineIndirect")
                        and indirect.routineIndirect
                    ):
                        routine_expr, _ = self._analyze_indirect_chain(
                            indirect.routineIndirect, call
                        )
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True

                    # Process arguments if present
                    if hasattr(indirect, "args") and indirect.args:
                        call.arguments = self._analyze_function_args(
                            indirect.args, call
                        )

                elif hasattr(target, "label") and target.label:
                    label_ref = target.label
                    call.name = label_ref.label or ""

                    # Handle routine: either literal name or indirect (@VAR, @@VAR)
                    if hasattr(label_ref, "routine") and label_ref.routine:
                        call.routine = label_ref.routine
                    elif (
                        hasattr(label_ref, "routineIndirect")
                        and label_ref.routineIndirect
                    ):
                        routine_expr, _ = self._analyze_indirect_chain(
                            label_ref.routineIndirect, call
                        )
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True

                    if hasattr(label_ref, "offset") and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)

                    self._track_label_call(call.name, call.routine)

                if hasattr(target, "args") and target.args:
                    call.arguments = self._analyze_function_args(target.args, call)

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
        while hasattr(current, "nested") and current.nested:
            levels += 1
            current = current.nested

        # Now 'current' is the innermost IndirectChain - get its expression
        # Note: 'global' is a Python keyword, so we use getattr
        if hasattr(current, "var") and current.var:
            expr = self.analyze(current.var, parent)
        elif hasattr(current, "global") and getattr(current, "global", None):
            expr = self.analyze(getattr(current, "global"), parent)
        elif hasattr(current, "expr") and current.expr:
            expr = self.analyze(current.expr, parent)
        else:
            expr = None

        # If there were nested levels, wrap in MIndirection objects
        # to represent the structure: @@A becomes Indirection(Indirection(var=A))
        for _ in range(levels - 1):
            inner = MIndirection(expression=expr, indirection_type=IndirectionType.NAME)
            expr = inner

        return expr, levels

    def _analyze_QuitCommand(self, cmd: Any, parent: Any) -> MQuitStatement:
        """Analyze QUIT command into MQuitStatement."""
        stmt = MQuitStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "value") and cmd.value:
            stmt.return_value = self.analyze(cmd.value, stmt)

        return stmt

    def _analyze_NewCommand(self, cmd: Any, parent: Any) -> MNewStatement:
        """Analyze NEW command into MNewStatement."""
        stmt = MNewStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "exclusive") and cmd.exclusive:
            stmt.exclusive = True
            exc = cmd.exclusive
            except_list = getattr(exc, "except", None) or getattr(exc, "except_", None)
            if except_list:
                stmt.except_list = list(except_list)
        elif hasattr(cmd, "vars") and cmd.vars:
            for v in cmd.vars:
                var_name = v.name if hasattr(v, "name") else str(v)
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
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Grammar: args is a list of KillArgument
        if hasattr(cmd, "args") and cmd.args:
            exclusive_groups = []
            selective_targets = []

            for arg in cmd.args:
                # Check if this is an exclusive group (has 'exclusive' flag and 'except' list)
                if hasattr(arg, "exclusive") and arg.exclusive:
                    # This is an exclusive group: (X,Y,Z)
                    except_list = getattr(arg, "except", None) or getattr(
                        arg, "except_", None
                    )
                    if except_list:
                        exclusive_groups.append(list(except_list))
                elif hasattr(arg, "target") and arg.target:
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

        return stmt

    def _analyze_HangCommand(self, cmd: Any, parent: Any) -> MHangStatement:
        """Analyze HANG command into MHangStatement."""
        stmt = MHangStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "seconds") and cmd.seconds:
            stmt.duration = self.analyze(cmd.seconds, stmt)

        return stmt

    def _analyze_HaltCommand(self, cmd: Any, parent: Any) -> MHaltStatement:
        """Analyze HALT command into MHaltStatement."""
        stmt = MHaltStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        return stmt

    def _analyze_BreakCommand(self, cmd: Any, parent: Any) -> MBreakStatement:
        """Analyze BREAK command into MBreakStatement."""
        stmt = MBreakStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        return stmt

    def _analyze_XecuteCommand(self, cmd: Any, parent: Any) -> MXecuteStatement:
        """Analyze XECUTE command into MXecuteStatement."""
        stmt = MXecuteStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                if hasattr(arg, "expr") and arg.expr:
                    stmt.code_expressions.append(self.analyze(arg.expr, stmt))
                else:
                    stmt.code_expressions.append(self.analyze(arg, stmt))

        # Check if all code expressions are constant string literals
        all_constant = True
        constant_values = []
        for expr in stmt.code_expressions:
            if isinstance(expr, MLiteral) and expr.literal_type == LiteralType.STRING:
                constant_values.append(expr.value)
            else:
                all_constant = False
                break

        if all_constant and constant_values:
            object.__setattr__(stmt, "is_constant", True)
            object.__setattr__(stmt, "constant_values", constant_values)

        return stmt

    def _analyze_LockCommand(self, cmd: Any, parent: Any) -> MLockStatement:
        """Analyze LOCK command into MLockStatement.

        Handles:
        - L (no args) - unlock all
        - L ^A - lock single target
        - L ^A:1 - lock with timeout
        - L ^A,^B - lock multiple targets
        - L (^A,^B):1 - parenthesized list with shared timeout
        - L @A - lock with indirection (name resolved at runtime)
        - L @A:1 - indirection with timeout
        - L +^A / L -^A - incremental lock/unlock
        """
        stmt = MLockStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "lockop") and cmd.lockop:
            stmt.lock_type = str(cmd.lockop)

        # Handle parenthesized lock list: L (^A,^B):timeout or L (@A,^B):timeout
        if hasattr(cmd, "locklist") and cmd.locklist:
            locklist = cmd.locklist
            if hasattr(locklist, "targets") and locklist.targets:
                for item in locklist.targets:
                    lock_info = self._analyze_lock_item(item, stmt)
                    stmt.targets.append(lock_info)
            if hasattr(locklist, "timeout") and locklist.timeout:
                stmt.timeout = self.analyze(locklist.timeout, stmt)

        # Handle regular target list: L ^A:1,^B:2 or L @A:1,^B:2
        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                lock_info = self._analyze_lock_target(target, stmt)
                stmt.targets.append(lock_info)

        return stmt

    def _analyze_lock_item(self, item: Any, parent: Any) -> dict:
        """Analyze a single item in a parenthesized lock list.

        LockListItem grammar produces both indirect and target attributes
        (one will be None, the other populated based on input syntax):
        - indirect: IndirectChain (e.g., @A, @@A, @(expr))
        - target: VarRef (e.g., ^A, X, ^A(1,2))
        """
        lock_info = {}

        # Handle indirection: @A, @@A, @(expr)
        if item.indirect:
            indirection_expr, levels = self._analyze_indirect_chain(
                item.indirect, parent
            )
            lock_info["indirection"] = indirection_expr
            lock_info["indirection_levels"] = levels
            lock_info["is_indirect"] = True
        # Handle direct variable reference
        elif item.target:
            lock_info["target"] = self.analyze(item.target, parent)

        return lock_info

    def _analyze_lock_target(self, target: Any, parent: Any) -> dict:
        """Analyze a LockTarget: postcond? (indirect | target) (':' timeout)?

        Handles:
        - L ^A:1 - variable with timeout
        - L @A:1 - indirection with timeout
        - L:cond ^A - postconditioned lock target
        """
        lock_info = {}

        # Handle postcondition on target
        if hasattr(target, "postcond") and target.postcond:
            lock_info["postcondition"] = self.analyze(target.postcond.condition, parent)

        # Handle indirection: L @A, L @@A, L @(expr)
        if hasattr(target, "indirect") and target.indirect:
            indirection_expr, levels = self._analyze_indirect_chain(
                target.indirect, parent
            )
            lock_info["indirection"] = indirection_expr
            lock_info["indirection_levels"] = levels
            lock_info["is_indirect"] = True
        # Handle direct variable reference
        elif hasattr(target, "target") and target.target:
            lock_info["target"] = self.analyze(target.target, parent)

        # Handle timeout
        if hasattr(target, "timeout") and target.timeout:
            lock_info["timeout"] = self.analyze(target.timeout, parent)

        return lock_info

    def _analyze_MergeCommand(self, cmd: Any, parent: Any) -> MMergeStatement:
        """Analyze MERGE command into MMergeStatement.

        Supports multiple merge pairs per MUMPS 1995 spec:
        M X=Y,Z=W copies both Y→X and W→Z
        """
        stmt = MMergeStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "merges") and cmd.merges:
            for merge in cmd.merges:
                pair = MMergePair()
                if hasattr(merge, "dest") and merge.dest:
                    pair.destination = self.analyze(merge.dest, stmt)
                if hasattr(merge, "src") and merge.src:
                    pair.source = self.analyze(merge.src, stmt)
                stmt.merges.append(pair)

        return stmt

    def _analyze_OpenCommand(self, cmd: Any, parent: Any) -> MOpenStatement:
        """Analyze OPEN command into MOpenStatement.

        Supports multiple devices per MUMPS 1995 spec:
        O DEV1:params,DEV2:params opens both devices
        """
        stmt = MOpenStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # OPEN device(:parameters)(:timeout)
        # cmd.args is a list of OpenArg objects
        if hasattr(cmd, "args") and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            for open_arg in args:
                device = MOpenDevice()

                # Handle OpenArg object - grammar always produces device attribute
                if hasattr(open_arg, "device") and open_arg.device:
                    device.device_expr = self.analyze(open_arg.device, stmt)

                if hasattr(open_arg, "params") and open_arg.params:
                    device.parameters = [self.analyze(p, stmt) for p in open_arg.params]

                if hasattr(open_arg, "timeout") and open_arg.timeout:
                    device.timeout = self.analyze(open_arg.timeout, stmt)

                stmt.devices.append(device)

        return stmt

    def _analyze_CloseCommand(self, cmd: Any, parent: Any) -> MCloseStatement:
        """Analyze CLOSE command into MCloseStatement.

        Supports multiple devices per MUMPS 1995 spec:
        C DEV1,DEV2 closes both devices
        """
        stmt = MCloseStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # CLOSE device(:parameters)
        if hasattr(cmd, "args") and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            for arg in args:
                device = MCloseDevice()
                # Handle CloseArg object - grammar always produces device attribute
                if hasattr(arg, "device") and arg.device:
                    device.device_expr = self.analyze(arg.device, stmt)
                if hasattr(arg, "params") and arg.params:
                    device.parameters = [self.analyze(p, stmt) for p in arg.params]
                stmt.devices.append(device)

        return stmt

    def _analyze_UseCommand(self, cmd: Any, parent: Any) -> MUseStatement:
        """Analyze USE command into MUseStatement.

        Supports multiple devices per MUMPS 1995 spec:
        U DEV1,DEV2 uses both devices in sequence
        """
        stmt = MUseStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # USE device(:parameters)
        if hasattr(cmd, "args") and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            for arg in args:
                device = MUseDevice()
                # Handle UseArg object - grammar always produces device attribute
                if hasattr(arg, "device") and arg.device:
                    device.device_expr = self.analyze(arg.device, stmt)
                if hasattr(arg, "params") and arg.params:
                    device.parameters = [self.analyze(p, stmt) for p in arg.params]
                stmt.devices.append(device)

        return stmt

    def _analyze_JobCommand(self, cmd: Any, parent: Any) -> MJobStatement:
        """Analyze JOB command into MJobStatement.

        Supports multiple targets per MUMPS 1995 spec:
        J LABEL1,LABEL2 starts two concurrent jobs

        Handles both direct labels and indirection (J @VAR, J @VAR^@ROU).
        """
        stmt = MJobStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # JOB uses targets like DO command (label^routine)
        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                call = MCall()

                if hasattr(target, "postcond") and target.postcond:
                    call.postcondition = self.analyze(target.postcond.condition, call)

                # Handle indirection: J @VAR, J @@VAR, J @VAR^@routine
                if hasattr(target, "indirect") and target.indirect:
                    indirect = target.indirect
                    call.name = ""  # Indirection target - no static name
                    call.label_is_indirect = True

                    # Process the IndirectChain for the label part
                    if hasattr(indirect, "labelIndirect") and indirect.labelIndirect:
                        indirection_expr, levels = self._analyze_indirect_chain(
                            indirect.labelIndirect, call
                        )
                        call.indirection = indirection_expr
                        call.indirection_levels = levels

                    # Process offset if present: @VAR+offset
                    if hasattr(indirect, "offset") and indirect.offset:
                        call.offset = self.analyze(indirect.offset, call)

                    # Process routine part: ^routine or ^@routine
                    if hasattr(indirect, "routine") and indirect.routine:
                        call.routine = indirect.routine
                    elif (
                        hasattr(indirect, "routineIndirect")
                        and indirect.routineIndirect
                    ):
                        routine_expr, _ = self._analyze_indirect_chain(
                            indirect.routineIndirect, call
                        )
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True

                    # Process arguments if present
                    if hasattr(indirect, "args") and indirect.args:
                        call.arguments = self._analyze_function_args(
                            indirect.args, call
                        )

                elif hasattr(target, "label") and target.label:
                    label_ref = target.label
                    call.name = label_ref.label or ""

                    # Handle routine: either literal name or indirect (@VAR, @@VAR)
                    if hasattr(label_ref, "routine") and label_ref.routine:
                        call.routine = label_ref.routine
                    elif (
                        hasattr(label_ref, "routineIndirect")
                        and label_ref.routineIndirect
                    ):
                        routine_expr, _ = self._analyze_indirect_chain(
                            label_ref.routineIndirect, call
                        )
                        call.routine_indirection = routine_expr
                        call.routine_is_indirect = True

                    if hasattr(label_ref, "offset") and label_ref.offset:
                        call.offset = self.analyze(label_ref.offset, call)

                    self._track_label_call(call.name, call.routine)

                if hasattr(target, "args") and target.args:
                    call.arguments = self._analyze_function_args(target.args, call)

                stmt.targets.append(call)

        return stmt

    def _analyze_ViewCommand(self, cmd: Any, parent: Any) -> MViewStatement:
        """Analyze VIEW command into MViewStatement."""
        stmt = MViewStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # VIEW arguments (implementation-specific parameters)
        if hasattr(cmd, "args") and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            stmt.arguments = [self.analyze(arg, stmt) for arg in args]

        return stmt

    # =========================================================================
    # Scope and Variable Tracking
    # =========================================================================

    def _push_scope(
        self,
        label_name: Optional[str] = None,
        routine_name: Optional[str] = None,
        is_for_body: bool = False,
    ) -> SemanticScope:
        """Create and enter a new scope."""
        new_scope = SemanticScope(
            parent_scope=self.current_scope,
            label_name=label_name,
            routine_name=routine_name,
            is_for_body=is_for_body,
            nesting_level=(self.current_scope.nesting_level + 1)
            if self.current_scope
            else 0,
        )
        self.current_scope = new_scope
        return new_scope

    def _pop_scope(self) -> Optional[SemanticScope]:
        """Exit current scope and return it."""
        old_scope = self.current_scope
        if old_scope:
            self.current_scope = old_scope.parent_scope
        return old_scope

    def _track_variable(
        self,
        name: str,
        node: Any,
        is_read: bool = False,
        is_set: bool = False,
        is_newed: bool = False,
    ):
        """Track variable usage in current scope."""
        if not self.current_scope:
            return

        if name not in self.current_scope.variables:
            self.current_scope.variables[name] = ScopeVariableInfo(
                name=name, first_reference=node
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

    def _analyze_postcondition(self, cmd: Any, stmt: Any) -> None:
        """Analyze postcondition from command and set on statement if present.

        This is a helper to reduce boilerplate in command handlers.

        Args:
            cmd: The textX command model
            stmt: The ASG statement to set postcondition on
        """
        if hasattr(cmd, "postcond") and cmd.postcond:
            stmt.postcondition = self.analyze(cmd.postcond.condition, stmt)


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


def analyze_statement(command_type: str, content: str) -> Optional[MStatement]:
    """Parse and analyze a MUMPS statement from command type and content.

    This is a convenience function for testing that parses a command string
    and returns a full-fidelity ASG statement node.

    Args:
        command_type: Command prefix (e.g., "S", "SET", "F", "FOR", "W", "WRITE")
        content: Statement content without command word (e.g., "X=1" for SET)

    Returns:
        Full-fidelity ASG statement node, or None if parsing fails

    Examples:
        >>> analyze_statement("S", "X=1")
        MSetStatement(assignments=[MAssignment(target=MVariable('X'), value=MLiteral(1))])

        >>> analyze_statement("F", "I=1:1:10")
        MForStatement(loop_var=MVariable('I'), parameters=[...])

        >>> analyze_statement("W", '"Hello"')
        MWriteStatement(arguments=[MLiteral("Hello")])
    """
    from m2py.parser.line_parser import parse_commands_from_line

    # Handle empty content for argumentless commands
    if not content or not content.strip():
        # Build minimal command string
        cmd_str = command_type.upper()[0]  # Use single-letter form
    else:
        # Combine command type with content
        # Use single-letter abbreviation for consistency
        cmd_letter = command_type.upper()[0]
        cmd_str = f"{cmd_letter} {content}"

    # Parse the command string via textX
    commands = parse_commands_from_line(cmd_str)
    if not commands:
        return None

    # Analyze the first command using full-fidelity SemanticAnalyzer
    return analyze_command(commands[0])


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

    # Expr with left attribute
    if hasattr(textx_expr, "left"):
        # If no binary ops (tail or ops/right), just unwrap the left
        has_tail = hasattr(textx_expr, "tail") and textx_expr.tail
        has_ops = hasattr(textx_expr, "ops") and textx_expr.ops
        if not has_tail and not has_ops:
            return unwrap_expression(textx_expr.left)
        # Has binary ops or pattern match - needs full analysis
        return textx_expr

    # UnaryExpr without operator
    if hasattr(textx_expr, "operand"):
        op = getattr(textx_expr, "operator", None)
        ops = getattr(textx_expr, "operators", None)
        if op is None and (ops is None or not ops):
            return unwrap_expression(textx_expr.operand)

    # ParenExpr
    if hasattr(textx_expr, "expr"):
        return unwrap_expression(textx_expr.expr)

    return textx_expr
