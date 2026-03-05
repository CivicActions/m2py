"""Statement code generation for MUMPS-to-Python transpilation.

Generates Python statements from MUMPS ASG statement nodes.
Handles SET, WRITE, QUIT, IF, ELSE, FOR, and other basic commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, cast

from m2py.asg.enums import (
    ForLoopType,
    FormatControlType,
    ForParamType,
    GotoType,
    PassingMode,
)
from m2py.asg.expressions import (
    MActualParameter,
    MBinaryOp,
    MExpr,
    MFormatControl,
    MIndirection,
    MIntrinsicFunction,
    MSpecialVariable,
    MVariable,
)
from m2py.parser.textx_classes import (
    GlobalVariable,
    NakedGlobal,
    ExtendedGlobalBracket,
    ExtendedGlobalPipe,
)
from m2py.asg.statements import (
    MAssignment,
    MBreakStatement,
    MCloseStatement,
    MDoStatement,
    MElseStatement,
    MForParameter,
    MForStatement,
    MGotoStatement,
    MHaltStatement,
    MHangStatement,
    MIfStatement,
    MJobStatement,
    MJobTarget,
    MKillStatement,
    MKSubscriptsStatement,
    MKValueStatement,
    MLockStatement,
    MLockTarget,
    MMergeStatement,
    MNewStatement,
    MOpenStatement,
    MQuitStatement,
    MReadStatement,
    MReadTarget,
    MSetStatement,
    MTCommitStatement,
    MTRollbackStatement,
    MTStartStatement,
    MUseStatement,
    MViewStatement,
    MWriteStatement,
    MXecuteStatement,
    # Z-commands - Implemented
    MZGotoStatement,
    MZHaltStatement,
    MZKillStatement,
    MZLinkStatement,
    MZLoadStatement,
    MZShowStatement,
    MZWithdrawStatement,
    MZWriteStatement,
    MZWriteSubscriptAll,
    MZWriteSubscriptRange,
    # Z-commands - Unimplemented (LIM-015)
    MZAllocateStatement,
    MZBreakStatement,
    MZCompileStatement,
    MZContinueStatement,
    MZDeallocateStatement,
    MZEditStatement,
    MZHelpStatement,
    MZMessageStatement,
    MZPrintStatement,
    MZStepStatement,
    MZSystemStatement,
    MZTriggerStatement,
)
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.exceptions import UnsupportedFeatureError
from m2py.codegen.expressions import contains_naked_global, generate_expr
from m2py.codegen.names import translate_name
from m2py.codegen.var_access import var_base_expr, var_write_stmt, scope_dict_expr

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
    from m2py.asg.statements import MStatement
    from m2py.codegen.routine import GeneratorContext


# =============================================================================
# Subscript Tuple Generation (S-02)
# =============================================================================


def gen_subscripts_tuple(
    subscripts: list,
    ctx: "GeneratorContext",
    *,
    subscript_context: bool = False,
    str_wrap: bool = False,
    empty: str = "()",
) -> str:
    """Generate Python tuple expression from ASG subscript node list.

    Handles 4 variations of subscript tuple generation:
    1. Standard: evaluate each subscript via generate_expr(), format as tuple
    2. Pre-evaluated: caller passes string list (detected by item type)
    3. str()-wrapped: each subscript expression wrapped in str() call
    4. Empty: returns ``empty`` sentinel when list is empty

    Args:
        subscripts: List of ASG expression nodes representing subscripts,
            or list of pre-evaluated expression strings.
        ctx: Current generator context.
        subscript_context: If True, pass subscript_context=True to generate_expr()
            so indirection in subscripts returns VALUE instead of NAME.
        str_wrap: If True, wrap each subscript expression in str().
        empty: String to return when subscripts is empty. Default is ``"()"``.
            Use ``'("",)'`` for $ORDER/$QUERY sentinel.

    Returns:
        Python tuple string, e.g. ``"(expr1, expr2,)"`` or ``"()"``.
    """
    if not subscripts:
        return empty

    # Build expression strings: either from ASG nodes or pre-evaluated strings
    if subscripts and isinstance(subscripts[0], str):
        sub_exprs = list(subscripts)
    else:
        sub_exprs = [
            generate_expr(sub, ctx, subscript_context=subscript_context)
            for sub in subscripts
        ]

    if str_wrap:
        sub_exprs = [f"str({e})" for e in sub_exprs]

    if not sub_exprs:
        return empty

    return f"({', '.join(sub_exprs)},)"


def emit_state_to_scope_sync(ctx: "GeneratorContext") -> None:
    """Emit state._locals → _scope synchronization code.

    Copies all entries from ``state._locals`` into ``_scope`` so that
    subroutines and external calls see the current variable values.

    Only emits if ``ctx.uses_dynamic_locals`` is True (no-op otherwise).

    Args:
        ctx: Current generator context with emitter.
    """
    if not ctx.uses_dynamic_locals:
        return
    ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")


def emit_state_var_to_scope(
    ctx: "GeneratorContext",
    var_name: str,
    py_name: str,
    *,
    scope_key: str | None = None,
) -> None:
    """Emit state→scope sync for a single static-field variable.

    For **array** variables (those in ``ctx.array_vars``), the MArray is
    assigned directly from state — preserving subscripts.

    For **simple** variables, ``state.X`` is a plain scalar (str/number).
    The generated code wraps it in an MArray before storing in ``_scope``
    because called routines expect ``_scope`` entries to be MArray objects
    (they use ``_scope['X'].value`` or ``_scope.setdefault('X', MArray()).value``).

    This is the inverse of :func:`emit_scope_var_to_state`.

    Args:
        ctx: Current generator context with emitter.
        var_name: Original MUMPS variable name (used for array_vars lookup).
        py_name: Python-translated variable name (used for state attribute).
        scope_key: Key used to store the variable in ``_scope``.
            Defaults to *py_name*.
    """
    key = scope_key or py_name
    if var_name in ctx.array_vars:
        # Array vars: MArray already, assign directly
        ctx.emitter.line(f"_scope[{key!r}] = state.{py_name}")
    else:
        # Simple vars: wrap scalar in MArray so called routines see MArray in _scope
        ctx.emitter.line(f"_m = _scope.get({key!r})")
        ctx.emitter.line("if not isinstance(_m, MArray):")
        with ctx.emitter.indented():
            ctx.emitter.line("_m = MArray()")
            ctx.emitter.line(f"_scope[{key!r}] = _m")
        ctx.emitter.line(f"_m.value = state.{py_name}")


def emit_scope_to_state_sync(ctx: "GeneratorContext") -> None:
    """Emit _scope → state._locals synchronization code.

    Wraps non-MArray values in MArray containers before storing into
    ``state._locals``, ensuring consistent data model after callee
    returns (callees using static state may produce plain values).

    Only emits if ``ctx.uses_dynamic_locals`` is True (no-op otherwise).

    Args:
        ctx: Current generator context with emitter.
    """
    if not ctx.uses_dynamic_locals:
        return
    ctx.emitter.line("for _k, _v in _scope.items():")
    with ctx.emitter.indented():
        ctx.emitter.line("if isinstance(_v, MArray):")
        with ctx.emitter.indented():
            ctx.emitter.line("state._locals[_k] = _v")
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            ctx.emitter.line("_m = MArray()")
            ctx.emitter.line("_m.value = _v")
            ctx.emitter.line("state._locals[_k] = _m")


def emit_scope_var_to_state(
    ctx: "GeneratorContext",
    var_name: str,
    py_name: str,
    *,
    scope_key: str | None = None,
) -> None:
    """Emit scope→state sync for a single static-field variable.

    For **array** variables (those in ``ctx.array_vars``), the scope value
    is assigned directly — preserving the full MArray with its subscripts.
    For **simple** variables, ``.value`` is extracted from MArray containers
    so that ``state.X`` remains a plain Python scalar.

    This fixes a bug where array variables like ``IO`` (which carry
    subscripts such as ``IO(0)``) were flattened to plain strings when
    synced back from ``_scope`` after a DO call, causing subsequent
    ``$DATA(IO(0))`` calls to crash with ``'str' has no '_children'``.

    Args:
        ctx: Current generator context with emitter.
        var_name: Original MUMPS variable name (used for array_vars lookup).
        py_name: Python-translated variable name (used for state attribute).
        scope_key: Key used to look up the variable in ``_scope``.
            Defaults to *py_name*.
    """
    key = scope_key or py_name
    ctx.emitter.line(f"if {key!r} in _scope:")
    with ctx.emitter.indented():
        if var_name in ctx.array_vars:
            # Array vars: preserve MArray from scope directly (keeps subscripts)
            ctx.emitter.line(f"state.{py_name} = _scope[{key!r}]")
        else:
            # Simple vars: extract .value from MArray, use plain value otherwise
            ctx.emitter.line(
                f"state.{py_name} = _scope[{key!r}].value "
                f"if isinstance(_scope.get({key!r}), MArray) "
                f"else _scope[{key!r}]"
            )


def _emit_goto_external_handler(ctx: "GeneratorContext") -> None:
    """Emit the body of a standard ``except GotoExternal`` handler.

    Emits three steps:
    1. state→scope sync (no-op when ``ctx.uses_dynamic_locals`` is False)
    2. ``run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)``
    3. scope→state sync (no-op when ``ctx.uses_dynamic_locals`` is False)

    The caller is responsible for emitting the ``except GotoExternal as _goto:``
    line and managing indentation.

    Args:
        ctx: Current generator context with emitter.
    """
    emit_state_to_scope_sync(ctx)
    ctx.emitter.line("run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)")
    emit_scope_to_state_sync(ctx)


# =============================================================================
# Limitation Constants
# =============================================================================


# =============================================================================
# Comment Preservation
# =============================================================================


def _emit_source_comment(stmt: "MStatement", ctx: "GeneratorContext") -> None:
    """Emit MUMPS inline comment as Python comment if present.

    Reads the pre-extracted comment from stmt.comment (populated during
    parsing by the parser module).

    Args:
        stmt: ASG statement node with optional comment field
        ctx: Generator context with emitter
    """
    if stmt.comment:
        ctx.emitter.line(f"# {stmt.comment}")


# =============================================================================
# Code Generation Context Helpers
# =============================================================================


def _generate_call_arguments(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> str:
    """Generate Python arguments from MUMPS call arguments.

    Handles:
    - BY_VALUE: Expression evaluated and passed
    - BY_REFERENCE: Variable passed directly; return tuple destructuring
      handles results at the call site
    - OMITTED: None placeholder

    Args:
        arguments: List of MActualParameter from MCall
        ctx: Generator context

    Returns:
        Comma-separated argument string for Python call
    """
    if not arguments:
        return ""

    parts = []
    for arg in arguments:
        if arg.passing_mode == PassingMode.OMITTED:
            parts.append("None")
        elif arg.passing_mode == PassingMode.BY_REFERENCE:
            # For by-ref, pass the MArray object for aliasing.
            # The callee detects isinstance(param, MArray) and aliases it.
            if arg.variable_name:
                # Simple variable: .W → pass MArray from scope
                python_name = translate_name(arg.variable_name)
                parts.append(f"_scope.setdefault({python_name!r}, MArray())")
            elif arg.expression:
                # Indirected by-ref: .@IX → use get_indirected_marray
                from m2py.asg.expressions import MIndirection as MIndirectionType

                if isinstance(arg.expression, MIndirectionType):
                    from m2py.codegen.indirection import (
                        generate_indirection_marray_expr,
                    )

                    parts.append(generate_indirection_marray_expr(arg.expression, ctx))
                else:
                    # Fallback: generate as value expression
                    parts.append(generate_expr(arg.expression, ctx))
            else:
                parts.append("None")
        else:  # BY_VALUE
            if arg.expression:
                parts.append(generate_expr(arg.expression, ctx))
            else:
                parts.append("None")

    return ", ".join(parts)


@dataclass
class ForGenContext:
    """Context for FOR loop code generation decisions.

    Aggregates analysis results from MForStatement to guide
    which Python pattern to generate.

    Attributes:
        stmt: The MForStatement being generated
        loop_var: Translated Python name for loop variable
        loop_var_name: Original MUMPS variable name (for _scope access)
        loop_var_subscripts: List of subscript expressions (for I(1), I(1,2), etc.)
        use_while: True if loop_var_modified_in_body requires while loop
        needs_break: True if has_internal_quit or exit GOTOs need break
        is_infinite: True for argumentless FOR (F)
        loop_type: Classification from analysis for pattern selection
        loop_var_indirect: True if loop variable uses indirection (@A)
        loop_var_expr: For indirect, the expression to get the target var name
        loop_id: Unique ID for this loop to generate unique variable names
    """

    stmt: MForStatement
    loop_var: str
    loop_var_name: str  # Original MUMPS name for _scope access
    loop_var_subscripts: List[str]  # Subscript expressions (empty if simple variable)
    use_while: bool  # True if loop_var_modified_in_body
    needs_break: bool  # True if has_internal_quit or has_internal_goto
    is_infinite: bool
    loop_type: ForLoopType
    loop_var_indirect: bool = False  # True if loop_var is @A
    loop_var_expr: Optional[str] = None  # Expression to get target var name
    loop_id: int = 0  # Unique ID for this loop (for generating unique var names)

    @classmethod
    def from_statement(
        cls,
        stmt: MForStatement,
        ctx: "GeneratorContext | None" = None,
    ) -> "ForGenContext":
        """Create ForGenContext from an MForStatement.

        Args:
            stmt: The FOR statement to analyze
            ctx: Optional generator context for strategy-aware naming

        Returns:
            ForGenContext with analysis results

        Raises:
            ValueError: If loop_type was not set by analysis
        """
        # Import here to avoid circular import
        from m2py.asg.expressions import MIndirection as MIndirectionType
        from m2py.codegen.expressions import generate_expr

        # Check for indirection loop variable (F @A=1:1:3)
        loop_var_indirect = False
        loop_var_expr: Optional[str] = None
        loop_var_subscripts: List[str] = []

        if isinstance(stmt.loop_var, MIndirectionType):
            # Indirect loop variable: F @A=1:1:3 where A contains "B"
            # Also handles multi-level: F @@A=1:1:5, F @@@A=1:1:5
            loop_var_indirect = True
            # Generate expression to get target variable name at runtime
            # Use generate_name_indirection_for which uses IndirectionResolver
            if ctx is not None and stmt.loop_var.expression is not None:
                from m2py.codegen.indirection import (
                    generate_name_indirection_for,
                )

                # Generate code to resolve the full indirection chain
                loop_var_expr = generate_name_indirection_for(stmt.loop_var, ctx)
            var_name = "_for_indirect_var"
            loop_var = "_for_val"  # Temporary for range iteration
        elif isinstance(stmt.loop_var, str):
            var_name = stmt.loop_var if stmt.loop_var else "_"
            loop_var = translate_name(var_name)
        elif isinstance(stmt.loop_var, MVariable):
            var_name = stmt.loop_var.name
            loop_var = translate_name(var_name)
            # Extract subscripts for subscripted loop variables (F I(1)=1:1:3)
            if stmt.loop_var.subscripts and ctx is not None:
                loop_var_subscripts = [
                    generate_expr(sub, ctx) for sub in stmt.loop_var.subscripts
                ]
        else:
            var_name = "_"
            loop_var = "_"  # Fallback for complex expressions

        # When inside inline XECUTE, prefix loop var to avoid shadowing
        # module-level label functions. E.g. "F I=1:1:3 G I" - the FOR loop
        # variable I would shadow def I() if we use bare "I".
        if ctx and ctx.in_inline_xecute and loop_var not in ("_", "_for_val"):
            loop_var = f"_xec_{loop_var}"

        # Check if loop var should use state for trampoline
        # Only use state.{var} when in TRAMPOLINE mode with static state vars.
        # If uses_dynamic_locals is True, RoutineState only has _locals dict,
        # so we can't use state.I — we must use local Python vars instead.
        if (
            ctx
            and ctx.strategy == GotoStrategy.TRAMPOLINE
            and var_name in ctx.state_vars
            and not loop_var_indirect
            and not ctx.uses_dynamic_locals
        ):
            loop_var = f"state.{translate_name(var_name)}"

        # Read analysis results - ASG fields have defaults, analysis passes populate them
        use_while = stmt.loop_var_modified_in_body
        needs_break = stmt.has_internal_quit or stmt.has_internal_goto
        is_infinite = stmt.is_infinite or not stmt.parameters

        loop_type = stmt.loop_type
        if loop_type is None:
            raise ValueError(
                "MForStatement.loop_type not set - ensure analyze_for_loops() was called"
            )

        # Get unique loop ID from context for variable naming
        loop_id = ctx.next_for_loop_id() if ctx else 0

        return cls(
            stmt=stmt,
            loop_var=loop_var,
            loop_var_name=var_name,
            loop_var_subscripts=loop_var_subscripts,
            use_while=use_while,
            needs_break=needs_break,
            is_infinite=is_infinite,
            loop_type=loop_type,
            loop_var_indirect=loop_var_indirect,
            loop_var_expr=loop_var_expr,
            loop_id=loop_id,
        )


@dataclass
class GotoGenContext:
    """Context for GOTO code generation decisions.

    Aggregates analysis results from MGotoStatement to determine
    which Python pattern to generate.

    Attributes:
        stmt: The MGotoStatement being generated
        in_for_loop: True if GOTO is inside a FOR loop
        enclosing_loops: Stack of FOR loops containing this GOTO
        target_label: Translated Python name for target label
        pattern: Code pattern to generate:
            - 'break': Single loop exit
            - 'multi_break': Multiple loop exit (exception)
            - 'forward': Forward jump restructuring
            - 'function_call': Simple function call with return
            - 'unsupported': Cannot be transpiled statically
    """

    stmt: MGotoStatement
    in_for_loop: bool
    enclosing_loops: List[MForStatement]
    target_label: str
    pattern: (
        str  # 'break' | 'multi_break' | 'forward' | 'function_call' | 'unsupported'
    )

    @classmethod
    def from_statement(cls, stmt: MGotoStatement) -> "GotoGenContext":
        """Create GotoGenContext from an MGotoStatement.

        Uses ASG fields populated by classify_gotos() analysis.

        Args:
            stmt: The GOTO statement to analyze

        Returns:
            GotoGenContext with analysis results
        """
        # exits_loops is populated by classify_gotos() analysis
        exits_loops = stmt.exits_loops or []
        in_for_loop = len(exits_loops) > 0
        enclosing_loops = list(exits_loops)

        # Get target label name
        target_label = ""
        if stmt.targets:
            target = stmt.targets[0]
            target_label = translate_name(target.name) if target.name else ""

        # Map GotoCodegenPattern enum to string pattern for backward compatibility
        from m2py.asg.enums import GotoCodegenPattern

        pattern_map = {
            GotoCodegenPattern.BREAK: "break",
            GotoCodegenPattern.MULTI_BREAK: "multi_break",
            GotoCodegenPattern.FORWARD: "forward",
            GotoCodegenPattern.FUNCTION_CALL: "function_call",
            GotoCodegenPattern.UNSUPPORTED: "unsupported",
        }

        if stmt.codegen_pattern is not None:
            pattern = pattern_map.get(stmt.codegen_pattern, "function_call")
        else:
            # Fallback for GOTOs where analysis hasn't run (shouldn't happen)
            pattern = "function_call"

        return cls(
            stmt=stmt,
            in_for_loop=in_for_loop,
            enclosing_loops=enclosing_loops,
            target_label=target_label,
            pattern=pattern,
        )


def _find_forward_goto_in_if(if_stmt: MIfStatement) -> "MGotoStatement | None":
    """Find a restructurable forward GOTO in an IF's then_scope.

    Uses pre-computed MIfStatement.restructurable_goto field set by
    classify_gotos() analysis. Avoids scanning at codegen time.

    Args:
        if_stmt: The MIfStatement to check

    Returns:
        The MGotoStatement if found and restructurable, None otherwise
    """
    return if_stmt.restructurable_goto


def _restructure_forward_goto(
    if_stmt: MIfStatement,
    if_index: int,
    statements: List["MStatement"],
    goto: MGotoStatement,
    ctx: "GeneratorContext",
) -> int:
    """Generate restructured code for forward GOTO in an IF statement.

    Transforms:
        IF cond GOTO target       ; if_index
        ... statements to skip ... ; if_index+1 to target_idx-1
        target_statement           ; target_idx

    Into:
        _test = m_truth(cond)
        if not _test:
            ... statements to skip ...
        target_statement  # continues at same level

    The transformation inverts the IF condition so that statements between
    the IF and the GOTO target are executed only when the condition is FALSE.
    When the condition is TRUE, those statements are skipped (the original
    GOTO behavior).

    Args:
        if_stmt: The MIfStatement containing the GOTO
        if_index: Index of the IF statement in the statement list
        statements: Full list of statements at this scope level
        goto: The MGotoStatement being restructured
        ctx: Generator context

    Returns:
        The next statement index to continue generation from (skip consumed statements)
    """
    # Get target statement index from analysis (populated by classify_gotos)
    target_idx = goto.target_stmt_index

    if target_idx is None:
        # Fall back to generating the IF normally
        _generate_if(if_stmt, ctx)
        return if_index + 1

    # Statements to skip are between IF (exclusive) and target (exclusive)
    skip_stmts = statements[if_index + 1 : target_idx]

    # Generate condition check and set _test
    # Handle single vs multiple conditions
    if len(if_stmt.conditions) == 1:
        cond_expr = generate_expr(if_stmt.conditions[0], ctx)
        ctx.emitter.line(f"_test = m_truth({cond_expr})")
        ctx.emitter.line("_rt._test = _test")
    elif if_stmt.conditions:
        cond_parts = [generate_expr(c, ctx) for c in if_stmt.conditions]
        cond_expr = " and ".join(f"m_truth({c})" for c in cond_parts)
        ctx.emitter.line(f"_test = {cond_expr}")
        ctx.emitter.line("_rt._test = _test")
    else:
        # Argumentless IF - use existing _test (GOTO executes if _test is true)
        pass  # _test already set

    # Generate the restructured if/else
    # Skipped statements go in "if not _test:" (execute when GOTO doesn't fire)
    if skip_stmts:
        ctx.emitter.line("if not _test:")
        with ctx.emitter.indented():
            for stmt in skip_stmts:
                generate_statement(stmt, ctx)

    # Return the target index - generation continues from there
    return target_idx


def generate_scope_statements(
    statements: List["MStatement"],
    ctx: "GeneratorContext",
    label_line: int | None = None,
) -> None:
    """Generate statements for a scope, handling forward GOTO restructuring.

    This function should be used when generating a sequence of statements
    (e.g., label body, DO block body) to properly handle intra-label forward
    GOTOs by restructuring them to if/else blocks.

    The restructuring transforms:
        I cond G SKIP
        W "skipped"
        SKIP W "target"

    Into:
        _test = m_truth(cond)
        if not _test:
            _rt.write("skipped")
        _rt.write("target")

    When label_line is provided, statements are also wrapped with offset guards
    for D LABEL+N^ROUTINE support. This allows external callers to enter at
    any line within the label by passing _start_offset parameter.

    Args:
        statements: List of statements to generate
        ctx: Generator context
        label_line: Optional line number of the containing label. If provided,
                   statements are wrapped with offset guards for _start_offset support.
    """
    i = 0
    while i < len(statements):
        stmt = statements[i]

        # Check for IF with restructurable forward GOTO
        if isinstance(stmt, MIfStatement):
            goto = _find_forward_goto_in_if(stmt)
            if goto:
                # Restructure and skip consumed statements
                i = _restructure_forward_goto(stmt, i, statements, goto, ctx)
                continue

        # Apply offset guard if label_line provided (for external offset calls)
        if label_line is not None and stmt.line_number is not None:
            offset = stmt.line_number - label_line
            ctx.emitter.line(f"if _start_offset <= {offset}:")
            with ctx.emitter.indented():
                # Track line count to detect if statement emits nothing
                lines_before = len(ctx.emitter._lines)
                generate_statement(stmt, ctx)
                lines_after = len(ctx.emitter._lines)
                # If statement emitted nothing (e.g., empty XECUTE), add pass
                if lines_after == lines_before:
                    ctx.emitter.line("pass")
        else:
            # Normal statement generation
            generate_statement(stmt, ctx)
        i += 1


def generate_offset_guarded_statements(
    statements: List["MStatement"],
    label_line: int,
    ctx: "GeneratorContext",
) -> None:
    """Generate statements with offset guards for computed offset support.

    Each statement is wrapped with an offset guard that
    checks if the statement should be skipped based on _start_offset.

    The guard is: if _start_offset <= offset:
    where offset = statement.line_number - label.line_number

    This ensures that when entering a label at offset N, statements
    at offsets 0 through N-1 are skipped.

    Args:
        statements: List of statements to generate
        label_line: Line number of the containing label (for offset calculation)
        ctx: Generator context
    """
    for stmt in statements:
        stmt_line = stmt.line_number
        if stmt_line is not None:
            # Calculate offset from label line
            offset = stmt_line - label_line
            ctx.emitter.line(f"if _start_offset <= {offset}:")
            with ctx.emitter.indented():
                generate_statement(stmt, ctx)
        else:
            # No line number - always execute (shouldn't happen normally)
            generate_statement(stmt, ctx)


def generate_statement(stmt: "MStatement", ctx: "GeneratorContext") -> None:
    """Generate Python statement from ASG statement node.

    Writes to ctx.emitter. Dispatches based on statement type:
    - MSetStatement → assignment
    - MWriteStatement → _rt.write() call
    - MQuitStatement → return
    - MIfStatement → if block with _test tracking
    - MElseStatement → if not _test block
    - MForStatement → for loop

    If stmt.postcondition is set, wraps the statement in a conditional:
    if m_truth(cond): <statement>

    Preserves MUMPS comments as Python comments.
    If the source line has an inline comment (;...), it is emitted
    as a Python comment before the statement.

    Args:
        stmt: ASG statement node
        ctx: Generator context with emitter

    Raises:
        NotImplementedError: For unsupported statement types
    """
    # Emit MUMPS comment as Python comment if present
    _emit_source_comment(stmt, ctx)

    # Check for postcondition
    if stmt.postcondition is not None:
        cond_expr = generate_expr(stmt.postcondition, ctx)
        ctx.emitter.line(f"if m_truth({cond_expr}):")
        ctx.emitter.indent()
        _dispatch_statement(stmt, ctx)
        ctx.emitter.dedent()
    else:
        _dispatch_statement(stmt, ctx)


def _dispatch_statement(stmt: "MStatement", ctx: "GeneratorContext") -> None:
    """Dispatch statement to type-specific generator.

    Internal helper that handles the actual statement generation
    after postcondition handling is complete.

    Args:
        stmt: ASG statement node
        ctx: Generator context with emitter

    Raises:
        NotImplementedError: For unsupported statement types
    """
    if isinstance(stmt, MSetStatement):
        _generate_set(stmt, ctx)
    elif isinstance(stmt, MWriteStatement):
        _generate_write(stmt, ctx)
    elif isinstance(stmt, MQuitStatement):
        _generate_quit(stmt, ctx)
    elif isinstance(stmt, MIfStatement):
        _generate_if(stmt, ctx)
    elif isinstance(stmt, MElseStatement):
        _generate_else(stmt, ctx)
    elif isinstance(stmt, MForStatement):
        _generate_for(stmt, ctx)
    elif isinstance(stmt, MGotoStatement):
        _generate_goto(stmt, ctx)
    elif isinstance(stmt, MDoStatement):
        _generate_do(stmt, ctx)
    elif isinstance(stmt, MKillStatement):
        _generate_kill(stmt, ctx)
    elif isinstance(stmt, MNewStatement):
        _generate_new(stmt, ctx)
    elif isinstance(stmt, MMergeStatement):
        _generate_merge(stmt, ctx)
    elif isinstance(stmt, MHangStatement):
        _generate_hang(stmt, ctx)
    elif isinstance(stmt, MHaltStatement):
        _generate_halt(stmt, ctx)
    elif isinstance(stmt, MReadStatement):
        _generate_read(stmt, ctx)
    elif isinstance(stmt, MXecuteStatement):
        _generate_xecute(stmt, ctx)
    elif isinstance(stmt, MTStartStatement):
        _generate_tstart(stmt, ctx)
    elif isinstance(stmt, MTCommitStatement):
        _generate_tcommit(stmt, ctx)
    elif isinstance(stmt, MTRollbackStatement):
        _generate_trollback(stmt, ctx)
    elif isinstance(stmt, MLockStatement):
        _generate_lock(stmt, ctx)
    elif isinstance(stmt, MOpenStatement):
        _generate_open(stmt, ctx)
    elif isinstance(stmt, MCloseStatement):
        _generate_close(stmt, ctx)
    elif isinstance(stmt, MUseStatement):
        _generate_use(stmt, ctx)
    elif isinstance(stmt, MJobStatement):
        _generate_job(stmt, ctx)
    elif isinstance(stmt, MViewStatement):
        _generate_view(stmt, ctx)
    elif isinstance(stmt, MBreakStatement):
        _generate_break(stmt, ctx)
    # Z-commands
    elif isinstance(stmt, MZWriteStatement):
        _generate_zwrite(stmt, ctx)
    elif isinstance(stmt, (MZKillStatement, MZWithdrawStatement)):
        _generate_zkill(stmt, ctx)
    elif isinstance(stmt, MZLinkStatement):
        _generate_zlink(stmt, ctx)
    elif isinstance(stmt, MZLoadStatement):
        _generate_zload(stmt, ctx)
    elif isinstance(stmt, MZShowStatement):
        _generate_zshow(stmt, ctx)
    elif isinstance(stmt, MZGotoStatement):
        _generate_zgoto(stmt, ctx)
    elif isinstance(stmt, MZHaltStatement):
        _generate_zhalt(stmt, ctx)
    # Unimplemented Z-commands
    elif isinstance(stmt, MZAllocateStatement):
        raise NotImplementedError("LIM-015: ZALLOCATE command not supported")
    elif isinstance(stmt, MZDeallocateStatement):
        raise NotImplementedError("LIM-015: ZDEALLOCATE command not supported")
    elif isinstance(stmt, MZBreakStatement):
        raise NotImplementedError("LIM-015: ZBREAK command not supported")
    elif isinstance(stmt, MZCompileStatement):
        raise NotImplementedError("LIM-015: ZCOMPILE command not supported")
    elif isinstance(stmt, MZContinueStatement):
        raise NotImplementedError("LIM-015: ZCONTINUE command not supported")
    elif isinstance(stmt, MZEditStatement):
        raise NotImplementedError("LIM-015: ZEDIT command not supported")
    elif isinstance(stmt, MZHelpStatement):
        raise NotImplementedError("LIM-015: ZHELP command not supported")
    elif isinstance(stmt, MZMessageStatement):
        _generate_zmessage(stmt, ctx)
    elif isinstance(stmt, MZPrintStatement):
        _generate_zprint(stmt, ctx)
    elif isinstance(stmt, MZStepStatement):
        # ZSTEP is a debugger-only command (single-step control).
        # No runtime impact on program output — emit as no-op.
        ctx.emitter.line("pass  # ZSTEP command no-op (debugger)")
    elif isinstance(stmt, MZSystemStatement):
        _generate_zsystem(stmt, ctx)
    elif isinstance(stmt, MZTriggerStatement):
        raise NotImplementedError("LIM-015: ZTRIGGER command not supported")
    # ANSI commands not supported by YDB
    elif isinstance(stmt, MKSubscriptsStatement):
        raise NotImplementedError(
            "LIM-016: KSUBSCRIPTS command not supported (not implemented in YDB)"
        )
    elif isinstance(stmt, MKValueStatement):
        raise NotImplementedError(
            "LIM-016: KVALUE command not supported (not implemented in YDB)"
        )
    else:
        raise NotImplementedError(f"Unsupported statement type: {type(stmt).__name__}")


def _generate_set(stmt: MSetStatement, ctx: "GeneratorContext") -> None:
    """Generate Python assignment from MSetStatement.

    When using TRAMPOLINE strategy and the variable is in state_vars,
    assigns to `state.VAR` instead of just `VAR`.

    Handles subscripted assignments for MArray-backed variables.
    For array variables, generates: state.A[subscripts] = value

    For SIMPLE_FUNCTIONS strategy, stores variables in _scope dictionary
    for cross-routine visibility: _scope['VAR'] = value

    Handles name indirection targets (@VAR) by generating:
    _rt.set_var(name_expr, value, _scope)

    Handles argument indirections (S @A where A="X=1") by generating:
    _rt.execute_mumps("S " + value, _scope)

    Uses ordered_items to maintain left-to-right evaluation order
    when SET has interleaved argument indirections (S X=1,@A,Y=2).

    Args:
        stmt: MSetStatement node
        ctx: Generator context
    """
    # Import MIndirection here to avoid circular imports at module level
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.asg.statements import MAssignment
    from m2py.codegen.indirection import (
        generate_set_argument_indirection,
    )

    # Use ordered_items for correct left-to-right evaluation
    # ordered_items is always populated by the semantic analyzer

    # Detect tuple SETs: consecutive assignments sharing the same value object
    # For tuple SETs like (A,B,B(A,B))="I", subscripts must be evaluated BEFORE
    # any assignments, per MUMPS 1995 spec
    i = 0
    while i < len(stmt.ordered_items):
        item = stmt.ordered_items[i]

        if isinstance(item, MIndirectionType):
            # Argument indirection: S @A where A contains "target=value"
            generate_set_argument_indirection(item, ctx)
            i += 1
        elif isinstance(item, MAssignment):
            # Check if this is the start of a tuple SET (multiple assignments with same value)
            tuple_assignments = [item]
            j = i + 1
            while j < len(stmt.ordered_items):
                next_item = stmt.ordered_items[j]
                if isinstance(next_item, MAssignment) and next_item.value is item.value:
                    tuple_assignments.append(next_item)
                    j += 1
                else:
                    break

            if len(tuple_assignments) > 1:
                # Tuple SET: pre-evaluate subscripts, then assign
                _generate_tuple_set(tuple_assignments, ctx)
                i = j
            else:
                # Regular single assignment
                _generate_single_assignment(item, ctx)
                i += 1
        else:
            i += 1


def _generate_tuple_set(assignments: list, ctx: "GeneratorContext") -> None:
    """Generate code for a tuple SET like (A,B,B(A,B))="I".

    MUMPS 1995 spec (Section 8.2.30) defines the evaluation order:
    1. ALL subscripts in ALL targets are evaluated (left-to-right)
    2. The RHS expression is evaluated
    3. Assignments are performed (left-to-right)

    This order is critical for naked global references because:
    - Subscript evaluation affects the naked indicator
    - RHS evaluation affects the naked indicator
    - Assignment to explicit globals affects the naked indicator
    - Naked global targets use the naked indicator at assignment time

    Example: S (^(^(1),^B(2)),^C(3))=^D(4)
    1. Eval subscripts: ^(1) uses current naked, ^B(2) updates naked to ^B
    2. Eval RHS: ^D(4) updates naked to ^D
    3. Assign: first target uses naked ^D, ^C(3) updates naked to ^C

    Args:
        assignments: List of MAssignment objects sharing the same value
        ctx: Generator context
    """

    # STEP 1: Pre-evaluate ALL subscripts in ALL targets FIRST
    # This must happen before RHS evaluation to maintain correct naked indicator flow
    pre_eval_map = {}  # Maps (assignment_index, subscript_index) -> temp_var_name
    temp_counter = 0

    for idx, assignment in enumerate(assignments):
        target = assignment.target
        subscripts = getattr(target, "subscripts", None) or []
        if subscripts:
            for sub_idx, sub in enumerate(subscripts):
                # Pre-evaluate ALL subscripts to capture correct naked indicator state
                # Also needed if subscript references a variable modified by prior assignments
                temp_name = f"_tuple_sub_{temp_counter}"
                temp_counter += 1
                sub_expr = generate_expr(sub, ctx)
                ctx.emitter.line(f"{temp_name} = {sub_expr}")
                pre_eval_map[(idx, sub_idx)] = temp_name

    # STEP 2: Pre-evaluate the shared VALUE expression ONCE
    # All assignments share the same value object
    shared_value = assignments[0].value
    value_expr = generate_expr(shared_value, ctx)
    ctx.emitter.line(f"_tuple_value = m_str({value_expr})")

    # STEP 3: Generate all assignments, using pre-evaluated subscripts and value
    for idx, assignment in enumerate(assignments):
        _generate_single_assignment_with_preeval_subs(
            assignment, idx, pre_eval_map, "_tuple_value", ctx
        )


def _generate_single_assignment_with_preeval_subs(
    assignment, idx: int, pre_eval_map: dict, value_var: str, ctx: "GeneratorContext"
) -> None:
    """Generate a single assignment using pre-evaluated subscripts and value.

    This is used by tuple SET to ensure:
    1. All subscripts are evaluated BEFORE the RHS (per MUMPS spec 8.2.30)
    2. The shared value is evaluated once and reused for all targets

    The pre_eval_map contains ALL subscripts pre-evaluated, which is critical
    for correct naked indicator behavior in complex expressions like:
    S (^(^(1),^B(2)),^C(3))=^D(4)

    Args:
        assignment: MAssignment to generate
        idx: Index of this assignment in the tuple
        pre_eval_map: Map of (idx, sub_idx) -> temp_var_name for pre-evaluated subscripts
        value_var: Name of the variable holding the pre-evaluated value
        ctx: Generator context
    """
    from m2py.asg.expressions import (
        MIndirection as MIndirectionType,
        MIntrinsicFunction,
        MVariable,
    )
    from m2py.codegen.indirection import generate_name_indirection_write
    from m2py.parser.textx_classes import LocalVariable, GlobalVariable, NakedGlobal

    if assignment.target is None:
        return

    # Handle indirection targets
    if isinstance(assignment.target, MIndirectionType):
        set_stmt = generate_name_indirection_write(assignment.target, value_var, ctx)
        ctx.emitter.line(set_stmt)
        return

    # Handle special variable targets in tuple SET: S ($X,$Y)=0
    if isinstance(assignment.target, MSpecialVariable):
        svar_name = assignment.target.name.upper()
        if svar_name in ("ETRAP", "ET"):
            ctx.emitter.line(f"_rt.set_etrap({value_var})")
        elif svar_name in ("ECODE", "EC"):
            ctx.emitter.line(f"_rt.set_ecode({value_var})")
        elif svar_name in ("ZERROR", "ZE"):
            ctx.emitter.line(f"_rt.set_zerror({value_var})")
        elif svar_name in ("ZTRAP", "ZT"):
            ctx.emitter.line(f"_rt.set_ztrap({value_var})")
        elif svar_name in ("ZSTATUS", "ZS"):
            ctx.emitter.line(f"_rt.set_zstatus({value_var})")
        elif svar_name in ("ZPOSITION", "ZP"):
            ctx.emitter.line(f"_rt.set_zposition({value_var})")
        elif svar_name == "X":
            ctx.emitter.line(f"_rt.set_x({value_var})")
        elif svar_name == "Y":
            ctx.emitter.line(f"_rt.set_y({value_var})")
        elif svar_name in ("NAMESPACE", "NSPACE"):
            ctx.emitter.line(f"_rt.set_namespace({value_var})")
        elif svar_name in ("ZINTERRUPT", "ZINT"):
            ctx.emitter.line(f"_rt.set_zinterrupt({value_var})")
        elif svar_name == "ZERR":
            ctx.emitter.line(f"_rt.set_zerror({value_var})")
        elif svar_name in ("ZSOURCE", "ZSO"):
            ctx.emitter.line(f"_rt.set_zsource({value_var})")
        elif svar_name == "ZGBLDIR":
            ctx.emitter.line(f"_rt.set_zgbldir({value_var})")
        elif svar_name in ("ZDIRECTORY", "ZD"):
            ctx.emitter.line("import os")
            ctx.emitter.line(f"os.chdir(str({value_var}))")
        elif svar_name in ("ZSTEP", "ZSTE"):
            ctx.emitter.line("pass  # SET $ZSTEP no-op (debugger intrinsic)")
        else:
            raise NotImplementedError(
                f"SET ${assignment.target.name} not supported in tuple SET"
            )
        return

    # Handle $PIECE/$EXTRACT targets in tuple SET: S ($P(X,"^",2),Y)=value
    if isinstance(assignment.target, MIntrinsicFunction):
        func = assignment.target
        func_name = func.name.upper()
        args = func.arguments
        if func_name in ("P", "PIECE"):
            if len(args) < 2:
                raise ValueError(
                    f"LHS $PIECE requires at least 2 arguments, got {len(args)}"
                )
            first_arg = args[0]
            getter, setter = _build_lhs_getter_setter(
                first_arg, ctx, str_wrap_getter=True
            )
            delimiter_expr = f"m_str({generate_expr(args[1], ctx)})"
            if len(args) >= 3:
                piece_from_expr = f"int(m_num({generate_expr(args[2], ctx)}))"
            else:
                piece_from_expr = "1"
            if len(args) >= 4:
                arg3 = args[3]
                assert arg3 is not None
                piece_to_expr = f"int(m_num({generate_expr(arg3, ctx)}))"
            else:
                piece_to_expr = "None"
            ctx.emitter.line(
                f"m_set_piece({getter}, {setter}, {delimiter_expr}, "
                f"{piece_from_expr}, {piece_to_expr}, m_str({value_var}))"
            )
        elif func_name in ("E", "EXTRACT"):
            if len(args) < 1:
                raise ValueError(
                    f"LHS $EXTRACT requires at least 1 argument, got {len(args)}"
                )
            first_arg = args[0]
            getter, setter = _build_lhs_getter_setter(first_arg, ctx)
            if len(args) == 1:
                from_pos_expr = "1"
                to_pos_expr = "1"
            elif len(args) == 2:
                from_pos_expr = generate_expr(args[1], ctx)
                to_pos_expr = "None"
            else:
                from_pos_expr = generate_expr(args[1], ctx)
                arg2 = args[2]
                assert arg2 is not None
                to_pos_expr = generate_expr(arg2, ctx)
            ctx.emitter.line(
                f"m_set_extract({getter}, {setter}, {from_pos_expr}, "
                f"{to_pos_expr}, {value_var})"
            )
        else:
            raise NotImplementedError(
                f"Unsupported LHS function in tuple SET: ${func.name}"
            )
        return

    target = assignment.target
    subscripts = getattr(target, "subscripts", None) or []

    # Build subscript expressions, using pre-evaluated values where available
    subscript_exprs = []
    for sub_idx, sub in enumerate(subscripts):
        if (idx, sub_idx) in pre_eval_map:
            subscript_exprs.append(pre_eval_map[(idx, sub_idx)])
        else:
            subscript_exprs.append(generate_expr(sub, ctx))

    # Generate the assignment based on target type
    if isinstance(target, (MVariable, LocalVariable)):
        var_name = target.name

        if subscript_exprs:
            # Subscripted assignment
            base = var_base_expr(var_name, ctx, for_write=True)
            ctx.emitter.line(f"{base}[{', '.join(subscript_exprs)}] = {value_var}")
        else:
            # Simple assignment
            ctx.emitter.line(var_write_stmt(var_name, value_var, ctx))
    elif isinstance(target, GlobalVariable):
        global_name = target.name
        subscripts_tuple = gen_subscripts_tuple(subscript_exprs, ctx)
        ctx.emitter.line(
            f'_rt.globals.set("{global_name}", {subscripts_tuple}, {value_var})'
        )
    elif isinstance(target, NakedGlobal):
        # Naked global target with pre-evaluated value
        # Generate subscript expressions for the naked global
        naked_subscript_exprs = []
        for sub_idx, sub in enumerate(subscripts):
            if (idx, sub_idx) in pre_eval_map:
                naked_subscript_exprs.append(pre_eval_map[(idx, sub_idx)])
            else:
                naked_subscript_exprs.append(generate_expr(sub, ctx))

        subscripts_tuple = gen_subscripts_tuple(naked_subscript_exprs, ctx)

        ctx.emitter.line(
            f"_name, _subs = _rt.globals.resolve_naked({subscripts_tuple})"
        )
        ctx.emitter.line(f"_rt.globals.set(_name, _subs, {value_var})")
    else:
        raise NotImplementedError(
            f"Unsupported target type in tuple SET: {type(target).__name__}"
        )


def _generate_single_assignment(
    assignment: MAssignment, ctx: "GeneratorContext"
) -> None:
    """Generate code for a single SET assignment.

    Extracted from _generate_set to support ordered_items iteration.
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.codegen.indirection import generate_name_indirection_write

    if assignment.target is None or assignment.value is None:
        return

    # Handle indirection targets (@VAR, @@VAR, @NAME@(1,2))
    # Uses unified set_indirected() which internally uses IndirectionResolver
    if isinstance(assignment.target, MIndirectionType):
        # Generate value expression first
        value_expr = generate_expr(assignment.value, ctx)
        # Generate the set_indirected call via unified indirection module
        set_stmt = generate_name_indirection_write(assignment.target, value_expr, ctx)
        ctx.emitter.line(set_stmt)
        return

    # Handle special variable assignments ($ETRAP, $ECODE, $ZERROR)
    # Also handles $ZTRAP, $ZSTATUS, $ZPOSITION
    if isinstance(assignment.target, MSpecialVariable):
        value_expr = generate_expr(assignment.value, ctx)
        svar_name = assignment.target.name.upper()
        if svar_name in ("ETRAP", "ET"):
            ctx.emitter.line(f"_rt.set_etrap({value_expr})")
        elif svar_name in ("ECODE", "EC"):
            ctx.emitter.line(f"_rt.set_ecode({value_expr})")
        elif svar_name in ("ZERROR", "ZE"):
            ctx.emitter.line(f"_rt.set_zerror({value_expr})")
        elif svar_name in ("ZTRAP", "ZT"):
            ctx.emitter.line(f"_rt.set_ztrap({value_expr})")
        elif svar_name in ("ZSTATUS", "ZS"):
            ctx.emitter.line(f"_rt.set_zstatus({value_expr})")
        elif svar_name in ("ZPOSITION", "ZP"):
            ctx.emitter.line(f"_rt.set_zposition({value_expr})")
        elif svar_name == "X":
            ctx.emitter.line(f"_rt.set_x({value_expr})")
        elif svar_name == "Y":
            ctx.emitter.line(f"_rt.set_y({value_expr})")
        elif svar_name in ("NAMESPACE", "NSPACE"):
            ctx.emitter.line(f"_rt.set_namespace({value_expr})")
        elif svar_name in ("ZINTERRUPT", "ZINT"):
            ctx.emitter.line(f"_rt.set_zinterrupt({value_expr})")
        elif svar_name == "ZERR":
            # $ZERR is a non-standard abbreviation for $ZERROR
            ctx.emitter.line(f"_rt.set_zerror({value_expr})")
        elif svar_name in ("ZSOURCE", "ZSO"):
            ctx.emitter.line(f"_rt.set_zsource({value_expr})")
        elif svar_name == "ZGBLDIR":
            ctx.emitter.line(f"_rt.set_zgbldir({value_expr})")
        elif svar_name in ("ZDIRECTORY", "ZD"):
            ctx.emitter.line("import os")
            ctx.emitter.line(f"os.chdir(str({value_expr}))")
        elif svar_name in ("TEST", "T"):
            # SET $TEST: update both _rt._test (runtime) and _test (module global)
            # so subsequent reads of $TEST via int(_test) see the new value.
            ctx.emitter.line(f"_rt._test = bool(m_truth({value_expr}))")
            ctx.emitter.line("_test = _rt._test")
        elif svar_name in ("ZSTEP", "ZSTE"):
            # $ZSTEP is a debugger intrinsic — SET $ZSTEP="code" defines
            # the step action.  No runtime impact; emit as no-op.
            ctx.emitter.line("pass  # SET $ZSTEP no-op (debugger intrinsic)")
        else:
            raise NotImplementedError(f"SET ${assignment.target.name} not supported")
        return

    # Get target variable name
    target_name = None
    if isinstance(assignment.target, MVariable):
        target_name = translate_name(assignment.target.name)
        var_name = assignment.target.name

        # Handle subscripted array assignments
        if assignment.target.subscripts:
            # Generate subscript expressions
            # Pass subscript_context=True so indirection in subscripts
            # returns VALUE instead of validating as NAME
            subscript_exprs = [
                generate_expr(sub, ctx, subscript_context=True)
                for sub in assignment.target.subscripts
            ]

            # Check if any LHS subscript contains naked global references
            # If so, we must pre-evaluate them BEFORE evaluating the RHS
            # because Python evaluates `a[x] = y` as y first, then a, then x,
            # but MUMPS requires left-to-right evaluation order.
            has_naked_in_subscripts = any(
                contains_naked_global(sub) for sub in assignment.target.subscripts
            )

            # Dynamic locals for argumentless KILL/NEW support
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # Access MArray from _locals dict, auto-vivify if needed
                base = f"state._locals.setdefault({target_name!r}, MArray())"
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.array_vars:
                # MArray in RoutineState: state.A[subscripts] = value
                base = f"state.{target_name}"
            elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                # Auto-vivify MArray for subscripted locals
                # _scope.setdefault('A', MArray())[subscripts] = value
                base = f"_scope.setdefault({target_name!r}, MArray())"
            else:
                # TRAMPOLINE var not in array_vars — store in _scope for
                # cross-routine visibility and consistency
                base = f"_scope.setdefault({target_name!r}, MArray())"

            if has_naked_in_subscripts:
                # Pre-evaluate subscripts to preserve correct naked reference order
                # Generate: _sub_0 = sub_expr_0; _sub_1 = sub_expr_1; ...
                # Then: base[(_sub_0, _sub_1)] = value
                for i, sub_expr in enumerate(subscript_exprs):
                    ctx.emitter.line(f"_sub_{i} = {sub_expr}")
                # Now evaluate the value expression
                value_expr = generate_expr(assignment.value, ctx)
                # Use pre-evaluated subscripts
                if len(subscript_exprs) == 1:
                    ctx.emitter.line(f"{base}[_sub_0] = {value_expr}")
                else:
                    sub_refs = ", ".join(
                        f"_sub_{i}" for i in range(len(subscript_exprs))
                    )
                    ctx.emitter.line(f"{base}[{sub_refs}] = {value_expr}")
            else:
                # No naked globals in subscripts - use standard generation
                # Format subscripts: single key or tuple
                if len(subscript_exprs) == 1:
                    target_expr = f"{base}[{subscript_exprs[0]}]"
                else:
                    target_expr = f"{base}[{', '.join(subscript_exprs)}]"

                # Generate value expression and emit assignment
                value_expr = generate_expr(assignment.value, ctx)
                ctx.emitter.line(f"{target_expr} = {value_expr}")
            return

        # Dynamic locals for argumentless KILL/NEW support
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Store in _locals dict as MArray for consistency with subscripted access
            target_name = f"state._locals.setdefault({target_name!r}, MArray()).value"
        # Check if variable should be accessed via state (TRAMPOLINE)
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
            if var_name in ctx.array_vars:
                # Array vars use .value for scalar SET to preserve MArray type.
                # This prevents type-narrowing issues: state.X = 0 would
                # narrow the type to int, breaking later state.X[sub] access.
                target_name = f"state.{target_name}.value"
            else:
                target_name = f"state.{target_name}"
        elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Store variables in _scope using MArray for consistency
            # This allows later subscripted access: S X=1 S X(1)=2 both work
            target_name = f"_scope.setdefault({target_name!r}, MArray()).value"
        else:
            # TRAMPOLINE var not in state_vars — store in _scope for
            # cross-routine visibility and to avoid F841 bare-local lint
            target_name = f"_scope.setdefault({target_name!r}, MArray()).value"

    elif isinstance(assignment.target, GlobalVariable):
        # Handle global variable SET targets
        # Generate: _rt.globals.set("NAME", (subscripts,), value)
        _generate_global_set(assignment, ctx)
        return

    elif isinstance(assignment.target, (ExtendedGlobalBracket, ExtendedGlobalPipe)):
        # Handle extended global reference SET targets
        # Pass namespace through to _rt.globals.set_ns()
        _generate_extended_global_set(assignment, ctx)
        return

    elif isinstance(assignment.target, NakedGlobal):
        # Handle naked global reference SET targets
        # Generate: resolve_naked then set
        _generate_naked_global_set(assignment, ctx)
        return

    elif isinstance(assignment.target, MIntrinsicFunction):
        # Handle LHS function targets ($PIECE, $EXTRACT)
        func_name = assignment.target.name.upper()

        if func_name in ("P", "PIECE"):
            _generate_lhs_piece(assignment, ctx)
            return
        elif func_name in ("E", "EXTRACT"):
            _generate_lhs_extract(assignment, ctx)
            return
        else:
            raise NotImplementedError(
                f"Unsupported LHS function: ${assignment.target.name}"
            )
    else:
        raise NotImplementedError(
            f"Unsupported SET target type: {type(assignment.target).__name__}"
        )

    # Generate value expression
    value_expr = generate_expr(assignment.value, ctx)

    # Emit assignment
    ctx.emitter.line(f"{target_name} = {value_expr}")


def _build_lhs_getter_setter(
    target: "MExpr",
    ctx: "GeneratorContext",
    *,
    str_wrap_getter: bool = False,
) -> tuple[str, str]:
    """Build getter/setter lambda expressions for LHS variable access.

    Handles all variable types: GlobalVariable, NakedGlobal, MIndirection, MVariable.
    3-way strategy dispatch for MVariable.

    For NakedGlobal targets, emits a resolve_naked() pre-computation line via
    ctx.emitter (side effect) before returning getter/setter strings.

    Args:
        target: ASG expression node for the LHS target variable (first arg
            of $PIECE/$EXTRACT).
        ctx: Current generator context.
        str_wrap_getter: If True, wrap MVariable getter results in str().
            Used by $PIECE which requires string values; $EXTRACT does not.

    Returns:
        (getter_expr, setter_expr) tuple of Python lambda expression strings.
    """
    if isinstance(target, GlobalVariable):
        global_name = target.name
        subscripts_tuple = gen_subscripts_tuple(target.subscripts, ctx, str_wrap=True)
        getter = f'lambda: _rt.globals.get("{global_name}", {subscripts_tuple}) or ""'
        setter = f'lambda v: _rt.globals.set("{global_name}", {subscripts_tuple}, v)'
    elif isinstance(target, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
        # Extended global LHS with namespace prefix
        global_name = target.name
        ns = getattr(target.environment, "value", "") if target.environment else ""
        ns_name = f"{ns}:{global_name}" if ns else global_name
        subscripts_tuple = gen_subscripts_tuple(target.subscripts, ctx, str_wrap=True)
        getter = f'lambda: _rt.globals.get("{ns_name}", {subscripts_tuple}) or ""'
        setter = f'lambda v: _rt.globals.set("{ns_name}", {subscripts_tuple}, v)'
    elif isinstance(target, NakedGlobal):
        # Naked global: resolve ONCE before the m_set_piece/m_set_extract call.
        # resolve_naked() returns (name, subscripts) from the naked indicator.
        #
        # IMPORTANT: Callers (_generate_lhs_piece, _generate_lhs_extract) must
        # ensure the RHS value expression is pre-computed BEFORE calling this
        # function for NakedGlobal targets.  In MUMPS, the RHS is evaluated
        # before the LHS naked reference is resolved, so global refs in the
        # RHS may change the naked indicator that resolve_naked uses.
        subscripts_tuple = gen_subscripts_tuple(target.subscripts, ctx)

        temp_name = f"_lhs_name_{id(target) % 10000}"
        temp_subs = f"_lhs_subs_{id(target) % 10000}"

        ctx.emitter.line(
            f"{temp_name}, {temp_subs} = _rt.globals.resolve_naked({subscripts_tuple})"
        )

        getter = f'lambda: _rt.globals.get({temp_name}, {temp_subs}) or ""'
        setter = f"lambda v: _rt.globals.set({temp_name}, {temp_subs}, v)"
    elif isinstance(target, MIndirection):
        from m2py.codegen.indirection import _count_indirection_levels

        levels, inner_expr = _count_indirection_levels(target)

        if target.name_indirection_subscripts:
            per_level_subs_code = []
            for sub_list in target.name_indirection_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                per_level_subs_code.append(f"[{', '.join(sub_exprs)}]")
            per_level_subscripts_str = f"[{', '.join(per_level_subs_code)}]"

            if isinstance(inner_expr, MVariable):
                base_name = inner_expr.name
                name_expr = f'_rt.resolve_for_target("{base_name}", _scope, levels={levels}, per_level_subscripts={per_level_subscripts_str})'
            else:
                name_expr_base = generate_expr(inner_expr, ctx)
                name_expr = f"_rt.resolve_for_target(str({name_expr_base}), _scope, levels={levels}, per_level_subscripts={per_level_subscripts_str})"
        else:
            if isinstance(inner_expr, MVariable):
                base_name = inner_expr.name
                name_expr = (
                    f'_rt.resolve_for_target("{base_name}", _scope, levels={levels})'
                )
            else:
                name_expr_base = generate_expr(inner_expr, ctx)
                if levels > 1:
                    name_expr = f"_rt.resolve_for_target(str({name_expr_base}), _scope, levels={levels - 1})"
                else:
                    name_expr = f"str({name_expr_base})"

        getter = f'lambda: _rt.get_var({name_expr}, _scope) or ""'
        setter = f"lambda v: _rt.set_var({name_expr}, v, _scope)"
    elif isinstance(target, MVariable):
        var_name = target.name
        translated_name = translate_name(var_name)

        if target.subscripts:
            # Subscripted local variable: X(1), X(1,2), etc.
            subs_code = [generate_expr(sub, ctx) for sub in target.subscripts]
            subs_args = ", ".join(subs_code)

            base_get = (
                f"_scope.setdefault({translated_name!r}, MArray()).get({subs_args})"
                f" or ''"
            )
            if str_wrap_getter:
                getter = f"lambda: str({base_get})"
            else:
                getter = f"lambda: {base_get}"
            setter = (
                f"lambda v: _scope.setdefault({translated_name!r}, MArray())"
                f".set({subs_args}, value=v)"
            )
        else:
            # Unsubscripted variable — 3-way strategy dispatch
            if ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                # TRAMPOLINE with state_vars
                base_get = f"getattr(state, {translated_name!r}, '') or ''"
                if str_wrap_getter:
                    getter = f"lambda: str({base_get})"
                else:
                    getter = f"lambda: {base_get}"
                setter = f"lambda v: setattr(state, {translated_name!r}, v)"
            else:
                # SIMPLE_FUNCTIONS or TRAMPOLINE without state_vars
                base_get = f"m_var_value(_scope.get({translated_name!r})) or ''"
                if str_wrap_getter:
                    getter = f"lambda: str({base_get})"
                else:
                    getter = f"lambda: {base_get}"
                setter = (
                    f"lambda v: setattr(_scope.setdefault({translated_name!r},"
                    f" MArray()), 'value', v)"
                )
    else:
        raise NotImplementedError(
            f"LHS $PIECE/$EXTRACT first argument must be a variable, "
            f"got {type(target).__name__}"
        )

    return getter, setter


def _generate_lhs_piece(assignment: MAssignment, ctx: "GeneratorContext") -> None:
    """Generate m_set_piece() call for LHS $PIECE assignment.

    Generate code for S $P(var,"^",pos)=value

    Args:
        assignment: MAssignment with IntrinsicFunction target
        ctx: Generator context

    The generated code calls m_set_piece with getter/setter lambdas:
        m_set_piece(
            lambda: _scope.get('X', MArray()).value or '',
            lambda v: _scope.__setitem__('X', MArray(value=v)) if not isinstance(_scope.get('X'), MArray) else setattr(_scope['X'], 'value', v),
            '^', 2, None, 'NEW'
        )

    For global variables:
        m_set_piece(
            lambda: _rt.globals.get("G", ()) or '',
            lambda v: _rt.globals.set("G", (), v),
            '^', 2, None, 'NEW'
        )
    """
    # We know target is MIntrinsicFunction because caller checked isinstance
    assert isinstance(assignment.target, MIntrinsicFunction)
    func = assignment.target
    args = func.arguments

    # $PIECE(var, delimiter [, piece_from [, piece_to]])
    # Per MUMPS standard, piece_from defaults to 1 if not specified
    if len(args) < 2:
        raise ValueError(f"LHS $PIECE requires at least 2 arguments, got {len(args)}")

    first_arg = args[0]

    # Generate delimiter expression (must be string)
    # Use m_str for MUMPS canonical form (e.g., 0.0 → "0")
    delimiter_expr = f"m_str({generate_expr(args[1], ctx)})"

    # Generate piece_from expression (defaults to 1 per MUMPS standard)
    # Must be converted to int since MUMPS expressions return strings
    if len(args) >= 3:
        piece_from_expr = f"int(m_num({generate_expr(args[2], ctx)}))"
    else:
        piece_from_expr = "1"

    # Generate piece_to expression (optional, 4th argument)
    # Must be converted to int since MUMPS expressions return strings
    if len(args) >= 4:
        arg3 = args[3]
        assert arg3 is not None  # Type narrowing for type checker
        piece_to_expr = f"int(m_num({generate_expr(arg3, ctx)}))"
    else:
        piece_to_expr = "None"

    # Generate value expression (wrapped in m_str to ensure string type)
    assert assignment.value is not None, "LHS $PIECE requires a value"
    value_expr = f"m_str({generate_expr(assignment.value, ctx)})"

    # CRITICAL: MUMPS evaluation order for S $P(^(subs),delim,from,to)=value:
    # 1. Evaluate ALL expressions (subscripts, delim, from, to, value)
    # 2. THEN resolve the naked reference for the target variable
    # 3. Read current value of target, modify pieces, write back
    #
    # When the LHS is a NakedGlobal, global references in the value
    # expression (or other arguments) may change the naked indicator.
    # We must pre-compute the value BEFORE calling _build_lhs_getter_setter
    # (which emits resolve_naked for NakedGlobal targets).
    if isinstance(first_arg, NakedGlobal):
        ctx.emitter.line(f"_sp_value = {value_expr}")
        getter, setter = _build_lhs_getter_setter(first_arg, ctx, str_wrap_getter=True)
        ctx.emitter.line(
            f"m_set_piece({getter}, {setter}, {delimiter_expr}, "
            f"{piece_from_expr}, {piece_to_expr}, _sp_value)"
        )
        return

    # Non-naked targets: standard order (resolve LHS, then evaluate args inline)
    getter, setter = _build_lhs_getter_setter(first_arg, ctx, str_wrap_getter=True)

    # Emit m_set_piece call
    ctx.emitter.line(
        f"m_set_piece({getter}, {setter}, {delimiter_expr}, {piece_from_expr}, {piece_to_expr}, {value_expr})"
    )


def _generate_lhs_extract(assignment: MAssignment, ctx: "GeneratorContext") -> None:
    """Generate m_set_extract() call for LHS $EXTRACT assignment.

    Generates code for S $E(var,from,to)=value

    Args:
        assignment: MAssignment with IntrinsicFunction target
        ctx: Generator context

    The generated code calls m_set_extract with getter/setter lambdas:
        m_set_extract(
            lambda: _scope.get('X', ''),
            lambda v: _scope.__setitem__('X', v),
            2, 3, 'XX'
        )

    For global variables:
        m_set_extract(
            lambda: _rt.globals.get("G", ()) or '',
            lambda v: _rt.globals.set("G", (), v),
            2, 3, 'XX'
        )
    """
    # We know target is MIntrinsicFunction because caller checked isinstance
    assert isinstance(assignment.target, MIntrinsicFunction)
    func = assignment.target
    args = func.arguments

    # $EXTRACT(var [, from_pos [, to_pos]])
    # 1-arg form: $E(X) is shorthand for $E(X,1,1) — replace first character
    if len(args) < 1:
        raise ValueError(f"LHS $EXTRACT requires at least 1 argument, got {len(args)}")

    # First argument must be a variable (local or global)
    first_arg = args[0]

    # Generate from_pos and to_pos expressions
    if len(args) == 1:
        # $E(X) = shorthand for $E(X,1,1) — replace first character
        from_pos_expr = "1"
        to_pos_expr = "1"
    elif len(args) == 2:
        from_pos_expr = generate_expr(args[1], ctx)
        to_pos_expr = "None"
    else:
        from_pos_expr = generate_expr(args[1], ctx)
        arg2 = args[2]
        assert arg2 is not None  # Type narrowing for type checker
        to_pos_expr = generate_expr(arg2, ctx)

    # Generate value expression
    assert assignment.value is not None, "LHS $EXTRACT requires a value"
    value_expr = generate_expr(assignment.value, ctx)

    # CRITICAL: Same naked evaluation order fix as _generate_lhs_piece.
    # For NakedGlobal targets, pre-compute value BEFORE resolve_naked.
    if isinstance(first_arg, NakedGlobal):
        ctx.emitter.line(f"_se_value = {value_expr}")
        getter, setter = _build_lhs_getter_setter(first_arg, ctx)
        ctx.emitter.line(
            f"m_set_extract({getter}, {setter}, {from_pos_expr}, "
            f"{to_pos_expr}, _se_value)"
        )
        return

    # Non-naked targets: standard order
    getter, setter = _build_lhs_getter_setter(first_arg, ctx)

    # Emit m_set_extract call
    ctx.emitter.line(
        f"m_set_extract({getter}, {setter}, {from_pos_expr}, {to_pos_expr}, {value_expr})"
    )


def _generate_global_set(assignment: MAssignment, ctx: "GeneratorContext") -> None:
    """Generate _rt.globals.set() call for global variable SET.

    Generates code for S ^NAME(subscripts)=value

    Args:
        assignment: MAssignment with GlobalVariable target
        ctx: Generator context

    The generated code calls _rt.globals.set():
        _rt.globals.set("NAME", (sub1, sub2), "value")
        _rt.globals.set("NAME", (), "value")  # No subscripts

    Subscripts are NOT wrapped in str() - the runtime's _canonicalize_subscript
    handles type-aware canonicalization. Numeric literals canonicalize differently
    than string literals (e.g., Decimal("1.0") → "1", but "1.0" → "1.0").
    """
    # We know target is GlobalVariable because caller checked isinstance
    assert isinstance(assignment.target, GlobalVariable)
    global_var = assignment.target

    # Get global name (without caret)
    global_name = global_var.name

    # Generate subscript expressions
    # DO NOT wrap in str() - let runtime handle canonicalization
    # Pass subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    subscripts_tuple = gen_subscripts_tuple(
        global_var.subscripts or [], ctx, subscript_context=True
    )

    # Generate value expression
    assert assignment.value is not None, "Global SET requires a value"
    value_expr = generate_expr(assignment.value, ctx)

    # Emit _rt.globals.set() call
    # Use m_str() to format numbers in MUMPS canonical form (no E-notation)
    ctx.emitter.line(
        f"_rt.globals.set({global_name!r}, {subscripts_tuple}, m_str({value_expr}))"
    )


def _generate_extended_global_set(
    assignment: MAssignment, ctx: "GeneratorContext"
) -> None:
    """Generate _rt.globals.set_ns() call for extended global reference SET.

    Generates code for S ^["env"]NAME(subscripts)=value
    and S ^|"env"|NAME(subscripts)=value.

    The namespace is passed to the runtime's set_ns() method which prefixes
    the global name internally, allowing isolation per environment.

    Args:
        assignment: MAssignment with ExtendedGlobalBracket or ExtendedGlobalPipe target
        ctx: Generator context

    The generated code calls _rt.globals.set_ns() with the namespace:
        _rt.globals.set_ns("NAME", ("sub1", "sub2"), "value", namespace="env")
    """
    assert isinstance(assignment.target, (ExtendedGlobalBracket, ExtendedGlobalPipe))
    ext_global = assignment.target

    # Get global name and namespace
    global_name = ext_global.name
    ns = getattr(ext_global.environment, "value", "") if ext_global.environment else ""

    # Generate subscript expressions
    # DO NOT wrap in str() - let runtime handle canonicalization
    # Pass subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    subscripts_tuple = gen_subscripts_tuple(
        ext_global.subscripts or [], ctx, subscript_context=True
    )

    # Generate value expression
    assert assignment.value is not None, "Global SET requires a value"
    value_expr = generate_expr(assignment.value, ctx)

    # Emit _rt.globals.set_ns() call with namespace
    # Use m_str() to format numbers in MUMPS canonical form (no E-notation)
    ctx.emitter.line(
        f"_rt.globals.set_ns({global_name!r}, {subscripts_tuple}, "
        f"m_str({value_expr}), namespace={ns!r})"
    )


def _generate_naked_global_set(
    assignment: MAssignment, ctx: "GeneratorContext"
) -> None:
    """Generate resolve_naked + set for naked global reference SET.

    Generates code for S ^(subscripts)=value

    Args:
        assignment: MAssignment with NakedGlobal target
        ctx: Generator context

    MUMPS evaluation order for S ^(subscripts)=value:
    1. Evaluate subscript expressions left-to-right (each updates naked indicator)
    2. Evaluate value expression (updates naked indicator)
    3. resolve_naked() is called with subscript VALUES using CURRENT naked indicator
    4. SET is performed

    This means the naked indicator used for the SET target is determined by
    the LAST global access during evaluation, which may be in the value expression.
    """
    # We know target is NakedGlobal because caller checked isinstance
    assert isinstance(assignment.target, NakedGlobal)
    naked_global = assignment.target

    # Generate subscript expressions
    # DO NOT wrap in str() - let runtime handle canonicalization
    # Pass subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    subscripts_tuple = gen_subscripts_tuple(
        naked_global.subscripts or [], ctx, subscript_context=True
    )

    # Generate value expression
    assert assignment.value is not None, "Naked global SET requires a value"
    value_expr = generate_expr(assignment.value, ctx)

    # CRITICAL: Evaluation order for MUMPS S ^(subs)=value:
    # 1. Pre-compute subscript values (updates naked indicator)
    # 2. Pre-compute value (updates naked indicator)
    # 3. resolve_naked uses CURRENT naked indicator (after value evaluation!)
    # 4. Perform SET
    #
    # This ensures naked refs in value expression update the naked indicator
    # BEFORE resolve_naked determines the target location.
    ctx.emitter.line(f"_naked_sub_vals = {subscripts_tuple}")
    ctx.emitter.line(f"_naked_value = m_str({value_expr})")
    ctx.emitter.line("_name, _subs = _rt.globals.resolve_naked(_naked_sub_vals)")
    ctx.emitter.line("_rt.globals.set(_name, _subs, _naked_value)")


def _generate_write(stmt: MWriteStatement, ctx: "GeneratorContext") -> None:
    """Generate _rt.write() calls from MWriteStatement.

    Handles both expressions and format controls:
    - MExpr: Generate expression and write it
    - MFormatControl: Handle !, #, ?n, *n format controls
    - MIndirection (ARGUMENT): Always use write_indirection
        (resolved value is processed as WRITE arguments, including format controls)

    WRITE argument indirection resolves to a STRING which is then executed as
    WRITE command arguments. This string may contain format controls, expressions,
    and nested indirections.

    Examples:
    - W @A where A="!?3,1" → outputs newline, tab to 3, then "1"
    - W @B(1),@@C → each indirection expands to WRITE args independently
    - W !,@@@B,@C → explicit !, then @@@B and @C as WRITE arg indirections

    Args:
        stmt: MWriteStatement node
        ctx: Generator context
    """
    from m2py.asg.expressions import MIndirection
    from m2py.asg.enums import IndirectionType
    from m2py.asg.expressions import MDeviceControl

    for arg in stmt.arguments:
        if isinstance(arg, MFormatControl):
            # Handle format control nodes
            _generate_format_control(arg, ctx)
        elif isinstance(arg, MDeviceControl):
            # Device control mnemonics (W /EOF, W /WAIT, etc.)
            # Stub: emit a runtime call that can be handled per-device
            keyword = arg.keyword.upper()
            if arg.params:
                params_code = ", ".join(generate_expr(p, ctx) for p in arg.params)
                ctx.emitter.line(f"_rt.device_control({keyword!r}, {params_code})")
            else:
                ctx.emitter.line(f"_rt.device_control({keyword!r})")
        elif (
            isinstance(arg, MIndirection)
            and arg.indirection_type == IndirectionType.ARGUMENT
        ):
            # WRITE argument indirection: @A, @B(1), @@C, @@@B, etc.
            # The resolved value is processed as WRITE command arguments
            # This handles format controls, expressions, and nested indirections
            _generate_write_indirection(arg, ctx)
        elif isinstance(arg, MExpr):
            # Regular expression - evaluate and write
            # This includes MIndirection when NOT typed as ARGUMENT
            expr = generate_expr(arg, ctx)
            ctx.emitter.line(f"_rt.write({expr})")
        else:
            # Unknown argument type - skip silently for now
            pass


def _generate_format_control(fc: MFormatControl, ctx: "GeneratorContext") -> None:
    """Generate Python code for WRITE format controls.

    Handles the four MUMPS format controls:
    - ! (NEWLINE): Output newline character
    - # (FORMFEED): Output form feed character
    - ?n (TAB): Tab to column n
    - *n (CHARCODE): Output character with ASCII code n

    Args:
        fc: MFormatControl node
        ctx: Generator context
    """
    if fc.control_type == FormatControlType.NEWLINE:
        # NEWLINE format control
        # Use write_newline() to properly reset $X and increment $Y
        ctx.emitter.line("_rt.write_newline()")

    elif fc.control_type == FormatControlType.FORMFEED:
        # FORMFEED format control
        # YDB: conditional newline before form feed only if $X > 0
        # (iorm_cond_wteol in YDB source code)
        # Form feed outputs \x0c and resets $Y to 0, NO trailing newline
        # The outref has an extra newline after form feed that we must add
        # separately to match the output, but NOT count for $Y
        ctx.emitter.line("_rt.write_formfeed()")

    elif fc.control_type == FormatControlType.CHARCODE:
        # CHARCODE format control (*n)
        if fc.expression is not None:
            expr = generate_expr(fc.expression, ctx)
            # Apply MUMPS numeric coercion before int() for *intexpr
            ctx.emitter.line(f"_rt.write(chr(int(m_num({expr}))))")
        else:
            # No expression - shouldn't happen but handle gracefully
            pass

    elif fc.control_type == FormatControlType.TAB:
        # TAB format control (?n)
        if fc.expression is not None:
            expr = generate_expr(fc.expression, ctx)
            # Apply MUMPS numeric coercion before int() for ?intexpr
            ctx.emitter.line(f"_rt.write_tab(int(m_num({expr})))")
        else:
            # No expression - shouldn't happen but handle gracefully
            pass


def _generate_write_indirection(ind: "MIndirection", ctx: "GeneratorContext") -> None:
    """Generate write_indirection call for WRITE argument indirection.

    WRITE argument indirection (W @A) must be handled specially because
    the resolved value may contain format controls like !?3 that cannot
    be evaluated as expressions.

    Example: W @A where A='!?3,"AB"'
    - The resolved value is: !?3,"AB"
    - This must be parsed as WRITE arguments, not evaluated as an expression

    Args:
        ind: MIndirection ASG node with ARGUMENT type
        ctx: Generator context
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.indirection import _count_indirection_levels_with_subscripts

    # Get scope expression
    scope_expr = "_scope"

    # Count indirection levels and get inner expression
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(ind)

    # Get the source variable name
    # For variable references, we pass the variable name and let write_indirection resolve it
    # For complex expressions, we evaluate the expression at compile time and pass the string result
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # Complex expression - evaluate to get source string
        # Must convert to string because write_indirection expects a string
        # For example: @''10 → evaluates ''10 to 1 → passes "1" to write_indirection
        #
        # For complex expressions, the expression evaluation counts as one level of
        # indirection, so we reduce levels by 1. Example:
        # - @A where A="B" → levels=1, source="A", then resolve A→"B"→execute "B"
        # - @''10 → compile-time: ''10=1 → levels=0, source="1", just execute "1"
        source_expr = f"m_str({generate_expr(inner_expr, ctx)})"
        levels = max(0, levels - 1)  # Expression evaluation counts as one level

    # Build per-level subscripts argument if needed
    subs_arg = ""
    if all_subscripts and any(all_subscripts):
        per_level_subs = []
        for subs in all_subscripts:
            if subs:
                sub_exprs = [generate_expr(s, ctx) for s in subs]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
        if per_level_subs:
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"

    # Generate the write_indirection call
    ctx.emitter.line(
        f"_rt.write_indirection({source_expr}, {scope_expr}, levels={levels}{subs_arg})"
    )


def _generate_quit(stmt: MQuitStatement, ctx: "GeneratorContext") -> None:
    """Generate break or return statement from MQuitStatement.

    MUMPS QUIT has context-dependent behavior:
    - With return value: returns value from extrinsic (Python: return value)
    - With return value + by-ref outputs: returns tuple (value, *byref_outputs)
    - Inside a FOR loop: exits the FOR loop (Python: break)
    - Inside a DO block: exits the DO block only (Python: break from while True)
    - Otherwise: returns from label/routine (Python: return or return (None, state))

    Priority order (checked first to last):
    1. return_value -> return <expr> (or tuple with by-ref outputs)
    2. exits_for (from ASG) -> break
    3. exits_do_block (from ASG) -> break (exit DO block's while True)
    4. default -> return (or return (None, state) for trampoline)

    Args:
        stmt: MQuitStatement node
        ctx: Generator context
    """
    # QUIT with return value (extrinsic function return)
    # If label has by-ref outputs, return tuple (value, *byref_outputs)
    if stmt.return_value is not None:
        value_expr = generate_expr(stmt.return_value, ctx)

        # TRAMPOLINE mode: Store return value in state and return (None, state)
        # The wrapper function will extract state._return_value for extrinsic calls
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line(f"state._return_value = {value_expr}")
            ctx.emitter.line("return (None, state)")
            return

        # Check if label has by-ref outputs that need to be included
        if (
            ctx.current_label
            and ctx.current_label.signature
            and ctx.current_label.signature.byref_outputs
        ):
            formal_params = ctx.current_label.signature.formal_params
            # Build tuple: (return_value, param1, param2, ...)
            # Include ALL formal params so tuple positions align with
            # the _byref list at the call site (which has entries for all
            # actual params, with None for by-value positions).
            # Use MArray.value for consistency
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                byref_exprs = [
                    f"_scope.get({translate_name(p)!r}, MArray()).value"
                    for p in formal_params
                ]
            else:
                byref_exprs = [translate_name(p) for p in formal_params]
            if byref_exprs:
                all_exprs = [value_expr] + byref_exprs
                ctx.emitter.line(f"return ({', '.join(all_exprs)})")
                return

        # No by-ref outputs - just return the value
        ctx.emitter.line(f"return {value_expr}")
        return

    # exits_for is set by analyze_quit_context() for QUITs inside FOR loops
    if stmt.exits_for is not None:
        # Inside a FOR loop - QUIT exits the innermost FOR
        ctx.emitter.line("break")
        return

    # exits_do_block is set by analyze_quit_context() for QUITs inside DO blocks
    if stmt.exits_do_block is not None:
        # Inside a DO block - QUIT exits only the block (break from while True)
        ctx.emitter.line("break")
        return

    # Self-loop pattern - QUIT exits the label function entirely.
    # The while True: loop wraps the label body; QUIT should not merely
    # break out of the loop (which would fall through to the next label)
    # but must signal a proper routine exit.
    if ctx.current_label and ctx.current_label.has_self_loop:
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("return (None, state)")
        else:
            ctx.emitter.line("return")
        return

    # Plain QUIT with by-ref outputs - return modified params as tuple
    # Check if current label has byref_outputs that need to be returned
    if (
        ctx.current_label
        and ctx.current_label.signature
        and ctx.current_label.signature.byref_outputs
    ):
        # For TRAMPOLINE, by-ref uses MArray aliasing — mutations are
        # already visible through the shared MArray reference, so we just
        # fall through to the normal return (None, state) below.
        # For SIMPLE_FUNCTIONS, return values from _scope.
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            formal_params = ctx.current_label.signature.formal_params
            return_exprs = [
                f"_scope.get({translate_name(p)!r}, MArray()).value"
                for p in formal_params
            ]
            if return_exprs:
                ctx.emitter.line(f"return {', '.join(return_exprs)}")
                return

    # Trampoline pattern - return (None, state) to signal exit
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
        if ctx.in_inline_xecute:
            ctx.emitter.line("raise _XecuteExit()")
        else:
            ctx.emitter.line("return (None, state)")
        return

    # Plain QUIT outside FOR/DO block - return from function/routine
    # Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
    if ctx.in_inline_xecute:
        ctx.emitter.line("raise _XecuteExit()")
    else:
        ctx.emitter.line("return")


def _generate_if(stmt: MIfStatement, ctx: "GeneratorContext") -> None:
    """Generate Python if statement from MIfStatement.

    MUMPS IF evaluates condition, sets $TEST, and conditionally executes body.
    Generated code: _test = m_truth(cond); if _test: ...

    For IF indirection (I @A where A=""), empty string is TRUE.
    Passes if_condition=True to generate_expr() so indirection codegen
    adds treat_empty_as_truthy=True to the runtime call.

    Args:
        stmt: MIfStatement node
        ctx: Generator context
    """
    # Get condition(s) - always use conditions list
    # Pass if_condition=True for indirection empty string handling
    if len(stmt.conditions) == 1:
        cond_expr = generate_expr(stmt.conditions[0], ctx, if_condition=True)
    elif stmt.conditions:
        # Multiple comma-separated conditions act as AND
        # Each condition is evaluated in sequence, with $TEST updated after EACH
        # This is critical for tests like "I 1,$T" where $T reads value from 1st arg
        # Use walrus operator to update _test after each condition evaluation
        cond_parts = [generate_expr(c, ctx, if_condition=True) for c in stmt.conditions]
        # Generate: (_test := m_truth(c1)) and (_test := m_truth(c2)) and ...
        cond_expr = " and ".join(f"(_test := m_truth({c}))" for c in cond_parts)
        # For multiple conditions, final _test is set by the walrus operator chain
        ctx.emitter.line(f"if {cond_expr}:")
        with ctx.emitter.indented():
            if stmt.then_scope and stmt.then_scope.statements:
                _pre_count = len(ctx.emitter._lines)
                for body_stmt in stmt.then_scope.statements:
                    generate_statement(body_stmt, ctx)
                # Guard against body statements that generate no code
                # (e.g., argumentless DO with body flattened into parent scope)
                if len(ctx.emitter._lines) == _pre_count:
                    ctx.emitter.line("pass")
            else:
                ctx.emitter.line("pass")
        # Sync $TEST to runtime after multi-condition IF
        ctx.emitter.line("_rt._test = _test")
        return
    else:
        # Argumentless IF uses existing $TEST
        ctx.emitter.line("if _test:")
        with ctx.emitter.indented():
            if stmt.then_scope and stmt.then_scope.statements:
                _pre_count = len(ctx.emitter._lines)
                for body_stmt in stmt.then_scope.statements:
                    generate_statement(body_stmt, ctx)
                if len(ctx.emitter._lines) == _pre_count:
                    ctx.emitter.line("pass")
            else:
                ctx.emitter.line("pass")
        return

    # Single condition case - evaluate and set _test
    ctx.emitter.line(f"_test = m_truth({cond_expr})")
    ctx.emitter.line("_rt._test = _test")
    ctx.emitter.line("if _test:")

    with ctx.emitter.indented():
        if stmt.then_scope and stmt.then_scope.statements:
            _pre_count = len(ctx.emitter._lines)
            for body_stmt in stmt.then_scope.statements:
                generate_statement(body_stmt, ctx)
            if len(ctx.emitter._lines) == _pre_count:
                ctx.emitter.line("pass")
        else:
            ctx.emitter.line("pass")


def _generate_else(stmt: MElseStatement, ctx: "GeneratorContext") -> None:
    """Generate Python if-not-_test statement from MElseStatement.

    MUMPS ELSE executes if $TEST is false.
    Generated code: if not _test: ...

    Args:
        stmt: MElseStatement node
        ctx: Generator context
    """
    ctx.emitter.line("if not _test:")

    with ctx.emitter.indented():
        if stmt.body and stmt.body.statements:
            _pre_count = len(ctx.emitter._lines)
            for body_stmt in stmt.body.statements:
                generate_statement(body_stmt, ctx)
            if len(ctx.emitter._lines) == _pre_count:
                ctx.emitter.line("pass")
        else:
            ctx.emitter.line("pass")


def _generate_for(stmt: MForStatement, ctx: "GeneratorContext") -> None:
    """Generate Python for loop from MForStatement.

    Dispatches based on loop_type and analysis flags to generate
    the appropriate Python pattern:
    - BOUNDED: for loop with range() or while loop if loop var modified
    - OPEN_ENDED: for loop with itertools.count()
    - ARGUMENTLESS: while True
    - STRING_LIST: for loop with list
    - MIXED: for loop with itertools.chain()

    If this FOR is the outermost target of a MULTI_LOOP_EXIT GOTO,
    wraps the entire loop in try/except _LoopExit.

    Cross-label loop exits call the target label after exiting.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    # Check if this FOR needs try/except wrapper for multi-loop exit
    needs_wrapper = stmt.needs_exception_wrapper

    # Check if this FOR has cross-label single-loop exits
    has_cross_label_exit = stmt.has_cross_label_exit

    # Check if this FOR has same-label single-loop exits
    # These need to break the FOR and continue the outer while True self-loop
    has_same_label_exit = stmt.has_same_label_exit

    # Initialize goto tracking before loop if needed
    if has_cross_label_exit and not needs_wrapper:
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("_goto_label = None")
        else:
            ctx.emitter.line("_goto_target = None")

    # Initialize same-label exit flag before loop if needed
    if has_same_label_exit and not needs_wrapper:
        ctx.emitter.line("_restart_self_loop = False")

    if needs_wrapper:
        ctx.emitter.line("try:")
        ctx.emitter.indent()

    # Use ForGenContext for analysis-based dispatch
    for_ctx = ForGenContext.from_statement(stmt, ctx)

    # Dispatch based on loop type and analysis flags
    if for_ctx.loop_type == ForLoopType.ARGUMENTLESS:
        _generate_for_argumentless(stmt, for_ctx, ctx)
    elif for_ctx.loop_type == ForLoopType.OPEN_ENDED:
        # Open-ended loops with body modification need while loop pattern
        if for_ctx.use_while:
            _generate_for_while(stmt, for_ctx, ctx)
        else:
            _generate_for_open_ended(stmt, for_ctx, ctx)
    elif for_ctx.loop_type == ForLoopType.MIXED:
        _generate_for_mixed(stmt, for_ctx, ctx)
    elif for_ctx.loop_var_subscripts and for_ctx.loop_type == ForLoopType.BOUNDED:
        # Subscripted loop variables (F A(B)=1:1:3) use bounded path which handles
        # subscripts specially - counter tracked separately from array storage.
        # Per MUMPS spec, subscripts are evaluated ONCE at start, so loop var
        # modifications in body don't affect the subscript (no need for while pattern).
        _generate_for_bounded(stmt, for_ctx, ctx)
    elif for_ctx.use_while:
        # BOUNDED or STRING_LIST with loop var modification needs while loop
        _generate_for_while(stmt, for_ctx, ctx)
    elif for_ctx.loop_type == ForLoopType.STRING_LIST:
        _generate_for_string_list(stmt, for_ctx, ctx)
    else:
        # BOUNDED - standard for loop with range
        _generate_for_bounded(stmt, for_ctx, ctx)

    if needs_wrapper:
        ctx.emitter.dedent()
        ctx.emitter.line("except _LoopExit as _e:")
        with ctx.emitter.indented():
            # Call/return to target label if provided
            ctx.emitter.line("if _e.target is not None:")
            with ctx.emitter.indented():
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    ctx.emitter.line("return (_e.target, state)")
                else:
                    ctx.emitter.line("_e.target()")
                    ctx.emitter.line("return")
            # V1FORC2: Same-label exit - continue to restart the while True self-loop
            if stmt.has_same_label_exit:
                ctx.emitter.line("else:")
                with ctx.emitter.indented():
                    ctx.emitter.line("continue")

    # Handle target after single-loop exit if set
    if has_cross_label_exit and not needs_wrapper:
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("if _goto_label is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line("return (_goto_label, state)")
        else:
            ctx.emitter.line("if _goto_target is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line("_goto_target()")
                ctx.emitter.line("return")

    # V1FORC2/I-377: Handle same-label single-loop exit
    # If the flag was set, continue the outer while True self-loop
    if has_same_label_exit and not needs_wrapper:
        ctx.emitter.line("if _restart_self_loop:")
        with ctx.emitter.indented():
            ctx.emitter.line("continue")


def _generate_for_body(
    stmt: MForStatement, ctx: "GeneratorContext", for_ctx: "ForGenContext | None" = None
) -> None:
    """Generate the body of a FOR loop.

    The QUIT context (exits_for) is set by analyze_quit_context() during analysis,
    so no runtime tracking is needed here.

    For SIMPLE_FUNCTIONS strategy with Python for-loops: sync Python's for-loop
    variable to _scope at the start of each iteration so that _scope-based reads
    work correctly. This is NOT needed for while loops (when loop_var_modified_in_body
    is True) because while loops already use _scope directly.

    Handles subscripted loop variables (F I(1)=1:1:3) by using .set() instead
    of .value assignment.

    When for_ctx is provided, uses for_ctx.loop_var instead of translate_name()
    to handle inline XECUTE prefixing (e.g. _xec_I instead of I).

    Args:
        stmt: MForStatement node
        ctx: Generator context
        for_ctx: Optional ForGenContext with actual Python variable name
    """
    from m2py.codegen.expressions import generate_expr

    # Sync for-loop variable to _scope for SIMPLE_FUNCTIONS strategy
    # Also sync for TRAMPOLINE with dynamic_locals (state._locals)
    # Only needed when using Python's `for` loop (not while loop)
    # When loop_var_modified_in_body is True, we use while loop with _scope directly
    # Use MArray.value for consistency with subscripted variables
    #
    # For subscripted loop vars (F A(B)=1:1:3), the sync is handled in
    # _generate_for_bounded which re-evaluates subscripts at each access.
    # Skip the sync here to avoid double-syncing with potentially stale subscripts.
    needs_scope_sync = (
        ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS
        and stmt.loop_var
        and not stmt.loop_var_modified_in_body
        and not (for_ctx and for_ctx.loop_var_subscripts)  # Skip for subscripted vars
    )
    # TRAMPOLINE vars not in state_vars also need _scope sync
    # (reads go through _scope, so FOR loop var must be synced there)
    needs_trampoline_scope_sync = (
        ctx.strategy == GotoStrategy.TRAMPOLINE
        and not ctx.uses_dynamic_locals
        and stmt.loop_var
        and not stmt.loop_var_modified_in_body
        and not (for_ctx and for_ctx.loop_var_subscripts)  # Skip for subscripted vars
        and for_ctx is not None
        and not for_ctx.loop_var.startswith(
            "state."
        )  # Skip state_vars (already in state)
    )
    # TRAMPOLINE with dynamic_locals also needs sync (state._locals)
    needs_locals_sync = (
        ctx.strategy == GotoStrategy.TRAMPOLINE
        and ctx.uses_dynamic_locals
        and stmt.loop_var
        and not stmt.loop_var_modified_in_body
        and not (for_ctx and for_ctx.loop_var_subscripts)  # Skip for subscripted vars
    )
    if needs_scope_sync or needs_locals_sync or needs_trampoline_scope_sync:
        if isinstance(stmt.loop_var, str):
            var_name = stmt.loop_var
            subscripts = []
        elif isinstance(stmt.loop_var, MVariable):
            var_name = stmt.loop_var.name
            # Extract subscripts for subscripted loop variables
            subscripts = [generate_expr(sub, ctx) for sub in stmt.loop_var.subscripts]
        else:
            var_name = None  # Complex case (indirection) - skip sync
            subscripts = []
        if var_name:
            # Use for_ctx.loop_var if provided (handles _xec_ prefix in inline XECUTE)
            python_name = for_ctx.loop_var if for_ctx else translate_name(var_name)
            # Use translated name for scope key to match SET statement behavior
            translated_var_name = translate_name(var_name)
            # Choose sync target based on strategy
            if needs_locals_sync:
                sync_target = (
                    f"state._locals.setdefault({translated_var_name!r}, MArray())"
                )
            else:
                sync_target = f"_scope.setdefault({translated_var_name!r}, MArray())"
            if subscripts:
                # Subscripted loop var - use .set(sub1, sub2, ..., value=val)
                subs_str = ", ".join(subscripts)
                ctx.emitter.line(f"{sync_target}.set({subs_str}, value={python_name})")
            else:
                # Simple variable - use .value
                ctx.emitter.line(f"{sync_target}.value = {python_name}")

    if stmt.body and stmt.body.statements:
        for body_stmt in stmt.body.statements:
            generate_statement(body_stmt, ctx)
    else:
        ctx.emitter.line("pass")


def _generate_for_bounded(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python while loop from bounded FOR (F I=1:1:10).

    Uses while loop to support non-integer step values (MUMPS allows fractional steps).
    Python's range() only works with integers, but MUMPS FOR i=.001:.01:1 is valid.

    MUMPS FOR always sets the loop variable to the start value,
    even when the loop body doesn't execute (e.g., F I=2:-1:3 sets I=2).
    The loop variable must be set before the loop.

    Uses unique variable names (_for_start_N, etc.) to prevent
    nested FOR loops from clobbering each other's loop control variables.

    For indirect loop variables (F @A=1:1:3), resolves the target
    variable name at runtime and updates via _rt.set_var().

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """

    # Get the single range parameter
    if not stmt.parameters or stmt.parameters[0].param_type != ForParamType.RANGE:
        raise NotImplementedError("Expected RANGE parameter for bounded FOR")

    param = stmt.parameters[0]
    if param.start is None or param.step is None or param.end is None:
        raise NotImplementedError("Incomplete FOR range parameters")

    # Use unique variable names to prevent nested loop collisions
    lid = for_ctx.loop_id
    start_var = f"_for_start_{lid}"
    step_var = f"_for_step_{lid}"
    end_var = f"_for_end_{lid}"

    # Per MUMPS spec 8.2.18: "Any expressions occurring in lvn, such as might occur
    # in subscripts or indirection, are evaluated once per execution of the For command,
    # prior to the first execution of any forparameter."
    # This means subscripts must be evaluated BEFORE start/step/end to ensure
    # correct naked indicator state during evaluation.
    cached_subs: list[str] = []
    if for_ctx.loop_var_subscripts:
        for i, sub_expr in enumerate(for_ctx.loop_var_subscripts):
            cache_var = f"_for_sub_{lid}_{i}"
            ctx.emitter.line(f"{cache_var} = {sub_expr}")
            cached_subs.append(cache_var)

    # NOW evaluate start/step/end (after subscripts have been evaluated)
    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)
    end_expr = generate_expr(param.end, ctx)

    # Set loop variable to start value before the loop
    # This ensures the variable is set even when the loop doesn't execute
    ctx.emitter.line(f"{start_var} = m_num({start_expr})")
    ctx.emitter.line(f"{step_var} = m_num({step_expr})")
    ctx.emitter.line(f"{end_var} = m_num({end_expr})")

    # Determine how to handle the loop variable
    # Three cases:
    # 1. Indirect loop var (F @A=1:1:3) - resolve target name, use _scope access
    # 2. Subscripted loop var (F A(1)=1:1:3 or F A(@B)=1:1:3) - subscripts re-evaluated each iteration
    # 3. Simple loop var (F I=1:1:3) - direct Python variable

    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        # Handle indirect loop variable (F @A=1:1:3)
        # Resolve the target variable name once before the loop
        ctx.emitter.line(f"_for_indirect_var_{lid} = {for_ctx.loop_var_expr}")
        # Set indirect var to start value
        ctx.emitter.line(
            f"_scope.setdefault(_for_indirect_var_{lid}, MArray()).value = m_num({start_var})"
        )
        ctx.emitter.line(
            f"while ({step_var} > 0 and _scope.setdefault(_for_indirect_var_{lid}, MArray()).value <= {end_var}) or "
            f"({step_var} < 0 and _scope.setdefault(_for_indirect_var_{lid}, MArray()).value >= {end_var}) or "
            f"({step_var} == 0 and _scope.setdefault(_for_indirect_var_{lid}, MArray()).value <= {end_var}):"
        )
        with ctx.emitter.indented():
            _generate_for_body(stmt, ctx, for_ctx)
            # Check if should continue before incrementing
            ctx.emitter.line(
                f"if not (({step_var} > 0 and m_add(_scope.setdefault(_for_indirect_var_{lid}, MArray()).value, {step_var}) <= {end_var}) or "
                f"({step_var} < 0 and m_add(_scope.setdefault(_for_indirect_var_{lid}, MArray()).value, {step_var}) >= {end_var}) or "
                f"({step_var} == 0)):"
            )
            with ctx.emitter.indented():
                ctx.emitter.line("break")
            # Increment loop variable
            ctx.emitter.line(
                f"_scope.setdefault(_for_indirect_var_{lid}, MArray()).value = m_add(_scope.setdefault(_for_indirect_var_{lid}, MArray()).value, {step_var})"
            )
    elif for_ctx.loop_var_subscripts:
        # Handle subscripted loop variable (F A(1)=1:1:3 or F A(@B)=1:1:3)
        # Per MUMPS spec: "Any expressions occurring in lvn, such as might occur in subscripts
        # or indirection, are evaluated once per execution of the For command, prior to the
        # first execution of any forparameter."
        # Subscripts were already cached above (before start/step/end evaluation).
        # The loop COUNTER is tracked separately and stored to the SAME subscript location.
        var_name = for_ctx.loop_var_name

        # Use the already-cached subscript values
        cached_subs_str = ", ".join(cached_subs)

        # Track the loop counter separately from the variable storage
        counter_var = f"_for_val_{lid}"

        # Choose correct variable storage based on code generation strategy
        # Must match the pattern used for variable access (expressions.py line 267)
        # Use translate_name() to ensure the key matches SET/expression codegen
        translated_var = translate_name(var_name)
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Dynamic locals - use state._locals for consistency with read access
            base = f"state._locals.setdefault({translated_var!r}, MArray())"
        elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Use _scope for SIMPLE_FUNCTIONS
            base = f"_scope.setdefault({translated_var!r}, MArray())"
        else:
            # Fallback to _scope (shouldn't normally be reached)
            base = f"_scope.setdefault({translated_var!r}, MArray())"

        def make_set_expr(val: str) -> str:
            return f"{base}.set({cached_subs_str}, value={val})"

        # Initial assignment - set counter and store to subscripted variable
        ctx.emitter.line(f"{counter_var} = {start_var}")
        ctx.emitter.line(make_set_expr(counter_var))

        # While loop - condition uses the counter, not the variable value
        ctx.emitter.line(
            f"while ({step_var} > 0 and {counter_var} <= {end_var}) or "
            f"({step_var} < 0 and {counter_var} >= {end_var}) or "
            f"({step_var} == 0 and {counter_var} <= {end_var}):"
        )
        with ctx.emitter.indented():
            # Generate loop body (may modify subscript source variables)
            _generate_for_body(stmt, ctx, for_ctx)

            # Check if should continue before incrementing
            # Use the counter variable for termination check, not the stored value
            ctx.emitter.line(
                f"if not (({step_var} > 0 and m_add({counter_var}, {step_var}) <= {end_var}) or "
                f"({step_var} < 0 and m_add({counter_var}, {step_var}) >= {end_var}) or "
                f"({step_var} == 0)):"
            )
            with ctx.emitter.indented():
                ctx.emitter.line("break")

            # Increment the counter
            ctx.emitter.line(f"{counter_var} = m_add({counter_var}, {step_var})")

            # Store the new counter value to the subscripted variable
            # (subscript is re-evaluated here)
            ctx.emitter.line(make_set_expr(counter_var))

    else:
        # Simple loop variable (F I=1:1:3)
        # Set loop var to start value (MUMPS semantics)
        ctx.emitter.line(f"{for_ctx.loop_var} = {start_var}")
        # Sync to storage BEFORE the while loop so the value is set even if loop doesn't execute
        _needs_scope_sync = False
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS and for_ctx.loop_var_name:
            translated_lv = translate_name(for_ctx.loop_var_name)
            ctx.emitter.line(
                f"_scope.setdefault({translated_lv!r}, MArray()).value = {start_var}"
            )
        elif (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.uses_dynamic_locals
            and for_ctx.loop_var_name
        ):
            # Sync to state._locals for TRAMPOLINE with dynamic locals
            translated_name = translate_name(for_ctx.loop_var_name)
            ctx.emitter.line(
                f"state._locals.setdefault({translated_name!r}, MArray()).value = {start_var}"
            )
        elif (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and not ctx.uses_dynamic_locals
            and for_ctx.loop_var_name
            and not for_ctx.loop_var.startswith("state.")
        ):
            # TRAMPOLINE var not in state_vars — sync to _scope
            translated_lv = translate_name(for_ctx.loop_var_name)
            ctx.emitter.line(
                f"_scope.setdefault({translated_lv!r}, MArray()).value = {start_var}"
            )
            _needs_scope_sync = True
        ctx.emitter.line(
            f"while ({step_var} > 0 and {for_ctx.loop_var} <= {end_var}) or "
            f"({step_var} < 0 and {for_ctx.loop_var} >= {end_var}) or "
            f"({step_var} == 0 and {for_ctx.loop_var} <= {end_var}):"
        )
        with ctx.emitter.indented():
            _generate_for_body(stmt, ctx, for_ctx)
            # Increment loop variable at end of iteration using m_add for precision
            ctx.emitter.line(
                f"{for_ctx.loop_var} = m_add({for_ctx.loop_var}, {step_var})"
            )
            # Sync to _scope after increment for TRAMPOLINE non-state_vars
            if _needs_scope_sync:
                translated_lv = translate_name(for_ctx.loop_var_name)
                ctx.emitter.line(
                    f"_scope.setdefault({translated_lv!r}, MArray()).value = {for_ctx.loop_var}"
                )


def _generate_for_string_list(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from string list FOR (F I="A","B","C").

    MUMPS evaluates each VALUE parameter when it becomes the current iteration,
    NOT upfront. So F I=1,I+1,3*I requires:
    1. I=1, execute body
    2. I=(current I)+1, execute body
    3. I=3*(current I), execute body

    When value_params_reference_loop_var is True, we generate sequential
    assignments instead of Python's for...in[...] which evaluates upfront.

    For indirect loop variables (F @A="X","Y","Z"), resolves the target
    variable name at runtime and updates via _rt.set_var().

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Check if VALUE params reference the loop variable
    if stmt.value_params_reference_loop_var:
        _generate_for_sequential_values(stmt, for_ctx, ctx)
        return

    values = []
    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE and param.value is not None:
            values.append(generate_expr(param.value, ctx))

    if not values:
        raise NotImplementedError("Empty string list FOR")

    values_str = ", ".join(values)

    # Handle indirect loop variable (F @A="X","Y","Z")
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        # Resolve the target variable name once before the loop
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")
        ctx.emitter.line(f"for {for_ctx.loop_var} in [{values_str}]:")
        with ctx.emitter.indented():
            # Update the indirect variable at start of each iteration
            ctx.emitter.line(
                f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
            )
            _generate_for_body(stmt, ctx, for_ctx)
    else:
        ctx.emitter.line(f"for {for_ctx.loop_var} in [{values_str}]:")
        with ctx.emitter.indented():
            _generate_for_body(stmt, ctx, for_ctx)


def _generate_for_sequential_values(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate sequential value assignments for FOR with loop-var-referencing params.

    MUMPS FOR I=1,I+1,3*I evaluates each param when it's current:
    1. I=1, body
    2. I=(current I)+1=2, body
    3. I=3*(current I)=6, body

    We wrap in a while True / break pattern so that QUIT (which generates break)
    will exit the entire FOR construct:

        while True:
            # Param 1
            <loop_var> = <value1>
            <body>  # may contain break
            # Param 2
            <loop_var> = <value2>
            <body>  # may contain break
            ...
            break  # Exit after all params processed

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Collect VALUE parameters
    value_params = [
        p for p in stmt.parameters if p.param_type == ForParamType.VALUE and p.value
    ]
    if not value_params:
        raise NotImplementedError("Empty sequential value FOR")

    # Wrap in while True so that break from QUIT works
    ctx.emitter.line("while True:")
    with ctx.emitter.indented():
        # Handle indirect loop variable setup
        if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
            ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")

        # Generate a single pass through all values
        for param in value_params:
            # value_params is filtered to only include params with value, assert for type checker
            assert param.value is not None
            value_expr = generate_expr(param.value, ctx)

            # Handle indirect loop variable
            if for_ctx.loop_var_indirect:
                ctx.emitter.line(f"{for_ctx.loop_var} = {value_expr}")
                ctx.emitter.line(
                    f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
                )
            else:
                ctx.emitter.line(f"{for_ctx.loop_var} = {value_expr}")

            # Generate body
            _generate_for_body(stmt, ctx, for_ctx)

        # Exit after all params processed (normal completion)
        ctx.emitter.line("break")


def _generate_for_open_ended(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from open-ended FOR (F I=1:1).

    Uses itertools.count() for unbounded iteration, UNLESS the loop variable
    is modified in the body. When modified, we use a while loop pattern that
    reads the current value and adds the step each iteration.

    MUMPS semantics: F I=start:step means:
    1. I = start (evaluated once)
    2. Execute body
    3. I = I + step (reads current I, which body may have modified)
    4. Goto 2

    Python's count() doesn't support step 3 reading from a modified I,
    so when loop_var_modified_in_body is True, we use while True + manual stepping.

    For indirect loop variables (F @A=1:1), resolves the target
    variable name at runtime and updates via _rt.set_var().

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Get the open range parameter
    open_param = None
    for param in stmt.parameters:
        if param.param_type == ForParamType.OPEN_RANGE:
            open_param = param
            break

    if open_param is None or open_param.start is None or open_param.step is None:
        raise NotImplementedError("Invalid open-ended FOR parameters")

    start_expr = generate_expr(open_param.start, ctx)
    step_expr = generate_expr(open_param.step, ctx)

    # When loop var is modified in body, we need while loop pattern
    # because count() doesn't pick up modifications to the loop var
    if stmt.loop_var_modified_in_body:
        _generate_for_open_ended_while(stmt, for_ctx, ctx, start_expr, step_expr)
        return

    # Handle indirect loop variable (F @A=1:1)
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        # Resolve the target variable name once before the loop
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")
        ctx.emitter.line(
            f"for {for_ctx.loop_var} in count(m_num({start_expr}), m_num({step_expr})):"
        )
        with ctx.emitter.indented():
            # Update the indirect variable at start of each iteration
            ctx.emitter.line(
                f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
            )
            _generate_for_body(stmt, ctx, for_ctx)
    else:
        ctx.emitter.line(
            f"for {for_ctx.loop_var} in count(m_num({start_expr}), m_num({step_expr})):"
        )
        with ctx.emitter.indented():
            _generate_for_body(stmt, ctx, for_ctx)


def _generate_for_open_ended_while(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
    start_expr: str,
    step_expr: str,
) -> None:
    """Generate while loop for open-ended FOR when loop var is modified.

    When the body modifies the loop variable, we can't use count() because
    MUMPS re-reads the loop var before adding step. Example:

    F I=10:10 S:I=40 I="ABCD" ...
    - I=10, body runs
    - I=20, body runs
    - I=30, body runs
    - I=40, body sets I="ABCD"
    - Next: I = "ABCD" + 10 = 0 + 10 = 10 (MUMPS string coercion)

    Pattern:
        _for_step = m_num(step_expr)
        I = m_num(start_expr)
        _scope['I'].value = I
        while True:
            <body>
            I = m_num(I) + _for_step
            _scope['I'].value = I

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context
        ctx: Generator context
        start_expr: Expression for start value
        step_expr: Expression for step value
    """
    # Compute step once at start
    ctx.emitter.line(f"_for_step = m_num({step_expr})")

    # Set initial value
    ctx.emitter.line(f"{for_ctx.loop_var} = m_num({start_expr})")

    # Handle indirect loop variable
    translated_loop_key = translate_name(for_ctx.loop_var_name)
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")
        ctx.emitter.line(f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)")
    else:
        ctx.emitter.line(
            f"_scope.setdefault({translated_loop_key!r}, MArray()).value = {for_ctx.loop_var}"
        )

    ctx.emitter.line("while True:")
    with ctx.emitter.indented():
        # Generate body
        _generate_for_body(stmt, ctx, for_ctx)

        # After body, update loop var: I = I + step
        # Read from scope since body may have modified it
        if for_ctx.loop_var_indirect:
            ctx.emitter.line(
                f"{for_ctx.loop_var} = m_add(m_num(_rt.get_var(_for_indirect_var, _scope)), _for_step)"
            )
            ctx.emitter.line(
                f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
            )
        else:
            ctx.emitter.line(
                f"{for_ctx.loop_var} = m_add(m_num(m_var_value(_scope[{translated_loop_key!r}])), _for_step)"
            )
            ctx.emitter.line(
                f"_scope.setdefault({translated_loop_key!r}, MArray()).value = {for_ctx.loop_var}"
            )


def _generate_for_argumentless(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python while True from argumentless FOR (F).

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    ctx.emitter.line("while True:")

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx, for_ctx)


def _generate_for_mixed(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from mixed FOR (F I=1:1:3,"X",10:2:14).

    Uses itertools.chain() to combine multiple iterables.

    MUMPS evaluates each VALUE parameter when it becomes the current iteration,
    NOT upfront. When value_params_reference_loop_var is True, we generate
    sequential code blocks instead of chain().

    For indirect loop variables (F @A=1:1:3,"X"), resolves the target
    variable name at runtime and updates via _rt.set_var().

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Check if VALUE params reference the loop variable
    if stmt.value_params_reference_loop_var:
        _generate_for_mixed_sequential(stmt, for_ctx, ctx)
        return

    # Build list of iterables to chain together
    iterables = []

    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE:
            if param.value is not None:
                # Single value as a list
                value_expr = generate_expr(param.value, ctx)
                iterables.append(f"[{value_expr}]")
        elif param.param_type == ForParamType.RANGE:
            if param.start is None or param.step is None or param.end is None:
                raise NotImplementedError("Incomplete FOR range in mixed loop")
            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)
            end_expr = generate_expr(param.end, ctx)
            # Use m_range for MUMPS end-inclusive semantics with fractional support
            iterables.append(f"m_range({start_expr}, {end_expr}, {step_expr})")
        elif param.param_type == ForParamType.OPEN_RANGE:
            if param.start is None or param.step is None:
                raise NotImplementedError("Incomplete open range in mixed loop")
            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)
            iterables.append(f"count(m_num({start_expr}), m_num({step_expr}))")

    if not iterables:
        raise NotImplementedError("Empty mixed FOR parameters")

    chain_args = ", ".join(iterables)

    # Handle indirect loop variable (F @A=1:1:3,"X",10:2:14)
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        # Resolve the target variable name once before the loop
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")
        ctx.emitter.line(f"for {for_ctx.loop_var} in chain({chain_args}):")
        with ctx.emitter.indented():
            # Update the indirect variable at start of each iteration
            ctx.emitter.line(
                f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
            )
            _generate_for_body(stmt, ctx, for_ctx)
    else:
        ctx.emitter.line(f"for {for_ctx.loop_var} in chain({chain_args}):")
        with ctx.emitter.indented():
            _generate_for_body(stmt, ctx, for_ctx)


def _generate_for_mixed_sequential(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate sequential code for mixed FOR with loop-var-referencing params.

    When VALUE parameters reference the loop variable (F I=1,I+1,3*I),
    we cannot use chain() because it evaluates all values upfront.
    Instead we generate sequential code blocks for each parameter.

    For RANGE and OPEN_RANGE parameters, we generate standard for loops.
    For VALUE parameters, we wrap in a single-iteration for loop so that
    break from QUIT works properly.

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Handle indirect loop variable setup once
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")

    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE:
            if param.value is not None:
                # VALUE: Evaluate expression NOW (with current loop var value)
                # Wrap in single-iteration for loop so break from QUIT works
                value_expr = generate_expr(param.value, ctx)

                if for_ctx.loop_var_indirect:
                    ctx.emitter.line(f"for {for_ctx.loop_var} in [{value_expr}]:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
                        )
                        _generate_for_body(stmt, ctx, for_ctx)
                else:
                    ctx.emitter.line(f"for {for_ctx.loop_var} in [{value_expr}]:")
                    with ctx.emitter.indented():
                        _generate_for_body(stmt, ctx, for_ctx)

        elif param.param_type == ForParamType.RANGE:
            if param.start is None or param.step is None or param.end is None:
                raise NotImplementedError("Incomplete FOR range in mixed loop")
            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)
            end_expr = generate_expr(param.end, ctx)

            if for_ctx.loop_var_indirect:
                ctx.emitter.line(
                    f"for {for_ctx.loop_var} in m_range({start_expr}, {end_expr}, {step_expr}):"
                )
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
                    )
                    _generate_for_body(stmt, ctx, for_ctx)
            else:
                ctx.emitter.line(
                    f"for {for_ctx.loop_var} in m_range({start_expr}, {end_expr}, {step_expr}):"
                )
                with ctx.emitter.indented():
                    _generate_for_body(stmt, ctx, for_ctx)

        elif param.param_type == ForParamType.OPEN_RANGE:
            if param.start is None or param.step is None:
                raise NotImplementedError("Incomplete open range in mixed loop")
            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)

            if for_ctx.loop_var_indirect:
                ctx.emitter.line(
                    f"for {for_ctx.loop_var} in count(m_num({start_expr}), m_num({step_expr})):"
                )
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)"
                    )
                    _generate_for_body(stmt, ctx, for_ctx)
            else:
                ctx.emitter.line(
                    f"for {for_ctx.loop_var} in count(m_num({start_expr}), m_num({step_expr})):"
                )
                with ctx.emitter.indented():
                    _generate_for_body(stmt, ctx, for_ctx)


def _generate_for_while(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python while loop for FOR with modified loop variable.

    When the loop variable is modified inside the body, we can't use
    Python's for loop because it would overwrite the modification.
    Instead we use a while loop with explicit stepping.

    For SIMPLE_FUNCTIONS: Use _scope['VAR'] directly so that modifications
    inside the body are visible to the loop condition and stepping.

    For indirect loop variables (F @A=1:1:3 with body modifying A),
    resolves the target variable name once at the start. When the resolved
    name might be a subscripted variable (like "A(22)"), uses _rt.get_var
    and _rt.set_var for proper subscript handling.

    MUMPS FOR semantics: After the loop exits, the loop variable retains
    the last value it held during iteration, NOT the value that would have
    failed the range check. We achieve this by checking if the NEXT value
    would be in range before incrementing.

    Supports both RANGE (F I=1:1:10) and STRING_LIST (F I="A","B","C").

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    if not stmt.parameters:
        raise NotImplementedError("While loop requires FOR parameters")

    # Handle indirect loop variable setup
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        # Resolve the target variable name once before the loop
        # The resolved name might be subscripted (e.g., "A(22)"), so we use
        # _rt.get_var and _rt.set_var which handle subscript parsing at runtime
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")
        # Dispatch to special indirect handler that uses get_var/set_var
        param = stmt.parameters[0]
        if param.param_type == ForParamType.RANGE:
            _generate_for_while_range_indirect(stmt, for_ctx, ctx, param)
        elif param.param_type == ForParamType.OPEN_RANGE:
            # Open-ended FOR with indirect loop var and body modification
            _generate_for_while_open_range_indirect(stmt, for_ctx, ctx, param)
        elif for_ctx.loop_type == ForLoopType.STRING_LIST:
            _generate_for_while_string_list_indirect(stmt, for_ctx, ctx)
        else:
            raise NotImplementedError(
                f"While loop for indirect var doesn't support {for_ctx.loop_type}"
            )
        return
    # For SIMPLE_FUNCTIONS or TRAMPOLINE with dynamic_locals,
    # use _scope/_locals directly so body modifications are visible to loop
    elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS or (
        ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals
    ):
        # Get the MUMPS variable name and translate it for _scope/_locals key
        # Must use translate_name() to match the keys used by SET/expression codegen
        # (e.g., MUMPS "I" → Python "_a_I" to avoid E743 lint ambiguity)
        if isinstance(stmt.loop_var, str):
            var_name = stmt.loop_var
        elif isinstance(stmt.loop_var, MVariable):
            var_name = stmt.loop_var.name
        else:
            var_name = None

        if var_name:
            translated_var = translate_name(var_name)
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # TRAMPOLINE with dynamic_locals: use state._locals
                loop_ref = (
                    f"state._locals.setdefault({translated_var!r}, MArray()).value"
                )
            else:
                # SIMPLE_FUNCTIONS: use _scope
                loop_ref = f"_scope.setdefault({translated_var!r}, MArray()).value"
        else:
            loop_ref = for_ctx.loop_var
    else:
        loop_ref = for_ctx.loop_var

    # Check loop type - dispatch to appropriate pattern
    param = stmt.parameters[0]
    if param.param_type == ForParamType.RANGE:
        _generate_for_while_range(stmt, for_ctx, ctx, loop_ref, param)
    elif param.param_type == ForParamType.OPEN_RANGE:
        # Open-ended FOR with body modification
        _generate_for_while_open_range(stmt, for_ctx, ctx, loop_ref, param)
    elif for_ctx.loop_type == ForLoopType.STRING_LIST:
        _generate_for_while_string_list(stmt, for_ctx, ctx, loop_ref)
    else:
        raise NotImplementedError(
            f"While loop for modified loop var doesn't support {for_ctx.loop_type}"
        )


def _generate_for_while_range(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
    loop_ref: str,
    param: MForParameter,
) -> None:
    """Generate while loop for RANGE FOR with modified loop variable.

    Uses unique variable names to prevent nested loop collisions.
    """
    if param.start is None or param.step is None or param.end is None:
        raise NotImplementedError("Incomplete FOR range parameters for while loop")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)
    end_expr = generate_expr(param.end, ctx)

    # Use unique variable names to prevent nested loop collisions
    lid = for_ctx.loop_id
    step_var = f"_for_step_{lid}"
    end_var = f"_for_end_{lid}"

    # Initialize loop variable and step/end values
    ctx.emitter.line(f"{loop_ref} = m_num({start_expr})")
    ctx.emitter.line(f"{step_var} = m_num({step_expr})")
    ctx.emitter.line(f"{end_var} = m_num({end_expr})")

    # While condition: check bounds based on step direction
    # When step == 0, loop is infinite (until QUIT) but only enters if start <= end
    in_range_cond = (
        f"({step_var} > 0 and {loop_ref} <= {end_var}) or "
        f"({step_var} < 0 and {loop_ref} >= {end_var}) or "
        f"({step_var} == 0 and {loop_ref} <= {end_var})"
    )
    ctx.emitter.line(f"while {in_range_cond}:")

    with ctx.emitter.indented():
        # Execute body
        _generate_for_body(stmt, ctx, for_ctx)
        # Check if the NEXT value would be in range BEFORE incrementing
        # For step == 0, we never break (infinite loop until QUIT)
        next_val_cond = (
            f"({step_var} > 0 and m_add({loop_ref}, {step_var}) <= {end_var}) or "
            f"({step_var} < 0 and m_add({loop_ref}, {step_var}) >= {end_var}) or "
            f"({step_var} == 0)"
        )
        ctx.emitter.line(f"if not ({next_val_cond}):")
        with ctx.emitter.indented():
            ctx.emitter.line("break")
        # Increment loop variable at end of iteration
        # Use m_add for proper MUMPS string-to-number coercion
        ctx.emitter.line(f"{loop_ref} = m_add({loop_ref}, {step_var})")


def _generate_for_while_open_range(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
    loop_ref: str,
    param: MForParameter,
) -> None:
    """Generate while loop for open-ended FOR with modified loop variable.

    When the loop variable is modified inside the body, Python's for loop
    with count() can't be used because it would overwrite the modification.
    Instead uses a while True loop with explicit stepping.

    MUMPS evaluates both start and step BEFORE assigning to the loop
    variable. So for F I=$D(I):$D(I), both $D(I) expressions are evaluated
    when $D(I)=10 (before I gets a value), not after I is assigned.

    For SIMPLE_FUNCTIONS: Use _scope['VAR'] directly so that modifications
    inside the body are visible to the stepping.

    Example: F I=-2:0 S VCOMP=VCOMP_I,I=I+1 I I=3 Q
    - Starts at -2, step is 0
    - Body modifies I (I=I+1) which affects the loop iteration
    - Without while loop, count(-2, 0) always yields -2

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        loop_ref: Reference to loop variable (e.g., "_scope['I'].value")
        param: The OPEN_RANGE parameter
    """
    if param.start is None or param.step is None:
        raise NotImplementedError("Incomplete open-ended FOR parameters for while loop")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)

    # Use unique variable names to prevent nested loop collisions
    lid = for_ctx.loop_id
    start_var = f"_for_start_{lid}"
    step_var = f"_for_step_{lid}"

    # MUMPS evaluates start and step BEFORE assigning to loop variable
    # Both must be evaluated before the assignment changes any state
    ctx.emitter.line(f"{start_var} = m_num({start_expr})")
    ctx.emitter.line(f"{step_var} = m_num({step_expr})")
    ctx.emitter.line(f"{loop_ref} = {start_var}")

    # Open-ended loops run forever until QUIT breaks out
    ctx.emitter.line("while True:")

    with ctx.emitter.indented():
        # Execute body
        _generate_for_body(stmt, ctx, for_ctx)
        # Increment loop variable at end of iteration
        # Use m_add for proper MUMPS string-to-number coercion
        ctx.emitter.line(f"{loop_ref} = m_add({loop_ref}, {step_var})")


def _generate_for_while_range_indirect(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
    param: MForParameter,
) -> None:
    """Generate while loop for RANGE FOR with indirect loop variable.

    When the loop variable is indirect (F @A=1:1:3) and the resolved name
    might be subscripted (e.g., "A(22)"), we need to use _rt.get_var and
    _rt.set_var for proper subscript handling at runtime.

    This is separate from _generate_for_while_range because we can't use
    a simple assignment expression like `loop_ref = value` when the variable
    name contains subscripts that need to be parsed.
    """
    if param.start is None or param.step is None or param.end is None:
        raise NotImplementedError("Incomplete FOR range parameters for while loop")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)
    end_expr = generate_expr(param.end, ctx)

    # Use unique variable names to prevent nested loop collisions
    lid = for_ctx.loop_id
    step_var = f"_for_step_{lid}"
    end_var = f"_for_end_{lid}"

    # Initialize loop variable using set_var for proper subscript handling
    ctx.emitter.line(f"_rt.set_var(_for_indirect_var, m_num({start_expr}), _scope)")
    ctx.emitter.line(f"{step_var} = m_num({step_expr})")
    ctx.emitter.line(f"{end_var} = m_num({end_expr})")

    # While condition: use get_var to read the current value
    get_var_expr = "_rt.get_var(_for_indirect_var, _scope)"
    in_range_cond = (
        f"({step_var} > 0 and {get_var_expr} <= {end_var}) or "
        f"({step_var} < 0 and {get_var_expr} >= {end_var}) or "
        f"({step_var} == 0 and {get_var_expr} <= {end_var})"
    )
    ctx.emitter.line(f"while {in_range_cond}:")

    with ctx.emitter.indented():
        # Execute body
        _generate_for_body(stmt, ctx, for_ctx)
        # Check if the NEXT value would be in range BEFORE incrementing
        # For step == 0, we never break (infinite loop until QUIT)
        next_val_cond = (
            f"({step_var} > 0 and m_add({get_var_expr}, {step_var}) <= {end_var}) or "
            f"({step_var} < 0 and m_add({get_var_expr}, {step_var}) >= {end_var}) or "
            f"({step_var} == 0)"
        )
        ctx.emitter.line(f"if not ({next_val_cond}):")
        with ctx.emitter.indented():
            ctx.emitter.line("break")
        # Increment loop variable using set_var
        ctx.emitter.line(
            f"_rt.set_var(_for_indirect_var, m_add({get_var_expr}, {step_var}), _scope)"
        )


def _generate_for_while_open_range_indirect(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
    param: MForParameter,
) -> None:
    """Generate while loop for open-ended FOR with indirect loop variable.

    When the loop variable is indirect (F @A=1:1) and the resolved name
    might be subscripted, uses _rt.get_var and _rt.set_var for
    proper subscript handling at runtime.

    MUMPS evaluates both start and step BEFORE assigning to the loop
    variable. So for F I=$D(I):$D(I), both $D(I) expressions are evaluated
    when $D(I)=10 (before I gets a value), not after I is assigned.

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
        param: The OPEN_RANGE parameter
    """
    if param.start is None or param.step is None:
        raise NotImplementedError("Incomplete open-ended FOR parameters for while loop")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)

    # Use unique variable names to prevent nested loop collisions
    lid = for_ctx.loop_id
    start_var = f"_for_start_{lid}"
    step_var = f"_for_step_{lid}"

    # MUMPS evaluates start and step BEFORE assigning to loop variable
    ctx.emitter.line(f"{start_var} = m_num({start_expr})")
    ctx.emitter.line(f"{step_var} = m_num({step_expr})")
    # Now assign to loop variable using set_var for proper subscript handling
    ctx.emitter.line(f"_rt.set_var(_for_indirect_var, {start_var}, _scope)")

    # Read via get_var for current value
    get_var_expr = "_rt.get_var(_for_indirect_var, _scope)"

    # Open-ended loops run forever until QUIT breaks out
    ctx.emitter.line("while True:")

    with ctx.emitter.indented():
        # Execute body
        _generate_for_body(stmt, ctx, for_ctx)
        # Increment loop variable using set_var
        ctx.emitter.line(
            f"_rt.set_var(_for_indirect_var, m_add({get_var_expr}, {step_var}), _scope)"
        )


def _generate_for_while_string_list_indirect(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
) -> None:
    """Generate while loop for STRING_LIST FOR with indirect loop variable.

    Similar to _generate_for_while_string_list but uses _rt.set_var for
    proper subscript handling when the resolved variable name is subscripted.
    """
    # Collect all values from parameters
    values = []
    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE and param.value is not None:
            values.append(generate_expr(param.value, ctx))

    if not values:
        raise NotImplementedError("Empty string list FOR")

    # Use unique variable names
    lid = for_ctx.loop_id
    idx_var = f"_for_idx_{lid}"

    # MUMPS FOR list semantics: evaluate each value LAZILY at iteration time
    ctx.emitter.line(f"{idx_var} = 0")
    ctx.emitter.line(f"while {idx_var} < {len(values)}:")

    with ctx.emitter.indented():
        # Lazy evaluation: compute current value based on index
        # Generate if/elif chain for each value
        for i, val_expr in enumerate(values):
            if i == 0:
                ctx.emitter.line(f"if {idx_var} == 0:")
            else:
                ctx.emitter.line(f"elif {idx_var} == {i}:")
            with ctx.emitter.indented():
                # Use set_var for proper subscript handling
                ctx.emitter.line(f"_rt.set_var(_for_indirect_var, {val_expr}, _scope)")
        # Execute body
        _generate_for_body(stmt, ctx, for_ctx)
        # Increment index
        ctx.emitter.line(f"{idx_var} += 1")


def _generate_for_while_string_list(
    stmt: MForStatement,
    for_ctx: ForGenContext,
    ctx: "GeneratorContext",
    loop_ref: str,
) -> None:
    """Generate while loop for STRING_LIST FOR with modified loop variable.

    For indirect loop variables like F @A="X","Y","Z":
    1. Build the list of values
    2. Use an index-based while loop
    3. Assign the current value to the indirect variable on each iteration

    Uses unique variable names to prevent nested loop collisions.
    Also, evaluates each list value lazily at iteration time, not upfront, since
    MUMPS FOR list semantics require evaluating k_"b" when k already contains
    the modified value from previous iteration.
    """
    # Collect all values from parameters
    values = []
    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE and param.value is not None:
            values.append(generate_expr(param.value, ctx))

    if not values:
        raise NotImplementedError("Empty string list FOR")

    # Use unique variable names to prevent nested loop collisions
    lid = for_ctx.loop_id
    idx_var = f"_for_idx_{lid}"

    # MUMPS FOR list semantics: evaluate each value lazily at iteration time
    # This is needed because F K="a",K_"b",K_"c" should evaluate K_"b" after
    # K has been modified by the first iteration's body
    ctx.emitter.line(f"{idx_var} = 0")
    ctx.emitter.line(f"while {idx_var} < {len(values)}:")

    with ctx.emitter.indented():
        # Lazy evaluation: compute current value based on index
        # Generate if/elif chain for each value
        for i, val_expr in enumerate(values):
            if i == 0:
                ctx.emitter.line(f"if {idx_var} == 0:")
            else:
                ctx.emitter.line(f"elif {idx_var} == {i}:")
            with ctx.emitter.indented():
                ctx.emitter.line(f"{loop_ref} = {val_expr}")
        # Execute body
        _generate_for_body(stmt, ctx, for_ctx)
        # Increment index
        ctx.emitter.line(f"{idx_var} += 1")


def _generate_goto(stmt: MGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate code from MGotoStatement.

    GOTO transfers control to a label. The generated Python depends on context:
    - Single loop exit: generate `break`
    - Multi-loop exit: generate `raise _LoopExit()`
    - Cross-label jump (SIMPLE_FUNCTIONS): generate function call + return
    - Cross-label jump (TRAMPOLINE): generate return (label_name, state)

    Multiple targets:
    - Targets evaluated left-to-right
    - If target has postcondition and it's false, try next target
    - If postcondition is true or no postcondition, go to that target
    - If all postconditions false, no jump (continue to next command)

    Note: There is no "continue" pattern. Per MUMPS spec (MDC 3.6.5):
    "Execution of GOTO effects the immediate termination of all FORs
    in the line containing the GOTO." A GOTO to the same label creates
    a function call/recursion, not continue semantics.

    Example patterns:
    - G DONE (cross-label, SIMPLE) → DONE(); return
    - G DONE (cross-label, TRAMPOLINE) → return ("DONE", state)
    - G A,B → go to A (targets evaluated left-to-right)
    - G A:cond,B → if cond: go to A, else: go to B
    - G DONE (inside FOR, exiting loop) → break
    - G DONE (inside nested FOR) → raise _LoopExit()

    Args:
        stmt: MGotoStatement node
        ctx: Generator context

    Raises:
        NotImplementedError: For unsupported GOTO patterns
        UnsupportedFeatureError: For backward intra-label GOTO
    """
    if not stmt.targets:
        raise NotImplementedError("Argumentless GOTO not supported")

    # Handle multiple targets
    if len(stmt.targets) > 1:
        _generate_multi_target_goto(stmt, ctx)
        return

    target = stmt.targets[0]
    _generate_single_target_goto(target, stmt, ctx)


def _generate_single_target_goto(
    target: "MCall", stmt: MGotoStatement, ctx: "GeneratorContext"
) -> None:
    """Generate GOTO code for a single target.

    This handles all single-target cases including loop exits and cross-label jumps.
    Same-routine GOTOs (G LABEL^ROUTINE where ROUTINE is current routine)
    are treated as local GOTOs instead of external.

    Args:
        target: The MCall target to jump to
        stmt: The parent MGotoStatement (for classification info)
        ctx: Generator context
    """
    # Check for indirection first
    # Must check before same-routine logic since indirection may also have routine set
    if target.label_is_indirect or target.routine_is_indirect:
        from m2py.codegen.indirection import generate_indirect_goto

        # Handle postcondition on indirect GOTO (e.g., G @A+@B:@B=@B)
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            with ctx.emitter.indented():
                generate_indirect_goto(target, ctx)
        else:
            generate_indirect_goto(target, ctx)
        return

    # Check for same-routine GOTO (G LABEL^ROUTINE where ROUTINE matches current)
    # Only treat as external if it's a DIFFERENT routine
    is_external = False
    if target.routine:
        # Use fallback to first label name (same logic as routine.py)
        current_routine_name = ctx.routine.name or (
            ctx.routine.labels[0].name if ctx.routine.labels else ""
        )
        # Compare case-insensitively since MUMPS routine names are case-insensitive
        if (
            not current_routine_name
            or target.routine.upper() != current_routine_name.upper()
        ):
            is_external = True

    # Handle external routine GOTO
    if is_external:
        # Handle postcondition on external GOTO (e.g., G E1^V1OVE:A=1)
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            with ctx.emitter.indented():
                _generate_external_goto(target, ctx)
        else:
            _generate_external_goto(target, ctx)
        return

    # Check for backward intra-label GOTO (creates implicit loops)
    # These cannot be restructured to simple control flow structures
    # ASG fields populated by classify_gotos() analysis
    goto_type = stmt.goto_type
    is_cross_label = stmt.is_cross_label
    exits_loops = stmt.exits_loops

    # Self-loop pattern - backward intra-label GOTO
    # When label has has_self_loop=True, body is wrapped in while True:
    # and this GOTO becomes continue to restart the loop
    if goto_type == GotoType.BACKWARD_JUMP and not is_cross_label:
        # Handle postcondition on self-loop target (e.g., G loop:q<3)
        # The continue should only execute if the postcondition is true
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            with ctx.emitter.indented():
                ctx.emitter.line("continue")
        else:
            # Self-loop: generate continue to restart the while True: loop
            ctx.emitter.line("continue")
        return

    # Loop exit patterns
    # There is no "continue" pattern — GOTO cannot create continue semantics.
    # Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
    # termination of all FORs in the line containing the GOTO."
    # exits_loops is populated by classify_gotos() analysis
    in_for_loop = bool(exits_loops)

    # exits_loops determines break vs raise _LoopExit()
    if exits_loops and in_for_loop:
        # Handle postcondition on target (e.g., G G379:X=1)
        # The target postcondition must be checked before the loop exit
        postcond_ctx = None
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            postcond_ctx = ctx.emitter.indented()
            postcond_ctx.__enter__()

        if len(exits_loops) == 1:
            # Single loop exit - generate break
            # For cross-label exits, track target so it can be called after loop
            if is_cross_label and target is not None:
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Trampoline: store label name as string
                    ctx.emitter.line(f'_goto_label = "{target.name}"')
                else:
                    # Simple functions: store function reference
                    label_name = translate_name(target.name)
                    ctx.emitter.line(f"_goto_target = {label_name}")
            # For same-label exits, set flag to continue outer while True
            elif not is_cross_label:
                ctx.emitter.line("_restart_self_loop = True")
            ctx.emitter.line("break")
        else:
            # Multi-loop exit - generate raise _LoopExit()
            # The exception will be caught by the outermost FOR loop
            # Pass target label name so it can be called in except block
            if is_cross_label and target is not None:
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Trampoline: pass label name as string
                    ctx.emitter.line(f'raise _LoopExit("{target.name}")')
                else:
                    # Simple functions: pass function reference
                    label_name = translate_name(target.name)
                    ctx.emitter.line(f"raise _LoopExit({label_name})")
            else:
                ctx.emitter.line("raise _LoopExit()")

        # Close postcondition block if we opened one
        if postcond_ctx is not None:
            postcond_ctx.__exit__(None, None, None)
        return

    # UNRESOLVED GOTO: target label doesn't exist in this routine.
    # Generate a runtime error instead of a compile-time rejection so that
    # routines with dead-code GOTOs to missing labels still compile.
    # Skip this check inside inline XECUTE blocks — the target may exist
    # in the enclosing routine's module globals (e.g., X "G B" where B is
    # a label in the outer routine, not the XECUTE scope).
    if (
        not target.is_resolved
        and target.target is None
        and not target.routine
        and not ctx.in_inline_xecute
    ):
        target_name = target.name or "unknown"
        routine_name = ctx.routine.name or "unknown"
        ctx.emitter.line(f'raise LabelNotFoundError("{target_name}", "{routine_name}")')
        return

    # Cross-label GOTO: pattern depends on strategy
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Inside inline XECUTE, call the label directly instead of returning
        # The label's QUIT will return normally, then we raise _XecuteExit to exit
        # the XECUTE block and continue the enclosing FOR loop
        if ctx.in_inline_xecute:
            # Call internal label function directly (prefixed with _)
            label_func_name = "_" + translate_name(target.name)
            if target.offset is not None:
                offset_code = generate_expr(target.offset, ctx)
                # Call with offset
                emit_state_to_scope_sync(ctx)
                ctx.emitter.line(
                    f"{label_func_name}(_rt, state, _scope, _start_offset=int(m_num({offset_code})))"
                )
            else:
                emit_state_to_scope_sync(ctx)
                ctx.emitter.line(f"{label_func_name}(_rt, state, _scope)")
            ctx.emitter.line("raise _XecuteExit()")
            return

        # Check for offset and emit line-based dispatch
        if target.offset is not None:
            # Offset GOTO: compute target line = label_line + offset
            # The dispatcher will look up (label, offset) in _line_map
            if target.target is None or target.target.line_number is None:
                raise UnsupportedFeatureError(
                    f"Cannot resolve offset GOTO target: {target.name}"
                )
            label_line = target.target.line_number
            offset_code = generate_expr(target.offset, ctx)
            # Validate offset and raise descriptive error
            # Skip non-executable lines (comments/blanks)
            # Check for negative offset (must resolve to non-negative integer)
            # Use m_num() to apply MUMPS numeric coercion (string→number) before int()
            ctx.emitter.line(f"_offset_val = int(m_num({offset_code}))")
            ctx.emitter.line("if _offset_val < 0:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    f'raise ValueError("Entry point {target.name}+" '
                    '+ str(_offset_val) + " not valid")'
                )
            ctx.emitter.line(f"_target = {label_line} + _offset_val")
            ctx.emitter.line("if _target not in _line_map:")
            with ctx.emitter.indented():
                # Find next executable line after target (inline)
                # When offset lands on comment/blank line, continue to next executable.
                # This inline logic is equivalent to find_next_executable() but avoids
                # function call overhead.
                ctx.emitter.line(
                    "_next = min((ln for ln in _line_map if ln > _target), default=None)"
                )
                ctx.emitter.line("if _next is None:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        f'raise ValueError("Entry point {target.name}+" '
                        '+ str(_offset_val) + " not valid")'
                    )
                ctx.emitter.line("_target = _next")
            if target.postcondition is not None:
                cond_expr = generate_expr(target.postcondition, ctx)
                ctx.emitter.line(f"if m_truth({cond_expr}):")
                with ctx.emitter.indented():
                    ctx.emitter.line("return (_target, state)")
            else:
                ctx.emitter.line("return (_target, state)")
        else:
            # Trampoline pattern: return (label_name, state) tuple
            # The trampoline dispatcher will call the target label
            if target.postcondition is not None:
                cond_expr = generate_expr(target.postcondition, ctx)
                ctx.emitter.line(f"if m_truth({cond_expr}):")
                with ctx.emitter.indented():
                    ctx.emitter.line(f'return ("{target.name}", state)')
            else:
                ctx.emitter.line(f'return ("{target.name}", state)')
    else:
        # SIMPLE_FUNCTIONS pattern: function call + exit
        # Get the label name and translate it
        label_name = translate_name(target.name)

        # Check for offset GOTO - should not reach here (strategy selection uses TRAMPOLINE)
        if target.offset is not None:
            # Strategy selection ensures TRAMPOLINE for offset calls, but add safety check
            raise UnsupportedFeatureError(
                f"Offset GOTO in SIMPLE_FUNCTIONS mode is not supported: G {target.name}+N. "
                "Strategy selection should have chosen TRAMPOLINE."
            )
        # No offset - simple function call
        # Generate: label(_rt, _scope=_scope); exit_statement
        # Pass _rt and _scope so XECUTE inline GOTO works correctly
        # Use _globals[] lookup to avoid parameter shadowing label names
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            with ctx.emitter.indented():
                ctx.emitter.line(f"_globals[{label_name!r}](_rt, _scope=_scope)")
                if ctx.in_inline_xecute:
                    ctx.emitter.line("raise _XecuteExit()")
                else:
                    ctx.emitter.line("return")
        else:
            ctx.emitter.line(f"_globals[{label_name!r}](_rt, _scope=_scope)")
            # Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
            # Outside inline XECUTE, return exits the entire function
            if ctx.in_inline_xecute:
                ctx.emitter.line("raise _XecuteExit()")
            else:
                ctx.emitter.line("return")


def _generate_multi_target_goto(stmt: MGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate GOTO code for multiple targets.

    Multiple targets are evaluated left-to-right:
    - If target has no postcondition, jump to it unconditionally
    - If target has postcondition and it's true, jump to it
    - If postcondition is false, try next target
    - If all postconditions are false, no jump (fall through)

    Supports external routines and indirect targets in multi-target GOTO.

    Generated pattern (for G A:cond1,B^ROUTINE:cond2,C):
        if m_truth(cond1):
            return ("A", state)
        elif m_truth(cond2):
            import ROUTINE
            raise GotoExternal(ROUTINE, "B", _rt=_rt)
        else:
            return ("C", state)

    For indirect targets (G @X:cond1,Y):
        if m_truth(cond1):
            # Runtime resolution of @X with GotoExternal handling
            ...
        else:
            return ("Y", state)

    Args:
        stmt: MGotoStatement with multiple targets
        ctx: Generator context
    """
    targets = stmt.targets

    # Check if any targets are indirect (postconditions may be embedded in indirection)
    has_indirect_targets = any(
        t.label_is_indirect or t.routine_is_indirect for t in targets
    )

    # Check if any targets have postconditions in the ASG
    has_postconditions = any(t.postcondition is not None for t in targets)

    # For multi-target indirect GOTOs, we need to handle ALL targets at runtime
    # because postconditions might be embedded in the indirection strings
    # (e.g., G @A,@B where A="1+3:0", B="1+4:1")
    if has_indirect_targets and not has_postconditions:
        _generate_multi_target_indirect_goto(targets, ctx)
        return

    if not has_postconditions:
        # No postconditions: just go to first target
        # This is semantically equivalent to single-target GOTO
        first_target = targets[0]
        _generate_single_target_goto(first_target, stmt, ctx)
        return

    # Generate if/elif chain for postconditioned targets
    first = True
    last_unconditional = None

    for i, target in enumerate(targets):
        if target.postcondition is not None:
            # Generate condition check
            cond_expr = generate_expr(target.postcondition, ctx)

            if first:
                ctx.emitter.line(f"if m_truth({cond_expr}):")
                first = False
            else:
                ctx.emitter.line(f"elif m_truth({cond_expr}):")

            # Generate jump inside condition block
            with ctx.emitter.indented():
                _generate_goto_jump(target, ctx)
        else:
            # Unconditional target (no postcondition) - save for else block
            # This should be the last one if there are conditional targets before it
            last_unconditional = target

    # If there's an unconditional target at the end, it goes in else block
    if last_unconditional is not None:
        if first:
            # No conditions at all - just jump (shouldn't happen, but handle it)
            _generate_goto_jump(last_unconditional, ctx)
        else:
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                _generate_goto_jump(last_unconditional, ctx)
    elif not first:
        # All targets had postconditions - need to handle "no match" case
        # This means no GOTO taken, execution continues
        # We need a pass to make the if/elif syntactically correct, but
        # actually we don't need an else at all - just let it fall through
        pass


def _generate_multi_target_indirect_goto(
    targets: list["MCall"], ctx: "GeneratorContext"
) -> None:
    """Generate GOTO code for multiple indirect targets.

    For G @A,@B where the indirection may contain embedded postconditions
    (e.g., A="1+3:0", B="1+4:1"), we need to:
    1. Build the full target string from all targets
    2. Pass it to resolve_do_targets which handles all the resolution
    3. Take the first matching target

    Args:
        targets: List of MCall targets (all or some with indirection)
        ctx: Generator context
    """
    from m2py.codegen.indirection import _generate_do_goto_indirection_string
    from m2py.codegen.enums import GotoStrategy

    # Build the target string expression for each target
    target_parts: list[str] = []

    for target in targets:
        if target.label_is_indirect and target.indirection:
            # Indirect label: @VAR
            label_expr = _generate_do_goto_indirection_string(target.indirection, ctx)
        elif target.name:
            label_expr = repr(target.name)
        else:
            label_expr = "''"

        if target.routine_is_indirect and target.routine_indirection:
            routine_expr = _generate_do_goto_indirection_string(
                target.routine_indirection, ctx
            )
        elif target.routine:
            routine_expr = repr(target.routine)
        else:
            routine_expr = None

        # Handle offset
        offset_expr = None
        if target.offset is not None:
            offset_expr = generate_expr(target.offset, ctx)

        # Build this target's string representation
        if routine_expr is None and offset_expr is None:
            target_parts.append(label_expr)
        else:
            # Need to build compound expression
            target_expr = f"str({label_expr})"
            if offset_expr is not None:
                target_expr = f'{target_expr} + "+" + str(int(m_num({offset_expr})))'
            if routine_expr is not None:
                target_expr = f'{target_expr} + "^" + str({routine_expr})'
            target_parts.append(target_expr)

    # Join all targets with commas
    if len(target_parts) == 1:
        target_str_expr = target_parts[0]
    else:
        # Build the combined target string
        ctx.emitter.line(f"_multi_targets = ','.join([{', '.join(target_parts)}])")
        target_str_expr = "_multi_targets"

    # Resolve and parse all targets at runtime
    is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
    scope_ref = scope_dict_expr(ctx)
    ctx.emitter.line(
        f"_call_targets = _rt.resolve_do_targets({target_str_expr}, {scope_ref})"
    )

    # GOTO takes only the first target whose postcondition evaluates to true
    # Postconditions are evaluated lazily (per-target) in order
    ctx.emitter.line("_matched_target = None")
    ctx.emitter.line("for _call_target in _call_targets:")
    with ctx.emitter.indented():
        # Lazy postcondition evaluation for GOTO
        ctx.emitter.line("if _call_target.postcondition:")
        with ctx.emitter.indented():
            ctx.emitter.line("_pc_temp_var = 'ZPOSTCOND'")
            ctx.emitter.line(f"_pc_scope = dict({scope_ref})")
            ctx.emitter.line(
                "_rt.execute_mumps(f'S {_pc_temp_var}={_call_target.postcondition}', _pc_scope)"
            )
            ctx.emitter.line("_pc_result = _pc_scope.get(_pc_temp_var)")
            ctx.emitter.line("if isinstance(_pc_result, MArray):")
            with ctx.emitter.indented():
                ctx.emitter.line("_pc_result = _pc_result.value")
            ctx.emitter.line("if _pc_result in (0, '', '0', None):")
            with ctx.emitter.indented():
                ctx.emitter.line("continue  # Postcondition false, try next target")
        ctx.emitter.line("_matched_target = _call_target")
        ctx.emitter.line("break  # Found target, stop looking")

    ctx.emitter.line("if _matched_target is None:")
    with ctx.emitter.indented():
        ctx.emitter.line("pass  # No matching target - fall through")
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line("_call_target = _matched_target")

        # Generate dispatch code for the first matching target
        # Check if it's an external or local GOTO
        ctx.emitter.line(
            "if _call_target.routine and _call_target.routine != _routine_name:"
        )
        with ctx.emitter.indented():
            # External GOTO: import routine and raise GotoExternal
            ctx.emitter.line("import importlib")
            ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")
            # GotoExternal is imported at module level, not locally (avoids scoping issues)
            ctx.emitter.line("if _call_target.offset is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    "raise GotoExternal(_module, _call_target.label, "
                    "offset=_call_target.offset, _rt=_rt)"
                )
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    "raise GotoExternal(_module, _call_target.label, _rt=_rt)"
                )

        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            # Local GOTO: validate label and return to trampoline
            if is_trampoline:
                ctx.emitter.line("if _call_target.label not in _label_lines:")
            else:
                ctx.emitter.line("if _call_target.label not in globals():")
            with ctx.emitter.indented():
                ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                ctx.emitter.line(
                    "raise LabelNotFoundError(_call_target.label, _routine_name, "
                    "list(_label_lines.keys()))"
                )

            # Handle offset for local GOTO
            ctx.emitter.line("if _call_target.offset is not None:")
            with ctx.emitter.indented():
                if is_trampoline:
                    # Return line number to trampoline
                    ctx.emitter.line(
                        "_label_line = _label_lines.get(_call_target.label, 0)"
                    )
                    ctx.emitter.line(
                        "_target_line = (_label_line + 1) + _call_target.offset"
                    )
                    ctx.emitter.line("if _target_line not in _line_map:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            "_next = min((ln for ln in _line_map if ln > _target_line), "
                            "default=None)"
                        )
                        ctx.emitter.line("if _next is None:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                'raise ValueError(f"Entry point '
                                '{_call_target.label}+{_call_target.offset} not valid")'
                            )
                        ctx.emitter.line("_target_line = _next")
                    ctx.emitter.line("return (_target_line, state)")
                else:
                    # Non-trampoline: call label function with offset
                    ctx.emitter.line(
                        "_label_line = _label_lines.get(_call_target.label, 0)"
                    )
                    ctx.emitter.line(
                        "_target_line = (_label_line + 1) + _call_target.offset"
                    )
                    ctx.emitter.line("if _target_line not in _line_map:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            "_next = min((ln for ln in _line_map if ln > _target_line), "
                            "default=None)"
                        )
                        ctx.emitter.line("if _next is None:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                'raise ValueError(f"Entry point '
                                '{_call_target.label}+{_call_target.offset} not valid")'
                            )
                        ctx.emitter.line("_target_line = _next")
                    ctx.emitter.line(
                        "_label_name, _line_offset = _line_map[_target_line]"
                    )
                    ctx.emitter.line(
                        "_globals[_label_name](_rt, _scope=_scope, _start_offset=_line_offset)"
                    )
                    ctx.emitter.line("return")

            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                if is_trampoline:
                    ctx.emitter.line("return (_call_target.label, state)")
                else:
                    ctx.emitter.line("_globals[_call_target.label](_rt, _scope=_scope)")
                    ctx.emitter.line("return")


def _generate_goto_jump(target: "MCall", ctx: "GeneratorContext") -> None:
    """Generate the actual jump code for a GOTO target.

    This generates just the jump statement without any condition checks.
    Handles all target types:
    - Local targets: return (label_name, state) or function call
    - External targets: raise GotoExternal exception
    - Indirect targets: runtime resolution with potential external handling

    Same-routine GOTOs (G LABEL^ROUTINE where ROUTINE is current routine)
    are treated as local GOTOs instead of external.

    Args:
        target: The MCall target to jump to
        ctx: Generator context
    """
    # Handle indirect targets (G @VAR) first since they may also have routine set
    if target.label_is_indirect or target.routine_is_indirect:
        from m2py.codegen.indirection import generate_indirect_goto

        generate_indirect_goto(target, ctx)
        return

    # Check if this is a "same-routine" GOTO (G LABEL^ROUTINE where ROUTINE is current)
    # MUMPS allows explicit routine specification even for local labels.
    # When the target routine matches the current routine, treat as local GOTO.
    if target.routine:
        # Use fallback to first label name (same logic as routine.py)
        current_routine_name = ctx.routine.name or (
            ctx.routine.labels[0].name if ctx.routine.labels else ""
        )
        # Compare case-insensitively since MUMPS routine names are case-insensitive
        if (
            current_routine_name
            and target.routine.upper() == current_routine_name.upper()
        ):
            # Same routine - treat as local GOTO
            # Fall through to local target handling below
            pass
        else:
            # Different routine - genuine external GOTO
            _generate_external_goto(target, ctx)
            return

    # UNRESOLVED GOTO: target label doesn't exist in this routine.
    # Generate a runtime error so the routine compiles but errors if reached.
    # Skip inside inline XECUTE — the target may exist in enclosing routine globals.
    if (
        not target.is_resolved
        and target.target is None
        and not target.routine
        and not ctx.in_inline_xecute
    ):
        target_name = target.name or "unknown"
        routine_name = ctx.routine.name or "unknown"
        ctx.emitter.line(f'raise LabelNotFoundError("{target_name}", "{routine_name}")')
        return

    # Local target - original behavior
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Inside inline XECUTE, call the label directly instead of returning
        # The label's QUIT will return normally, then we raise _XecuteExit to exit
        # the XECUTE block and continue the enclosing FOR loop
        if ctx.in_inline_xecute:
            # Call internal label function directly (prefixed with _)
            label_func_name = "_" + translate_name(target.name)
            if target.offset is not None:
                offset_code = generate_expr(target.offset, ctx)
                # Call with offset
                emit_state_to_scope_sync(ctx)
                ctx.emitter.line(
                    f"{label_func_name}(_rt, state, _scope, _start_offset=int(m_num({offset_code})))"
                )
            else:
                emit_state_to_scope_sync(ctx)
                ctx.emitter.line(f"{label_func_name}(_rt, state, _scope)")
            ctx.emitter.line("raise _XecuteExit()")
            return

        # Handle local GOTO with offset (G LABEL+N)
        # Convert to absolute line number for _line_map dispatch
        # _label_lines stores 0-indexed line numbers, so we add 1 for 1-indexed source lines
        if target.offset is not None:
            offset_code = generate_expr(target.offset, ctx)
            ctx.emitter.line(
                f'return (_label_lines["{target.name}"] + 1 + int(m_num({offset_code})), state)'
            )
        else:
            ctx.emitter.line(f'return ("{target.name}", state)')

    else:
        label_name = translate_name(target.name)
        # Pass _rt and _scope so XECUTE inline GOTO works correctly
        # Use _globals[] lookup to avoid parameter shadowing label names
        ctx.emitter.line(f"_globals[{label_name!r}](_rt, _scope=_scope)")
        # Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
        # Outside inline XECUTE, return exits the entire function
        if ctx.in_inline_xecute:
            ctx.emitter.line("raise _XecuteExit()")
        else:
            ctx.emitter.line("return")


def _generate_external_goto(target: "MCall", ctx: "GeneratorContext") -> None:
    """Generate code for external GOTO (G ^ROUTINE, G LABEL^ROUTINE).

    External GOTO transfers control permanently to another routine by raising
    GotoExternal exception. The exception is caught by run_with_goto_support()
    which handles the transfer.

    Patterns:
    - G ^ROUTINE: raise GotoExternal(module, None) - entry label
    - G LABEL^ROUTINE: raise GotoExternal(module, "LABEL") - specific label
    - G LABEL+N^ROUTINE: raise GotoExternal(module, "LABEL", offset=N) - label with offset
    - G +N^ROUTINE: raise GotoExternal(module, None, offset=N) - absolute line offset

    Args:
        target: The MCall target with routine field set
        ctx: Generator context
    """
    from m2py.codegen.enums import GotoStrategy

    # Sync local variables to _scope before external GOTO so target routine sees them
    # For TRAMPOLINE with dynamic_locals: copy state._locals to _scope
    # For TRAMPOLINE without dynamic_locals: copy state_vars to _scope
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        if ctx.uses_dynamic_locals:
            # Dynamic locals: copy entire state._locals dict to _scope
            emit_state_to_scope_sync(ctx)
        elif ctx.state_vars:
            # Static state vars: copy each state variable to _scope
            for var_name in sorted(ctx.state_vars):
                python_name = translate_name(var_name)
                ctx.emitter.line(
                    f"_scope[{python_name!r}] = MArray(value=state.{python_name}) "
                    f"if not isinstance(state.{python_name}, MArray) else state.{python_name}"
                )

    # Translate routine name to valid Python module name (%FOO → _pct_FOO)
    # Note: target.routine is guaranteed non-None by caller (checked before calling this function)
    assert target.routine is not None, (
        "_generate_external_goto requires target.routine to be set"
    )
    routine_name = translate_name(target.routine)

    # Generate import statement for external routine
    ctx.emitter.line(f"import {routine_name}")
    # GotoExternal is imported at module level, not locally (avoids scoping issues)

    # Handle offset patterns (G LABEL+N^ROUTINE, G +N^ROUTINE)
    if target.offset is not None:
        offset_code = generate_expr(target.offset, ctx)
        # Pass offset to GotoExternal
        if target.name:
            # G LABEL+N^ROUTINE
            label_name = target.name
            ctx.emitter.line(
                f"raise GotoExternal({routine_name}, {label_name!r}, "
                f"offset=int(m_num({offset_code})), _rt=_rt)"
            )
        else:
            # G +N^ROUTINE (absolute line offset)
            ctx.emitter.line(
                f"raise GotoExternal({routine_name}, None, "
                f"offset=int(m_num({offset_code})), _rt=_rt)"
            )
    elif target.name:
        # G LABEL^ROUTINE - specific label
        label_name = target.name
        ctx.emitter.line(f"raise GotoExternal({routine_name}, {label_name!r}, _rt=_rt)")
    else:
        # G ^ROUTINE - entry label (same name as routine)
        ctx.emitter.line(f"raise GotoExternal({routine_name}, None, _rt=_rt)")


# ---- DOT block helpers (Fix A/C: scoping and $ETRAP) ----

# Counter for unique DOT-level scope manager variable names
_dot_mgr_counter: int = 0


def _dot_block_has_new(stmt: MDoStatement) -> bool:
    """Check if a DOT block body contains any NEW statements (recursively).

    Used to decide whether to wrap the DOT block in a nested NewScopeManager.
    """
    if not stmt.body:
        return False
    for s in stmt.body.walk_statements():
        if isinstance(s, MNewStatement):
            return True
    return False


def _dot_block_has_etrap(stmt: MDoStatement) -> bool:
    """Check if a DOT block body sets $ETRAP (N $ETRAP or S $ETRAP=...).

    Used to decide whether to wrap the DOT block body in try/except for
    $ETRAP error handling at the DOT level (Fix C).
    """
    if not stmt.body:
        return False
    for s in stmt.body.statements:
        # Check for N $ETRAP (direct child only — first level)
        if isinstance(s, MNewStatement):
            for var in s.variables:
                if isinstance(var, MSpecialVariable) and var.name.upper() in (
                    "ETRAP",
                    "ET",
                ):
                    return True
        # Check for S $ETRAP="..." (direct child only)
        if isinstance(s, MSetStatement):
            for assignment in s.assignments:
                if isinstance(assignment, MAssignment):
                    target = assignment.target
                    if isinstance(target, MSpecialVariable) and target.name.upper() in (
                        "ETRAP",
                        "ET",
                    ):
                        return True
    return False


def _unique_dot_mgr_var(ctx: "GeneratorContext") -> str:
    """Generate a unique variable name for a DOT block scope manager."""
    global _dot_mgr_counter
    _dot_mgr_counter += 1
    return f"_dot_mgr_{_dot_mgr_counter}"


def _generate_do_block_body(stmt: MDoStatement, ctx: "GeneratorContext") -> None:
    """Generate the inner body of a DO block (while True: ... break).

    This is the core body generation shared by both scoped and unscoped
    DO blocks.  When $ETRAP is set inside the block, wraps the body in
    try/except so errors are caught at DOT level (Fix C), allowing
    enclosing FOR loops to continue after error handling.
    """
    has_etrap = _dot_block_has_etrap(stmt)

    if has_etrap:
        # $ETRAP set inside this DOT block → catch errors at DOT level
        # so the enclosing FOR loop can continue after error handling.
        ctx.emitter.line("while True:  # DO block")
        with ctx.emitter.indented():
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                for body_stmt in stmt.body.statements:
                    generate_statement(body_stmt, ctx)
            ctx.emitter.line("except Exception as _e:")
            with ctx.emitter.indented():
                ctx.emitter.line("if _rt._handle_etrap(_e, _scope):")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        "break  # $ETRAP handled; exit DOT block, continue loop"
                    )
                ctx.emitter.line("raise  # Propagate unhandled error")
            # Always break at end to ensure single iteration
            ctx.emitter.line("break")
    else:
        # No $ETRAP in this DOT block — no try/except needed
        ctx.emitter.line("while True:  # DO block")
        with ctx.emitter.indented():
            for body_stmt in stmt.body.statements:
                generate_statement(body_stmt, ctx)
            ctx.emitter.line("break")


def _generate_do(stmt: MDoStatement, ctx: "GeneratorContext") -> None:
    """Generate function call from MDoStatement.

    DO calls a subroutine and returns to the caller.
    Unlike GOTO, control continues after DO returns.

    $TEST Stacking (verified against YottaDB):
    - Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack $TEST
      Callee's $TEST changes ARE visible to caller
    - DO blocks (D followed by dot-indented lines) DO stack $TEST
      Caller's $TEST is saved before and restored after

    Execution Level (§6.3):
    - DO blocks increment $STACK (execution level) on entry
    - $STACK is decremented on block exit (even on exceptions)
    - Nested DO blocks accumulate: outer=1, inner=2, etc.

    Example: D SUB → SUB()  (no save/restore)

    Args:
        stmt: MDoStatement node
        ctx: Generator context
    """
    # Check for argumentless DO block (inline block with body)
    # This is the ONLY case where $TEST is stacked
    # The is_inline_block field is set by the parser when dot-indented lines are collected
    if stmt.is_inline_block:
        # Save $TEST before block (spec §6.2.6)
        ctx.emitter.line("_saved_test = _test")

        # Save and clear _in_extrinsic for $QUIT tracking (spec §6.3)
        # Inside an argumentless DO block, QUIT exits the block (not the function),
        # so $QUIT must be 0 even if we're inside an extrinsic function.
        # Uses stack push/pop to avoid variable name collisions in nested blocks.
        ctx.emitter.line("_rt._extrinsic_stack.append(_rt._in_extrinsic)")
        ctx.emitter.line("_rt._in_extrinsic = False")

        # Increment execution level (spec §6.3) - $STACK increases inside DO blocks
        # Pass routine/label metadata for $STACK introspection
        _routine_name = ctx.routine.name or ""
        _label_name_str = ctx.current_label.name if ctx.current_label else ""
        ctx.emitter.line(
            f'_rt.push_stack_frame("DO", routine={_routine_name!r}, label={_label_name_str!r})'
        )

        # Check whether this DOT block body contains NEW statements.
        # If so, wrap in a nested NewScopeManager so each iteration of
        # an enclosing FOR loop gets a fresh scope (Fix A: DOT block scoping).
        dot_has_new = _dot_block_has_new(stmt)

        # In TRAMPOLINE/dynamic_locals mode, record the NEW stack depth
        # before the dot block so we can unwind NEW'd variables on exit.
        # This is critical because NewScopeManager only handles _scope,
        # while NEW pushes to state._new_stack which must be separately unwound.
        _needs_ns_unwind = dot_has_new and ctx.uses_dynamic_locals
        _ns_mark_var = ""
        if _needs_ns_unwind:
            _ns_mark_var = _unique_dot_mgr_var(ctx).replace("_dot_mgr_", "_ns_mark_")
            ctx.emitter.line(f"{_ns_mark_var} = len(state._new_stack)")

        # Wrap in try/finally to ensure stack cleanup even on exceptions
        ctx.emitter.line("try:")
        with ctx.emitter.indented():
            if dot_has_new:
                # Generate nested NewScopeManager for DOT block scope.
                # This ensures N VAR inside a DOT block creates a fresh
                # variable on each entry and restores it on exit — critical
                # when the DOT block is inside a FOR loop.
                _dot_mgr_var = _unique_dot_mgr_var(ctx)
                ctx.emitter.line(f"with NewScopeManager(_scope) as {_dot_mgr_var}:")
                _saved_scope_mgr = ctx.new_scope_manager_var
                ctx.new_scope_manager_var = _dot_mgr_var
                with ctx.emitter.indented():
                    _generate_do_block_body(stmt, ctx)
                ctx.new_scope_manager_var = _saved_scope_mgr
            else:
                _generate_do_block_body(stmt, ctx)
        ctx.emitter.line("finally:")
        with ctx.emitter.indented():
            # Decrement execution level (spec §6.3)
            ctx.emitter.line("_rt.pop_stack_frame()")
            # Unwind NEW stack entries pushed inside this dot block
            if _needs_ns_unwind:
                ctx.emitter.line(f"unwind_new_stack_to_mark(state, {_ns_mark_var})")

        # Restore $TEST and _in_extrinsic after block
        ctx.emitter.line("_test = _saved_test")
        ctx.emitter.line("_rt._test = _test")
        ctx.emitter.line("_rt._in_extrinsic = _rt._extrinsic_stack.pop()")
        return

    # Argumentless DO without body - this should not happen as parser sets
    # is_inline_block=True when collecting dot-indented lines. If we get here,
    # it means the ASG is malformed (standalone D with no body and no targets).
    if not stmt.targets:
        # Generate empty block - no-op (pass statement not needed, just return)
        return

    # Label calls - NO $TEST save/restore
    # Handle each target (multiple targets allowed: D A,B,C)
    # Each target's postcondition is evaluated independently
    # D L1:0,L2:1 → only L2 executes (L1's postcondition is false)
    # D L1:1,L2:1 → both execute (both postconditions are true)
    for target in stmt.targets:
        # Check for argument-level postcondition (different from command postcondition)
        # Argument postconditions gate individual targets, not the whole command
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            ctx.emitter.indent()
            _generate_do_target(target, ctx)
            ctx.emitter.dedent()
        else:
            _generate_do_target(target, ctx)


def _generate_do_target(target: "MCall", ctx: "GeneratorContext") -> None:
    """Generate code for a single DO target.

    This is a helper function that generates the actual call code for a DO target.
    It's called by _generate_do after any postcondition checks.

    Args:
        target: MCall target to generate code for
        ctx: Generator context
    """
    # Check for indirection
    if target.label_is_indirect or target.routine_is_indirect:
        from m2py.codegen.indirection import generate_indirect_do

        generate_indirect_do(target, ctx)
        return

    # Handle external routine reference D ^ROUTINE
    if target.routine:
        # Translate routine name to valid Python module name (%FOO → _pct_FOO)
        # Note: target.routine is guaranteed non-None by the if check above
        assert target.routine is not None  # Help type checker
        routine_name = translate_name(target.routine)

        # Generate import statement
        ctx.emitter.line(f"import {routine_name}")

        # Save runtime context before external call for $TEXT support
        # This ensures $TEXT(+N) in the caller still works after the callee returns
        ctx.emitter.line("_saved_routine = _rt._current_routine")
        ctx.emitter.line("_saved_source_lines = _rt._current_source_lines")
        ctx.emitter.line("_saved_label_lines = _rt._current_label_lines")

        # Sync state to _scope before calling external routine so callee
        # can see caller's current variable values.
        # - TRAMPOLINE + dynamic locals: bulk copy state._locals → _scope
        # - TRAMPOLINE + static state_vars: per-field sync state.X → _scope['X']
        if (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.state_vars
            and not ctx.uses_dynamic_locals
        ):
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_state_var_to_scope(ctx, var_name, py_name)
        else:
            emit_state_to_scope_sync(ctx)

        # Push DO stack frame for external subroutine call
        # Pass routine/label metadata for $STACK introspection
        _ext_label = repr(target.name) if target.name else "''"
        _ext_routine = repr(target.routine) if target.routine else "''"
        ctx.emitter.line(
            f'_rt.push_stack_frame("DO", routine={_ext_routine}, label={_ext_label})'
        )

        # Handle different external DO patterns
        if target.offset is not None:
            # D LABEL+N^ROUTINE or D +N^ROUTINE - uses line dispatch
            offset_code = generate_expr(target.offset, ctx)

            if target.name:
                # D LABEL+N^ROUTINE - label + offset
                # Check label exists in _label_lines
                ctx.emitter.line(
                    f"if {target.name!r} not in {routine_name}._label_lines:"
                )
                with ctx.emitter.indented():
                    ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                    ctx.emitter.line(
                        f"raise LabelNotFoundError({target.name!r}, {routine_name!r}, "
                        f"list({routine_name}._label_lines.keys()))"
                    )
                # Calculate target line from label's line + offset
                # _label_lines stores 0-indexed line numbers, _line_map uses 1-indexed
                # So we add 1 to convert to 1-indexed before adding offset
                # Offset must be truncated to integer per MUMPS spec
                # Use m_num() for MUMPS-style numeric conversion (extracts leading numeric)
                ctx.emitter.line(
                    f"_target_line = {routine_name}._label_lines[{target.name!r}] + 1 + int(m_num({offset_code}))"
                )
            else:
                # D +N^ROUTINE - absolute line offset (already 1-indexed, use directly)
                # Offset must be truncated to integer per MUMPS spec
                # Use m_num() for MUMPS-style numeric conversion (extracts leading numeric)
                ctx.emitter.line(f"_target_line = int(m_num({offset_code}))")

            # Call via line dispatch map, passing _rt and _scope
            # _line_map returns (label_name, offset) tuple - extract and call
            ctx.emitter.line(
                f"_label_name, _line_offset = {routine_name}._line_map[_target_line]"
            )
            # Wrap in run_with_goto_support to handle GotoExternal from subroutine
            # When subroutine does external GOTO, we catch it and transfer control,
            # then return to caller when target QUITs
            #
            # For label+offset calls, we need to handle both TRAMPOLINE and
            # SIMPLE_FUNCTIONS strategies. TRAMPOLINE has _-prefixed internal functions
            # that accept _start_offset. SIMPLE_FUNCTIONS has public functions that
            # either accept _start_offset (if they have fall-through lines) or don't.
            # We check at runtime for the internal function first.
            ctx.emitter.line("_internal_name = '_' + _label_name")
            ctx.emitter.line(f"if hasattr({routine_name}, _internal_name):")
            with ctx.emitter.indented():
                # TRAMPOLINE strategy - use call_external_with_offset helper
                # This properly initializes state from _scope and syncs back
                ctx.emitter.line("from m2py.runtime import call_external_with_offset")
                ctx.emitter.line(
                    f"call_external_with_offset({routine_name}, _label_name, _line_offset, _rt, _scope)"
                )
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                # SIMPLE_FUNCTIONS strategy - try public function with _start_offset
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=_scope: "
                    f"getattr({routine_name}, _label_name)(_rt, _scope=_scope, _start_offset=_line_offset), _rt, _scope)"
                )
        elif target.name:
            # D LABEL^ROUTINE - call specific label
            label_name = translate_name(target.name)
            # Generate LabelNotFoundError check
            ctx.emitter.line(f"if not hasattr({routine_name}, {label_name!r}):")
            with ctx.emitter.indented():
                ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                ctx.emitter.line(
                    f"raise LabelNotFoundError({target.name!r}, {routine_name!r}, "
                    f"list({routine_name}._label_lines.keys()))"
                )
            # Pass _rt and _scope for cross-routine variable visibility
            # Wrap in run_with_goto_support to handle GotoExternal from subroutine
            # Use getattr() instead of direct attribute access so the type checker
            # doesn't flag cross-module label references that may not be statically visible.
            args = _generate_call_arguments(target.arguments, ctx)
            if args:
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=_scope: "
                    f"getattr({routine_name}, {label_name!r})(_rt, {args}, _scope=_scope), _rt, _scope)"
                )
            else:
                ctx.emitter.line(
                    f"run_with_goto_support(getattr({routine_name}, {label_name!r}), _rt, _scope)"
                )
        else:
            # D ^ROUTINE - call entry function (may be _preamble for labelless first lines)
            # Use the module's _entry_function attribute which is set correctly at codegen time
            entry_func = f"{routine_name}._entry_function"
            # Pass _rt and _scope for cross-routine variable visibility
            # Wrap in run_with_goto_support to handle GotoExternal from subroutine
            args = _generate_call_arguments(target.arguments, ctx)
            if args:
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=_scope: "
                    f"{entry_func}(_rt, {args}, _scope=_scope), _rt, _scope)"
                )
            else:
                ctx.emitter.line(f"run_with_goto_support({entry_func}, _rt, _scope)")

        # Sync _scope back to state after returning from external routine
        # so caller can see callee's modifications to shared variables.
        # - TRAMPOLINE + static state_vars: per-field sync _scope['X'] → state.X
        # - TRAMPOLINE + dynamic locals: bulk copy _scope → state._locals
        if (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.state_vars
            and not ctx.uses_dynamic_locals
        ):
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_scope_var_to_state(ctx, var_name, py_name)
        else:
            emit_scope_to_state_sync(ctx)

        # Restore runtime context after external call returns
        ctx.emitter.line("_rt._current_routine = _saved_routine")
        ctx.emitter.line("_rt._current_source_lines = _saved_source_lines")
        ctx.emitter.line("_rt._current_label_lines = _saved_label_lines")
        # Pop DO stack frame after external subroutine returns
        ctx.emitter.line("_rt.pop_stack_frame()")
        # Sync $TEST from runtime after cross-module call
        # DO calls don't stack $TEST - callee's changes must be visible to caller
        ctx.emitter.line("_test = _rt._test")
        return

    # Get the label name and translate it
    label_name = translate_name(target.name)

    # Generate arguments if any
    args = _generate_call_arguments(target.arguments, ctx)

    # Save/restore _in_extrinsic for $QUIT tracking
    # Internal DO calls are subroutine invocations, so $QUIT=0 inside them
    # Uses stack push/pop to avoid variable name collisions in nested calls.
    ctx.emitter.line("_rt._extrinsic_stack.append(_rt._in_extrinsic)")
    ctx.emitter.line("_rt._in_extrinsic = False")

    # Push DO stack frame for internal subroutine call
    # Pass routine/label metadata for $STACK introspection
    _int_routine = repr(ctx.routine.name) if ctx.routine.name else "''"
    _int_label = repr(target.name) if target.name else "''"
    ctx.emitter.line(
        f'_rt.push_stack_frame("DO", routine={_int_routine}, label={_int_label})'
    )

    # Handle DO with offset
    # In TRAMPOLINE strategy, call the internal function with _start_offset
    if target.offset is not None and ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Prefix with _ for internal trampoline function
        internal_func = "_" + label_name
        # Generate offset expression code
        offset_code = generate_expr(target.offset, ctx)

        # Validate offset for DO as well
        # Skip non-executable lines (comments/blanks)
        # Get the label's line number for validation
        if target.target is not None and target.target.line_number is not None:
            label_line = target.target.line_number
            # Check for negative offset (must resolve to non-negative integer)
            # Use m_num() to apply MUMPS numeric coercion (string→number) before int()
            ctx.emitter.line(f"_offset_val = int(m_num({offset_code}))")
            ctx.emitter.line("if _offset_val < 0:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    f'raise ValueError("Entry point {target.name}+" '
                    '+ str(_offset_val) + " not valid")'
                )
            ctx.emitter.line(f"_target = {label_line} + _offset_val")
            ctx.emitter.line("if _target not in _line_map:")
            with ctx.emitter.indented():
                # Find next executable line after target (inline)
                # When offset lands on comment/blank line, continue to next executable.
                ctx.emitter.line(
                    "_next = min((ln for ln in _line_map if ln > _target), "
                    "default=None)"
                )
                ctx.emitter.line("if _next is None:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        f'raise ValueError("Entry point {target.name}+" '
                        '+ str(_offset_val) + " not valid")'
                    )
                ctx.emitter.line("_target = _next")
            # Now update the offset based on the new target line
            ctx.emitter.line(
                f"_offset = _line_map[_target][1] if _target != {label_line} + "
                "_offset_val else _offset_val"
            )

        # Build call with _rt, state, _scope, and _start_offset
        # Capture return value and follow trampoline loop
        # The internal function may return a label transition (e.g., when offset
        # lands at end of label block and execution should continue to next label)
        # Wrap in try/except to handle GotoExternal from subroutine
        ctx.emitter.line("try:")
        with ctx.emitter.indented():
            if args:
                ctx.emitter.line(
                    f"_do_target, state = {internal_func}(_rt, state, _scope, {args}, _start_offset=_offset_val)"
                )
            else:
                ctx.emitter.line(
                    f"_do_target, state = {internal_func}(_rt, state, _scope, _start_offset=_offset_val)"
                )
        ctx.emitter.line("except GotoExternal as _goto:")
        with ctx.emitter.indented():
            # Handle external GOTO from within DO - run it, then continue after DO
            _emit_goto_external_handler(ctx)
            ctx.emitter.line("_do_target = None")

        # Follow trampoline loop if internal function returned a label
        # Handle both string targets (label names) and int targets (line numbers)
        ctx.emitter.line("while _do_target is not None:")
        with ctx.emitter.indented():
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                ctx.emitter.line("if isinstance(_do_target, int):")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        "_label_name, _line_offset = _line_map[_do_target]"
                    )
                    ctx.emitter.line("_do_func = _labels[_label_name]")
                    ctx.emitter.line(
                        "_do_target, state = _do_func(_rt, state, _scope, _start_offset=_line_offset)"
                    )
                ctx.emitter.line("else:")
                with ctx.emitter.indented():
                    ctx.emitter.line("_do_func = _labels[_do_target]")
                    ctx.emitter.line("_do_target, state = _do_func(_rt, state, _scope)")
            ctx.emitter.line("except GotoExternal as _goto:")
            with ctx.emitter.indented():
                _emit_goto_external_handler(ctx)
                ctx.emitter.line("_do_target = None")
        # Pop DO stack frame
        ctx.emitter.line("_rt.pop_stack_frame()")
        # Restore _in_extrinsic for $QUIT tracking
        ctx.emitter.line("_rt._in_extrinsic = _rt._extrinsic_stack.pop()")
        return

    # Check if any argument is passed by-reference (.VAR syntax).
    # If so, pass MArray objects directly for true call-by-reference aliasing.
    # This doesn't require callee signature analysis — the caller just needs
    # to pass MArray objects, and the callee detects isinstance(param, MArray).
    actual_args = target.arguments or []
    has_byref_args = any(
        arg.passing_mode == PassingMode.BY_REFERENCE and arg.variable_name
        for arg in actual_args
    )

    if has_byref_args and ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
        # True call-by-reference via MArray aliasing:
        # Pass the actual MArray object for by-ref params. The callee
        # detects isinstance(param, MArray) and uses it directly as an
        # alias, so SET/KILL on the formal param directly affects the
        # actual variable.
        new_arg_parts = []
        for arg_node in actual_args:
            if arg_node.passing_mode == PassingMode.OMITTED:
                new_arg_parts.append("None")
            elif (
                arg_node.passing_mode == PassingMode.BY_REFERENCE
                and arg_node.variable_name
            ):
                actual_var = translate_name(arg_node.variable_name)
                new_arg_parts.append(f"_scope.setdefault({actual_var!r}, MArray())")
            elif arg_node.expression is not None:
                new_arg_parts.append(generate_expr(arg_node.expression, ctx))
        byref_args = ", ".join(new_arg_parts)

        if byref_args:
            call_expr = f"_globals[{label_name!r}](_rt, {byref_args}, _scope=_scope)"
        else:
            call_expr = f"_globals[{label_name!r}](_rt, _scope=_scope)"
        ctx.emitter.line(call_expr)

    elif has_byref_args:
        # TRAMPOLINE by-ref: pass MArray from state._locals for aliasing.
        # In TRAMPOLINE, variables live in state._locals, NOT _scope.
        # We pass the MArray from state._locals so the callee aliases
        # the same object the caller reads/writes from.
        new_arg_parts = []
        for arg_node in actual_args:
            if arg_node.passing_mode == PassingMode.OMITTED:
                new_arg_parts.append("None")
            elif (
                arg_node.passing_mode == PassingMode.BY_REFERENCE
                and arg_node.variable_name
            ):
                actual_var = translate_name(arg_node.variable_name)
                new_arg_parts.append(
                    f"state._locals.setdefault({actual_var!r}, MArray())"
                )
            elif arg_node.expression is not None:
                new_arg_parts.append(generate_expr(arg_node.expression, ctx))
        byref_args = ", ".join(new_arg_parts)

        # Sync state._locals → _scope before call so callee sees current
        # variable values (the callee copies _scope into its own state).
        # Without this, variables SET only in state._locals (e.g. after NEW)
        # are invisible to the callee, and variables SET by the callee
        # (propagated back to _scope on return) are lost when the next call
        # overwrites _scope from stale state._locals.
        if ctx.uses_dynamic_locals:
            ctx.emitter.line("for _k in list(_scope.keys()):")
            with ctx.emitter.indented():
                ctx.emitter.line("if _k not in state._locals:")
                with ctx.emitter.indented():
                    ctx.emitter.line("del _scope[_k]")
            ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")
        elif ctx.state_vars:
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_state_var_to_scope(ctx, var_name, py_name)

        if byref_args:
            call_expr = f"{label_name}(_rt, {byref_args}, _scope=_scope)"
        else:
            call_expr = f"{label_name}(_rt, _scope=_scope)"
        ctx.emitter.line(call_expr)

        # Sync _scope → state._locals after return so caller sees variables
        # SET by the callee (e.g. DIKJ set inside DISKIPIN via DDGO→DIKJ label).
        if ctx.uses_dynamic_locals:
            emit_scope_to_state_sync(ctx)
        elif ctx.state_vars:
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_scope_var_to_state(ctx, var_name, py_name)
    else:
        # No by-ref params at call site - just call with _rt
        # Pass _scope for cross-routine variable visibility
        # For TRAMPOLINE with state_vars, sync state to _scope before call
        # and sync _scope back to state after call for intra-routine DO
        if (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.state_vars
            and not ctx.uses_dynamic_locals
        ):
            # Sync state to _scope before call
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_state_var_to_scope(ctx, var_name, py_name)
        # For TRAMPOLINE with dynamic_locals, sync state._locals to _scope
        # before internal DO calls so subroutine sees current variable values
        # Must remove stale keys too (e.g., after KILL clears _locals
        # but _scope retains old entries)
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            ctx.emitter.line("for _k in list(_scope.keys()):")
            with ctx.emitter.indented():
                ctx.emitter.line("if _k not in state._locals:")
                with ctx.emitter.indented():
                    ctx.emitter.line("del _scope[_k]")
            ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")
        # Use globals() lookup for SIMPLE_FUNCTIONS to avoid parameter
        # shadowing label names (e.g., A(A,B) where param A shadows label A)
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            if args:
                ctx.emitter.line(
                    f"_globals[{label_name!r}](_rt, {args}, _scope=_scope)"
                )
            else:
                ctx.emitter.line(f"_globals[{label_name!r}](_rt, _scope=_scope)")
        elif args:
            ctx.emitter.line(f"{label_name}(_rt, {args}, _scope=_scope)")
        else:
            ctx.emitter.line(f"{label_name}(_rt, _scope=_scope)")
        # Sync _scope back to state after call
        if (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.state_vars
            and not ctx.uses_dynamic_locals
        ):
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_scope_var_to_state(ctx, var_name, py_name)
        # For TRAMPOLINE with dynamic_locals, sync _scope back to state._locals
        # Wrap plain values in MArray when syncing back (callee may use static state)
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            emit_scope_to_state_sync(ctx)
    # Pop DO stack frame
    ctx.emitter.line("_rt.pop_stack_frame()")
    # Restore _in_extrinsic for $QUIT tracking
    ctx.emitter.line("_rt._in_extrinsic = _rt._extrinsic_stack.pop()")


def _generate_kill(stmt: MKillStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for KILL command.

    KILL deletes a variable node and all its descendants.

    Supports:
    - K X → MArray.kill() on local variable X
    - K X(1,2) → MArray.kill(1, 2) on subscripted local
    - K ^G → _rt.globals.kill("G", ()) on global
    - K ^G(1,2) → _rt.globals.kill("G", ("1", "2")) on subscripted global
    - K ^(1,2) → resolve_naked then kill (naked global reference)
    - K (X,Y) → Exclusive KILL: kill all locals except X,Y

    NOT yet implemented:
    - K (argumentless) - kill all locals

    Args:
        stmt: MKillStatement node
        ctx: Generator context
    """
    # Handle exclusive KILL: K (X,Y) - kill all except X,Y
    if stmt.exclusive:
        # Build set of variables to keep (translated to Python names for _scope matching)
        keep_vars_repr = repr({translate_name(v) for v in stmt.except_list})

        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Kill MArray content for non-kept variables,
            # but keep entries in _scope to preserve call-by-reference aliasing.
            ctx.emitter.line("for _var_name in list(_scope.keys()):")
            with ctx.emitter.indented():
                ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                with ctx.emitter.indented():
                    ctx.emitter.line("_arr = _scope.get(_var_name)")
                    ctx.emitter.line("if isinstance(_arr, MArray):")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_arr.kill()")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Iterate over _locals and remove non-kept variables
            ctx.emitter.line("for _var_name in list(state._locals.keys()):")
            with ctx.emitter.indented():
                ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                with ctx.emitter.indented():
                    ctx.emitter.line("state._locals.pop(_var_name, None)")
        else:
            # TRAMPOLINE strategy without dynamic locals - not supported
            raise NotImplementedError(
                "Exclusive KILL not supported in TRAMPOLINE strategy"
            )
        return

    # Handle argumentless KILL (kill all locals)
    if stmt.is_kill_all:
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Kill MArray content but keep entries in _scope.
            # Preserves call-by-reference aliasing: shared MArrays remain
            # linked, so subsequent SET on one name affects the other.
            ctx.emitter.line("for _v in _scope.values():")
            with ctx.emitter.indented():
                ctx.emitter.line("if isinstance(_v, MArray):")
                with ctx.emitter.indented():
                    ctx.emitter.line("_v.kill()")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Clear _locals dict for dynamic locals mode
            ctx.emitter.line("state._locals.clear()")
        else:
            # TRAMPOLINE strategy without dynamic locals - not supported
            raise NotImplementedError(
                "Argumentless KILL not supported in TRAMPOLINE strategy"
            )
        return

    # Process each target in the kill list
    for target in stmt.targets:
        if isinstance(target, GlobalVariable):
            # Global variable: K ^G or K ^G(subs)
            global_name = target.name

            # Generate subscript tuple
            subscripts_tuple = gen_subscripts_tuple(
                target.subscripts or [], ctx, str_wrap=True
            )

            ctx.emitter.line(f'_rt.globals.kill("{global_name}", {subscripts_tuple})')

        elif isinstance(target, NakedGlobal):
            # Naked global: K ^(subs) - resolve then kill
            subscripts_tuple = gen_subscripts_tuple(
                target.subscripts or [], ctx, str_wrap=True
            )

            # Resolve naked to (name, full_subscripts), then kill
            ctx.emitter.line(
                f"_naked_name, _naked_subs = _rt.globals.resolve_naked({subscripts_tuple})"
            )
            ctx.emitter.line("_rt.globals.kill(_naked_name, _naked_subs)")

        elif isinstance(target, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
            # Extended global KILL with namespace
            global_name = target.name
            ns = getattr(target.environment, "value", "") if target.environment else ""
            subscripts_tuple = gen_subscripts_tuple(
                target.subscripts or [], ctx, str_wrap=True
            )
            ctx.emitter.line(
                f"_rt.globals.kill_ns({global_name!r}, {subscripts_tuple}, "
                f"namespace={ns!r})"
            )

        elif isinstance(target, MVariable):
            # Local variable: K X or K X(subs)
            var_name = target.name
            translated = translate_name(var_name)

            # Generate subscript arguments
            if target.subscripts:
                subs_code = []
                for sub in target.subscripts:
                    subs_code.append(generate_expr(sub, ctx))
                subscripts_args = ", ".join(subs_code)
            else:
                subscripts_args = ""

            # For SIMPLE_FUNCTIONS strategy, use _scope with translated name
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                if subscripts_args:
                    ctx.emitter.line(
                        f"_scope.get({translated!r}, MArray()).kill({subscripts_args})"
                    )
                else:
                    # Kill entire variable - clear MArray content but keep in scope.
                    # Not removing from scope preserves call-by-reference
                    # aliasing. If this variable shares an MArray with another name,
                    # clearing makes $DATA return 0 for both names. The killed MArray
                    # stays in _scope so subsequent SET re-uses it (maintaining alias).
                    ctx.emitter.line(f"_scope.get({translated!r}, MArray()).kill()")
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # TRAMPOLINE with dynamic_locals - use state._locals with translated name.
                # Kill MArray content in-place to propagate through pass-by-reference
                # aliases (same principle as SIMPLE_FUNCTIONS path).
                if subscripts_args:
                    ctx.emitter.line(
                        f"state._locals.get({translated!r}, MArray()).kill({subscripts_args})"
                    )
                else:
                    ctx.emitter.line(
                        f"state._locals.get({translated!r}, MArray()).kill()"
                    )
            else:
                # TRAMPOLINE strategy with static state vars
                if var_name in ctx.state_vars:
                    # State var: use state.X attribute access
                    state_name = f"state.{translated}"
                    if subscripts_args:
                        ctx.emitter.line(f"{state_name}.kill({subscripts_args})")
                    else:
                        ctx.emitter.line(f"{state_name} = MArray()")
                else:
                    # Non-state var: use _scope (matches SET/READ pattern)
                    if subscripts_args:
                        ctx.emitter.line(
                            f"_scope.get({translated!r}, MArray()).kill({subscripts_args})"
                        )
                    else:
                        ctx.emitter.line(f"_scope.get({translated!r}, MArray()).kill()")

        elif isinstance(target, MIndirection):
            # Indirection target: K @A or K @A@(subs) using unified components
            # Uses _rt.kill_indirected() which handles multi-level indirection and
            # per-level subscripts via IndirectionResolver
            from m2py.codegen.indirection import generate_name_indirection_kill

            if target.expression is None:
                raise ValueError("KILL indirection has no expression")

            # Generate unified kill_indirected call
            kill_stmt = generate_name_indirection_kill(target, ctx)
            ctx.emitter.line(kill_stmt)

        else:
            raise NotImplementedError(
                f"KILL target type not supported: {type(target).__name__}"
            )


def _generate_new(stmt: MNewStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for NEW command.

    NEW creates a new local scope for specified variables.
    The old values are shadowed until the routine/label exits.

    Supports:
    - N → NEW all (argumentless - save and remove all locals until function exit)
    - N X → NEW X (save and remove from _scope until function exit)
    - N X,Y,Z → NEW multiple variables
    - N (X,Y) → Exclusive NEW: NEW all locals except X,Y

    Note: N () (empty exclusive NEW) is invalid MUMPS syntax - YDB rejects it.
    Our parser silently skips it, which is acceptable.

    When ctx.new_scope_manager_var is set, uses NewScopeManager.new_var()
    for proper save/restore semantics on function exit.
    Otherwise, uses simple _scope.pop() for within-routine NEW.

    Args:
        stmt: MNewStatement node
        ctx: Generator context
    """
    # Process selective variables FIRST for left-to-right order
    # (mixed NEW B,(C,B) does selective B first, then exclusive (C,B))
    _has_selective = bool(stmt.variables)
    if _has_selective:
        _generate_new_selective_vars(stmt, ctx)

    # Handle exclusive NEW: N (X,Y) - NEW all except X,Y
    if stmt.exclusive:
        # Import MIndirection here to avoid circular imports at module level
        from m2py.asg.expressions import MIndirection as MIndirectionType

        # Check if any element in except_list is an MIndirection
        has_indirection = any(isinstance(v, MIndirectionType) for v in stmt.except_list)

        if has_indirection:
            from m2py.codegen.indirection import _generate_inner_name_expr

            # Build the keep set dynamically at runtime
            # Start with known string variables
            string_vars = [v for v in stmt.except_list if isinstance(v, str)]
            indirection_vars = [
                v for v in stmt.except_list if isinstance(v, MIndirectionType)
            ]

            if string_vars:
                ctx.emitter.line(
                    f"_keep_vars = {repr({translate_name(v) for v in string_vars})}"
                )
            else:
                ctx.emitter.line("_keep_vars = set()")

            # Add indirection-resolved names at runtime
            for ind_var in indirection_vars:
                if ind_var.expression is None:
                    raise ValueError("NEW indirection has no expression")
                target_name_expr = _generate_inner_name_expr(ind_var.expression, ctx)
                ctx.emitter.line(f"_keep_vars.add({target_name_expr})")

            keep_vars_repr = "_keep_vars"
        else:
            # All elements are strings - use static set (translated to Python names)
            keep_vars_repr = repr({translate_name(v) for v in stmt.except_list})

        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            if ctx.new_scope_manager_var:
                # Use NewScopeManager.new_exclusive() for proper
                # scope snapshot/restore (handles nested NEW with formal params)
                ctx.emitter.line(
                    f"{ctx.new_scope_manager_var}.new_exclusive({keep_vars_repr})"
                )
            else:
                # Simple pop for non-kept variables
                ctx.emitter.line("for _var_name in list(_scope.keys()):")
                with ctx.emitter.indented():
                    ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_scope.pop(_var_name, None)")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Push tagged exclusive NEW entry to _new_stack
            # Format: ('excl', keep_vars_set, saved_non_kept_dict)
            ctx.emitter.line(
                f"state._new_stack.append(('excl', {keep_vars_repr}, {{k: v.copy() if hasattr(v, 'copy') else v for k, v in state._locals.items() if k not in {keep_vars_repr}}}))"
            )
            ctx.emitter.line("for _var_name in list(state._locals.keys()):")
            with ctx.emitter.indented():
                ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                with ctx.emitter.indented():
                    ctx.emitter.line("state._locals.pop(_var_name, None)")
        else:
            # TRAMPOLINE strategy without dynamic locals - not supported
            raise NotImplementedError(
                "Exclusive NEW not supported in TRAMPOLINE strategy"
            )
        return

    # Handle argumentless NEW (new all locals)
    # N with no args creates a new scope for ALL local variables
    # This is equivalent to exclusive NEW with empty except list: N ()
    # (though N () is technically invalid MUMPS syntax - YDB rejects it)
    if not stmt.variables and not stmt.exclusive:
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            if ctx.new_scope_manager_var:
                # Use NewScopeManager.new_all() for proper scope
                # snapshot/restore (handles nested NEW with formal params)
                ctx.emitter.line(f"{ctx.new_scope_manager_var}.new_all()")
            else:
                # Simple clear of all local variables
                ctx.emitter.line("_scope.clear()")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Push tagged argumentless NEW entry to _new_stack
            # Format: ('all', saved_full_dict)
            ctx.emitter.line(
                "state._new_stack.append(('all', {k: v.copy() if hasattr(v, 'copy') else v for k, v in state._locals.items()}))"
            )
            ctx.emitter.line("state._locals.clear()")
        else:
            # TRAMPOLINE strategy without dynamic locals - not supported
            raise NotImplementedError(
                "Argumentless NEW not supported in TRAMPOLINE strategy"
            )
        return

    # Selective vars already processed above (before exclusive check)
    # Only reach here for argumentless NEW or if no vars/exclusive
    if _has_selective:
        return

    # Process each variable in the new list
    _generate_new_selective_vars(stmt, ctx)


def _generate_new_selective_vars(stmt: MNewStatement, ctx: "GeneratorContext") -> None:
    """Generate code for selective NEW variables (the for-loop over stmt.variables)."""
    for var in stmt.variables:
        # Handle indirection in NEW (N @A where A contains variable name)
        if isinstance(var, MIndirection):
            from m2py.codegen.expressions import generate_expr

            if var.expression is None:
                raise ValueError("NEW indirection has no expression")

            # Get the VALUE of the indirection expression directly.
            # Unlike FOR @A which expects a single variable name, NEW @A
            # expects a comma-separated list of variable names or exclusive
            # groups. E.g., S A="X,Y" N @A should NEW both X and Y.
            # S A="(B,C)" N @A should do exclusive NEW keeping B,C.
            value_expr = generate_expr(var.expression, ctx)

            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                if ctx.new_scope_manager_var:
                    # Use execute_new_indirection for full MUMPS NEW argument
                    # parsing at runtime — handles selective, exclusive, mixed,
                    # and nested indirection patterns
                    ctx.emitter.line(
                        f"_rt.execute_new_indirection(str({value_expr}), {ctx.new_scope_manager_var}, _scope)"
                    )
                else:
                    # Fallback: simple split and pop (no scope manager)
                    ctx.emitter.line(
                        f"_ind_var_list = _rt._split_argument_list(str({value_expr}))"
                    )
                    ctx.emitter.line("for _ind_var in _ind_var_list:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_scope.pop(_ind_var, None)")
            elif ctx.strategy == GotoStrategy.TRAMPOLINE:
                if ctx.uses_dynamic_locals:
                    # TRAMPOLINE with dynamic locals: split the variable name
                    # list and push each to state._new_stack for unwind on QUIT
                    ctx.emitter.line(
                        f"for _ind_var in _rt._split_argument_list(str({value_expr})):"
                    )
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            "state._new_stack.append(('var', _ind_var, "
                            "state._locals.pop(_ind_var, None)))"
                        )
                else:
                    # TRAMPOLINE without dynamic locals
                    if ctx.new_scope_manager_var:
                        # DOT block with scope manager: use new_var() for save/restore
                        ctx.emitter.line(
                            f"for _ind_var in _rt._split_argument_list(str({value_expr})):"
                        )
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                f"{ctx.new_scope_manager_var}.new_var(_ind_var)"
                            )
                    else:
                        # Pop from _scope (no save/restore)
                        ctx.emitter.line(
                            f"for _ind_var in _rt._split_argument_list(str({value_expr})):"
                        )
                        with ctx.emitter.indented():
                            ctx.emitter.line("_scope.pop(_ind_var, None)")
            else:
                raise NotImplementedError(
                    f"NEW indirection not supported for strategy {ctx.strategy}"
                )
        elif isinstance(var, MSpecialVariable):
            # Handle NEW for special variables ($ETRAP, $ECODE, $ZERROR, etc.)
            # VistA uses patterns like: N $ETRAP,$ESTACK S $ETRAP="..."
            # This saves current value and initializes to empty on scope exit
            svar_name = var.name.upper()
            if svar_name in ("ETRAP", "ET"):
                if ctx.new_scope_manager_var:
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_special_var('etrap', _rt.etrap(), _rt.set_etrap)"
                    )
                else:
                    # Fallback: no-op if no scope manager
                    ctx.emitter.line("_rt.set_etrap('')")
            elif svar_name in ("ECODE", "EC"):
                if ctx.new_scope_manager_var:
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_special_var('ecode', _rt.ecode(), _rt.set_ecode)"
                    )
                else:
                    ctx.emitter.line("_rt.set_ecode('')")
            elif svar_name in ("ZERROR", "ZE"):
                if ctx.new_scope_manager_var:
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_special_var('zerror', _rt.zerror(), _rt.set_zerror)"
                    )
                else:
                    ctx.emitter.line("_rt.set_zerror('')")
            elif svar_name in ("ESTACK", "ES"):
                # NEW $ESTACK resets the error stack tracking
                # Sets a marker so that QUIT from this level ignores $ECODE errors
                # This allows routines to establish a "clean" error handling frame
                if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                    if ctx.new_scope_manager_var:
                        # Save current estack level and reset to current depth
                        ctx.emitter.line(
                            f"{ctx.new_scope_manager_var}.new_special_var('estack', "
                            f"_rt._etrap_set_level, lambda v: setattr(_rt, '_etrap_set_level', v))"
                        )
                        # Reset to current stack depth
                        ctx.emitter.line(
                            "_rt._etrap_set_level = len(_rt._stack_frames)"
                        )
                    else:
                        # Fallback: just reset level
                        ctx.emitter.line(
                            "_rt._etrap_set_level = len(_rt._stack_frames)"
                        )
                else:
                    ctx.emitter.line("_rt._etrap_set_level = len(_rt._stack_frames)")
            elif svar_name in ("ZTRAP", "ZT"):
                # NEW $ZTRAP saves/restores on scope exit
                if ctx.new_scope_manager_var:
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_special_var('ztrap', _rt.ztrap(), _rt.set_ztrap)"
                    )
                else:
                    ctx.emitter.line("_rt.set_ztrap('')")
            elif svar_name in ("ZSTATUS", "ZS"):
                # NEW $ZSTATUS saves/restores on scope exit
                if ctx.new_scope_manager_var:
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_special_var('zstatus', _rt.zstatus(), _rt.set_zstatus)"
                    )
                else:
                    ctx.emitter.line("_rt.set_zstatus('')")
            elif svar_name in ("ZPOSITION", "ZP"):
                # NEW $ZPOSITION saves/restores on scope exit
                if ctx.new_scope_manager_var:
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_special_var('zposition', _rt.zposition(), _rt.set_zposition)"
                    )
                else:
                    ctx.emitter.line("_rt.set_zposition('')")
            else:
                raise NotImplementedError(f"NEW ${var.name} not supported")
        else:
            # Regular variable name (string)
            var_name = var
            # For SIMPLE_FUNCTIONS strategy with NewScopeManager, use .new_var()
            # This ensures proper save/restore on function exit
            translated = translate_name(var_name)
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                if ctx.new_scope_manager_var:
                    # Use NewScopeManager for proper save/restore semantics
                    # Must use translated name since _scope keys are translated
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_var({translated!r})"
                    )
                else:
                    # Fallback: simple pop (used when no NewScopeManager in context)
                    ctx.emitter.line(f"_scope.pop({translated!r}, None)")
            else:
                # TRAMPOLINE strategy
                translated = translate_name(var_name)
                if ctx.uses_dynamic_locals:
                    # Push tagged selective NEW entry to _new_stack
                    # Format: ('var', name, saved_value_or_None)
                    ctx.emitter.line(
                        f"state._new_stack.append(('var', {translated!r}, state._locals.pop({translated!r}, None)))"
                    )
                elif ctx.new_scope_manager_var:
                    # DOT block with scope manager: use new_var() for proper
                    # save/restore on block exit. This handles non-dynamic_locals
                    # TRAMPOLINE where vars live in _scope, not state._locals.
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_var({translated!r})"
                    )
                elif var_name in ctx.state_vars:
                    # State var: reset via state attribute
                    ctx.emitter.line(f"state.{translated} = MArray()")
                else:
                    # Non-state var: clear from _scope
                    ctx.emitter.line(f"_scope.pop({translated!r}, None)")


def _generate_merge(stmt: MMergeStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for MERGE command.

    MERGE copies entire variable subtrees.

    Supports:
    - M B=A → Copy local A tree to local B
    - M L=^G → Copy global ^G tree to local L
    - M ^G=A → Copy local A tree to global ^G
    - M ^G=^H → Copy global ^H tree to global ^G

    MERGE does NOT delete existing nodes in destination - it only adds/overwrites.

    Args:
        stmt: MMergeStatement node
        ctx: Generator context
    """
    for merge_pair in stmt.merges:
        dest = merge_pair.destination
        src = merge_pair.source

        if dest is None or src is None:
            continue

        # Generate source access code
        if isinstance(src, GlobalVariable):
            # Source is global: ^G or ^G(subs)
            src_name = src.name
            src_subs = gen_subscripts_tuple(src.subscripts, ctx, str_wrap=True)

            # Get source tree from global storage
            src_tree_expr = f'_rt.globals.get_tree("{src_name}", {src_subs})'

        elif isinstance(src, NakedGlobal):
            # Source is naked global: ^(subs)
            src_subs = gen_subscripts_tuple(src.subscripts, ctx, str_wrap=True)

            # Resolve naked then get tree
            ctx.emitter.line(
                f"_naked_name, _naked_subs = _rt.globals.resolve_naked({src_subs})"
            )
            src_tree_expr = "_rt.globals.get_tree(_naked_name, _naked_subs)"

        elif isinstance(src, MVariable):
            # Source is local variable: A or A(subs)
            src_var_name = src.name

            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # TRAMPOLINE with dynamic_locals: variables live in state._locals
                if src.subscripts:
                    subs_code = [generate_expr(sub, ctx) for sub in src.subscripts]
                    src_tree_expr = f"state._locals.get({src_var_name!r}, MArray())[{', '.join(subs_code)}]"
                else:
                    src_tree_expr = f"state._locals.get({src_var_name!r}, MArray())"
            elif (
                ctx.strategy == GotoStrategy.TRAMPOLINE
                and not ctx.uses_dynamic_locals
                and src_var_name in ctx.array_vars
            ):
                # TRAMPOLINE static: variable is a field on RoutineState dataclass
                src_translated = translate_name(src_var_name)
                if src.subscripts:
                    subs_code = [generate_expr(sub, ctx) for sub in src.subscripts]
                    src_tree_expr = f"state.{src_translated}[{', '.join(subs_code)}]"
                else:
                    src_tree_expr = f"state.{src_translated}"
            else:
                # SIMPLE_FUNCTIONS or TRAMPOLINE fallback: use _scope
                if src.subscripts:
                    subs_code = [generate_expr(sub, ctx) for sub in src.subscripts]
                    src_tree_expr = f"_scope.get({src_var_name!r}, MArray())[{', '.join(subs_code)}]"
                else:
                    src_tree_expr = f"_scope.get({src_var_name!r}, MArray())"

        elif isinstance(src, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
            # Source is extended global: ^|"env"|name or ^["gld"]name
            # Use namespace-qualified key for isolation
            src_name = src.name
            src_ns = getattr(src.environment, "value", "") if src.environment else ""
            src_subs = gen_subscripts_tuple(src.subscripts, ctx, str_wrap=True)
            ns_name = f"{src_ns}:{src_name}" if src_ns else src_name

            src_tree_expr = f'_rt.globals.get_tree("{ns_name}", {src_subs})'

        elif isinstance(src, MIndirection):
            # Source is indirection: @VAR or @VAR@(subs)
            # Use unified resolve_for_target API to resolve variable name
            from m2py.codegen.indirection import generate_merge_indirection_name

            name_expr = generate_merge_indirection_name(src, ctx)
            src_tree_expr = f"_rt.get_tree_var({name_expr}, _scope)"

        else:
            raise NotImplementedError(
                f"MERGE source type not supported: {type(src).__name__}"
            )

        # Generate destination merge code
        if isinstance(dest, GlobalVariable):
            # Destination is global: ^G or ^G(subs)
            dest_name = dest.name
            dest_subs = gen_subscripts_tuple(dest.subscripts, ctx, str_wrap=True)

            # Get source tree and merge into global
            ctx.emitter.line(f"_merge_src = {src_tree_expr}")
            ctx.emitter.line("if _merge_src is not None:")
            ctx.emitter.indent()
            ctx.emitter.line(
                f'_rt.globals.merge_tree("{dest_name}", {dest_subs}, _merge_src)'
            )
            ctx.emitter.dedent()

        elif isinstance(dest, NakedGlobal):
            # Destination is naked global: ^(subs)
            # IMPORTANT: Must evaluate source FIRST (including get_tree which updates
            # naked indicator), THEN resolve destination naked reference.
            # This matches MUMPS semantics where source side-effects occur before
            # destination is resolved.
            dest_subs = gen_subscripts_tuple(dest.subscripts, ctx, str_wrap=True)

            # Get source tree FIRST (this updates naked indicator)
            ctx.emitter.line(f"_merge_src = {src_tree_expr}")
            # THEN resolve destination naked using updated indicator
            ctx.emitter.line(
                f"_naked_dest_name, _naked_dest_subs = _rt.globals.resolve_naked({dest_subs})"
            )
            ctx.emitter.line("if _merge_src is not None:")
            ctx.emitter.indent()
            ctx.emitter.line(
                "_rt.globals.merge_tree(_naked_dest_name, _naked_dest_subs, _merge_src)"
            )
            ctx.emitter.dedent()

        elif isinstance(dest, MVariable):
            # Destination is local variable: B or B(subs)
            dest_var_name = dest.name

            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                # Ensure destination exists as MArray
                ctx.emitter.line(f"if {dest_var_name!r} not in _scope:")
                ctx.emitter.indent()
                ctx.emitter.line(f"_scope[{dest_var_name!r}] = MArray()")
                ctx.emitter.dedent()

                if dest.subscripts:
                    subs_code = []
                    for sub in dest.subscripts:
                        subs_code.append(generate_expr(sub, ctx))
                    dest_expr = f"_scope[{dest_var_name!r}][{', '.join(subs_code)}]"
                else:
                    dest_expr = f"_scope[{dest_var_name!r}]"

                # Check if source exists before merging
                ctx.emitter.line(f"_merge_src = {src_tree_expr}")
                ctx.emitter.line("if _merge_src is not None:")
                ctx.emitter.indent()
                ctx.emitter.line(f"{dest_expr}.merge_from(_merge_src)")
                ctx.emitter.dedent()
            else:
                # TRAMPOLINE strategy
                if ctx.uses_dynamic_locals:
                    # TRAMPOLINE with dynamic_locals: variables live in state._locals
                    if dest.subscripts:
                        subs_code = [generate_expr(sub, ctx) for sub in dest.subscripts]
                        dest_expr = f"state._locals.setdefault({dest_var_name!r}, MArray())[{', '.join(subs_code)}]"
                    else:
                        dest_expr = (
                            f"state._locals.setdefault({dest_var_name!r}, MArray())"
                        )
                elif dest_var_name in ctx.array_vars:
                    # TRAMPOLINE static: variable is a field on RoutineState dataclass
                    dest_translated = translate_name(dest_var_name)
                    if dest.subscripts:
                        subs_code = [generate_expr(sub, ctx) for sub in dest.subscripts]
                        dest_expr = f"state.{dest_translated}[{', '.join(subs_code)}]"
                    else:
                        dest_expr = f"state.{dest_translated}"
                else:
                    # TRAMPOLINE fallback: use _scope
                    if dest.subscripts:
                        subs_code = [generate_expr(sub, ctx) for sub in dest.subscripts]
                        dest_expr = f"_scope.setdefault({dest_var_name!r}, MArray())[{', '.join(subs_code)}]"
                    else:
                        dest_expr = f"_scope.setdefault({dest_var_name!r}, MArray())"

                ctx.emitter.line(f"_merge_src = {src_tree_expr}")
                ctx.emitter.line("if _merge_src is not None:")
                ctx.emitter.indent()
                ctx.emitter.line(f"{dest_expr}.merge_from(_merge_src)")
                ctx.emitter.dedent()

        elif isinstance(dest, MIndirection):
            # Destination is indirection: @VAR or @VAR@(subs)
            # Use unified resolve_for_target API to resolve variable name
            from m2py.codegen.indirection import generate_merge_indirection_name

            name_expr = generate_merge_indirection_name(dest, ctx)

            ctx.emitter.line(f"_merge_src = {src_tree_expr}")
            ctx.emitter.line("if _merge_src is not None:")
            ctx.emitter.indent()
            ctx.emitter.line(f"_rt.merge_var({name_expr}, _merge_src, _scope)")
            ctx.emitter.dedent()

        elif isinstance(dest, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
            # Extended global: ^|"env"|name or ^["gld"]name
            # Use namespace-qualified key for isolation
            dest_name = dest.name
            dest_ns = getattr(dest.environment, "value", "") if dest.environment else ""
            dest_subs = gen_subscripts_tuple(dest.subscripts, ctx, str_wrap=True)
            ns_name = f"{dest_ns}:{dest_name}" if dest_ns else dest_name

            ctx.emitter.line(f"_merge_src = {src_tree_expr}")
            ctx.emitter.line("if _merge_src is not None:")
            ctx.emitter.indent()
            ctx.emitter.line(
                f'_rt.globals.merge_tree("{ns_name}", {dest_subs}, _merge_src)'
            )
            ctx.emitter.dedent()

        else:
            raise NotImplementedError(
                f"MERGE destination type not supported: {type(dest).__name__}"
            )


def _generate_hang(stmt: MHangStatement, ctx: "GeneratorContext") -> None:
    """Generate Python sleep for HANG command.

    MUMPS HANG pauses execution for the specified number of seconds.
    Supports fractional seconds (e.g., H 0.5 for half a second).

    Examples:
        H 5     -> time.sleep(5)
        H 0.1   -> time.sleep(0.1)
        H X     -> time.sleep(float(m_num(X)))

    Args:
        stmt: MHangStatement node with durations list
        ctx: Generator context
    """
    # HANG can have multiple durations: H 1,2,3 hangs for 1+2+3=6 seconds total
    for duration in stmt.durations:
        duration_expr = generate_expr(duration, ctx)
        # Use float() to ensure time.sleep() works with Decimal values
        ctx.emitter.line(f"time.sleep(float(m_num({duration_expr})))")


def _generate_halt(stmt: MHaltStatement, ctx: "GeneratorContext") -> None:
    """Generate Python exit for HALT command.

    MUMPS HALT terminates execution immediately. Unlike QUIT which returns
    from a subroutine, HALT stops the entire program.

    Examples:
        H (argumentless) -> raise SystemExit(0)

    Args:
        stmt: MHaltStatement node (no fields)
        ctx: Generator context
    """
    ctx.emitter.line("raise SystemExit(0)")


def _generate_read(stmt: MReadStatement, ctx: "GeneratorContext") -> None:
    """Generate Python input for READ command.

    MUMPS READ reads input from stdin into variables.
    Supports prompts, timeouts, and format controls.

    Examples:
        R X              -> X = input()
        R "Name: ",X     -> print("Name: ", end=""); X = input()
        R X:5            -> X = m_read_timeout(5); _test = _read_succeeded
        R !,X            -> print(); X = input()

    Args:
        stmt: MReadStatement node with arguments list
        ctx: Generator context
    """
    from m2py.asg.enums import LiteralType
    from m2py.asg.expressions import MLiteral

    for arg in stmt.arguments:
        if isinstance(arg, MFormatControl):
            # Handle format controls (!, #, ?n)
            _generate_format_control(arg, ctx)
        elif isinstance(arg, MLiteral) and arg.literal_type == LiteralType.STRING:
            # Handle prompt string - output without newline
            prompt_val = arg.value
            ctx.emitter.line(f'print({prompt_val!r}, end="")')
        elif isinstance(arg, MReadTarget):
            # Handle variable read target
            _generate_read_target(arg, ctx)


def _generate_read_target(target: MReadTarget, ctx: "GeneratorContext") -> None:
    """Generate Python input for a single READ target.

    Routes READ through the device layer via MUMPSRuntime methods:
    - read_line() for basic READ X
    - read_line_timeout(t) for READ X:t
    - read_char() for READ *X
    - read_maxlen(n) for READ X#n
    - read_maxlen_timeout(n, t) for READ X#n:t

    This ensures that after USE "file", READ X reads from the file device,
    not from stdin directly.

    Updated to emit _rt.read_* calls instead of bare input() / standalone
    helper functions.

    Args:
        target: MReadTarget with variable and optional timeout
        ctx: Generator context
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.asg.expressions import MGlobal
    from m2py.codegen.indirection import generate_name_indirection_write

    if target.variable is None:
        return

    # Check if target is indirection - needs special handling with set_indirected
    is_indirection = isinstance(target.variable, MIndirectionType)

    if is_indirection:
        # Indirection target: R @A - uses unified set_indirected
        # Type narrowing: we know target.variable is MIndirection from is_indirection check
        ind_var = cast(MIndirectionType, target.variable)
        if target.fixed_length is not None and target.timeout is not None:
            # R @A#n:t — maxlen + timeout with indirection
            maxlen_expr = generate_expr(target.fixed_length, ctx)
            timeout_expr = generate_expr(target.timeout, ctx)
            ctx.emitter.line(
                f"_read_val, _read_key, _test = _rt.read_maxlen_timeout("
                f"int({maxlen_expr}), {timeout_expr})"
            )
            ctx.emitter.line("_rt._test = _test")
            ctx.emitter.line("_rt._current_device.key = _read_key")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        elif target.fixed_length is not None:
            # R @A#n — maxlen with indirection
            maxlen_expr = generate_expr(target.fixed_length, ctx)
            ctx.emitter.line(
                f"_read_val, _read_key = _rt.read_maxlen(int({maxlen_expr}))"
            )
            ctx.emitter.line("_rt._current_device.key = _read_key")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        elif target.timeout is not None:
            # Timeout read with indirection: R @A:n
            timeout_expr = generate_expr(target.timeout, ctx)
            ctx.emitter.line(
                f"_read_val, _test = _rt.read_line_timeout({timeout_expr})"
            )
            ctx.emitter.line("_rt._test = _test")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        elif target.is_char_read:
            # Single character read with indirection: R *@A
            ctx.emitter.line("_read_val = _rt.read_char()")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        else:
            # Basic read with indirection: R @A
            ctx.emitter.line("_read_val = _rt.read_line()")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        return

    # Get the target variable name and determine storage location
    is_global_target = isinstance(target.variable, MGlobal)
    global_name = ""
    subs_tuple_str = "()"

    if isinstance(target.variable, MVariable):
        var_name = translate_name(target.variable.name)
        has_subscripts = bool(target.variable.subscripts)

        # Determine the base expression for the MArray container
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            base_expr = f"_scope.setdefault({var_name!r}, MArray())"
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            base_expr = f"state._locals.setdefault({var_name!r}, MArray())"
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
            base_expr = f"state.{var_name}"
        else:
            base_expr = f"_scope.setdefault({var_name!r}, MArray())"

        if has_subscripts:
            # Subscripted local: R ARR(I):0 → _scope['ARR'][sub] = _read_val
            # Pre-evaluate subscripts to avoid duplicate side effects
            sub_exprs: list[str] = []
            for i, sub in enumerate(target.variable.subscripts):
                sub_code = generate_expr(sub, ctx, subscript_context=True)
                sub_exprs.append(sub_code)
            if len(sub_exprs) == 1:
                storage_target = f"{base_expr}[{sub_exprs[0]}]"
            else:
                storage_target = f"{base_expr}[{', '.join(sub_exprs)}]"
        else:
            # Non-subscripted: R X → _scope['X'].value = _read_val
            storage_target = f"{base_expr}.value"
    elif is_global_target:
        # Global variable target (e.g., R ^TMP($J,$I(^TMP($J)))):
        # Pre-evaluate subscripts into temp vars, then use _rt.globals.set()
        # to store. This avoids generate_expr() producing a non-assignable LHS
        # (e.g., _rt.globals.get('TMP', (...)) or '' = value is not valid Python).
        global_var: MGlobal = target.variable  # type: ignore[assignment]
        global_name = global_var.name
        # Pre-evaluate each subscript into a temp variable so side effects
        # (like $INCREMENT) happen exactly once and in order
        sub_temps: list[str] = []
        for i, sub_expr in enumerate(global_var.subscripts or []):
            sub_code = generate_expr(sub_expr, ctx, subscript_context=True)
            temp = f"_rsub{i}"
            ctx.emitter.line(f"{temp} = {sub_code}")
            sub_temps.append(temp)
        if sub_temps:
            subs_tuple = f"({', '.join(sub_temps)},)"
        else:
            subs_tuple = "()"
        subs_tuple_str = subs_tuple
        storage_target = None  # Marker: use _rt.globals.set() below
    else:
        # Could be array subscript - generate expression
        storage_target = generate_expr(target.variable, ctx)

    if target.fixed_length is not None and target.timeout is not None:
        # R X#n:t — maxlen + timeout
        maxlen_expr = generate_expr(target.fixed_length, ctx)
        timeout_expr = generate_expr(target.timeout, ctx)
        ctx.emitter.line(
            f"_read_val, _read_key, _test = _rt.read_maxlen_timeout("
            f"int({maxlen_expr}), {timeout_expr})"
        )
        ctx.emitter.line("_rt._test = _test")
        ctx.emitter.line("_rt._current_device.key = _read_key")
    elif target.fixed_length is not None:
        # R X#n — maxlen read
        maxlen_expr = generate_expr(target.fixed_length, ctx)
        ctx.emitter.line(f"_read_val, _read_key = _rt.read_maxlen(int({maxlen_expr}))")
        ctx.emitter.line("_rt._current_device.key = _read_key")
    elif target.timeout is not None:
        # Timeout read: R X:n
        timeout_expr = generate_expr(target.timeout, ctx)
        ctx.emitter.line(f"_read_val, _test = _rt.read_line_timeout({timeout_expr})")
        ctx.emitter.line("_rt._test = _test")
    elif target.is_char_read:
        # Single character read: R *X
        ctx.emitter.line("_read_val = _rt.read_char()")
    else:
        # Basic read: R X
        ctx.emitter.line("_read_val = _rt.read_line()")

    # Store the read value into the target
    if is_global_target:
        # Use _rt.globals.set() for global targets — avoids non-assignable LHS
        # from generate_expr() (e.g., `_rt.globals.get(...) or ''`)
        ctx.emitter.line(
            f"_rt.globals.set({global_name!r}, {subs_tuple_str}, m_str(_read_val))"
        )
    else:
        ctx.emitter.line(f"{storage_target} = _read_val")


# =============================================================================
# Transaction Statement Generation
# =============================================================================


def _generate_tstart(stmt: MTStartStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for TSTART command.

    Begin transaction via database abstraction.
    TSTART restart variable snapshots.

    MUMPS: TS, TSTART, TS (), TS (A,B), TS *

    Generated:
        _rt.globals.transaction_start()
        _rt.snapshot_locals(_scope, var_names=[...])  # if restart vars specified
        _rt.snapshot_locals(_scope, all_vars=True)     # if TSTART *

    Args:
        stmt: MTStartStatement node
        ctx: Generator context
    """
    scope_expr = scope_dict_expr(ctx)

    # Start the global transaction first
    ctx.emitter.line("_rt.globals.transaction_start()")

    # Snapshot locals for restart variables if specified
    if stmt.restart_all:
        ctx.emitter.line(f"_rt.snapshot_locals({scope_expr}, all_vars=True)")
    elif stmt.restart_vars:
        # Build list of variable names from MVariable nodes
        var_names = [getattr(v, "name", str(v)) for v in stmt.restart_vars]
        var_list = "[" + ", ".join(repr(n) for n in var_names) + "]"
        ctx.emitter.line(f"_rt.snapshot_locals({scope_expr}, var_names={var_list})")
    else:
        # No restart vars — still create an empty snapshot to track nesting
        ctx.emitter.line(f"_rt.snapshot_locals({scope_expr})")


def _generate_tcommit(stmt: MTCommitStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for TCOMMIT command.

    Commit transaction via database abstraction.

    MUMPS: TC, TCOMMIT

    Generated: _rt.globals.transaction_commit()

    Per MUMPS spec:
    - If $TLEVEL = 1, commits the transaction
    - If $TLEVEL > 1, decrements $TLEVEL (nested transaction)
    - Error M44 if $TLEVEL = 0

    Args:
        stmt: MTCommitStatement node
        ctx: Generator context
    """
    ctx.emitter.line("_rt.globals.transaction_commit()")
    ctx.emitter.line("_rt.discard_local_snapshot()")


def _generate_trollback(stmt: MTRollbackStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for TROLLBACK command.

    Rollback transaction via database abstraction.

    MUMPS: TRO, TROLLBACK, TRO 1

    Generated: _rt.globals.transaction_rollback()

    Per MUMPS spec:
    - Rolls back all changes since transaction start
    - Sets $TLEVEL = 0 and $TRESTART = 0
    - Optional level argument specifies transaction level to roll back to

    LIM-016: TROLLBACK:n (with level argument) has zero VistA usage and raises
    NotImplementedError.

    Args:
        stmt: MTRollbackStatement node
        ctx: Generator context
    """
    # LIM-016: TROLLBACK:n has zero VistA usage
    if stmt.level is not None:
        raise NotImplementedError(
            "LIM-016: TROLLBACK:n (rollback to specific level) not supported"
        )

    # Roll back globals and discard all local snapshots
    # TROLLBACK rolls back to $TLEVEL=0, so discard all snapshots
    ctx.emitter.line("_rt.globals.transaction_rollback()")
    ctx.emitter.line("_rt.discard_all_local_snapshots()")


# =============================================================================
# LOCK Statement Generation
# =============================================================================


def _generate_lock(stmt: MLockStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for LOCK command.

    LOCK command via database abstraction.

    MUMPS Forms:
    - L              ; Release all locks (argumentless)
    - L ^A           ; Exclusive lock on ^A (releases all previous locks first)
    - L +^A          ; Increment lock count on ^A
    - L -^A          ; Decrement lock count on ^A
    - L ^A:5         ; Lock with timeout (sets $TEST)
    - L (^A,^B)      ; Lock multiple simultaneously (releases all previous)
    - L +(^A,^B)     ; Increment locks on multiple
    - L -(^A,^B)     ; Decrement locks on multiple

    Generated code:
    - _rt.globals.unlock_all() for release-all semantics
    - _rt.globals.lock(name, subscripts, timeout, lock_type)

    Per MUMPS spec §8.2.12:
    - Timed LOCK sets $TEST: 1 for success, 0 for timeout
    - Untimed LOCK does NOT modify $TEST
    - LOCK - always sets $TEST to 1

    Args:
        stmt: MLockStatement node
        ctx: Generator context
    """
    # Handle argumentless LOCK - releases all locks
    if not stmt.targets:
        ctx.emitter.line("_rt.globals.unlock_all()")
        return

    # Handle lock_type at statement level (applies to all targets)
    # lock_type can be "" (exclusive - releases all first), "+" (increment), "-" (decrement)
    stmt_lock_type = stmt.lock_type

    # For exclusive lock (no + or -), we first release all locks
    # This happens BEFORE any locks are acquired.
    #
    # HOWEVER: when ALL targets are indirected, we must defer the unlock_all()
    # to runtime because the indirection may evaluate to an incremental lock.
    # Example: LOCK @("+"_REF_":DILOCKTM") in DILF evaluates to
    # LOCK +^DMU(subs):1 — the "+" makes it incremental, not exclusive.
    # The runtime lock_indirected() handles this correctly by parsing the
    # lock operation prefix from the resolved string.
    all_indirect = all(t.is_indirect for t in stmt.targets)
    if stmt_lock_type == "" and not all_indirect:
        ctx.emitter.line("_rt.globals.unlock_all()")

    # Process each target (now MLockTarget instances instead of dicts)
    for lock_target in stmt.targets:
        # Get lock operation from target (overrides stmt-level if present)
        target_lockop = lock_target.lockop
        # Use target lockop if present, otherwise use stmt-level
        lock_type = target_lockop if target_lockop else stmt_lock_type
        # For exclusive lock, use "+" since we already released all above
        # (unless deferred to runtime for all-indirect statements)
        if lock_type == "":
            if all_indirect:
                # Defer exclusive semantics to lock_indirected() at runtime
                effective_lockop = ""
            else:
                effective_lockop = "+"
        else:
            effective_lockop = lock_type

        # Handle indirection
        if lock_target.is_indirect:
            # Generate code for LOCK indirection using lock_indirected()
            _generate_lock_indirection_call(lock_target, stmt, effective_lockop, ctx)
            continue

        # Get the name from the MLockTarget
        name = lock_target.name
        if name is None:
            # Check if this is a naked global reference (name is None, is_global is True)
            if lock_target.is_global:
                raise NotImplementedError(
                    "Naked reference not supported in LOCK (YDB restriction)"
                )
            continue

        # Get subscripts from MLockTarget
        subscripts = lock_target.subscripts

        # Generate subscript expressions
        subs_str = gen_subscripts_tuple(subscripts, ctx)

        # Get timeout from target
        timeout_expr = lock_target.timeout

        # For parenthesized lists, timeout may be on the statement
        if timeout_expr is None and stmt.timeout is not None:
            timeout_expr = stmt.timeout

        # Generate lock call
        if timeout_expr is not None:
            # Timed lock - sets $TEST
            timeout_val = generate_expr(timeout_expr, ctx)
            if effective_lockop == "-":
                # LOCK -name:timeout always sets $TEST to 1
                ctx.emitter.line(
                    f'_rt.globals.lock("{name}", {subs_str}, lock_type="-")'
                )
                ctx.emitter.line("_test = True")
                ctx.emitter.line("_rt._test = _test")
            else:
                # LOCK +name:timeout sets $TEST based on success/timeout
                ctx.emitter.line(
                    f'_test = _rt.globals.lock("{name}", {subs_str}, '
                    f'timeout={timeout_val}, lock_type="{effective_lockop}")'
                )
                ctx.emitter.line("_rt._test = _test")
        else:
            # Untimed lock - does NOT modify $TEST
            ctx.emitter.line(
                f'_rt.globals.lock("{name}", {subs_str}, lock_type="{effective_lockop}")'
            )


def _generate_lock_indirection_call(
    lock_target: "MLockTarget",
    stmt: "MLockStatement",
    lockop: str,
    ctx: "GeneratorContext",
) -> None:
    """Generate code for LOCK indirection target.

    Emits _rt.lock_indirected() call for @NAME lock targets.

    Args:
        lock_target: MLockTarget with is_indirect=True
        stmt: Parent MLockStatement (for statement-level timeout)
        lockop: Effective lock operation ("", "+", "-")
        ctx: Generator context
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.asg.expressions import MVariable
    from m2py.codegen.indirection import (
        _count_indirection_levels_with_subscripts,
        generate_lock_indirection,
    )
    from m2py.parser.textx_classes import GlobalVariable

    ind = lock_target.indirection
    if ind is None:
        ctx.emitter.line("# LOCK indirection: missing indirection expression")
        return

    # Ensure we have an indirection expression
    if not isinstance(ind, MIndirectionType):
        ctx.emitter.line(
            f"# LOCK indirection: expected MIndirection, got {type(ind).__name__}"
        )
        return

    # Count indirection levels and get inner expression
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(ind)

    # Build source expression
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(_format_subscript(s) for s in '
                f'[{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(_format_subscript(s) for s in '
                f'[{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    else:
        # Complex expression - evaluate to get source string.
        # The expression is fully evaluated in Python, producing the LOCK
        # argument string directly (e.g., "+^DD(1,2):n" from "+"_REF_":n").
        # Set levels=0 so lock_indirected uses the string directly instead
        # of trying to resolve it as a variable name.
        source_expr = f"str({generate_expr(inner_expr, ctx)})"
        levels = 0

    # Build per-level subscripts if present
    if all_subscripts and any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subscripts_expr = f"[{', '.join(per_level_subs)}]"
    else:
        subscripts_expr = None

    # Get timeout from target or statement
    timeout_expr = lock_target.timeout
    if timeout_expr is None and stmt.timeout is not None:
        timeout_expr = stmt.timeout

    timeout_val = generate_expr(timeout_expr, ctx) if timeout_expr else None

    # In TRAMPOLINE mode, state._locals is the canonical variable store.
    # _scope may be stale (only synced at DO boundaries).  Sync before
    # the lock_indirected call so the indirection resolver finds current
    # variable values.
    if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
        ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")

    # Generate the lock_indirected call
    code = generate_lock_indirection(
        lock_expr=source_expr,
        lockop=lockop,
        timeout_expr=timeout_val,
        subscripts_expr=subscripts_expr,
        levels=levels,
    )
    ctx.emitter.line(code)


# =============================================================================
# I/O Statement Generation
# =============================================================================


def _generate_open(stmt: MOpenStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for OPEN command.

    Opens devices/files for I/O.

    MUMPS Forms:
    - O "file"                ; Open file
    - O "file":NEWVERSION     ; Open for write (create/truncate)
    - O "file":(params)       ; Open with parenthesized params
    - O "file":(params):timeout ; Open with timeout (sets $TEST)
    - O device1,device2       ; Open multiple devices

    Note: The parser may interpret bare :KEYWORD as a timeout due to
    MUMPS syntax ambiguity. We detect common device keywords and treat
    them as parameters.

    Generated code:
    - _rt.open_device("file", ["params"])
    - With timeout: _test = _rt.open_device("file", ["params"], timeout)

    Per MUMPS spec §8.2.15:
    - Timed OPEN sets $TEST: 1 for success, 0 for timeout
    - Untimed OPEN does NOT modify $TEST

    Args:
        stmt: MOpenStatement node
        ctx: Generator context
    """
    from m2py.asg.expressions import MVariable as MVar

    # Common device keywords that may be misinterpreted as timeouts
    DEVICE_KEYWORDS = {
        "NEWVERSION",
        "NEW",
        "READONLY",
        "READ",
        "WRITE",
        "APPEND",
        "STREAM",
        "FIXED",
        "VARIABLE",
        "NOWRAP",
        "WRAP",
        "NOTRUNCATE",
        "TRUNCATE",
        "REWIND",
        "SEEK",
        "DELETE",
        "RENAME",
    }

    for device in stmt.devices:
        if device.device_expr is None:
            continue

        # --- OPEN command argument indirection: O @VAR ---
        # When the entire device spec is indirected (no separate params/timeout
        # from the parser), the variable contains the full OPEN spec string
        # e.g. %I2 = "%IO:(newversion:nowrap:stream):0"
        # Delegate to open_device_indirected which parses at runtime.
        from m2py.asg.expressions import MIndirection as _MIndirection

        if (
            isinstance(device.device_expr, _MIndirection)
            and not device.parameters
            and device.timeout is None
        ):
            # For command argument indirection, we need the RAW VALUE of the
            # variable (the OPEN spec string), not a further indirection
            # resolution. generate_expr on the operand gives us the variable
            # value directly (e.g. _scope.get("%I2", "")), whereas
            # generate_expr on the full MIndirection would try to resolve
            # that value as yet another variable name.
            indir_expr = device.device_expr.expression
            assert indir_expr is not None, "MIndirection.expression is None"
            spec_expr = generate_expr(indir_expr, ctx)
            # The spec may contain a timeout (parsed at runtime), so always
            # capture result and sync $TEST — open_device_indirected returns
            # True/False and sets _rt._test when timeout is present.
            ctx.emitter.line(
                f"_test = _rt.open_device_indirected(m_str({spec_expr}), _scope)"
            )
            ctx.emitter.line("_rt._test = _test")
            continue

        # Generate device name expression
        device_name = generate_expr(device.device_expr, ctx)

        # Collect parameters - device params are keywords, not variables
        params = []
        for param in device.parameters:
            # Device parameters can be:
            # - Identifiers (NEWVERSION, READONLY, etc.) - treat as string constants
            # - Expressions for dynamic parameters
            if isinstance(param, MVar) and not param.subscripts:
                # Simple identifier - treat as string keyword
                params.append(repr(param.name))
            else:
                # Expression - evaluate it
                param_str = generate_expr(param, ctx)
                params.append(param_str)

        # Check if timeout is actually a device keyword (parser ambiguity)
        actual_timeout = device.timeout
        if (
            actual_timeout is not None
            and isinstance(actual_timeout, MVar)
            and not actual_timeout.subscripts
            and actual_timeout.name.upper() in DEVICE_KEYWORDS
        ):
            # This is a device keyword, not a timeout
            params.append(repr(actual_timeout.name))
            actual_timeout = None

        # Build parameters list string
        if params:
            params_str = f"[{', '.join(params)}]"
        else:
            params_str = "None"

        # Generate the open call
        if actual_timeout is not None:
            # Timed OPEN - sets $TEST
            timeout_val = generate_expr(actual_timeout, ctx)
            ctx.emitter.line(
                f"_test = _rt.open_device({device_name}, {params_str}, {timeout_val})"
            )
            ctx.emitter.line("_rt._test = _test")
        else:
            # Untimed OPEN - does NOT modify $TEST
            ctx.emitter.line(f"_rt.open_device({device_name}, {params_str})")


def _generate_close(stmt: MCloseStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for CLOSE command.

    Closes devices/files.

    MUMPS Forms:
    - C "file"         ; Close file
    - C device1,device2 ; Close multiple devices
    - C device:params   ; Close with parameters

    Generated code:
    - _rt.close_device("file")
    - _rt.close_device("file", ["params"])

    Args:
        stmt: MCloseStatement node
        ctx: Generator context
    """
    from m2py.asg.expressions import MVariable as MVar

    for device in stmt.devices:
        if device.device_expr is None:
            continue

        # Generate device name expression
        device_name = generate_expr(device.device_expr, ctx)

        # Collect parameters - device params are keywords, not variables
        params = []
        for param in device.parameters:
            if isinstance(param, MVar) and not param.subscripts:
                # Simple identifier - treat as string keyword
                params.append(repr(param.name))
            else:
                # Expression - evaluate it
                param_str = generate_expr(param, ctx)
                params.append(param_str)

        # Build parameters list string
        if params:
            params_str = f"[{', '.join(params)}]"
        else:
            params_str = "None"

        ctx.emitter.line(f"_rt.close_device({device_name}, {params_str})")


def _generate_use(stmt: MUseStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for USE command.

    Switches current I/O device.

    MUMPS Forms:
    - U "file"          ; Use file as current device
    - U 0               ; Use principal device (stdin/stdout)
    - U device:params   ; Use with parameters

    Generated code:
    - _rt.use_device("file")
    - _rt.use_device("file", ["params"])

    Note: USE does not affect $TEST.

    Args:
        stmt: MUseStatement node
        ctx: Generator context
    """
    from m2py.asg.expressions import MVariable as MVar

    for device in stmt.devices:
        if device.device_expr is None:
            continue

        # Generate device name expression
        device_name = generate_expr(device.device_expr, ctx)

        # Collect parameters - device params are keywords, not variables
        params = []
        for param in device.parameters:
            if isinstance(param, MVar) and not param.subscripts:
                # Simple identifier - treat as string keyword
                params.append(repr(param.name))
            else:
                # Expression - evaluate it
                param_str = generate_expr(param, ctx)
                params.append(param_str)

        # Build parameters list string
        if params:
            params_str = f"[{', '.join(params)}]"
        else:
            params_str = "None"

        ctx.emitter.line(f"_rt.use_device({device_name}, {params_str})")


def _generate_xecute(stmt: MXecuteStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for XECUTE command.

    For constant string XECUTE, inline the generated Python code at transpile
    time for better performance and debuggability.

    For dynamic XECUTE (variables/expressions), generate runtime.execute_mumps()
    calls that parse and execute at runtime with shared scope.

    Args:
        stmt: MXecuteStatement node
        ctx: Generator context

    Behavior:
        - Constant strings (is_constant=True): Parse at transpile time, inline Python
        - Dynamic expressions (is_constant=False): Call _rt.execute_mumps() at runtime
        - Multiple arguments: Process each in order
        - Postconditions: Wrap in if block
        - $TEST is NOT stacked (XECUTE mutations visible to caller)
    """
    # Import here to avoid circular imports
    from m2py.asg.elements import MParseError
    from m2py.parser.compiler import compile_mumps_line

    def contains_control_flow(mumps_code: str) -> bool:
        """Check if MUMPS code contains control flow that affects XECUTE scope.

        Detects:
        - GOTO (G/GOTO) - transfers control to label
        - DO (D/DO) - calls subroutine
        - QUIT (Q/QUIT) - exits current scope
        - Nested XECUTE (X/XECUTE) - may contain any of the above
        """
        import re

        # Pattern: G, GOTO, D, DO followed by label/target
        # or Q, QUIT (bare or with condition/value)
        # or X, XECUTE (nested XECUTE may contain control flow)
        goto_do_pattern = re.compile(r"\b(G|GOTO|D|DO)\s+[A-Za-z0-9^]+", re.IGNORECASE)
        quit_pattern = re.compile(r"\b(Q|QUIT)\b", re.IGNORECASE)
        xecute_pattern = re.compile(r'\b(X|XECUTE)\s+"', re.IGNORECASE)
        return bool(
            goto_do_pattern.search(mumps_code)
            or quit_pattern.search(mumps_code)
            or xecute_pattern.search(mumps_code)
        )

    def generate_inline_code(mumps_code: str) -> None:
        """Parse and generate inline Python for constant MUMPS code.

        Uses compile_mumps_line() to run the full parse→analyze→structure
        pipeline, then generates Python for each resulting ASG statement.
        """
        result = compile_mumps_line(mumps_code)
        if isinstance(result, MParseError):
            # Include original code in error message for context.
            # Use repr() to safely escape all quotes in the message.
            error_msg = f"XECUTE parse error in {mumps_code!r}: {result.message}"
            # Double-escape for code generation: the repr() already handles
            # inner quotes, so we just need to emit a valid Python string.
            ctx.emitter.line(f"raise SyntaxError({error_msg!r})")
            return

        # Generate Python for each structured statement
        for asg_stmt in result:
            generate_statement(asg_stmt, ctx)

    def generate_inline_with_control_flow(code_strings: list) -> None:
        """Generate inline XECUTE code that contains GOTO/DO.

        GOTO/DO inside inline XECUTE needs special handling.
        We wrap the inline code in a try/except block and use _XecuteExit
        exception to exit just the XECUTE context without returning from
        the enclosing function.

        Each XECUTE argument has its own control flow scope.
        QUIT in one argument should not skip subsequent arguments.
        Generate a separate try/except for each code string.

        Also handles GotoExternal from called labels. When an XECUTE'd
        GOTO calls an internal label that raises GotoExternal (external GOTO),
        we need to run the external routine to completion and continue.
        Only applies in TRAMPOLINE mode where state._locals exists.
        """
        from m2py.codegen.enums import GotoStrategy

        # Set flag so GOTO/DO generate raise _XecuteExit instead of return
        old_in_inline_xecute = ctx.in_inline_xecute
        ctx.in_inline_xecute = True

        # Check if we're in TRAMPOLINE mode (where state._locals exists)
        is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE

        # Also handle external GOTOs in non-TRAMPOLINE mode
        # Check if the routine has external GOTOs detected in analysis
        has_external_gotos = ctx.routine.has_external_gotos

        # Each code string gets its own try/except
        for code_str in code_strings:
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                generate_inline_code(code_str)
            # Generate GotoExternal handler in TRAMPOLINE mode
            # where state._locals exists and cross-routine GOTOs are possible
            # Also generate handler in SIMPLE_FUNCTIONS mode
            # when routine has external GOTOs (uses _scope directly)
            if is_trampoline or has_external_gotos:
                ctx.emitter.line("except GotoExternal as _goto:")
                with ctx.emitter.indented():
                    _emit_goto_external_handler(ctx)
            ctx.emitter.line("except _XecuteExit:")
            with ctx.emitter.indented():
                ctx.emitter.line("pass  # GOTO/DO exited XECUTE block")

        ctx.in_inline_xecute = old_in_inline_xecute

    def generate_dynamic_xecute() -> None:
        """Generate runtime calls for dynamic XECUTE expressions.

        Each code expression is evaluated at runtime and executed via
        _rt.execute_mumps() with shared _scope.

        XECUTE does NOT stack $TEST. After execute_mumps(), sync _test from
        _rt._test so mutations made by XECUTEd code are visible to caller.

        Pass globals() to execute_mumps so it can access module labels
        for DO/GOTO commands in dynamic XECUTE.

        XECUTE argument indirection: X @X where X="Y,Z" should:
        1. Resolve @X → "Y,Z"
        2. Split into ["Y", "Z"]
        3. For each: resolve @Y → code1, @Z → code2
        4. Execute each code string
        """
        from m2py.asg.expressions import MIndirection
        from m2py.codegen.indirection import (
            _count_indirection_levels_with_subscripts,
        )
        from m2py.codegen.var_access import scope_dict_expr

        # Sync state._locals → _scope in TRAMPOLINE mode so nested XECUTE
        # calls can access variables from the calling scope. MArray objects
        # are put directly since SIMPLE_FUNCTIONS code handles them natively.
        emit_state_to_scope_sync(ctx)

        # Use arguments structure (always populated by semantic analyzer)
        for xecute_arg in stmt.arguments:
            expr = xecute_arg.expression

            # Check if this is an indirection that needs special XECUTE handling
            if isinstance(expr, MIndirection):
                # XECUTE argument indirection: X @X where X="Y,Z"
                # Use execute_mumps_indirected which handles the comma-separated
                # variable list and resolves each to get the code to execute
                levels, inner_expr, all_subscripts = (
                    _count_indirection_levels_with_subscripts(expr)
                )
                scope_expr = scope_dict_expr(ctx)

                # Get the source variable name
                from m2py.asg.expressions import MVariable
                from m2py.parser.textx_classes import GlobalVariable

                if isinstance(inner_expr, MVariable):
                    source_name = inner_expr.name
                    if inner_expr.subscripts:
                        sub_exprs = [
                            generate_expr(s, ctx) for s in inner_expr.subscripts
                        ]
                        subs_str = ", ".join(sub_exprs)
                        source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
                    else:
                        source_expr = f'"{source_name}"'
                elif isinstance(inner_expr, GlobalVariable):
                    source_name = f"^{inner_expr.name}"
                    if inner_expr.subscripts:
                        sub_exprs = [
                            generate_expr(s, ctx) for s in inner_expr.subscripts
                        ]
                        subs_str = ", ".join(sub_exprs)
                        source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
                    else:
                        source_expr = f'"{source_name}"'
                else:
                    # Complex expression - fall back to regular execute_mumps
                    expr_code = generate_expr(expr, ctx)
                    if xecute_arg.postcondition is not None:
                        cond_code = generate_expr(xecute_arg.postcondition, ctx)
                        ctx.emitter.line(f"if m_truth({cond_code}):")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                f"_rt.execute_mumps({expr_code}, _scope, globals())"
                            )
                            ctx.emitter.line("_test = _rt._test")
                            emit_scope_to_state_sync(ctx)
                    else:
                        ctx.emitter.line(
                            f"_rt.execute_mumps({expr_code}, _scope, globals())"
                        )
                        ctx.emitter.line("_test = _rt._test")
                        emit_scope_to_state_sync(ctx)
                    continue

                # Build per_level_subscripts argument if needed
                if all_subscripts and any(all_subscripts):
                    per_level_subs = []
                    for subs in all_subscripts:
                        if subs:
                            sub_exprs = [generate_expr(s, ctx) for s in subs]
                            per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                        else:
                            per_level_subs.append("[]")
                    subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
                else:
                    subs_arg = ""

                # Generate call to execute_mumps_indirected
                if xecute_arg.postcondition is not None:
                    cond_code = generate_expr(xecute_arg.postcondition, ctx)
                    ctx.emitter.line(f"if m_truth({cond_code}):")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f"_rt.execute_mumps_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg}, caller_globals=globals())"
                        )
                        ctx.emitter.line("_test = _rt._test")
                        emit_scope_to_state_sync(ctx)
                else:
                    ctx.emitter.line(
                        f"_rt.execute_mumps_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg}, caller_globals=globals())"
                    )
                    ctx.emitter.line("_test = _rt._test")
                    emit_scope_to_state_sync(ctx)
            else:
                # Regular expression (variable, string, function call, etc.)
                expr_code = generate_expr(xecute_arg.expression, ctx)
                if xecute_arg.postcondition is not None:
                    # Wrap in postcondition check
                    cond_code = generate_expr(xecute_arg.postcondition, ctx)
                    ctx.emitter.line(f"if m_truth({cond_code}):")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f"_rt.execute_mumps({expr_code}, _scope, globals())"
                        )
                        ctx.emitter.line("_test = _rt._test")
                        emit_scope_to_state_sync(ctx)
                else:
                    ctx.emitter.line(
                        f"_rt.execute_mumps({expr_code}, _scope, globals())"
                    )
                    ctx.emitter.line("_test = _rt._test")
                    emit_scope_to_state_sync(ctx)

    # Check if any constant strings contain control flow
    has_control_flow = False
    if stmt.is_constant:
        for code_str in stmt.constant_values:
            if contains_control_flow(code_str):
                has_control_flow = True
                break

    # Check if any argument has a postcondition (per-argument postcond)
    has_arg_postconditions = False
    if stmt.arguments:
        for xarg in stmt.arguments:
            if xarg.postcondition is not None:
                has_arg_postconditions = True
                break

    # Handle postcondition if present (statement-level postcondition)
    if stmt.postcondition:
        cond_expr = generate_expr(stmt.postcondition, ctx)
        ctx.emitter.line(f"if m_truth({cond_expr}):")
        with ctx.emitter.indented():
            if has_arg_postconditions:
                # Per-argument postconditions - must process each individually
                _generate_xecute_args_with_postconds(
                    stmt,
                    ctx,
                    has_control_flow,
                    generate_inline_code,
                    generate_inline_with_control_flow,
                    contains_control_flow,
                )
            elif stmt.is_constant:
                # Inline constant strings
                if has_control_flow:
                    generate_inline_with_control_flow(stmt.constant_values)
                else:
                    for code_str in stmt.constant_values:
                        generate_inline_code(code_str)
            else:
                # Dynamic XECUTE - call runtime
                generate_dynamic_xecute()
    else:
        # No statement-level postcondition - generate code directly
        if has_arg_postconditions:
            # Per-argument postconditions - must process each individually
            _generate_xecute_args_with_postconds(
                stmt,
                ctx,
                has_control_flow,
                generate_inline_code,
                generate_inline_with_control_flow,
                contains_control_flow,
            )
        elif stmt.is_constant:
            # Inline constant strings
            if has_control_flow:
                generate_inline_with_control_flow(stmt.constant_values)
            else:
                for code_str in stmt.constant_values:
                    generate_inline_code(code_str)
        else:
            # Dynamic XECUTE - call runtime
            generate_dynamic_xecute()


def _generate_xecute_args_with_postconds(
    stmt: MXecuteStatement,
    ctx: "GeneratorContext",
    has_control_flow: bool,
    generate_inline_code,
    generate_inline_with_control_flow,
    contains_control_flow,
) -> None:
    """Generate XECUTE handling arguments with per-argument postconditions.

    When XECUTE has arguments with postconditions like:
      X "code1":postcond1,"code2":postcond2,"code3"
    Each argument must be checked individually.

    For constant strings, we still inline if possible, but wrap each
    in its postcondition check. For control flow, we use the
    try/except _XecuteExit pattern.
    """
    from m2py.codegen.expressions import generate_expr
    from m2py.asg.expressions import MLiteral
    from m2py.asg.enums import LiteralType

    # Group consecutive arguments by whether they have postconditions
    # and whether they contain control flow
    for xarg in stmt.arguments:
        # Check if this argument is a constant string
        is_constant = (
            isinstance(xarg.expression, MLiteral)
            and xarg.expression.literal_type == LiteralType.STRING
        )

        if xarg.postcondition is not None:
            # Has postcondition - wrap in if block
            cond_code = generate_expr(xarg.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_code}):")
            with ctx.emitter.indented():
                if is_constant:
                    # We verified it's an MLiteral above, so cast is safe
                    literal = xarg.expression
                    assert isinstance(literal, MLiteral)
                    code_str = literal.value
                    if contains_control_flow(code_str):
                        # Inline with control flow handling
                        generate_inline_with_control_flow([code_str])
                    else:
                        generate_inline_code(code_str)
                else:
                    # Dynamic - use runtime
                    expr_code = generate_expr(xarg.expression, ctx)
                    ctx.emitter.line(
                        f"_rt.execute_mumps({expr_code}, _scope, globals())"
                    )
                    ctx.emitter.line("_test = _rt._test")
                    emit_scope_to_state_sync(ctx)
        else:
            # No postcondition - execute directly
            if is_constant:
                # We verified it's an MLiteral above, so cast is safe
                literal = xarg.expression
                assert isinstance(literal, MLiteral)
                code_str = literal.value
                if contains_control_flow(code_str):
                    generate_inline_with_control_flow([code_str])
                else:
                    generate_inline_code(code_str)
            else:
                # Dynamic - use runtime
                expr_code = generate_expr(xarg.expression, ctx)
                ctx.emitter.line(f"_rt.execute_mumps({expr_code}, _scope, globals())")
                ctx.emitter.line("_test = _rt._test")
                emit_scope_to_state_sync(ctx)


def _generate_job_process_params(
    job_target: "MJobTarget", ctx: "GeneratorContext"
) -> str:
    """Generate JOB process parameters as a list of KEY=VALUE strings.

    MUMPS JOB process parameters use keyword=value syntax:
        JOB ^RTN:(output="file":error="errfile")

    These are NOT comparisons — they are I/O redirection directives.
    The grammar parses them as Expr nodes, so `output="file"` becomes
    MBinaryOp(operator="=", left=MVariable(name="output"), right=MLiteral("file")).

    The runtime expects strings like "OUTPUT=file", "INPUT=file", "ERROR=file".
    """
    if not job_target.processparameters:
        return "None"

    parts: list[str] = []
    for param in job_target.processparameters:
        if (
            isinstance(param, MBinaryOp)
            and param.operator == "="
            and isinstance(param.left, MVariable)
            and not param.left.subscripts
        ):
            # keyword=value process parameter: generate "KEYWORD=" + str(value)
            keyword = param.left.name.upper()
            assert param.right is not None  # binary op with '=' always has rhs
            value_expr = generate_expr(param.right, ctx)
            parts.append(f'"{keyword}=" + str({value_expr})')
        else:
            # Fallback: treat as generic expression
            parts.append(generate_expr(param, ctx))

    return f"[{', '.join(parts)}]"


def _generate_job(stmt: MJobStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for JOB command.

    Starts a new process executing a routine.

    MUMPS Forms:
    - J label           ; Start job at label in current routine
    - J label^routine   ; Start job at label in external routine
    - J label::5        ; Start job with 5-second timeout
    - J label:():5      ; Start job with empty params and timeout
    - J label:params    ; Start job with process parameters

    Timeout behavior per MUMPS spec 8.2.10:
    - No timeout: Does not affect $TEST
    - Timeout present: Sets $TEST=1 on success, $TEST=0 on timeout

    Generated code:
    - _rt.job("label", "routine", args, timeout) -> (success, pid)
    - $ZJOB is set to the spawned process ID

    Note: In Python transpilation, JOB creates a subprocess running
    the transpiled Python module with the specified entry point.

    Args:
        stmt: MJobStatement node
        ctx: Generator context
    """
    for job_target in stmt.targets:
        if job_target.call is None:
            continue

        call = job_target.call

        # Check for indirection - handle like indirect GOTO
        if call.label_is_indirect or call.routine_is_indirect:
            _generate_indirect_job(job_target, ctx)
            continue

        # Build label/routine reference
        label_name = repr(call.name) if call.name else "None"
        routine_name = repr(call.routine) if call.routine else "None"

        # Generate arguments if any
        args_parts = []
        for arg in call.arguments:
            if arg.expression is not None:
                arg_expr = generate_expr(arg.expression, ctx)
            else:
                arg_expr = "None"
            args_parts.append(arg_expr)
        args_str = f"[{', '.join(args_parts)}]" if args_parts else "[]"

        # Generate process parameters if any
        params_str = _generate_job_process_params(job_target, ctx)

        # Generate timeout expression
        has_timeout = job_target.timeout is not None
        if has_timeout and job_target.timeout is not None:
            timeout_expr = generate_expr(job_target.timeout, ctx)
        else:
            timeout_expr = "None"

        # Generate JOB call - runtime handles subprocess creation
        # _rt.start_job() returns True on success, False on timeout
        if has_timeout:
            # With timeout: _test = _rt.start_job(label, routine, args, timeout)
            ctx.emitter.line(
                f"_test = _rt.start_job({label_name}, {routine_name}, {args_str}, "
                f"{params_str}, {timeout_expr})"
            )
            ctx.emitter.line("_rt._test = _test")
        else:
            # Without timeout: just call start_job, don't modify $TEST
            ctx.emitter.line(
                f"_rt.start_job({label_name}, {routine_name}, {args_str}, "
                f"{params_str}, {timeout_expr})"
            )


def _generate_indirect_job(job_target: "MJobTarget", ctx: "GeneratorContext") -> None:
    """Generate Python code for indirect JOB (J @TARGET).

    Generate runtime dispatch for indirect JOB.
    Handles various patterns:
    - J @TARGET: Full indirection (label comes from variable)
    - J LABEL^@RTN: Partial indirection (routine from variable)
    - J @LBL^@RTN: Double indirection (both from variables)

    Similar to indirect GOTO but starts a background job instead of
    transferring control.

    Args:
        job_target: MJobTarget ASG node with indirect call
        ctx: Generator context
    """
    call = job_target.call
    if call is None:
        return

    # Determine what's indirect and what's static
    label_is_indirect = call.label_is_indirect
    routine_is_indirect = call.routine_is_indirect

    # Generate the target expression
    if label_is_indirect and call.indirection:
        # Label comes from indirection: J @TARGET or J @TARGET^ROUTINE
        label_expr = generate_expr(call.indirection, ctx)
    elif call.name:
        # Static label name
        label_expr = repr(call.name)
    else:
        label_expr = "''"

    if routine_is_indirect and call.routine_indirection:
        # Routine comes from indirection: J LABEL^@RTN or J @LBL^@RTN
        routine_expr = generate_expr(call.routine_indirection, ctx)
    elif call.routine:
        # Static routine name
        routine_expr = repr(call.routine)
    else:
        routine_expr = None

    # Build the target string for parsing
    # Format: "LABEL^ROUTINE" (any part may be absent)
    if routine_expr is None:
        # Simple case: just label (J @TARGET)
        target_str_expr = label_expr
    else:
        # Need to build a compound target string
        ctx.emitter.line(f"_indirect_label = str({label_expr})")
        ctx.emitter.line("_indirect_target = _indirect_label")
        ctx.emitter.line(f"_indirect_routine = str({routine_expr})")
        ctx.emitter.line(
            '_indirect_target = _indirect_target + "^" + _indirect_routine'
        )
        target_str_expr = "_indirect_target"

    # Parse the target string
    ctx.emitter.line(f"_call_target = _rt.parse_call_target({target_str_expr})")

    # Generate arguments if any
    args_parts = []
    for arg in call.arguments:
        if arg.expression is not None:
            arg_expr = generate_expr(arg.expression, ctx)
        else:
            arg_expr = "None"
        args_parts.append(arg_expr)
    args_str = f"[{', '.join(args_parts)}]" if args_parts else "[]"

    # Generate process parameters if any
    params_str = _generate_job_process_params(job_target, ctx)

    # Generate timeout expression
    has_timeout = job_target.timeout is not None
    if has_timeout and job_target.timeout is not None:
        timeout_expr = generate_expr(job_target.timeout, ctx)
    else:
        timeout_expr = "None"

    # Generate JOB call with resolved target
    if has_timeout:
        ctx.emitter.line(
            f"_test = _rt.start_job(_call_target.label, _call_target.routine, "
            f"{args_str}, {params_str}, {timeout_expr})"
        )
        ctx.emitter.line("_rt._test = _test")
    else:
        ctx.emitter.line(
            f"_rt.start_job(_call_target.label, _call_target.routine, "
            f"{args_str}, {params_str}, {timeout_expr})"
        )


def _generate_view(stmt: MViewStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for VIEW command.

    VIEW is implementation-specific.

    Per MUMPS 1995 MDC spec section 8.2.24, VIEW has "arguments unspecified"
    meaning the exact syntax and semantics are implementation-defined.

    Common YDB VIEW keywords (for reference):
    - LVNULLSUBS: Control null subscript behavior
    - NOUNDEF: Control undefined variable behavior
    - TRACE: Enable/disable tracing

    For m2py: VIEW is a no-op by default since the Python runtime
    doesn't have equivalent low-level implementation controls.
    A comment is generated to document the original VIEW command.

    Args:
        stmt: MViewStatement node
        ctx: Generator context
    """
    # Generate arguments for documentation
    if stmt.arguments:
        args_strs = []
        for arg in stmt.arguments:
            arg_str = generate_expr(arg, ctx)
            args_strs.append(arg_str)
        args_comment = ", ".join(args_strs)
        ctx.emitter.line(f"pass  # VIEW {args_comment}")
    else:
        ctx.emitter.line("pass  # VIEW (no args)")


def _generate_break(stmt: MBreakStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for BREAK command.

    BREAK enters debugger.

    Per MUMPS 1995 MDC spec section 8.2.1, BREAK transfers control
    to the MUMPS debugger for interactive debugging.

    In Python, we use the built-in breakpoint() function which:
    - Enters pdb debugger in interactive mode
    - Can be disabled via PYTHONBREAKPOINT=0

    Args:
        stmt: MBreakStatement node
        ctx: Generator context
    """
    ctx.emitter.line("breakpoint()  # BREAK - enter debugger")


# =============================================================================
# Z-Commands
# =============================================================================


def _zwrite_build_call(target: Any, ctx: "GeneratorContext") -> tuple[str, str]:
    """Build the argument fragments for a zwrite_local / zwrite_global call.

    Walks ``target.subscripts``, collecting concrete subscripts and
    recognising ``MZWriteSubscriptAll`` (wildcard) and
    ``MZWriteSubscriptRange`` (range filter) nodes.

    Returns:
        A tuple of (subs_tuple_str, range_kwargs_str).
        subs_tuple_str: e.g. ``"(sub1, sub2,)"`` or ``"()"``
        range_kwargs_str: e.g. ``", range_start=str(2), range_end=str(4)"``
            or ``""`` if no range.
    """
    if not target.subscripts:
        return "()", ""

    concrete_subs: list[str] = []
    range_kw = ""

    for s in target.subscripts:
        if isinstance(s, MZWriteSubscriptAll):
            break
        elif isinstance(s, MZWriteSubscriptRange):
            # Evaluate start/end expressions and pass as kwargs
            parts: list[str] = []
            if s.start is not None:
                parts.append(f"range_start=str({generate_expr(s.start, ctx)})")
            if s.end is not None:
                parts.append(f"range_end=str({generate_expr(s.end, ctx)})")
            if parts:
                range_kw = ", " + ", ".join(parts)
            break
        else:
            concrete_subs.append(f"str({generate_expr(s, ctx)})")

    if concrete_subs:
        subs_str = ", ".join(concrete_subs)
        return f"({subs_str},)", range_kw
    return "()", range_kw


def _generate_zwrite(stmt: MZWriteStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZWRITE command.

    ZWRITE displays variables with names.

    ZWRITE outputs variables in a format that can be used with SET @:
    - Variable names are shown
    - String values are quoted
    - Subscripted descendants are shown recursively

    Examples:
        ZW X      -> X=1
                    X(1)="A"
        ZW        -> (all local variables)
        ZW ^GLOB  -> ^GLOB=value (global and descendants)

    Args:
        stmt: MZWriteStatement node
        ctx: Generator context
    """
    from m2py.parser.textx_classes import (
        LocalVariable,
        MGlobal,
        ZWriteGlobal,
        ZWriteLocal,
    )

    if not stmt.args:
        # Argumentless ZWRITE - display all local variables
        ctx.emitter.line("_rt.zwrite(_scope)")
    else:
        for arg in stmt.args:
            if arg.target is None:
                continue

            target = arg.target

            # Check for any global type (GlobalVariable, ZWriteGlobal, or MGlobal subclass)
            if isinstance(target, (GlobalVariable, ZWriteGlobal, MGlobal)):
                # Global variable: ZW ^NAME or ZW ^NAME(subs)
                name = target.name
                subs_str, range_kw = _zwrite_build_call(target, ctx)
                ctx.emitter.line(f"_rt.zwrite_global('{name}', {subs_str}{range_kw})")
            elif isinstance(target, (LocalVariable, ZWriteLocal)):
                # Local variable: ZW X or ZW X(subs)
                name = target.name
                subs_str, range_kw = _zwrite_build_call(target, ctx)
                ctx.emitter.line(
                    f"_rt.zwrite_local('{name}', {subs_str}, _scope{range_kw})"
                )
            else:
                # Fallback - generate expression and try to write it
                ctx.emitter.line(f"pass  # ZWRITE {generate_expr(target, ctx)}")


def _generate_zkill(
    stmt: "MZKillStatement | MZWithdrawStatement", ctx: "GeneratorContext"
) -> None:
    """Generate Python code for ZKILL/ZWITHDRAW command.

    ZKILL removes node value but preserves descendants.

    Unlike KILL which removes the entire subtree, ZKILL only removes the value
    at the specified node, leaving all subscripted descendants intact.

    Example:
        S ^A=1,^A(1)=2,^A(2)=3
        ZK ^A        ; Removes ^A value, keeps ^A(1) and ^A(2)
        W $D(^A)     ; Returns 10 (has descendants but no value)

    Args:
        stmt: MZKillStatement or MZWithdrawStatement node
        ctx: Generator context
    """
    from m2py.parser.textx_classes import LocalVariable

    for target in stmt.targets:
        if isinstance(target, GlobalVariable):
            name = target.name
            if target.subscripts:
                subs = ", ".join(
                    f"str({generate_expr(s, ctx)})" for s in target.subscripts
                )
                ctx.emitter.line(f"_rt.globals.kill_node('{name}', ({subs},))")
            else:
                ctx.emitter.line(f"_rt.globals.kill_node('{name}', ())")
        elif isinstance(target, LocalVariable):
            name = target.name
            py_name = translate_name(name)
            if target.subscripts:
                subs = ", ".join(
                    f"str({generate_expr(s, ctx)})" for s in target.subscripts
                )
                ctx.emitter.line(
                    f"_scope.setdefault('{py_name}', MArray()).kill_node(({subs},))"
                )
            else:
                # ZKILL on unsubscripted local - remove value but keep children
                ctx.emitter.line(
                    f"_scope.setdefault('{py_name}', MArray()).kill_node(())"
                )
        else:
            # Fallback
            ctx.emitter.line(f"pass  # ZKILL {generate_expr(target, ctx)}")


def _generate_zlink(stmt: MZLinkStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZLINK command.

    ZLINK dynamically links/loads a routine.

    In the transpiler context, ZLINK imports a Python module representing
    the routine and registers it in the runtime's routine registry.

    Example:
        ZLINK "MYROUTINE"
        D ^MYROUTINE

    Args:
        stmt: MZLinkStatement node
        ctx: Generator context
    """
    if not stmt.args:
        ctx.emitter.line("pass  # ZLINK (no args)")
        return

    for arg in stmt.args:
        routine_expr = generate_expr(arg, ctx)
        ctx.emitter.line(f"_rt.zlink({routine_expr})")


def _generate_zload(stmt: MZLoadStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZLOAD command.

    ZLOAD loads a routine into the routine buffer for editing.
    In transpiler context, we treat it the same as ZLINK since
    both load a routine; editing semantics don't apply in Python.

    Example:
        ZL "MYROUTINE"

    Args:
        stmt: MZLoadStatement node
        ctx: Generator context
    """
    if not stmt.args:
        ctx.emitter.line("pass  # ZLOAD (no args)")
        return

    for arg in stmt.args:
        routine_expr = generate_expr(arg, ctx)
        ctx.emitter.line(f"_rt.zlink({routine_expr})")


def _generate_zsystem(stmt: MZSystemStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZSYSTEM command.

    ZSYSTEM executes a shell command.

    Example:
        ZSYSTEM "echo hello"
        ZSY command_var

    Args:
        stmt: MZSystemStatement node
        ctx: Generator context
    """
    if not stmt.args:
        ctx.emitter.line("_rt.zsystem()")
        return

    for arg in stmt.args:
        cmd_expr = generate_expr(arg, ctx)
        ctx.emitter.line(f"_rt.zsystem(m_str({cmd_expr}))")


def _generate_zshow(stmt: MZShowStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZSHOW command.

    ZSHOW displays system information.

    Codes:
    - S: Stack trace
    - V: Local variables (like ZWRITE)
    - D: Devices
    - I: Intrinsic special variables
    - G: Global variables
    - L: Locks held
    - *: All of the above

    Example:
        ZSHOW "S"    ; Show call stack
        ZSHOW "V"    ; Show variables

    Args:
        stmt: MZShowStatement node
        ctx: Generator context
    """
    if not stmt.args:
        # Argumentless ZSHOW shows everything
        ctx.emitter.line('_rt.zshow("*", _scope)')
        return

    for arg in stmt.args:
        if arg.codes:
            codes_expr = generate_expr(arg.codes, ctx)
            if arg.destination:
                dest_expr = generate_expr(arg.destination, ctx)
                ctx.emitter.line(f"_rt.zshow({codes_expr}, _scope, {dest_expr})")
            else:
                ctx.emitter.line(f"_rt.zshow({codes_expr}, _scope)")
        else:
            ctx.emitter.line('_rt.zshow("*", _scope)')


def _generate_zgoto(stmt: MZGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZGOTO command.

    ZGOTO unwinds stack to specified level.

    ZGOTO is a powerful control flow mechanism that can:
    - Unwind the call stack to a specific level
    - Transfer control to a label after unwinding
    - Exit the program (ZGOTO 0)

    Example:
        ZGOTO 0         ; Exit program
        ZGOTO 1:ERROR   ; Unwind to level 1, go to ERROR

    Implementation uses an exception-based approach for stack unwinding.

    Args:
        stmt: MZGotoStatement node
        ctx: Generator context
    """
    if not stmt.args:
        # Argumentless ZGOTO - return to direct mode (exit in batch)
        ctx.emitter.line("raise SystemExit(0)  # ZGOTO - return to direct mode")
        return

    for arg in stmt.args:
        level_expr = "0"
        if arg.level is not None:
            level_expr = generate_expr(arg.level, ctx)

        if arg.target is not None:
            # ZGOTO level:label - unwind and transfer
            # arg.target may be an MCall (label reference) — extract name as string
            from m2py.asg.elements import MCall as MCallType

            if isinstance(arg.target, MCallType):
                target_expr = repr(arg.target.name or "")
            else:
                target_expr = generate_expr(arg.target, ctx)
            ctx.emitter.line(
                f"raise _rt.ZGotoException({level_expr}, {target_expr})  # ZGOTO"
            )
        else:
            # ZGOTO level - unwind only
            if level_expr == "0":
                ctx.emitter.line("raise SystemExit(0)  # ZGOTO 0 - exit")
            else:
                ctx.emitter.line(
                    f"raise _rt.ZGotoException({level_expr})  # ZGOTO {level_expr}"
                )


def _generate_zhalt(stmt: MZHaltStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZHALT command.

    ZHALT terminates with exit status.

    Similar to HALT but allows specifying an exit code.

    Example:
        ZHALT 0     ; Exit with success
        ZHALT 1     ; Exit with error

    Args:
        stmt: MZHaltStatement node
        ctx: Generator context
    """
    if stmt.exitcode is not None:
        exit_expr = generate_expr(stmt.exitcode, ctx)
        ctx.emitter.line(f"raise SystemExit(int({exit_expr}))  # ZHALT")
    else:
        ctx.emitter.line("raise SystemExit(0)  # ZHALT")


def _generate_zprint(stmt: MZPrintStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZPRINT command.

    ZPRINT displays source code of a routine. In transpiled code this is a
    no-op since the original MUMPS source is not available at runtime.

    Example:
        ZPRINT label^routine
        ZP

    Args:
        stmt: MZPrintStatement node
        ctx: Generator context
    """
    ctx.emitter.line("pass  # ZPRINT (no-op in transpiled code)")


def _generate_zmessage(stmt: MZMessageStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZMESSAGE command.

    ZMESSAGE generates a MUMPS error by code number. In transpiled code,
    we call the runtime's m_zmessage helper which maps codes to error text,
    and raise it as an exception (matching YDB/IRIS behavior).

    Example:
        ZMESSAGE 150372994
        ZM error_code

    Args:
        stmt: MZMessageStatement node
        ctx: Generator context
    """
    if stmt.args:
        for arg in stmt.args:
            code_expr = generate_expr(arg, ctx)
            ctx.emitter.line(f"raise RuntimeError(m_zmessage({code_expr}))  # ZMESSAGE")
    else:
        ctx.emitter.line("pass  # ZMESSAGE (no args)")


__all__ = [
    "generate_statement",
    "generate_scope_statements",
    "ForGenContext",
    "GotoGenContext",
    "_generate_call_arguments",
]
