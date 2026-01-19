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
    MExternalFunction,
    MIndirection,
    MBinaryOp,
    MUnaryOp,
    MFormatControl,
    MDeviceControl,
    MPatternMatch,
    MActualParameter,
    MSelectArg,
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
    MKSubscriptsStatement,
    MKValueStatement,
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
    MJobTarget,
    MViewStatement,
    MTStartParam,
    MTStartStatement,
    MTCommitStatement,
    MTRestartStatement,
    MTRollbackStatement,
    MZTStartStatement,
    MZTCommitStatement,
    # Z-commands
    MZShowStatement,
    MZShowArg,
    MZWriteSubscriptAll,
    MZWriteSubscriptRange,
    MZWriteStatement,
    MZWriteArg,
    MZBreakClearAll,
    MZBreakStatement,
    MZBreakArg,
    MZStepStatement,
    MZGotoStatement,
    MZGotoArg,
    MZKillStatement,
    MZWithdrawStatement,
    MZAllocateStatement,
    MZDeallocateStatement,
    MZHaltStatement,
    MZHelpStatement,
    MZHelpArg,
    MZLinkStatement,
    MZPrintStatement,
    MZPrintArg,
    MZSystemStatement,
    MZMessageStatement,
    MZTriggerStatement,
    MZCompileStatement,
    MZEditStatement,
    MZContinueStatement,
    MZLoadStatement,
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

        elif isinstance(expr, MExternalFunction):
            new_args = []
            for arg in expr.arguments:
                new_args.append(self.analyze(arg, expr))
            object.__setattr__(expr, "arguments", new_args)

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

        elif isinstance(expr, MDeviceControl):
            # Analyze device control parameters
            if expr.params:
                new_params = [self.analyze(p, expr) for p in expr.params]
                object.__setattr__(expr, "params", new_params)

        return expr

    def _analyze_function_arg(self, arg: Any, parent: Any) -> MActualParameter:
        """Analyze a FunctionArg into an MActualParameter.

        Handles four cases:
        1. By-reference variable: .VAR passes variable by reference
        2. By-reference indirection: .@VAR passes indirect variable by reference
        3. By-value: Expression is evaluated and passed by value
        4. Omitted: Empty parameter position (nothing between commas)

        Args:
            arg: A FunctionArg textX object with byref or expr attributes
            parent: Parent ASG node for setting parent reference

        Returns:
            MActualParameter with appropriate passing mode
        """
        # Check for by-reference argument: .VAR or .@VAR
        if hasattr(arg, "byref") and arg.byref:
            byref = arg.byref
            # Check for indirection: .@VAR
            if hasattr(byref, "indirect") and byref.indirect:
                indirect_expr = self.analyze(byref.indirect, parent)
                return MActualParameter(
                    passing_mode=PassingMode.BY_REFERENCE,
                    expression=indirect_expr,
                    variable_name=None,  # Name determined at runtime
                )
            # Regular variable: .VAR
            elif hasattr(byref, "var") and byref.var:
                var = byref.var
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
            # atom.alternation is a list of PatternAlternative objects
            # Each PatternAlternative has atoms (plural) - a list of PatternAtom
            alt_parts = []
            for alt in atom.alternation:
                if hasattr(alt, "atoms") and alt.atoms:
                    # Serialize each atom in the alternative
                    alt_str = "".join(
                        self._pattern_atom_to_string(a) for a in alt.atoms
                    )
                    alt_parts.append(alt_str)
                else:
                    # Fallback for single atom (shouldn't happen per grammar)
                    alt_parts.append(self._pattern_atom_to_string(alt))
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

    def _analyze_ParenExpr(self, model: Any, parent: Any) -> Any:
        """Unwrap parenthesized expression: (expr) -> expr.

        textX grammar creates ParenExpr wrapper nodes for parenthesized
        expressions. This handler unwraps them to expose the inner expression.
        """
        return self.analyze(model.expr, parent)

    def _analyze_OffsetParenExpr(self, model: Any, parent: Any) -> Any:
        """Unwrap parenthesized offset expression: (offset_expr) -> expr.

        Similar to ParenExpr but used in GOTO offset expressions context.
        textX grammar uses separate rule to avoid ambiguity with ^NAME.
        """
        return self.analyze(model.expr, parent)

    def _analyze_generic(self, model: Any, parent: Any) -> Any:
        """Fallback handler for unknown textX types.

        This handler should not normally be reached. If a new grammar construct
        is added without a corresponding analyzer handler, this will raise an
        error to ensure the issue is caught during parsing rather than later
        during code generation.

        Raises:
            NotImplementedError: Always - unknown types indicate missing handler
        """
        cls_name = model.__class__.__name__
        raise NotImplementedError(
            f"SemanticAnalyzer has no handler for textX type '{cls_name}'. "
            f"Add _analyze_{cls_name}() method to semantic_analyzer.py."
        )

    def _analyze_str(self, model: str, parent: Any) -> MVariable:
        """Handle raw variable name strings from grammar rules like VARNAME.

        Some grammar rules capture variable names as raw strings (e.g.,
        TStartRestartArg's `vars+=VARNAME[',']`). This handler converts
        them to proper MVariable ASG nodes.

        Args:
            model: A variable name string (e.g., 'X', 'DATA', '%ABC')
            parent: Parent ASG node

        Returns:
            MVariable instance with the given name
        """
        var = MVariable(name=model, subscripts=[])
        object.__setattr__(var, "parent", parent)
        self._track_variable(model, var, is_read=True)
        return var

    def _analyze_MSelectArg(self, arg: MSelectArg, parent: Any) -> MSelectArg:
        """Analyze MSelectArg to properly unwrap condition and value expressions.

        MSelectArg is created by SelectFunction custom class with potentially
        raw textX Expr objects in condition/value fields. This handler ensures
        they're properly converted to ASG nodes (e.g., MBinaryOp for A=B).
        """
        object.__setattr__(arg, "parent", parent)

        if arg.condition is not None:
            analyzed_condition = self.analyze(arg.condition, arg)
            object.__setattr__(arg, "condition", analyzed_condition)

        if arg.value is not None:
            analyzed_value = self.analyze(arg.value, arg)
            object.__setattr__(arg, "value", analyzed_value)

        return arg

    def _analyze_TextFunction(self, model: Any, parent: Any) -> Any:
        """Analyze TextFunction ($TEXT) arguments.

        TextFunction stores its arguments in a `line_ref` dictionary, not the
        standard `arguments` list. We need to analyze any expressions within
        this dictionary (e.g., offset, routine_indirect).
        """
        # Set parent
        object.__setattr__(model, "parent", parent)

        # Analyze expressions in line_ref
        if hasattr(model, "line_ref") and model.line_ref:
            line_ref = model.line_ref

            # Analyze offset expression if present
            if "offset" in line_ref and line_ref["offset"]:
                line_ref["offset"] = self.analyze(line_ref["offset"], model)

            # Analyze routine indirection expression if present
            if "routine_indirect" in line_ref and line_ref["routine_indirect"]:
                line_ref["routine_indirect"] = self.analyze(
                    line_ref["routine_indirect"], model
                )

            # Analyze full indirection expression if present
            if "full_indirect" in line_ref and line_ref["full_indirect"]:
                line_ref["full_indirect"] = self.analyze(
                    line_ref["full_indirect"], model
                )

        return model

    def _analyze_MActualParameter(
        self, param: MActualParameter, parent: Any
    ) -> MActualParameter:
        """Analyze MActualParameter to properly set parent and unwrap expression.

        MActualParameter is created by textX custom classes (ExtrinsicFunction,
        DoCommand) with potentially raw textX objects in the expression field.
        This handler ensures proper parent references and expression unwrapping.
        """
        object.__setattr__(param, "parent", parent)

        if param.expression is not None:
            analyzed_expr = self.analyze(param.expression, param)
            object.__setattr__(param, "expression", analyzed_expr)

        return param

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
                # Check for SetIndirection (@A where A contains "X=1")
                # Grammar: SetIndirection: indirect=Indirection
                if hasattr(assign, "indirect") and assign.indirect is not None:
                    # Argument-level indirection: S @A
                    indir = self.analyze(assign.indirect, stmt)
                    # Mark as ARGUMENT type indirection
                    from m2py.asg.enums import IndirectionType

                    indir.indirection_type = IndirectionType.ARGUMENT
                    stmt.argument_indirections.append(indir)
                # Handle regular assignments with targets
                elif hasattr(assign, "targets") and assign.targets:
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
        ReadArg: /,/? arg=ReadArgValue
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
                # ReadArg grammar: /,/? arg=ReadArgValue
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

    def _analyze_IndirectChain(self, chain: Any, parent: Any) -> MIndirection:
        """Analyze IndirectChain into MIndirection.

        IndirectChain handles patterns like @VAR, @@VAR, @@@VAR, @(expr), @^GLOBAL.
        Returns an MIndirection with nested levels properly represented.
        """
        expr, levels = self._analyze_indirect_chain(chain, parent)

        # Wrap the innermost expression in MIndirection
        result = MIndirection(expression=expr, indirection_type=IndirectionType.NAME)
        object.__setattr__(result, "parent", parent)

        return result

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
        elif hasattr(current, "string") and current.string:
            # String literal: @"LABEL^ROUTINE"
            expr = MLiteral(
                value=current.string.strip("\"'"), literal_type=LiteralType.STRING
            )
            object.__setattr__(expr, "parent", parent)
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
        """Analyze NEW command into MNewStatement.

        Handles:
        - N X,Y - selective NEW of X and Y
        - N @A - NEW with indirection
        - N @@B@(2) - NEW with subscripted double indirection
        - N (X,Y) - exclusive NEW (keep all except X,Y)
        - N (@A,B) - exclusive NEW with indirection in list
        """
        stmt = MNewStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "exclusive") and cmd.exclusive:
            stmt.exclusive = True
            exc = cmd.exclusive
            except_list = getattr(exc, "except", None) or getattr(exc, "except_", None)
            if except_list:
                # ExclusiveNewVar can have .name or .indirect
                names = []
                for v in except_list:
                    if hasattr(v, "name") and v.name:
                        names.append(v.name)
                    elif hasattr(v, "indirect") and v.indirect:
                        # Indirection in exclusive list - store as analyzed expression
                        names.append(self.analyze(v.indirect, stmt))
                    else:
                        names.append(str(v))
                stmt.except_list = names
        elif hasattr(cmd, "vars") and cmd.vars:
            for v in cmd.vars:
                if hasattr(v, "indirect") and v.indirect:
                    # Indirection: @A, @@B@(2), etc.
                    indirect_expr = self.analyze(v.indirect, stmt)
                    stmt.variables.append(indirect_expr)
                elif hasattr(v, "svar") and v.svar:
                    # Special variable: $ZTRAP, etc.
                    svar_expr = self.analyze(v.svar, stmt)
                    stmt.variables.append(svar_expr)
                elif hasattr(v, "name") and v.name:
                    var_name = v.name
                    stmt.variables.append(var_name)
                    self._track_variable(var_name, v, is_newed=True)
                else:
                    stmt.variables.append(str(v))

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

    def _analyze_KSubscriptsCommand(
        self, cmd: Any, parent: Any
    ) -> MKSubscriptsStatement:
        """Analyze KSUBSCRIPTS command into MKSubscriptsStatement.

        KSUBSCRIPTS kills only subscripts (descendants), preserving values.
        Reference: MUMPS 1995 ANSI Standard, Section 8.2.20

        Handles same argument patterns as KILL:
        - KS (no args) - kill all local subscripts
        - KS X,Y - selective kill of X and Y subscripts
        - KS (X,Y) - exclusive kill (keep only X,Y subscripts)
        """
        stmt = MKSubscriptsStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            exclusive_groups = []
            selective_targets = []

            for arg in cmd.args:
                if hasattr(arg, "exclusive") and arg.exclusive:
                    except_list = getattr(arg, "except", None) or getattr(
                        arg, "except_", None
                    )
                    if except_list:
                        exclusive_groups.append(list(except_list))
                elif hasattr(arg, "target") and arg.target:
                    selective_targets.append(self.analyze(arg.target, stmt))

            if exclusive_groups:
                stmt.exclusive = True
                stmt.except_groups = exclusive_groups
                if len(exclusive_groups) == 1:
                    stmt.except_list = exclusive_groups[0]
                else:
                    result = set(exclusive_groups[0])
                    for group in exclusive_groups[1:]:
                        result &= set(group)
                    stmt.except_list = sorted(list(result))

            stmt.targets = selective_targets

        return stmt

    def _analyze_KValueCommand(self, cmd: Any, parent: Any) -> MKValueStatement:
        """Analyze KVALUE command into MKValueStatement.

        KVALUE kills only values, preserving subscripts (descendants).
        Reference: MUMPS 1995 ANSI Standard, Section 8.2.21

        Handles same argument patterns as KILL:
        - KV (no args) - kill all local values
        - KV X,Y - selective kill of X and Y values
        - KV (X,Y) - exclusive kill (keep only X,Y values)
        """
        stmt = MKValueStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            exclusive_groups = []
            selective_targets = []

            for arg in cmd.args:
                if hasattr(arg, "exclusive") and arg.exclusive:
                    except_list = getattr(arg, "except", None) or getattr(
                        arg, "except_", None
                    )
                    if except_list:
                        exclusive_groups.append(list(except_list))
                elif hasattr(arg, "target") and arg.target:
                    selective_targets.append(self.analyze(arg.target, stmt))

            if exclusive_groups:
                stmt.exclusive = True
                stmt.except_groups = exclusive_groups
                if len(exclusive_groups) == 1:
                    stmt.except_list = exclusive_groups[0]
                else:
                    result = set(exclusive_groups[0])
                    for group in exclusive_groups[1:]:
                        result &= set(group)
                    stmt.except_list = sorted(list(result))

            stmt.targets = selective_targets

        return stmt

    def _analyze_HangCommand(self, cmd: Any, parent: Any) -> MHangStatement:
        """Analyze HANG command into MHangStatement."""
        stmt = MHangStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle multiple duration arguments (new 'args' attribute)
        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed_arg = self.analyze(arg, stmt)
                if analyzed_arg is not None:
                    stmt.durations.append(analyzed_arg)
            # For backward compatibility, set duration to first arg
            if stmt.durations:
                stmt.duration = stmt.durations[0]
        # Legacy support for old 'seconds' attribute
        elif hasattr(cmd, "seconds") and cmd.seconds:
            stmt.duration = self.analyze(cmd.seconds, stmt)
            if stmt.duration is not None:
                stmt.durations.append(stmt.duration)

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
        - L +(^A,^B):1 - parenthesized list with +/- prefix
        - L @A - lock with indirection (name resolved at runtime)
        - L @A:1 - indirection with timeout
        - L +^A,-^B - per-target incremental/decremental lock
        """
        stmt = MLockStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle parenthesized lock list: L (^A,^B):timeout or L +(^A,^B):timeout
        if hasattr(cmd, "locklist") and cmd.locklist:
            locklist = cmd.locklist
            # Get list-level lockop (for L +(^A,^B) syntax)
            list_lockop = ""
            if hasattr(locklist, "lockop") and locklist.lockop:
                list_lockop = str(locklist.lockop)
            if hasattr(locklist, "targets") and locklist.targets:
                for item in locklist.targets:
                    lock_info = self._analyze_lock_item(item, stmt, list_lockop)
                    stmt.targets.append(lock_info)
            if hasattr(locklist, "timeout") and locklist.timeout:
                stmt.timeout = self.analyze(locklist.timeout, stmt)

        # Handle regular target list: L +^A:1,-^B:2 or L @A:1,^B:2
        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                lock_info = self._analyze_lock_target(target, stmt)
                stmt.targets.append(lock_info)

        # Derive statement-level lock_type from targets (for simple cases)
        # If all targets have same lockop, use it; otherwise leave empty
        if stmt.targets:
            lockops = [t.get("lockop", "") for t in stmt.targets]
            if lockops and all(op == lockops[0] for op in lockops):
                stmt.lock_type = lockops[0]

        return stmt

    def _analyze_lock_item(self, item: Any, parent: Any, list_lockop: str = "") -> dict:
        """Analyze a single item in a parenthesized lock list.

        LockListItem grammar produces lockop, indirect, and target attributes:
        - lockop: "+" or "-" for incremental/decremental
        - indirect: IndirectChain (e.g., @A, @@A, @(expr))
        - target: VarRef (e.g., ^A, X, ^A(1,2))

        The list_lockop is inherited from the parent LockList (for L +(^A,^B) syntax).
        Item-level lockop takes precedence over list-level lockop.
        """
        lock_info = {}

        # Handle lockop (+/-): item-level takes precedence over list-level
        if hasattr(item, "lockop") and item.lockop:
            lock_info["lockop"] = str(item.lockop)
        else:
            lock_info["lockop"] = list_lockop

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
        """Analyze a LockTarget: lockop? postcond? (indirect | target) (':' timeout)?

        Handles:
        - L +^A:1 - incremental lock with timeout
        - L -^A:1 - decremental lock with timeout
        - L @A:1 - indirection with timeout
        - L:cond ^A - postconditioned lock target
        """
        lock_info = {}

        # Handle lockop (+/-)
        if hasattr(target, "lockop") and target.lockop:
            lock_info["lockop"] = str(target.lockop)
        else:
            lock_info["lockop"] = ""

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

        Also supports GT.M/YottaDB device parameter variations:
        - C file:(DELETE) - parenthesized keyword
        - C file:delete - single keyword without parens
        - C file:(RENAME=newname) - keyword with value
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
                # Handle parenthesized params
                if hasattr(arg, "params") and arg.params:
                    device.parameters = [
                        self._analyze_device_param(p, stmt) for p in arg.params
                    ]
                # Handle single param (no parens)
                if hasattr(arg, "single_param") and arg.single_param:
                    device.parameters = [
                        self._analyze_device_param(arg.single_param, stmt)
                    ]
                stmt.devices.append(device)

        return stmt

    def _analyze_device_param(self, param: Any, parent: Any) -> MExpr:
        """Analyze a DeviceParam into an expression.

        DeviceParam can be:
        - keyword (like DELETE, REWIND)
        - keyword=value (like EXCEPTION="G EOF")
        - plain expr (legacy or numeric params)
        """
        # If it has a keyword attribute, treat keyword as a string literal
        if hasattr(param, "keyword") and param.keyword:
            # For keyword=value, create an assignment-like expression
            if hasattr(param, "value") and param.value:
                # Return the value expression - keyword is metadata
                return self.analyze(param.value, parent)
            else:
                # Return keyword as a literal string
                from m2py.asg.expressions import MLiteral

                lit = MLiteral()
                object.__setattr__(lit, "parent", parent)
                lit.value = param.keyword
                return lit
        # Plain expression
        if hasattr(param, "expr") and param.expr:
            return self.analyze(param.expr, parent)
        # Fallback - analyze the param itself
        return self.analyze(param, parent)

    def _analyze_UseCommand(self, cmd: Any, parent: Any) -> MUseStatement:
        """Analyze USE command into MUseStatement.

        Supports multiple devices per MUMPS 1995 spec:
        U DEV1,DEV2 uses both devices in sequence

        Also supports GT.M/YottaDB device parameter variations:
        - U p:(REWIND:FOLLOW) - parenthesized keywords
        - U p:rewind - single keyword without parens
        - U p:exception="G EOF" - keyword with value
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
                # Handle parenthesized params
                if hasattr(arg, "params") and arg.params:
                    device.parameters = [
                        self._analyze_device_param(p, stmt) for p in arg.params
                    ]
                # Handle single param (no parens)
                if hasattr(arg, "single_param") and arg.single_param:
                    device.parameters = [
                        self._analyze_device_param(arg.single_param, stmt)
                    ]
                stmt.devices.append(device)

        return stmt

    def _analyze_JobCommand(self, cmd: Any, parent: Any) -> MJobStatement:
        """Analyze JOB command into MJobStatement.

        Supports multiple targets per MUMPS 1995 spec (MDC 8.2.10):
        J LABEL1,LABEL2 starts two concurrent jobs

        Full syntax: J label^routine(actuallist):(processparameters):timeout
        - actuallist: parameters passed to the JOB'd routine (via args)
        - processparameters: implementation-specific (partition size, device settings)
        - timeout: affects $TEST, optional

        Each target has its own processparameters and timeout per MUMPS spec.

        Handles both direct labels and indirection (J @VAR, J @VAR^@ROU).
        """
        stmt = MJobStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # JOB uses targets like DO command (label^routine) but with extra params
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

                # Create MJobTarget with per-target processparameters and timeout
                job_target = MJobTarget(call=call)

                # Populate processparameters for this target (JOB-specific)
                if hasattr(target, "processparams") and target.processparams:
                    job_target.processparameters = [
                        self.analyze(p, stmt) for p in target.processparams
                    ]

                # Populate timeout for this target (JOB-specific)
                if hasattr(target, "timeout") and target.timeout:
                    job_target.timeout = self.analyze(target.timeout, stmt)

                stmt.targets.append(job_target)

        return stmt

    def _analyze_ViewCommand(self, cmd: Any, parent: Any) -> MViewStatement:
        """Analyze VIEW command into MViewStatement."""
        stmt = MViewStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # VIEW arguments (implementation-specific parameters)
        # ViewArg contains expr and optional colon-separated values
        if hasattr(cmd, "args") and cmd.args:
            args = cmd.args if isinstance(cmd.args, list) else [cmd.args]
            stmt.arguments = [self._analyze_ViewArg(arg, stmt) for arg in args]

        return stmt

    def _analyze_ViewArg(self, arg: Any, parent: Any) -> MExpr:
        """Analyze VIEW argument (ViewArg) into expression.

        ViewArg contains:
        - expr: The main expression (keyword or value)
        - values: Optional list of colon-separated ViewColonValue items

        For now, we return the main expression. The colon-separated values
        are preserved in the textX model but not separately tracked in ASG
        since they are implementation-specific GT.M/YottaDB parameters.
        """
        if hasattr(arg, "expr"):
            return self.analyze(arg.expr, parent)
        # Fallback for direct expressions
        return self.analyze(arg, parent)

    def _analyze_ViewColonValue(self, val: Any, parent: Any) -> MExpr:
        """Analyze colon-separated value in VIEW command."""
        if hasattr(val, "value"):
            return self.analyze(val.value, parent)
        return self.analyze(val, parent)

    def _analyze_TStartCommand(self, cmd: Any, parent: Any) -> MTStartStatement:
        """Analyze TSTART command into MTStartStatement.

        TSTART [:pc] [[(lvn[,...])][:keyword[,...]]]
        - lvn: Local variables to restore on TROLLBACK (restart variables)
        - keywords: Parameters like SERIAL, TRANSACTIONID=name
        """
        stmt = MTStartStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle restart variables (lvn list in parentheses)
        if hasattr(cmd, "restart_arg") and cmd.restart_arg:
            restart_arg = cmd.restart_arg
            # Check for * (restart all variables)
            if hasattr(restart_arg, "all") and restart_arg.all:
                stmt.restart_all = True
            elif hasattr(restart_arg, "vars") and restart_arg.vars:
                vars_list = restart_arg.vars
                if not isinstance(vars_list, list):
                    vars_list = [vars_list]
                stmt.restart_vars = [
                    self._analyze_TStartRestartVar(var, stmt) for var in vars_list
                ]

        # Handle parameters (keyword arguments after colon)
        if hasattr(cmd, "params") and cmd.params:
            params = cmd.params if isinstance(cmd.params, list) else [cmd.params]
            result_params = []
            for param in params:
                # Handle compound parenthesized form: (serial:t="BA")
                if hasattr(param, "inner_params") and param.inner_params:
                    # Expand compound form into multiple params
                    for inner in param.inner_params:
                        result_params.append(
                            self._analyze_TStartParamInner(inner, stmt)
                        )
                else:
                    result_params.append(self._analyze_TStartParam(param, stmt))
            stmt.parameters = result_params

        return stmt

    def _analyze_TStartRestartVar(self, var: Any, parent: Any):
        """Analyze TStartRestartVar - can be varname or @indirection."""
        if hasattr(var, "indirect") and var.indirect:
            return self.analyze(var.indirect, parent)
        elif hasattr(var, "varname") and var.varname:
            # Return as MVariable to be consistent
            from m2py.asg.expressions import MVariable

            return MVariable(name=var.varname)
        else:
            # Fallback for bare strings
            from m2py.asg.expressions import MVariable

            return MVariable(name=str(var))

    def _analyze_TStartParam(self, param: Any, parent: Any) -> MTStartParam:
        """Analyze TSTART parameter into MTStartParam.

        Parameters like SERIAL, S, TRANSACTIONID="value", T="value".
        Supports both bare names, parenthesized forms: serial or (serial),
        and compound forms: (serial:t="BA") which expand to multiple params.
        """
        # Handle parenthesized compound form: (serial:t="BA")
        if hasattr(param, "inner_params") and param.inner_params:
            # This contains multiple params - return first one for now
            # The caller should handle multiple params if needed
            first = param.inner_params[0]
            name = str(first.name) if hasattr(first, "name") else str(first)
            value = None
            if hasattr(first, "value") and first.value is not None:
                value = self.analyze(first.value, parent)
            return MTStartParam(name=name, value=value)
        elif hasattr(param, "name") and param.name:
            name = str(param.name)
        else:
            name = str(param)

        value = None
        if hasattr(param, "value") and param.value is not None:
            value = self.analyze(param.value, parent)
        return MTStartParam(name=name, value=value)

    def _analyze_TStartParamInner(self, param: Any, parent: Any) -> MTStartParam:
        """Analyze TStartParamInner - a parameter inside compound (serial:t=val) form."""
        name = str(param.name) if hasattr(param, "name") else str(param)
        value = None
        if hasattr(param, "value") and param.value is not None:
            value = self.analyze(param.value, parent)
        return MTStartParam(name=name, value=value)

    def _analyze_TStartParamName(self, param: Any, parent: Any) -> str:
        """Analyze TStartParamName rule - just returns the matched string."""
        return str(param)

    def _analyze_TCommitCommand(self, cmd: Any, parent: Any) -> MTCommitStatement:
        """Analyze TCOMMIT command into MTCommitStatement.

        TCOMMIT [:pc]
        Commits the current transaction level.
        """
        stmt = MTCommitStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)
        return stmt

    def _analyze_TRestartCommand(self, cmd: Any, parent: Any) -> MTRestartStatement:
        """Analyze TRESTART command into MTRestartStatement.

        TRESTART [:pc]
        Restarts the current transaction.
        """
        stmt = MTRestartStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)
        return stmt

    def _analyze_TRollbackCommand(self, cmd: Any, parent: Any) -> MTRollbackStatement:
        """Analyze TROLLBACK command into MTRollbackStatement.

        TROLLBACK [:pc] [tlevel]
        Rolls back to specified transaction level or all if not specified.
        """
        stmt = MTRollbackStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle optional transaction level argument
        if hasattr(cmd, "level") and cmd.level is not None:
            stmt.level = self.analyze(cmd.level, stmt)

        return stmt

    def _analyze_TRollbackLevel(self, level: Any, parent: Any) -> MLiteral:
        """Analyze TROLLBACK level expression.

        TRollbackLevel captures a simple numeric-looking expression as raw text.
        We return it as a string literal for now.
        """
        # Get the full level text from textX position info
        full_text = ""
        if hasattr(level, "_tx_parser") and hasattr(level, "_tx_position"):
            # Access the original text
            input_text = level._tx_parser.input
            start = level._tx_position
            end = level._tx_position_end
            full_text = input_text[start:end]
        else:
            # Fallback: combine captured parts (first + rest)
            first = getattr(level, "first", "") or ""
            rest = getattr(level, "rest", "") or ""
            full_text = first + rest
        return MLiteral(value=full_text, literal_type=LiteralType.STRING)

    def _analyze_ZTStartCommand(self, cmd: Any, parent: Any) -> MZTStartStatement:
        """Analyze ZTSTART command into MZTStartStatement.

        ZTSTART [:pc]
        GT.M/YDB-specific journaled transaction start.
        """
        stmt = MZTStartStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)
        return stmt

    def _analyze_ZTCommitCommand(self, cmd: Any, parent: Any) -> MZTCommitStatement:
        """Analyze ZTCOMMIT command into MZTCommitStatement.

        ZTCOMMIT [:pc] [level]
        GT.M/YDB-specific journaled transaction commit.
        """
        stmt = MZTCommitStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle optional commit level argument
        if hasattr(cmd, "level") and cmd.level is not None:
            stmt.level = self.analyze(cmd.level, stmt)

        return stmt

    # =========================================================================
    # Z-Command Analysis (YottaDB/GT.M Extensions)
    # =========================================================================

    def _analyze_ZShowCommand(self, cmd: Any, parent: Any) -> MZShowStatement:
        """Analyze ZSHOW command into MZShowStatement.

        ZSHOW [:pc] [codes] [:destination]
        Displays process environment information.
        """
        stmt = MZShowStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                zshow_arg = MZShowArg()
                if hasattr(arg, "codes") and arg.codes:
                    zshow_arg.codes = self.analyze(arg.codes, stmt)
                if hasattr(arg, "destination") and arg.destination:
                    zshow_arg.destination = self.analyze(arg.destination, stmt)
                stmt.args.append(zshow_arg)

        return stmt

    def _analyze_ZWriteCommand(self, cmd: Any, parent: Any) -> MZWriteStatement:
        """Analyze ZWRITE command into MZWriteStatement.

        ZWRITE [:pc] [target]
        Writes variables with their names in readable format.
        """
        stmt = MZWriteStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                zwrite_arg = MZWriteArg()
                if hasattr(arg, "target") and arg.target:
                    zwrite_arg.target = self.analyze(arg.target, stmt)
                stmt.args.append(zwrite_arg)

        return stmt

    def _analyze_MZWriteSubscriptAll(
        self, model: MZWriteSubscriptAll, parent: Any
    ) -> MZWriteSubscriptAll:
        """Handle ZWRITE wildcard subscript (*).

        The MZWriteSubscriptAll is already an ASG type from the custom class,
        just needs parent set.
        """
        return model

    def _analyze_MZWriteSubscriptRange(
        self, model: MZWriteSubscriptRange, parent: Any
    ) -> MZWriteSubscriptRange:
        """Handle ZWRITE range subscript (start:end).

        The MZWriteSubscriptRange is already an ASG type from the custom class,
        but we need to analyze its start/end expressions if present.
        """
        if model.start is not None:
            object.__setattr__(model, "start", self.analyze(model.start, parent))
        if model.end is not None:
            object.__setattr__(model, "end", self.analyze(model.end, parent))
        return model

    def _analyze_ZWriteGlobalPattern(self, model: Any, parent: Any) -> Any:
        """Handle ZWRITE global name pattern match (^?.E).

        The ZWriteGlobalPattern is already an ASG type from the custom class.
        Pattern atoms within name_pattern may contain expressions that need analysis.
        """
        # Analyze subscripts if present (they may contain expressions)
        if model.subscripts:
            analyzed_subscripts = []
            for sub in model.subscripts:
                analyzed_subscripts.append(self.analyze(sub, parent))
            object.__setattr__(model, "subscripts", analyzed_subscripts)
        return model

    def _analyze_ZBreakCommand(self, cmd: Any, parent: Any) -> MZBreakStatement:
        """Analyze ZBREAK command into MZBreakStatement.

        ZBREAK [:pc] [location[:action[:count]]]
        Sets or removes breakpoints.
        """
        stmt = MZBreakStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                zbreak_arg = MZBreakArg()
                if hasattr(arg, "location") and arg.location:
                    zbreak_arg.location = self.analyze(arg.location, stmt)
                if hasattr(arg, "action") and arg.action:
                    zbreak_arg.action = self.analyze(arg.action, stmt)
                if hasattr(arg, "count") and arg.count:
                    zbreak_arg.count = self.analyze(arg.count, stmt)
                stmt.args.append(zbreak_arg)

        return stmt

    def _analyze_ZStepCommand(self, cmd: Any, parent: Any) -> MZStepStatement:
        """Analyze ZSTEP command into MZStepStatement.

        ZSTEP [:pc] [mode[:action]]
        Single-step debugging control.
        """
        stmt = MZStepStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "mode") and cmd.mode:
            stmt.mode = str(cmd.mode).upper()
        if hasattr(cmd, "action") and cmd.action:
            stmt.action = self.analyze(cmd.action, stmt)

        return stmt

    def _analyze_ZGotoCommand(self, cmd: Any, parent: Any) -> MZGotoStatement:
        """Analyze ZGOTO command into MZGotoStatement.

        ZGOTO [:pc] [level[:target]] | @indirection
        Extended GOTO with stack unwinding.
        """
        stmt = MZGotoStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                zgoto_arg = MZGotoArg()
                if hasattr(arg, "level") and arg.level:
                    zgoto_arg.level = self.analyze(arg.level, stmt)
                if hasattr(arg, "target") and arg.target:
                    zgoto_arg.target = self.analyze(arg.target, stmt)
                if hasattr(arg, "indirection") and arg.indirection:
                    zgoto_arg.indirection = self.analyze(arg.indirection, stmt)
                stmt.args.append(zgoto_arg)

        return stmt

    def _analyze_ZKillCommand(self, cmd: Any, parent: Any) -> MZKillStatement:
        """Analyze ZKILL command into MZKillStatement.

        ZKILL [:pc] targets
        Kills variable but preserves descendants.
        """
        stmt = MZKillStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                analyzed = self.analyze(target, stmt)
                if analyzed:
                    stmt.targets.append(analyzed)

        return stmt

    def _analyze_ZWithdrawCommand(self, cmd: Any, parent: Any) -> MZWithdrawStatement:
        """Analyze ZWITHDRAW command into MZWithdrawStatement.

        ZWITHDRAW [:pc] targets
        Alias for ZKILL - kills variable but preserves descendants.
        """
        stmt = MZWithdrawStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                analyzed = self.analyze(target, stmt)
                if analyzed:
                    stmt.targets.append(analyzed)

        return stmt

    def _analyze_ZHaltCommand(self, cmd: Any, parent: Any) -> MZHaltStatement:
        """Analyze ZHALT command into MZHaltStatement.

        ZHALT [:pc] exitcode
        Halts with an exit code.
        """
        stmt = MZHaltStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "exitcode") and cmd.exitcode:
            stmt.exitcode = self.analyze(cmd.exitcode, stmt)

        return stmt

    def _analyze_ZHelpCommand(self, cmd: Any, parent: Any) -> MZHelpStatement:
        """Analyze ZHELP command into MZHelpStatement.

        ZHELP [:pc] topic[:library],...
        Displays help from help libraries.
        """
        stmt = MZHelpStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                help_arg = MZHelpArg()
                object.__setattr__(help_arg, "parent", stmt)

                if hasattr(arg, "topic") and arg.topic:
                    help_arg.topic = self.analyze(arg.topic, help_arg)

                if hasattr(arg, "library") and arg.library:
                    help_arg.library = self.analyze(arg.library, help_arg)

                stmt.args.append(help_arg)

        return stmt

    def _analyze_ZAllocateCommand(self, cmd: Any, parent: Any) -> MZAllocateStatement:
        """Analyze ZALLOCATE command into MZAllocateStatement.

        ZALLOCATE [:pc] targets
        Incremental lock (always uses +).
        Uses same target structure as LOCK command.
        """
        stmt = MZAllocateStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle parenthesized lock list: ZA (^A,^B):timeout
        if hasattr(cmd, "locklist") and cmd.locklist:
            locklist = cmd.locklist
            # ZALLOCATE always uses incremental locking
            list_lockop = "+"
            if hasattr(locklist, "targets") and locklist.targets:
                for item in locklist.targets:
                    lock_info = self._analyze_lock_item(item, stmt, list_lockop)
                    stmt.targets.append(lock_info)
            if hasattr(locklist, "timeout") and locklist.timeout:
                stmt.timeout = self.analyze(locklist.timeout, stmt)

        # Handle regular target list: ZA ^A:1,^B:2
        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                lock_info = self._analyze_lock_target(target, stmt)
                # Force incremental lock for ZALLOCATE
                lock_info["lockop"] = "+"
                stmt.targets.append(lock_info)

        return stmt

    def _analyze_ZDeallocateCommand(
        self, cmd: Any, parent: Any
    ) -> MZDeallocateStatement:
        """Analyze ZDEALLOCATE command into MZDeallocateStatement.

        ZDEALLOCATE [:pc] targets
        Decremental unlock (always uses -).
        Opposite of ZALLOCATE - releases incremental locks.
        """
        stmt = MZDeallocateStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        # Handle parenthesized lock list: ZD (^A,^B)
        if hasattr(cmd, "locklist") and cmd.locklist:
            locklist = cmd.locklist
            # ZDEALLOCATE always uses decremental unlocking
            list_lockop = "-"
            if hasattr(locklist, "targets") and locklist.targets:
                for item in locklist.targets:
                    lock_info = self._analyze_lock_item(item, stmt, list_lockop)
                    stmt.targets.append(lock_info)

        # Handle regular target list: ZD ^A,^B
        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                lock_info = self._analyze_lock_target(target, stmt)
                # Force decremental unlock for ZDEALLOCATE
                lock_info["lockop"] = "-"
                stmt.targets.append(lock_info)

        return stmt

    def _analyze_ZLoadCommand(self, cmd: Any, parent: Any) -> MZLoadStatement:
        """Analyze ZLOAD command into MZLoadStatement.

        ZLOAD [:pc] routine
        Loads routine object file into memory (YottaDB extension).
        """

        stmt = MZLoadStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed = self.analyze(arg, stmt)
                if analyzed:
                    stmt.args.append(analyzed)

        return stmt

    def _analyze_ZLinkCommand(self, cmd: Any, parent: Any) -> MZLinkStatement:
        """Analyze ZLINK command into MZLinkStatement.

        ZLINK [:pc] routine
        Compiles and links routine into process.
        """
        stmt = MZLinkStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed = self.analyze(arg, stmt)
                if analyzed:
                    stmt.args.append(analyzed)

        return stmt

    def _analyze_ZPrintCommand(self, cmd: Any, parent: Any) -> MZPrintStatement:
        """Analyze ZPRINT command into MZPrintStatement.

        ZPRINT [:pc] [label[:routine]]
        Prints source code.
        """
        stmt = MZPrintStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                zprint_arg = MZPrintArg()
                if hasattr(arg, "start_label") and arg.start_label:
                    zprint_arg.start_label = arg.start_label
                if hasattr(arg, "start_offset") and arg.start_offset:
                    zprint_arg.start_offset = self.analyze(arg.start_offset, stmt)
                if hasattr(arg, "routine") and arg.routine:
                    zprint_arg.routine = arg.routine
                if hasattr(arg, "end_label") and arg.end_label:
                    zprint_arg.end_label = arg.end_label
                if hasattr(arg, "end_offset") and arg.end_offset:
                    zprint_arg.end_offset = self.analyze(arg.end_offset, stmt)
                stmt.args.append(zprint_arg)

        return stmt

    def _analyze_ZSystemCommand(self, cmd: Any, parent: Any) -> MZSystemStatement:
        """Analyze ZSYSTEM command into MZSystemStatement.

        ZSYSTEM [:pc] [command]
        Executes shell command.
        """
        stmt = MZSystemStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed = self.analyze(arg, stmt)
                if analyzed:
                    stmt.args.append(analyzed)

        return stmt

    def _analyze_ZMessageCommand(self, cmd: Any, parent: Any) -> MZMessageStatement:
        """Analyze ZMESSAGE command into MZMessageStatement.

        ZMESSAGE [:pc] error_code
        Generates MUMPS error.
        """
        stmt = MZMessageStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed = self.analyze(arg, stmt)
                if analyzed:
                    stmt.args.append(analyzed)

        return stmt

    def _analyze_ZTriggerCommand(self, cmd: Any, parent: Any) -> MZTriggerStatement:
        """Analyze ZTRIGGER command into MZTriggerStatement.

        ZTRIGGER [:pc] target[,target...]
        Invokes triggers associated with global references.
        """
        stmt = MZTriggerStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "targets") and cmd.targets:
            for target in cmd.targets:
                analyzed = self.analyze(target, stmt)
                if analyzed:
                    stmt.targets.append(analyzed)

        return stmt

    def _analyze_ZCompileCommand(self, cmd: Any, parent: Any) -> MZCompileStatement:
        """Analyze ZCOMPILE command into MZCompileStatement.

        ZCOMPILE [:pc] routine
        Compiles routine without linking.
        """
        stmt = MZCompileStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed = self.analyze(arg, stmt)
                if analyzed:
                    stmt.args.append(analyzed)

        return stmt

    def _analyze_ZEditCommand(self, cmd: Any, parent: Any) -> MZEditStatement:
        """Analyze ZEDIT command into MZEditStatement.

        ZED[IT] [:pc] routine
        Opens routine in editor.
        """
        stmt = MZEditStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)

        if hasattr(cmd, "args") and cmd.args:
            for arg in cmd.args:
                analyzed = self.analyze(arg, stmt)
                if analyzed:
                    stmt.args.append(analyzed)

        return stmt

    def _analyze_ZContinueCommand(self, cmd: Any, parent: Any) -> MZContinueStatement:
        """Analyze ZCONTINUE command into MZContinueStatement.

        ZCONTINUE [:pc]
        Continues execution after breakpoint.
        """
        stmt = MZContinueStatement()
        object.__setattr__(stmt, "parent", parent)
        self._analyze_postcondition(cmd, stmt)
        return stmt

    # =========================================================================
    # Z-Command Helper Type Handlers
    # =========================================================================

    def _analyze_ZBreakArg(self, arg: Any, parent: Any) -> MZBreakArg:
        """Analyze ZBreakArg into MZBreakArg."""
        result = MZBreakArg()
        if hasattr(arg, "location") and arg.location:
            result.location = self.analyze(arg.location, parent)
        if hasattr(arg, "action") and arg.action:
            result.action = self.analyze(arg.action, parent)
        if hasattr(arg, "count") and arg.count:
            result.count = self.analyze(arg.count, parent)
        return result

    def _analyze_ZBreakLocation(self, loc: Any, parent: Any) -> Any:
        """Analyze ZBreakLocation - dispatches to Indirection, ZBreakClearAll, or ZBreakTarget."""
        # Grammar: ZBreakLocation: Indirection | ZBreakClearAll | ZBreakTarget
        # Since it's a union, the actual object is the matched alternative
        return self.analyze(loc, parent)

    def _analyze_ZBreakClearAll(self, node: Any, parent: Any) -> MZBreakClearAll:
        """Analyze ZBreakClearAll (-*) into MZBreakClearAll marker."""
        result = MZBreakClearAll()
        object.__setattr__(result, "parent", parent)
        return result

    def _analyze_ZBreakTarget(self, target: Any, parent: Any) -> MCall:
        """Analyze ZBreakTarget into MCall for label/routine reference."""
        # ZBreakTarget: ('+' offset=Expr)? label=VARNAME? ('^' routine=VARNAME)?
        call = MCall()
        object.__setattr__(call, "parent", parent)

        if hasattr(target, "label") and target.label:
            call.name = target.label
        if hasattr(target, "routine") and target.routine:
            call.routine = target.routine
        if hasattr(target, "routineIndirect") and target.routineIndirect:
            call.routine_indirection = self.analyze(target.routineIndirect, call)
        if hasattr(target, "offset") and target.offset:
            call.offset = self.analyze(target.offset, call)

        return call

    def _analyze_ZGotoArg(self, arg: Any, parent: Any) -> MZGotoArg:
        """Analyze ZGotoArg into MZGotoArg."""
        result = MZGotoArg()
        if hasattr(arg, "level") and arg.level:
            result.level = self.analyze(arg.level, parent)
        if hasattr(arg, "target") and arg.target:
            result.target = self.analyze(arg.target, parent)
        if hasattr(arg, "indirection") and arg.indirection:
            result.indirection = self.analyze(arg.indirection, parent)
        return result

    def _analyze_ZGotoTarget(self, target: Any, parent: Any) -> Any:
        """Analyze ZGotoTarget - dispatches to Indirection or LabelRef."""
        # Grammar: ZGotoTarget: Indirection | LabelRef
        return self.analyze(target, parent)

    def _analyze_LabelRef(self, label_ref: Any, parent: Any) -> MCall:
        """Analyze LabelRef into MCall.

        LabelRef: (label=LABELNAME ('+' offset=OffsetExpr?)?)?
                  ('^' (routineIndirect=IndirectChain | routine=VARNAME))?

        Returns an MCall with the label name, offset, and routine information.
        """
        call = MCall()

        # Get label name
        if hasattr(label_ref, "label") and label_ref.label:
            call.name = label_ref.label

        # Get offset if present (label+offset)
        if hasattr(label_ref, "offset") and label_ref.offset:
            call.offset = self.analyze(label_ref.offset, parent)

        # Get routine - either literal name or indirect expression
        if hasattr(label_ref, "routine") and label_ref.routine:
            call.routine = label_ref.routine
        elif hasattr(label_ref, "routineIndirect") and label_ref.routineIndirect:
            routine_expr, levels = self._analyze_indirect_chain(
                label_ref.routineIndirect, parent
            )
            call.routine_indirection = routine_expr
            call.routine_is_indirect = True
            call.indirection_levels = levels

        # Track the label call for reference resolution
        if call.name:
            self._track_label_call(call.name, call.routine)

        return call

    def _analyze_ZPrintArg(self, arg: Any, parent: Any) -> MZPrintArg:
        """Analyze ZPrintArg into MZPrintArg."""
        result = MZPrintArg()
        if hasattr(arg, "start_label") and arg.start_label:
            result.start_label = arg.start_label
        if hasattr(arg, "start_offset") and arg.start_offset:
            result.start_offset = self.analyze(arg.start_offset, parent)
        if hasattr(arg, "routine") and arg.routine:
            result.routine = arg.routine
        if hasattr(arg, "routineIndirect") and arg.routineIndirect:
            result.routine_indirection = self.analyze(arg.routineIndirect, parent)
        if hasattr(arg, "end_label") and arg.end_label:
            result.end_label = arg.end_label
        if hasattr(arg, "end_offset") and arg.end_offset:
            result.end_offset = self.analyze(arg.end_offset, parent)
        return result

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
    from m2py.asg.elements import MParseError
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
    if not commands or isinstance(commands, MParseError):
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
