"""Statement code generation for MUMPS-to-Python transpilation.

Generates Python statements from MUMPS ASG statement nodes.
Handles SET, WRITE, QUIT, IF, ELSE, FOR, and other basic commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, cast

from m2py.asg.enums import (
    ForLoopType,
    FormatControlType,
    ForParamType,
    GotoType,
    PassingMode,
)
from m2py.asg.expressions import (
    MActualParameter,
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
    # Z-commands (Phase 19) - Implemented
    MZGotoStatement,
    MZHaltStatement,
    MZKillStatement,
    MZLinkStatement,
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
from m2py.codegen.expressions import contains_naked_global, generate_expr
from m2py.codegen.names import translate_name

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
    from m2py.asg.statements import MStatement
    from m2py.codegen.routine import GeneratorContext


# =============================================================================
# Exceptions (imported locally to avoid circular import)
# =============================================================================


class UnsupportedFeatureError(Exception):
    """Raised when attempting to generate code for unsupported feature.

    Note: This is a local definition to avoid circular import.
    The canonical definition is in m2py.codegen.__init__.py.
    """

    pass


# =============================================================================
# Limitation Constants (Spec 014)
# =============================================================================

# YDB Z-commands with zero VistA usage (LIM-015)
# These are implementation-defined per FR-017 and parsed but not implemented.
# Codegen raises NotImplementedError for these commands.
# Note: ZWRITE, ZKILL, ZLINK, ZSHOW, ZGOTO, ZHALT are implemented.
Z_COMMANDS_UNIMPLEMENTED: frozenset[str] = frozenset(
    {
        "ZALLOCATE",
        "ZDEALLOCATE",
        "ZBREAK",
        "ZCOMPILE",
        "ZCONTINUE",
        "ZEDIT",
        "ZHELP",
        "ZMESSAGE",
        "ZPRINT",
        "ZSTEP",
        "ZSYSTEM",
        "ZTRIGGER",
    }
)


# =============================================================================
# Spec 014: Comment Preservation
# =============================================================================


def _emit_source_comment(stmt: "MStatement", ctx: "GeneratorContext") -> None:
    """Emit MUMPS inline comment as Python comment if present.

    Spec 014 (T067): Preserves MUMPS comments in generated Python code.
    Looks up the source line for the statement and extracts any inline
    comment (text after `;`).

    Args:
        stmt: ASG statement node with line_number
        ctx: Generator context with routine.source_lines
    """
    # Skip if no line number or no source lines
    if stmt.line_number is None:
        return
    source_lines = ctx.routine.source_lines
    if not source_lines:
        return

    # Get the source line (1-indexed)
    line_idx = stmt.line_number - 1
    if line_idx < 0 or line_idx >= len(source_lines):
        return

    source_line = source_lines[line_idx]

    # Extract comment if present (everything after unquoted semicolon)
    comment = _extract_comment(source_line)
    if comment:
        ctx.emitter.line(f"# {comment}")


def _extract_comment(source_line: str) -> str:
    """Extract comment text from a MUMPS source line.

    Finds the first semicolon not inside a string literal and returns
    the text after it (stripped of leading/trailing whitespace).

    Args:
        source_line: Original MUMPS source line

    Returns:
        Comment text without the leading semicolon, or empty string if no comment
    """
    in_string = False
    for i, char in enumerate(source_line):
        if char == '"':
            in_string = not in_string
        elif char == ";" and not in_string:
            # Found unquoted semicolon - rest is comment
            comment_text = source_line[i + 1 :].strip()
            return comment_text
    return ""


# =============================================================================
# Spec 005: Code Generation Context Helpers
# =============================================================================


def _generate_call_arguments(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> str:
    """Generate Python arguments from MUMPS call arguments.

    Handles:
    - BY_VALUE: Expression evaluated and passed
    - BY_REFERENCE: Variable passed (actual by-ref return tuple handled at call site)
    - OMITTED: None placeholder

    Note: Full by-reference semantics with return tuple destructuring
    is implemented in Phase 10 (US8). For now, by-ref passes the variable.

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
            # For by-ref, pass the variable value
            # Full tuple return pattern in Phase 10
            if arg.expression:
                parts.append(generate_expr(arg.expression, ctx))
            elif arg.variable_name:
                parts.append(translate_name(arg.variable_name))
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
    loop_var_indirect: bool = False  # T068: True if loop_var is @A
    loop_var_expr: Optional[str] = None  # T068: Expression to get target var name
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

        # T068: Check for indirection loop variable (F @A=1:1:3)
        loop_var_indirect = False
        loop_var_expr: Optional[str] = None
        loop_var_subscripts: List[str] = []

        if isinstance(stmt.loop_var, MIndirectionType):
            # Indirect loop variable: F @A=1:1:3 where A contains "B"
            # Also handles multi-level: F @@A=1:1:5, F @@@A=1:1:5
            loop_var_indirect = True
            # Generate expression to get target variable name at runtime
            # Feature: 018-unified-variable-system (T089, T134)
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
            # T032: Extract subscripts for subscripted loop variables (F I(1)=1:1:3)
            if stmt.loop_var.subscripts and ctx is not None:
                loop_var_subscripts = [
                    generate_expr(sub, ctx) for sub in stmt.loop_var.subscripts
                ]
        else:
            var_name = "_"
            loop_var = "_"  # Fallback for complex expressions

        # T075n: When inside inline XECUTE, prefix loop var to avoid shadowing
        # module-level label functions. E.g. "F I=1:1:3 G I" - the FOR loop
        # variable I would shadow def I() if we use bare "I".
        if ctx and ctx.in_inline_xecute and loop_var not in ("_", "_for_val"):
            loop_var = f"_xec_{loop_var}"

        # Spec 006: Check if loop var should use state for trampoline
        if (
            ctx
            and ctx.strategy == GotoStrategy.TRAMPOLINE
            and var_name in ctx.state_vars
            and not loop_var_indirect
        ):
            loop_var = f"state.{translate_name(var_name)}"

        # Read analysis results - ASG fields have defaults, analysis passes populate them
        use_while = stmt.loop_var_modified_in_body
        needs_break = stmt.has_internal_quit or stmt.has_internal_goto
        is_infinite = stmt.is_infinite or not stmt.parameters

        # T095: loop_type is now always set by analysis - no fallback needed
        loop_type = stmt.loop_type
        if loop_type is None:
            raise ValueError(
                "MForStatement.loop_type not set - ensure analyze_for_loops() was called"
            )

        # Spec 017 Phase 11: Get unique loop ID from context for variable naming
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


# T092-T094: Removed _for_needs_loop_exit_wrapper(), _for_has_cross_label_exit(),
# and _get_multi_loop_exit_target() - now using pre-computed ASG fields:
# - MForStatement.needs_exception_wrapper
# - MForStatement.has_cross_label_exit
# - MForStatement.exit_target


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

        # T101: Read pre-computed codegen_pattern from analysis instead of recomputing
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


# T100: Removed _is_restructurable_goto() - now using pre-computed
# MGotoStatement.is_restructurable field populated by classify_gotos()


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
    if if_stmt.condition is not None:
        cond_expr = generate_expr(if_stmt.condition, ctx)
        ctx.emitter.line(f"_test = m_truth({cond_expr})")
    elif if_stmt.conditions:
        cond_parts = [generate_expr(c, ctx) for c in if_stmt.conditions]
        cond_expr = " and ".join(f"m_truth({c})" for c in cond_parts)
        ctx.emitter.line(f"_test = {cond_expr}")
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

    Spec 007 (T021): Each statement is wrapped with an offset guard that
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

    Spec 011 (T032-T033): If stmt.postcondition is set, wrap the statement
    in a conditional: if m_truth(cond): <statement>

    Spec 014 (T067): Preserves MUMPS comments as Python comments.
    If the source line has an inline comment (;...), it is emitted
    as a Python comment before the statement.

    Args:
        stmt: ASG statement node
        ctx: Generator context with emitter

    Raises:
        NotImplementedError: For unsupported statement types
    """
    # Spec 014 (T067): Emit MUMPS comment as Python comment if present
    _emit_source_comment(stmt, ctx)

    # Spec 011 (T032): Check for postcondition
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
    # Z-commands (Phase 19)
    elif isinstance(stmt, MZWriteStatement):
        _generate_zwrite(stmt, ctx)
    elif isinstance(stmt, (MZKillStatement, MZWithdrawStatement)):
        _generate_zkill(stmt, ctx)
    elif isinstance(stmt, MZLinkStatement):
        _generate_zlink(stmt, ctx)
    elif isinstance(stmt, MZShowStatement):
        _generate_zshow(stmt, ctx)
    elif isinstance(stmt, MZGotoStatement):
        _generate_zgoto(stmt, ctx)
    elif isinstance(stmt, MZHaltStatement):
        _generate_zhalt(stmt, ctx)
    # Z-commands - Unimplemented (LIM-015)
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
        raise NotImplementedError("LIM-015: ZMESSAGE command not supported")
    elif isinstance(stmt, MZPrintStatement):
        raise NotImplementedError("LIM-015: ZPRINT command not supported")
    elif isinstance(stmt, MZStepStatement):
        raise NotImplementedError("LIM-015: ZSTEP command not supported")
    elif isinstance(stmt, MZSystemStatement):
        raise NotImplementedError("LIM-015: ZSYSTEM command not supported")
    elif isinstance(stmt, MZTriggerStatement):
        raise NotImplementedError("LIM-015: ZTRIGGER command not supported")
    # ANSI commands not supported by YDB (LIM-016)
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

    Spec 006: When using TRAMPOLINE strategy and the variable is in state_vars,
    assign to `state.VAR` instead of just `VAR`.

    Spec 006 (T075): Handle subscripted assignments for MArray-backed variables.
    For array variables, generate: state.A[subscripts] = value

    Spec 008 (T084): For SIMPLE_FUNCTIONS strategy, store variables in _scope
    dictionary for cross-routine visibility: _scope['VAR'] = value

    Spec 012 (T017): Handle name indirection targets (@VAR).
    For indirection targets, generate: _rt.set_var(name_expr, value, _scope)

    Spec 012 (T056): Handle argument indirections (S @A where A="X=1").
    For argument indirection, generate: _rt.execute_mumps("S " + value, _scope)

    Spec 017: Uses ordered_items to maintain left-to-right evaluation order
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

    # Spec 017: Use ordered_items for correct left-to-right evaluation
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


def _subscript_needs_pre_eval(sub, prior_assignments: list) -> bool:
    """Check if a subscript expression needs pre-evaluation.

    A subscript needs pre-evaluation if it references a variable that
    is being set by a prior assignment in the tuple.

    Args:
        sub: Subscript expression
        prior_assignments: Assignments that will execute before this subscript is used

    Returns:
        True if subscript contains a variable that will be modified
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable

    # Get set of variable names being modified by prior assignments
    modified_vars = set()
    for assign in prior_assignments:
        target = assign.target
        if isinstance(target, (MVariable, LocalVariable)):
            var_name = getattr(target, "name", None)
            if var_name:
                modified_vars.add(var_name)

    if not modified_vars:
        return False

    # Check if subscript references any modified variable
    return _expr_references_vars(sub, modified_vars)


def _expr_references_vars(expr, var_names: set) -> bool:
    """Check if expression references any of the given variable names.

    Args:
        expr: Expression to check
        var_names: Set of variable names to look for

    Returns:
        True if expression contains a reference to any of the variables
    """
    from m2py.asg.expressions import MVariable, MBinaryOp, MUnaryOp, MIntrinsicFunction
    from m2py.parser.textx_classes import LocalVariable

    if isinstance(expr, (MVariable, LocalVariable)):
        name = getattr(expr, "name", None)
        if name in var_names:
            return True
        # Also check subscripts
        subscripts = getattr(expr, "subscripts", None) or []
        for sub in subscripts:
            if _expr_references_vars(sub, var_names):
                return True
        return False

    if isinstance(expr, MBinaryOp):
        return _expr_references_vars(expr.left, var_names) or _expr_references_vars(
            expr.right, var_names
        )

    if isinstance(expr, MUnaryOp):
        return _expr_references_vars(expr.operand, var_names)

    if isinstance(expr, MIntrinsicFunction):
        for arg in expr.arguments or []:
            if _expr_references_vars(arg, var_names):
                return True
        return False

    return False


def _generate_single_assignment_with_preeval(
    assignment, idx: int, pre_eval_map: dict, ctx: "GeneratorContext"
) -> None:
    """Generate a single assignment, using pre-evaluated subscripts from the map."""
    from m2py.asg.expressions import MIndirection as MIndirectionType, MVariable
    from m2py.codegen.indirection import generate_name_indirection_write
    from m2py.parser.textx_classes import LocalVariable, GlobalVariable

    if assignment.target is None or assignment.value is None:
        return

    # Handle indirection targets
    if isinstance(assignment.target, MIndirectionType):
        value_expr = generate_expr(assignment.value, ctx)
        set_stmt = generate_name_indirection_write(assignment.target, value_expr, ctx)
        ctx.emitter.line(set_stmt)
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

    # Generate value expression
    value_expr = generate_expr(assignment.value, ctx)

    # Generate the assignment based on target type
    if isinstance(target, (MVariable, LocalVariable)):
        var_name = target.name
        python_name = translate_name(var_name)

        if subscript_exprs:
            # Subscripted assignment
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                ctx.emitter.line(
                    f"state._locals.setdefault({python_name!r}, MArray())[{', '.join(subscript_exprs)}] = {value_expr}"
                )
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                ctx.emitter.line(
                    f"state.{python_name}[{', '.join(subscript_exprs)}] = {value_expr}"
                )
            else:
                ctx.emitter.line(
                    f"_scope.setdefault({python_name!r}, MArray())[{', '.join(subscript_exprs)}] = {value_expr}"
                )
        else:
            # Simple assignment
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                ctx.emitter.line(
                    f"state._locals.setdefault({python_name!r}, MArray()).value = {value_expr}"
                )
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                ctx.emitter.line(f"state.{python_name} = {value_expr}")
            else:
                ctx.emitter.line(
                    f"_scope.setdefault({python_name!r}, MArray()).value = {value_expr}"
                )
    elif isinstance(target, GlobalVariable):
        global_name = target.name
        if subscript_exprs:
            subscripts_tuple = (
                f"({', '.join(subscript_exprs)},)"
                if len(subscript_exprs) == 1
                else f"({', '.join(subscript_exprs)})"
            )
            ctx.emitter.line(
                f'_rt.globals.set("{global_name}", {subscripts_tuple}, {value_expr})'
            )
        else:
            ctx.emitter.line(f'_rt.globals.set("{global_name}", (), {value_expr})')
    else:
        # Fallback to regular single assignment
        _generate_single_assignment(assignment, ctx)


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
    from m2py.asg.expressions import MIndirection as MIndirectionType, MVariable
    from m2py.codegen.indirection import generate_name_indirection_write
    from m2py.parser.textx_classes import LocalVariable, GlobalVariable, NakedGlobal

    if assignment.target is None:
        return

    # Handle indirection targets
    if isinstance(assignment.target, MIndirectionType):
        set_stmt = generate_name_indirection_write(assignment.target, value_var, ctx)
        ctx.emitter.line(set_stmt)
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
        python_name = translate_name(var_name)

        if subscript_exprs:
            # Subscripted assignment
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                ctx.emitter.line(
                    f"state._locals.setdefault({python_name!r}, MArray())[{', '.join(subscript_exprs)}] = {value_var}"
                )
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                ctx.emitter.line(
                    f"state.{python_name}[{', '.join(subscript_exprs)}] = {value_var}"
                )
            else:
                ctx.emitter.line(
                    f"_scope.setdefault({python_name!r}, MArray())[{', '.join(subscript_exprs)}] = {value_var}"
                )
        else:
            # Simple assignment
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                ctx.emitter.line(
                    f"state._locals.setdefault({python_name!r}, MArray()).value = {value_var}"
                )
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                ctx.emitter.line(f"state.{python_name} = {value_var}")
            else:
                ctx.emitter.line(
                    f"_scope.setdefault({python_name!r}, MArray()).value = {value_var}"
                )
    elif isinstance(target, GlobalVariable):
        global_name = target.name
        if subscript_exprs:
            subscripts_tuple = (
                f"({', '.join(subscript_exprs)},)"
                if len(subscript_exprs) == 1
                else f"({', '.join(subscript_exprs)})"
            )
            ctx.emitter.line(
                f'_rt.globals.set("{global_name}", {subscripts_tuple}, {value_var})'
            )
        else:
            ctx.emitter.line(f'_rt.globals.set("{global_name}", (), {value_var})')
    elif isinstance(target, NakedGlobal):
        # Naked global target with pre-evaluated value
        # Generate subscript expressions for the naked global
        naked_subscript_exprs = []
        for sub_idx, sub in enumerate(subscripts):
            if (idx, sub_idx) in pre_eval_map:
                naked_subscript_exprs.append(pre_eval_map[(idx, sub_idx)])
            else:
                naked_subscript_exprs.append(generate_expr(sub, ctx))

        if naked_subscript_exprs:
            if len(naked_subscript_exprs) == 1:
                subscripts_tuple = f"({naked_subscript_exprs[0]},)"
            else:
                subscripts_tuple = f"({', '.join(naked_subscript_exprs)})"
        else:
            subscripts_tuple = "()"

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

    # Spec 012 (T017) + 018 (T041): Handle indirection targets (@VAR, @@VAR, @NAME@(1,2))
    # Uses unified set_indirected() which internally uses IndirectionResolver
    if isinstance(assignment.target, MIndirectionType):
        # Generate value expression first
        value_expr = generate_expr(assignment.value, ctx)
        # Generate the set_indirected call via unified indirection module
        set_stmt = generate_name_indirection_write(assignment.target, value_expr, ctx)
        ctx.emitter.line(set_stmt)
        return

    # Spec 013 Phase 12: Handle special variable assignments ($ETRAP, $ECODE, $ZERROR)
    if isinstance(assignment.target, MSpecialVariable):
        value_expr = generate_expr(assignment.value, ctx)
        svar_name = assignment.target.name.upper()
        if svar_name in ("ETRAP", "ET"):
            ctx.emitter.line(f"_rt.set_etrap({value_expr})")
        elif svar_name in ("ECODE", "EC"):
            ctx.emitter.line(f"_rt.set_ecode({value_expr})")
        elif svar_name in ("ZERROR", "ZE"):
            ctx.emitter.line(f"_rt.set_zerror({value_expr})")
        else:
            raise NotImplementedError(f"SET ${assignment.target.name} not supported")
        return

    # Get target variable name
    target_name = None
    if isinstance(assignment.target, MVariable):
        target_name = translate_name(assignment.target.name)
        var_name = assignment.target.name

        # Spec 006 (T075): Handle subscripted array assignments
        if assignment.target.subscripts:
            # Generate subscript expressions
            # T087: Pass subscript_context=True so indirection in subscripts
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

            # Spec 017 (T014): Dynamic locals for argumentless KILL/NEW support
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # Access MArray from _locals dict, auto-vivify if needed
                base = f"state._locals.setdefault({target_name!r}, MArray())"
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.array_vars:
                # MArray in RoutineState: state.A[subscripts] = value
                base = f"state.{target_name}"
            elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                # Spec 009 (T021): Auto-vivify MArray for subscripted locals
                # _scope.setdefault('A', MArray())[subscripts] = value
                base = f"_scope.setdefault({target_name!r}, MArray())"
            else:
                # Plain Python local variable (TRAMPOLINE without array_vars)
                base = target_name

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

        # Spec 017 (T014): Dynamic locals for argumentless KILL/NEW support
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Store in _locals dict as MArray for consistency with subscripted access
            target_name = f"state._locals.setdefault({target_name!r}, MArray()).value"
        # Spec 006: Check if variable should be accessed via state (TRAMPOLINE)
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
            target_name = f"state.{target_name}"
        elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Spec 009 (T021): Store variables in _scope using MArray for consistency
            # This allows later subscripted access: S X=1 S X(1)=2 both work
            target_name = f"_scope.setdefault({target_name!r}, MArray()).value"
        # else: use plain Python local variable (TRAMPOLINE without state_vars)

    elif isinstance(assignment.target, GlobalVariable):
        # Spec 009 (T026): Handle global variable SET targets
        # Generate: _rt.globals.set("NAME", (subscripts,), value)
        _generate_global_set(assignment, ctx)
        return

    elif isinstance(assignment.target, ExtendedGlobalBracket):
        # Spec 017: Handle extended global reference SET targets
        # For m2py, environment is ignored - treat as regular global
        # Generate: _rt.globals.set("NAME", (subscripts,), value)
        _generate_extended_global_set(assignment, ctx)
        return

    elif isinstance(assignment.target, NakedGlobal):
        # Spec 009 (T031): Handle naked global reference SET targets
        # Generate: resolve_naked then set
        _generate_naked_global_set(assignment, ctx)
        return

    elif isinstance(assignment.target, MIntrinsicFunction):
        # Spec 009 (T012-T013): Handle LHS function targets ($PIECE, $EXTRACT)
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


def _generate_lhs_piece(assignment: MAssignment, ctx: "GeneratorContext") -> None:
    """Generate m_set_piece() call for LHS $PIECE assignment.

    Spec 009 (T013): Generate code for S $P(var,"^",pos)=value

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

    # First argument must be a variable (local, global, naked global, or indirection)
    first_arg = args[0]
    if isinstance(first_arg, GlobalVariable):
        # Global variable: use _rt.globals.get/set
        global_name = first_arg.name
        if first_arg.subscripts:
            subs_code = []
            for sub in first_arg.subscripts:
                subs_code.append(f"str({generate_expr(sub, ctx)})")
            subscripts_tuple = f"({', '.join(subs_code)},)"
        else:
            subscripts_tuple = "()"
        getter = f'lambda: _rt.globals.get("{global_name}", {subscripts_tuple}) or ""'
        setter = f'lambda v: _rt.globals.set("{global_name}", {subscripts_tuple}, v)'
    elif isinstance(first_arg, NakedGlobal):
        # Spec 017 Phase 6 (T026): Naked global: resolve ONCE before m_set_piece
        # resolve_naked() returns (name, subscripts) from the naked indicator
        # We must capture the resolved name/subscripts BEFORE calling m_set_piece
        # because the getter will update the naked indicator when it reads the value
        # DO NOT wrap in str() - let runtime handle canonicalization
        if first_arg.subscripts:
            subscript_exprs = [generate_expr(sub, ctx) for sub in first_arg.subscripts]
            if len(subscript_exprs) == 1:
                subscripts_tuple = f"({subscript_exprs[0]},)"
            else:
                subscripts_tuple = f"({', '.join(subscript_exprs)},)"
        else:
            subscripts_tuple = "()"

        # Generate unique temp variable names for resolved name and subscripts
        temp_name = f"_lhsp_name_{id(assignment) % 10000}"
        temp_subs = f"_lhsp_subs_{id(assignment) % 10000}"

        # Emit the resolution BEFORE the m_set_piece call
        ctx.emitter.line(
            f"{temp_name}, {temp_subs} = _rt.globals.resolve_naked({subscripts_tuple})"
        )

        # Use the pre-resolved values in getter/setter
        getter = f'lambda: _rt.globals.get({temp_name}, {temp_subs}) or ""'
        setter = f"lambda v: _rt.globals.set({temp_name}, {temp_subs}, v)"
    elif isinstance(first_arg, MIndirection):
        # Feature: 018-unified-variable-system
        # Indirection: use resolve_for_target to get NAME, then get_var/set_var for VALUE
        from m2py.codegen.indirection import _count_indirection_levels

        levels, inner_expr = _count_indirection_levels(first_arg)

        # Handle name+subscript syntax: @NAME@(1,2)
        if first_arg.name_indirection_subscripts:
            # Build per_level_subscripts for proper subscript merging
            # This is critical when the resolved name already has subscripts
            # e.g., @A@(1) where A="ABC(1,2,3)" should become "ABC(1,2,3,1)"
            # NOT "ABC(1,2,3)(1)" which is what string concatenation produces
            per_level_subs_code = []
            for sub_list in first_arg.name_indirection_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                per_level_subs_code.append(f"[{', '.join(sub_exprs)}]")
            per_level_subscripts_str = f"[{', '.join(per_level_subs_code)}]"

            if isinstance(inner_expr, MVariable):
                base_name = inner_expr.name
                # Use resolve_for_target with per_level_subscripts for proper subscript merging
                name_expr = f'_rt.resolve_for_target("{base_name}", _scope, levels={levels}, per_level_subscripts={per_level_subscripts_str})'
            else:
                name_expr_base = generate_expr(inner_expr, ctx)
                # For non-variable base, still need per_level_subscripts
                name_expr = f"_rt.resolve_for_target(str({name_expr_base}), _scope, levels={levels}, per_level_subscripts={per_level_subscripts_str})"
        else:
            # Simple indirection without subscripts
            if isinstance(inner_expr, MVariable):
                base_name = inner_expr.name
                # Use resolve_for_target with appropriate levels
                name_expr = (
                    f'_rt.resolve_for_target("{base_name}", _scope, levels={levels})'
                )
            else:
                name_expr_base = generate_expr(inner_expr, ctx)
                if levels > 1:
                    # For non-variable expressions with multi-level, use resolve_for_target
                    name_expr = f"_rt.resolve_for_target(str({name_expr_base}), _scope, levels={levels - 1})"
                else:
                    name_expr = f"str({name_expr_base})"

        # Use _rt.get_var/_rt.set_var for indirected access
        getter = f'lambda: _rt.get_var({name_expr}, _scope) or ""'
        setter = f"lambda v: _rt.set_var({name_expr}, v, _scope)"
    elif isinstance(first_arg, MVariable):
        var = first_arg
        var_name = var.name
        translated_name = translate_name(var_name)

        if var.subscripts:
            # Subscripted local variable: X(1), X(1,2), etc.
            # Don't use str() - keep subscripts as their natural type for MArray key matching
            subs_code = [generate_expr(sub, ctx) for sub in var.subscripts]
            subs_args = ", ".join(subs_code)

            # Build getter/setter that navigates through subscripts
            # Getter must convert to string since MUMPS values can be numeric
            getter = f"lambda: str(_scope.setdefault({translated_name!r}, MArray()).get({subs_args}) or '')"
            setter = f"lambda v: _scope.setdefault({translated_name!r}, MArray()).set({subs_args}, value=v)"
        else:
            # Unsubscripted variable - use MArray.value
            # Build getter/setter based on strategy
            # Note: Getter must convert to string since MUMPS values can be numeric
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                # _scope-based access using m_var_value for compatibility with
                # both MArray and plain values from external TRAMPOLINE routines
                getter = (
                    f"lambda: str(m_var_value(_scope.get({translated_name!r})) or '')"
                )
                setter = f"lambda v: setattr(_scope.setdefault({translated_name!r}, MArray()), 'value', v)"
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                # state-based access
                getter = f"lambda: str(getattr(state, {translated_name!r}, '') or '')"
                setter = f"lambda v: setattr(state, {translated_name!r}, v)"
            else:
                # Plain local variable (would need nonlocal in real scenario)
                # For now, fall back to _scope pattern for safety
                getter = (
                    f"lambda: str(m_var_value(_scope.get({translated_name!r})) or '')"
                )
                setter = f"lambda v: setattr(_scope.setdefault({translated_name!r}, MArray()), 'value', v)"
    else:
        raise NotImplementedError(
            f"LHS $PIECE first argument must be a variable, got {type(first_arg).__name__}"
        )

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
        assert arg3 is not None  # Type narrowing for pyright
        piece_to_expr = f"int(m_num({generate_expr(arg3, ctx)}))"
    else:
        piece_to_expr = "None"

    # Generate value expression (wrapped in m_str to ensure string type)
    assert assignment.value is not None, "LHS $PIECE requires a value"
    value_expr = f"m_str({generate_expr(assignment.value, ctx)})"

    # Emit m_set_piece call
    ctx.emitter.line(
        f"m_set_piece({getter}, {setter}, {delimiter_expr}, {piece_from_expr}, {piece_to_expr}, {value_expr})"
    )


def _generate_lhs_extract(assignment: MAssignment, ctx: "GeneratorContext") -> None:
    """Generate m_set_extract() call for LHS $EXTRACT assignment.

    Spec 009 (T017-T018): Generate code for S $E(var,from,to)=value

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

    # $EXTRACT(var, from_pos [, to_pos])
    if len(args) < 2:
        raise ValueError(f"LHS $EXTRACT requires at least 2 arguments, got {len(args)}")

    # First argument must be a variable (local or global)
    first_arg = args[0]
    if isinstance(first_arg, GlobalVariable):
        # Global variable: use _rt.globals.get/set
        global_name = first_arg.name
        if first_arg.subscripts:
            subs_code = []
            for sub in first_arg.subscripts:
                subs_code.append(f"str({generate_expr(sub, ctx)})")
            subscripts_tuple = f"({', '.join(subs_code)},)"
        else:
            subscripts_tuple = "()"
        getter = f'lambda: _rt.globals.get("{global_name}", {subscripts_tuple}) or ""'
        setter = f'lambda v: _rt.globals.set("{global_name}", {subscripts_tuple}, v)'
    elif isinstance(first_arg, MVariable):
        var = first_arg
        var_name = var.name
        translated_name = translate_name(var_name)

        # Build getter/setter based on strategy
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # _scope-based access using m_var_value for compatibility with
            # both MArray and plain values from external TRAMPOLINE routines
            getter = f"lambda: m_var_value(_scope.get({translated_name!r})) or ''"
            setter = f"lambda v: setattr(_scope.setdefault({translated_name!r}, MArray()), 'value', v)"
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
            # state-based access
            getter = f"lambda: getattr(state, {translated_name!r}, '') or ''"
            setter = f"lambda v: setattr(state, {translated_name!r}, v)"
        else:
            # Plain local variable - fall back to _scope pattern for safety
            getter = f"lambda: m_var_value(_scope.get({translated_name!r})) or ''"
            setter = f"lambda v: setattr(_scope.setdefault({translated_name!r}, MArray()), 'value', v)"
    else:
        raise NotImplementedError(
            f"LHS $EXTRACT first argument must be a variable, got {type(first_arg).__name__}"
        )

    # Generate from_pos expression
    from_pos_expr = generate_expr(args[1], ctx)

    # Generate to_pos expression (optional, 3rd argument)
    if len(args) >= 3:
        arg2 = args[2]
        assert arg2 is not None  # Type narrowing for pyright
        to_pos_expr = generate_expr(arg2, ctx)
    else:
        to_pos_expr = "None"

    # Generate value expression
    assert assignment.value is not None, "LHS $EXTRACT requires a value"
    value_expr = generate_expr(assignment.value, ctx)

    # Emit m_set_extract call
    ctx.emitter.line(
        f"m_set_extract({getter}, {setter}, {from_pos_expr}, {to_pos_expr}, {value_expr})"
    )


def _generate_global_set(assignment: MAssignment, ctx: "GeneratorContext") -> None:
    """Generate _rt.globals.set() call for global variable SET.

    Spec 009 (T026): Generate code for S ^NAME(subscripts)=value

    Args:
        assignment: MAssignment with GlobalVariable target
        ctx: Generator context

    The generated code calls _rt.globals.set():
        _rt.globals.set("NAME", (sub1, sub2), "value")
        _rt.globals.set("NAME", (), "value")  # No subscripts

    Note: Subscripts are NOT wrapped in str() - the runtime's _canonicalize_subscript
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
    # T087: Pass subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    if global_var.subscripts:
        subscript_exprs = [
            generate_expr(sub, ctx, subscript_context=True)
            for sub in global_var.subscripts
        ]
        # Format as tuple: (sub1, sub2, ...) or (sub1,) for single element
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

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
    """Generate _rt.globals.set() call for extended global reference SET.

    Spec 017: Generate code for S ^["env"]NAME(subscripts)=value

    For m2py, the environment parameter is ignored - the global is accessed
    as a regular global. This handles the syntax but doesn't implement
    multi-environment global access.

    Args:
        assignment: MAssignment with ExtendedGlobalBracket target
        ctx: Generator context

    The generated code calls _rt.globals.set() ignoring the environment:
        _rt.globals.set("NAME", ("sub1", "sub2"), "value")
    """
    assert isinstance(assignment.target, ExtendedGlobalBracket)
    ext_global = assignment.target

    # Get global name (environment is ignored)
    global_name = ext_global.name

    # Generate subscript expressions
    # DO NOT wrap in str() - let runtime handle canonicalization
    # T087: Pass subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    if ext_global.subscripts:
        subscript_exprs = [
            generate_expr(sub, ctx, subscript_context=True)
            for sub in ext_global.subscripts
        ]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    # Generate value expression
    assert assignment.value is not None, "Global SET requires a value"
    value_expr = generate_expr(assignment.value, ctx)

    # Emit _rt.globals.set() call
    # Use m_str() to format numbers in MUMPS canonical form (no E-notation)
    ctx.emitter.line(
        f"_rt.globals.set({global_name!r}, {subscripts_tuple}, m_str({value_expr}))"
    )


def _generate_naked_global_set(
    assignment: MAssignment, ctx: "GeneratorContext"
) -> None:
    """Generate resolve_naked + set for naked global reference SET.

    Spec 009 (T031): Generate code for S ^(subscripts)=value

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
    # T087: Pass subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    if naked_global.subscripts:
        subscript_exprs = [
            generate_expr(sub, ctx, subscript_context=True)
            for sub in naked_global.subscripts
        ]
        # Format as tuple: (sub1, sub2, ...) or (sub1,) for single element
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

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
    - MIndirection (ARGUMENT): Use write_indirection for W @A

    Spec 011 (T025-T029): Format control support.

    Args:
        stmt: MWriteStatement node
        ctx: Generator context
    """
    from m2py.asg.expressions import MIndirection
    from m2py.asg.enums import IndirectionType

    for arg in stmt.arguments:
        if isinstance(arg, MFormatControl):
            # Spec 011 (T025): Handle format control nodes
            _generate_format_control(arg, ctx)
        elif (
            isinstance(arg, MIndirection)
            and arg.indirection_type == IndirectionType.ARGUMENT
        ):
            # WRITE argument indirection: W @A where A contains WRITE args
            # Must use write_indirection, NOT evaluate_argument_indirection,
            # because A may contain format controls like !?3 that aren't expressions
            _generate_write_indirection(arg, ctx)
        elif isinstance(arg, MExpr):
            # Generate expression and write it
            # Runtime handles None -> empty string conversion (MUMPS undefined semantics)
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

    Spec 011 (T026-T029): Format control code generation.

    Args:
        fc: MFormatControl node
        ctx: Generator context
    """
    if fc.control_type == FormatControlType.NEWLINE:
        # Spec 011 (T026): NEWLINE format control
        # Use write_newline() to properly reset $X and increment $Y
        ctx.emitter.line("_rt.write_newline()")

    elif fc.control_type == FormatControlType.FORMFEED:
        # Spec 011 (T027): FORMFEED format control
        # YDB: conditional newline before form feed only if $X > 0
        # (iorm_cond_wteol in YDB source code)
        # Form feed outputs \x0c and resets $Y to 0, NO trailing newline
        # The outref has an extra newline after form feed that we must add
        # separately to match the output, but NOT count for $Y
        ctx.emitter.line("_rt.write_formfeed()")

    elif fc.control_type == FormatControlType.CHARCODE:
        # Spec 011 (T028): CHARCODE format control (*n)
        if fc.expression is not None:
            expr = generate_expr(fc.expression, ctx)
            # Apply MUMPS numeric coercion before int() for *intexpr
            ctx.emitter.line(f"_rt.write(chr(int(m_num({expr}))))")
        else:
            # No expression - shouldn't happen but handle gracefully
            pass

    elif fc.control_type == FormatControlType.TAB:
        # Spec 011 (T029): TAB format control (?n)
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
        source_expr = generate_expr(inner_expr, ctx)

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
    # T045: QUIT with return value (extrinsic function return)
    # Spec 010 (T020): If label has by-ref outputs, return tuple (value, *byref_outputs)
    if stmt.return_value is not None:
        value_expr = generate_expr(stmt.return_value, ctx)

        # Check if label has by-ref outputs that need to be included
        if (
            ctx.current_label
            and ctx.current_label.signature
            and ctx.current_label.signature.byref_outputs
        ):
            byref_outputs = ctx.current_label.signature.byref_outputs
            formal_params = ctx.current_label.signature.formal_params
            # Build tuple: (return_value, byref1, byref2, ...)
            # Spec 009 (T021): Use MArray.value for consistency
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                byref_exprs = [
                    f"_scope.get({p!r}, MArray()).value"
                    for p in formal_params
                    if p in byref_outputs
                ]
            else:
                byref_exprs = [
                    translate_name(p) for p in formal_params if p in byref_outputs
                ]
            if byref_exprs:
                all_exprs = [value_expr] + byref_exprs
                ctx.emitter.line(f"return ({', '.join(all_exprs)})")
                return

        # No by-ref outputs - just return the value
        ctx.emitter.line(f"return {value_expr}")
        return

    # T108: exits_for is set by analyze_quit_context() for QUITs inside FOR loops
    if stmt.exits_for is not None:
        # Inside a FOR loop - QUIT exits the innermost FOR
        ctx.emitter.line("break")
        return

    # T109: exits_do_block is set by analyze_quit_context() for QUITs inside DO blocks
    if stmt.exits_do_block is not None:
        # Inside a DO block - QUIT exits only the block (break from while True)
        ctx.emitter.line("break")
        return

    # Spec 006 (T069a): Self-loop pattern - QUIT exits the while True: loop
    if ctx.current_label and ctx.current_label.has_self_loop:
        ctx.emitter.line("break")
        return

    # T059: Plain QUIT with by-ref outputs - return modified params as tuple
    # Check if current label has byref_outputs that need to be returned
    if (
        ctx.current_label
        and ctx.current_label.signature
        and ctx.current_label.signature.byref_outputs
    ):
        byref_outputs = ctx.current_label.signature.byref_outputs
        # Return byref params in formal_params order (for consistent tuple unpacking)
        formal_params = ctx.current_label.signature.formal_params
        # T084: For SIMPLE_FUNCTIONS, return from _scope; for TRAMPOLINE, use local vars
        # Spec 009 (T021): Use MArray.value for consistency
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            return_exprs = [
                f"_scope.get({p!r}, MArray()).value"
                for p in formal_params
                if p in byref_outputs
            ]
        else:
            return_exprs = [
                translate_name(p) for p in formal_params if p in byref_outputs
            ]
        if return_exprs:
            ctx.emitter.line(f"return {', '.join(return_exprs)}")
            return

    # Spec 006: Trampoline pattern - return (None, state) to signal exit
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        # T075m: Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
        if ctx.in_inline_xecute:
            ctx.emitter.line("raise _XecuteExit()")
        else:
            ctx.emitter.line("return (None, state)")
        return

    # Plain QUIT outside FOR/DO block - return from function/routine
    # T075m: Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
    if ctx.in_inline_xecute:
        ctx.emitter.line("raise _XecuteExit()")
    else:
        ctx.emitter.line("return")


def _generate_if(stmt: MIfStatement, ctx: "GeneratorContext") -> None:
    """Generate Python if statement from MIfStatement.

    MUMPS IF evaluates condition, sets $TEST, and conditionally executes body.
    Generated code: _test = m_truth(cond); if _test: ...

    T052: For IF indirection (I @A where A=""), empty string is TRUE.
    We pass if_condition=True to generate_expr() so indirection codegen
    adds treat_empty_as_truthy=True to the runtime call.

    Args:
        stmt: MIfStatement node
        ctx: Generator context
    """
    # Get condition(s) - single condition uses .condition, multiple uses .conditions
    # T052: Pass if_condition=True for indirection T052 empty string handling
    if stmt.condition is not None:
        cond_expr = generate_expr(stmt.condition, ctx, if_condition=True)
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
                for body_stmt in stmt.then_scope.statements:
                    generate_statement(body_stmt, ctx)
            else:
                ctx.emitter.line("pass")
        return
    else:
        # Argumentless IF uses existing $TEST
        ctx.emitter.line("if _test:")
        with ctx.emitter.indented():
            if stmt.then_scope and stmt.then_scope.statements:
                for body_stmt in stmt.then_scope.statements:
                    generate_statement(body_stmt, ctx)
            else:
                ctx.emitter.line("pass")
        return

    # Single condition case - evaluate and set _test
    ctx.emitter.line(f"_test = m_truth({cond_expr})")
    ctx.emitter.line("if _test:")

    with ctx.emitter.indented():
        if stmt.then_scope and stmt.then_scope.statements:
            for body_stmt in stmt.then_scope.statements:
                generate_statement(body_stmt, ctx)
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
            for body_stmt in stmt.body.statements:
                generate_statement(body_stmt, ctx)
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

    T038: If this FOR is the outermost target of a MULTI_LOOP_EXIT GOTO,
    wrap the entire loop in try/except _LoopExit.

    FR-018: Cross-label loop exits must call the target label after exiting.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    # T038: Check if this FOR needs try/except wrapper for multi-loop exit
    # T091: Use pre-computed field from analysis instead of helper function
    needs_wrapper = stmt.needs_exception_wrapper

    # FR-018: Check if this FOR has cross-label single-loop exits
    # T091: Use pre-computed field from analysis instead of helper function
    has_cross_label_exit = stmt.has_cross_label_exit

    # V1FORC2/I-377: Check if this FOR has same-label single-loop exits
    # These need to break the FOR and continue the outer while True self-loop
    has_same_label_exit = stmt.has_same_label_exit

    # FR-018: Initialize goto tracking before loop if needed
    if has_cross_label_exit and not needs_wrapper:
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("_goto_label = None")
        else:
            ctx.emitter.line("_goto_target = None")

    # V1FORC2/I-377: Initialize same-label exit flag before loop if needed
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
        # T096: Open-ended loops with body modification need while loop pattern
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
            # FR-018: Call/return to target label if provided
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

    # FR-018: Handle target after single-loop exit if set
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

    T032: Handle subscripted loop variables (F I(1)=1:1:3) by using .set() instead
    of .value assignment.

    T075n: When for_ctx is provided, use for_ctx.loop_var instead of translate_name()
    to handle inline XECUTE prefixing (e.g. _xec_I instead of I).

    Args:
        stmt: MForStatement node
        ctx: Generator context
        for_ctx: Optional ForGenContext with actual Python variable name
    """
    from m2py.codegen.expressions import generate_expr

    # T084: Sync for-loop variable to _scope for SIMPLE_FUNCTIONS strategy
    # T089h: Also sync for TRAMPOLINE with dynamic_locals (state._locals)
    # Only needed when using Python's `for` loop (not while loop)
    # When loop_var_modified_in_body is True, we use while loop with _scope directly
    # Spec 009 (T021): Use MArray.value for consistency with subscripted variables
    #
    # NOTE: For subscripted loop vars (F A(B)=1:1:3), the sync is handled in
    # _generate_for_bounded which re-evaluates subscripts at each access.
    # Skip the sync here to avoid double-syncing with potentially stale subscripts.
    needs_scope_sync = (
        ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS
        and stmt.loop_var
        and not stmt.loop_var_modified_in_body
        and not (for_ctx and for_ctx.loop_var_subscripts)  # Skip for subscripted vars
    )
    # T089h: TRAMPOLINE with dynamic_locals also needs sync (state._locals)
    needs_locals_sync = (
        ctx.strategy == GotoStrategy.TRAMPOLINE
        and ctx.uses_dynamic_locals
        and stmt.loop_var
        and not stmt.loop_var_modified_in_body
        and not (for_ctx and for_ctx.loop_var_subscripts)  # Skip for subscripted vars
    )
    if needs_scope_sync or needs_locals_sync:
        if isinstance(stmt.loop_var, str):
            var_name = stmt.loop_var
            subscripts = []
        elif isinstance(stmt.loop_var, MVariable):
            var_name = stmt.loop_var.name
            # T032: Extract subscripts for subscripted loop variables
            subscripts = [generate_expr(sub, ctx) for sub in stmt.loop_var.subscripts]
        else:
            var_name = None  # Complex case (indirection) - skip sync
            subscripts = []
        if var_name:
            # T075n: Use for_ctx.loop_var if provided (handles _xec_ prefix in inline XECUTE)
            python_name = for_ctx.loop_var if for_ctx else translate_name(var_name)
            # Use translated name for scope key to match SET statement behavior
            translated_var_name = translate_name(var_name)
            # T089h: Choose sync target based on strategy
            if needs_locals_sync:
                sync_target = (
                    f"state._locals.setdefault({translated_var_name!r}, MArray())"
                )
            else:
                sync_target = f"_scope.setdefault({translated_var_name!r}, MArray())"
            if subscripts:
                # T032: Subscripted loop var - use .set(sub1, sub2, ..., value=val)
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

    Spec 017: MUMPS FOR always sets the loop variable to the start value,
    even when the loop body doesn't execute (e.g., F I=2:-1:3 sets I=2).
    We must set the loop variable before the loop.

    Spec 017 Phase 11: Use unique variable names (_for_start_N, etc.) to prevent
    nested FOR loops from clobbering each other's loop control variables.

    T068: For indirect loop variables (F @A=1:1:3), resolve the target
    variable name at runtime and update via _rt.set_var().

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

    # Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions
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

    # Spec 017: Set loop variable to start value before the loop
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
        # T068: Handle indirect loop variable (F @A=1:1:3)
        # Resolve the target variable name once before the loop
        ctx.emitter.line(f"_for_indirect_var_{lid} = {for_ctx.loop_var_expr}")
        # Set loop var to start value (MUMPS semantics)
        ctx.emitter.line(f"{for_ctx.loop_var} = {start_var}")
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
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # T014: Dynamic locals - use state._locals for consistency with read access
            base = f"state._locals.setdefault({var_name!r}, MArray())"
        elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Use _scope for SIMPLE_FUNCTIONS
            base = f"_scope.setdefault({var_name!r}, MArray())"
        else:
            # Fallback to _scope (shouldn't normally be reached)
            base = f"_scope.setdefault({var_name!r}, MArray())"

        def make_set_expr(val: str) -> str:
            return f"{base}.set({cached_subs_str}, value={val})"

        # Initial assignment - set counter and store to subscripted variable
        ctx.emitter.line(f"{counter_var} = {start_var}")
        ctx.emitter.line(make_set_expr(counter_var))

        # Also set Python temp var for body access (some body code may use it)
        ctx.emitter.line(f"{for_ctx.loop_var} = {start_var}")

        # While loop - condition uses the counter, not the variable value
        ctx.emitter.line(
            f"while ({step_var} > 0 and {counter_var} <= {end_var}) or "
            f"({step_var} < 0 and {counter_var} >= {end_var}) or "
            f"({step_var} == 0 and {counter_var} <= {end_var}):"
        )
        with ctx.emitter.indented():
            # Sync Python temp var at start of each iteration
            ctx.emitter.line(f"{for_ctx.loop_var} = {counter_var}")

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

            # Sync Python temp var for next iteration
            ctx.emitter.line(f"{for_ctx.loop_var} = {counter_var}")
    else:
        # Simple loop variable (F I=1:1:3)
        # Set loop var to start value (MUMPS semantics)
        ctx.emitter.line(f"{for_ctx.loop_var} = {start_var}")
        # Sync to storage BEFORE the while loop so the value is set even if loop doesn't execute
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS and for_ctx.loop_var_name:
            ctx.emitter.line(
                f"_scope.setdefault({for_ctx.loop_var_name!r}, MArray()).value = {start_var}"
            )
        elif (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.uses_dynamic_locals
            and for_ctx.loop_var_name
        ):
            # T089: Sync to state._locals for TRAMPOLINE with dynamic locals
            translated_name = translate_name(for_ctx.loop_var_name)
            ctx.emitter.line(
                f"state._locals.setdefault({translated_name!r}, MArray()).value = {start_var}"
            )
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

    T068: For indirect loop variables (F @A="X","Y","Z"), resolve the target
    variable name at runtime and update via _rt.set_var().

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

    # T068: Handle indirect loop variable (F @A="X","Y","Z")
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

    T068: For indirect loop variables (F @A=1:1), resolve the target
    variable name at runtime and update via _rt.set_var().

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

    # T068: Handle indirect loop variable (F @A=1:1)
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

    # T068: Handle indirect loop variable
    if for_ctx.loop_var_indirect and for_ctx.loop_var_expr:
        ctx.emitter.line(f"_for_indirect_var = {for_ctx.loop_var_expr}")
        ctx.emitter.line(f"_rt.set_var(_for_indirect_var, {for_ctx.loop_var}, _scope)")
    else:
        ctx.emitter.line(
            f"_scope.setdefault('{for_ctx.loop_var}', MArray()).value = {for_ctx.loop_var}"
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
                f"{for_ctx.loop_var} = m_add(m_num(m_var_value(_scope.get('{for_ctx.loop_var}'))), _for_step)"
            )
            ctx.emitter.line(
                f"_scope.setdefault('{for_ctx.loop_var}', MArray()).value = {for_ctx.loop_var}"
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

    T068: For indirect loop variables (F @A=1:1:3,"X"), resolve the target
    variable name at runtime and update via _rt.set_var().

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

    # T068: Handle indirect loop variable (F @A=1:1:3,"X",10:2:14)
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

    T068: For indirect loop variables (F @A=1:1:3 with body modifying A),
    resolve the target variable name once at the start. When the resolved
    name might be a subscripted variable (like "A(22)"), use _rt.get_var
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

    # T068: Handle indirect loop variable setup
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
            # T096: Open-ended FOR with indirect loop var and body modification
            _generate_for_while_open_range_indirect(stmt, for_ctx, ctx, param)
        elif for_ctx.loop_type == ForLoopType.STRING_LIST:
            _generate_for_while_string_list_indirect(stmt, for_ctx, ctx)
        else:
            raise NotImplementedError(
                f"While loop for indirect var doesn't support {for_ctx.loop_type}"
            )
        return
    # T084: For SIMPLE_FUNCTIONS or TRAMPOLINE with dynamic_locals,
    # use _scope/_locals directly so body modifications are visible to loop
    elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS or (
        ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals
    ):
        # Get the original MUMPS variable name for _scope/_locals key
        if isinstance(stmt.loop_var, str):
            var_name = stmt.loop_var
        elif isinstance(stmt.loop_var, MVariable):
            var_name = stmt.loop_var.name
        else:
            var_name = None

        if var_name:
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # TRAMPOLINE with dynamic_locals: use state._locals
                loop_ref = f"state._locals.setdefault({var_name!r}, MArray()).value"
            else:
                # SIMPLE_FUNCTIONS: use _scope
                loop_ref = f"_scope.setdefault({var_name!r}, MArray()).value"
        else:
            loop_ref = for_ctx.loop_var
    else:
        loop_ref = for_ctx.loop_var

    # Check loop type - dispatch to appropriate pattern
    param = stmt.parameters[0]
    if param.param_type == ForParamType.RANGE:
        _generate_for_while_range(stmt, for_ctx, ctx, loop_ref, param)
    elif param.param_type == ForParamType.OPEN_RANGE:
        # T096: Open-ended FOR with body modification
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

    Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions.
    """
    if param.start is None or param.step is None or param.end is None:
        raise NotImplementedError("Incomplete FOR range parameters for while loop")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)
    end_expr = generate_expr(param.end, ctx)

    # Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions
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

    T096: When the loop variable is modified inside the body, we can't use
    Python's for loop with count() because it would overwrite the modification.
    Instead we use a while True loop with explicit stepping.

    CRITICAL: MUMPS evaluates both start and step BEFORE assigning to the loop
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

    # Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions
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

    # Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions
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

    T096: When the loop variable is indirect (F @A=1:1) and the resolved name
    might be subscripted, we need to use _rt.get_var and _rt.set_var for
    proper subscript handling at runtime.

    CRITICAL: MUMPS evaluates both start and step BEFORE assigning to the loop
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

    # Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions
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

    # Spec 017 Phase 11: Use unique variable names
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

    For indirect loop variables like F @A="X","Y","Z", we need to:
    1. Build the list of values
    2. Use an index-based while loop
    3. Assign the current value to the indirect variable on each iteration

    Spec 017 Phase 11: Use unique variable names to prevent nested loop collisions.
    Also, evaluate each list value LAZILY at iteration time, not upfront, since
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

    # Spec 017 Phase 11: Use unique variable names
    lid = for_ctx.loop_id
    idx_var = f"_for_idx_{lid}"

    # MUMPS FOR list semantics: evaluate each value LAZILY at iteration time
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

    Multiple targets (Phase 11):
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
        UnsupportedFeatureError: For backward intra-label GOTO (requires Spec 006)
    """
    if not stmt.targets:
        raise NotImplementedError("Argumentless GOTO not supported")

    # Phase 11 (T098-T100): Handle multiple targets
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
    T086: Same-routine GOTOs (G LABEL^ROUTINE where ROUTINE is current routine)
          are now treated as local GOTOs instead of external.

    Args:
        target: The MCall target to jump to
        stmt: The parent MGotoStatement (for classification info)
        ctx: Generator context
    """
    # Spec 012 Phase 8 (T049-T052): Check for indirection first
    # Must check before same-routine logic since indirection may also have routine set
    if target.label_is_indirect or target.routine_is_indirect:
        from m2py.codegen.indirection import generate_indirect_goto

        generate_indirect_goto(target, ctx)
        return

    # T086: Check for same-routine GOTO (G LABEL^ROUTINE where ROUTINE matches current)
    # Only treat as external if it's a DIFFERENT routine
    is_external = False
    if target.routine:
        # T086: Use fallback to first label name (same logic as routine.py line 352-355)
        current_routine_name = ctx.routine.name or (
            ctx.routine.labels[0].name if ctx.routine.labels else ""
        )
        # Compare case-insensitively since MUMPS routine names are case-insensitive
        if (
            not current_routine_name
            or target.routine.upper() != current_routine_name.upper()
        ):
            is_external = True

    # Spec 008 Phase 6 (T034-T038): Handle external routine GOTO
    if is_external:
        # T085-ext: Handle postcondition on external GOTO (e.g., G E1^V1OVE:A=1)
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            with ctx.emitter.indented():
                _generate_external_goto(target, ctx)
        else:
            _generate_external_goto(target, ctx)
        return

    # Check for backward intra-label GOTO (creates implicit loops)
    # These cannot be restructured to simple if/else and require Spec 006
    # ASG fields populated by classify_gotos() analysis
    goto_type = stmt.goto_type
    is_cross_label = stmt.is_cross_label
    exits_loops = stmt.exits_loops

    # Spec 006 (T069a): Self-loop pattern - backward intra-label GOTO
    # When label has has_self_loop=True, body is wrapped in while True:
    # and this GOTO becomes continue to restart the loop
    if goto_type == GotoType.BACKWARD_JUMP and not is_cross_label:
        # T093 fix: Handle postcondition on self-loop target (e.g., G loop:q<3)
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

    # Phase 7 (US5): Loop exit patterns
    # Note: There is no "continue" pattern - GOTO cannot create continue semantics.
    # Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
    # termination of all FORs in the line containing the GOTO."
    # exits_loops is populated by classify_gotos() analysis
    in_for_loop = bool(exits_loops)

    # T035/T037: exits_loops determines break vs raise _LoopExit()
    if exits_loops and in_for_loop:
        # V1FORC2 fix: Handle postcondition on target (e.g., G G379:X=1)
        # The target postcondition must be checked before the loop exit
        postcond_ctx = None
        if target.postcondition is not None:
            cond_expr = generate_expr(target.postcondition, ctx)
            ctx.emitter.line(f"if m_truth({cond_expr}):")
            postcond_ctx = ctx.emitter.indented()
            postcond_ctx.__enter__()

        if len(exits_loops) == 1:
            # Single loop exit - generate break
            # FR-018: For cross-label exits, track target so it can be called after loop
            if is_cross_label and target is not None:
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Trampoline: store label name as string
                    ctx.emitter.line(f'_goto_label = "{target.name}"')
                else:
                    # Simple functions: store function reference
                    label_name = translate_name(target.name)
                    ctx.emitter.line(f"_goto_target = {label_name}")
            # V1FORC2/I-377: For same-label exits, set flag to continue outer while True
            elif not is_cross_label:
                ctx.emitter.line("_restart_self_loop = True")
            ctx.emitter.line("break")
        else:
            # Multi-loop exit - generate raise _LoopExit()
            # The exception will be caught by the outermost FOR loop
            # FR-018: Pass target label name so it can be called in except block
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

    # Cross-label GOTO: pattern depends on strategy
    # Spec 006 (T055): Check strategy and generate appropriate pattern
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Spec 007 (T015-T017): Check for offset and emit line-based dispatch
        if target.offset is not None:
            # Offset GOTO: compute target line = label_line + offset
            # The dispatcher will look up (label, offset) in _line_map
            if target.target is None or target.target.line_number is None:
                raise UnsupportedFeatureError(
                    f"Cannot resolve offset GOTO target: {target.name}"
                )
            label_line = target.target.line_number
            offset_code = generate_expr(target.offset, ctx)
            # Spec 007 Phase 7 (T035-T037): Validate offset and raise descriptive error
            # Spec 007 Phase 9 (T045-T046): Skip non-executable lines (comments/blanks)
            # Spec 007: Check for negative offset (must resolve to non-negative integer)
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
                # Spec 007: Find next executable line after target (inline)
                # When offset lands on comment/blank line, continue to next executable.
                # This inline logic is equivalent to find_next_executable() but simpler
                # to generate and performs better (no function call overhead).
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
            ctx.emitter.line("return (_target, state)")
        else:
            # Trampoline pattern: return (label_name, state) tuple
            # The trampoline dispatcher will call the target label
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
        # T075l: Pass _rt and _scope so XECUTE inline GOTO works correctly
        ctx.emitter.line(f"{label_name}(_rt, _scope=_scope)")
        # T075m: Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
        # Outside inline XECUTE, return exits the entire function
        if ctx.in_inline_xecute:
            ctx.emitter.line("raise _XecuteExit()")
        else:
            ctx.emitter.line("return")


def _generate_multi_target_goto(stmt: MGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate GOTO code for multiple targets (Phase 11 + T085).

    Multiple targets are evaluated left-to-right:
    - If target has no postcondition, jump to it unconditionally
    - If target has postcondition and it's true, jump to it
    - If postcondition is false, try next target
    - If all postconditions are false, no jump (fall through)

    T085: Now supports external routines and indirect targets in multi-target GOTO.

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

    # T085: No longer check for unsupported patterns - all target types are now supported

    # Check if any targets have postconditions
    has_postconditions = any(t.postcondition is not None for t in targets)

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


def _generate_goto_jump(target: "MCall", ctx: "GeneratorContext") -> None:
    """Generate the actual jump code for a GOTO target.

    This generates just the jump statement without any condition checks.
    Handles all target types:
    - Local targets: return (label_name, state) or function call
    - External targets: raise GotoExternal exception
    - Indirect targets: runtime resolution with potential external handling

    T085: Extended to support external and indirect targets in multi-target GOTO.
    T086: Same-routine GOTOs (G LABEL^ROUTINE where ROUTINE is current routine)
          are now treated as local GOTOs instead of external.

    Args:
        target: The MCall target to jump to
        ctx: Generator context
    """
    # T085: Handle indirect targets (G @VAR) first since they may also have routine set
    if target.label_is_indirect or target.routine_is_indirect:
        from m2py.codegen.indirection import generate_indirect_goto

        generate_indirect_goto(target, ctx)
        return

    # T086: Check if this is a "same-routine" GOTO (G LABEL^ROUTINE where ROUTINE is current)
    # MUMPS allows explicit routine specification even for local labels.
    # When the target routine matches the current routine, treat as local GOTO.
    if target.routine:
        # T086: Use fallback to first label name (same logic as routine.py line 352-355)
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

    # Local target - original behavior
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        ctx.emitter.line(f'return ("{target.name}", state)')
    else:
        label_name = translate_name(target.name)
        # T075l: Pass _rt and _scope so XECUTE inline GOTO works correctly
        ctx.emitter.line(f"{label_name}(_rt, _scope=_scope)")
        # T075m: Inside inline XECUTE, raise _XecuteExit to exit just the XECUTE block
        # Outside inline XECUTE, return exits the entire function
        if ctx.in_inline_xecute:
            ctx.emitter.line("raise _XecuteExit()")
        else:
            ctx.emitter.line("return")


def _generate_external_goto(target: "MCall", ctx: "GeneratorContext") -> None:
    """Generate code for external GOTO (G ^ROUTINE, G LABEL^ROUTINE).

    Spec 008 Phase 6 (T034-T038): External GOTO transfers control permanently
    to another routine by raising GotoExternal exception. The exception is
    caught by run_with_goto_support() which handles the transfer.

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
            ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")
        elif ctx.state_vars:
            # Static state vars: copy each state variable to _scope
            for var_name in sorted(ctx.state_vars):
                python_name = translate_name(var_name)
                ctx.emitter.line(
                    f"_scope[{var_name!r}] = MArray(value=state.{python_name}) "
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
    ctx.emitter.line("from m2py.runtime import GotoExternal")

    # Handle offset patterns (G LABEL+N^ROUTINE, G +N^ROUTINE)
    if target.offset is not None:
        offset_code = generate_expr(target.offset, ctx)
        # T037-T038: Pass offset to GotoExternal
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
        # T035: G LABEL^ROUTINE - specific label
        label_name = target.name
        ctx.emitter.line(f"raise GotoExternal({routine_name}, {label_name!r}, _rt=_rt)")
    else:
        # T034: G ^ROUTINE - entry label (same name as routine)
        ctx.emitter.line(f"raise GotoExternal({routine_name}, None, _rt=_rt)")


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

        # Increment execution level (spec §6.3) - $STACK increases inside DO blocks
        ctx.emitter.line("_rt.push_frame()")

        # Wrap in try/finally to ensure stack cleanup even on exceptions
        ctx.emitter.line("try:")
        with ctx.emitter.indented():
            # Wrap in while True: so QUIT can use break to exit only the block
            # This is a single-iteration "loop" used for early exit support
            # The exits_do_block field is set by analyze_quit_context() during analysis,
            # so no runtime depth tracking is needed here.
            ctx.emitter.line("while True:  # DO block")
            with ctx.emitter.indented():
                # Generate block body
                for body_stmt in stmt.body.statements:
                    generate_statement(body_stmt, ctx)
                # Always break at end to ensure single iteration
                ctx.emitter.line("break")
        ctx.emitter.line("finally:")
        with ctx.emitter.indented():
            # Decrement execution level (spec §6.3)
            ctx.emitter.line("_rt.pop_frame()")

        # Restore $TEST after block
        ctx.emitter.line("_test = _saved_test")
        return

    # Argumentless DO without body - this should not happen as parser sets
    # is_inline_block=True when collecting dot-indented lines. If we get here,
    # it means the ASG is malformed (standalone D with no body and no targets).
    if not stmt.targets:
        # Generate empty block - no-op (pass statement not needed, just return)
        return

    # Label calls - NO $TEST save/restore
    # Handle each target (multiple targets allowed: D A,B,C)
    # Spec 014 (T076-T078): Each target's postcondition is evaluated independently
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
    # Spec 012 Phase 7 (T042-T045): Check for indirection
    if target.label_is_indirect or target.routine_is_indirect:
        from m2py.codegen.indirection import generate_indirect_do

        generate_indirect_do(target, ctx)
        return

    # Spec 008 (T018-T029): Handle external routine reference D ^ROUTINE
    if target.routine:
        # Translate routine name to valid Python module name (%FOO → _pct_FOO)
        # Note: target.routine is guaranteed non-None by the if check above
        assert target.routine is not None  # Help type checker
        routine_name = translate_name(target.routine)

        # Generate import statement
        ctx.emitter.line(f"import {routine_name}")

        # T075f: Save runtime context before external call for $TEXT support
        # This ensures $TEXT(+N) in the caller still works after the callee returns
        ctx.emitter.line("_saved_routine = _rt._current_routine")
        ctx.emitter.line("_saved_source_lines = _rt._current_source_lines")
        ctx.emitter.line("_saved_label_lines = _rt._current_label_lines")

        # T075b: For TRAMPOLINE with dynamic locals, sync state._locals to _scope
        # before calling external routine so callee can see caller's variables
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")

        # Handle different external DO patterns
        if target.offset is not None:
            # D LABEL+N^ROUTINE or D +N^ROUTINE - uses line dispatch
            offset_code = generate_expr(target.offset, ctx)

            if target.name:
                # T024: D LABEL+N^ROUTINE - label + offset
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
                # T075a: Offset must be truncated to integer per MUMPS spec
                # Use m_num() for MUMPS-style numeric conversion (extracts leading numeric)
                ctx.emitter.line(
                    f"_target_line = {routine_name}._label_lines[{target.name!r}] + 1 + int(m_num({offset_code}))"
                )
            else:
                # T025: D +N^ROUTINE - absolute line offset (already 1-indexed, use directly)
                # T075a: Offset must be truncated to integer per MUMPS spec
                # Use m_num() for MUMPS-style numeric conversion (extracts leading numeric)
                ctx.emitter.line(f"_target_line = int(m_num({offset_code}))")

            # T079: Call via line dispatch map, passing _rt and _scope
            # _line_map returns (label_name, offset) tuple - extract and call
            ctx.emitter.line(
                f"_label_name, _line_offset = {routine_name}._line_map[_target_line]"
            )
            # T075e: Wrap in run_with_goto_support to handle GotoExternal from subroutine
            # When subroutine does external GOTO, we catch it and transfer control,
            # then return to caller when target QUITs
            #
            # T100: For label+offset calls, we need to handle both TRAMPOLINE and
            # SIMPLE_FUNCTIONS strategies. TRAMPOLINE has _-prefixed internal functions
            # that accept _start_offset. SIMPLE_FUNCTIONS has public functions that
            # either accept _start_offset (if they have fall-through lines) or don't.
            # We check at runtime for the internal function first.
            ctx.emitter.line("from m2py.runtime import run_with_goto_support")
            ctx.emitter.line("_internal_name = '_' + _label_name")
            ctx.emitter.line(f"if hasattr({routine_name}, _internal_name):")
            with ctx.emitter.indented():
                # TRAMPOLINE strategy - use internal function with RoutineState
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=None: "
                    f"getattr({routine_name}, _internal_name)(_rt, {routine_name}.RoutineState(), _scope or {{}}, _start_offset=_line_offset), _rt, _scope)"
                )
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                # SIMPLE_FUNCTIONS strategy - try public function with _start_offset
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=None: "
                    f"getattr({routine_name}, _label_name)(_rt, _scope=_scope, _start_offset=_line_offset), _rt, _scope)"
                )
        elif target.name:
            # T022-T023: D LABEL^ROUTINE - call specific label
            label_name = translate_name(target.name)
            # T026: Generate LabelNotFoundError check
            ctx.emitter.line(f"if not hasattr({routine_name}, {label_name!r}):")
            with ctx.emitter.indented():
                ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                ctx.emitter.line(
                    f"raise LabelNotFoundError({target.name!r}, {routine_name!r}, "
                    f"list({routine_name}._label_lines.keys()))"
                )
            # T079: Pass _rt and _scope for cross-routine variable visibility
            # T075e: Wrap in run_with_goto_support to handle GotoExternal from subroutine
            ctx.emitter.line("from m2py.runtime import run_with_goto_support")
            args = _generate_call_arguments(target.arguments, ctx)
            if args:
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=None: "
                    f"{routine_name}.{label_name}(_rt, {args}, _scope=_scope), _rt, _scope)"
                )
            else:
                ctx.emitter.line(
                    f"run_with_goto_support({routine_name}.{label_name}, _rt, _scope)"
                )
        else:
            # D ^ROUTINE - call entry label (same name as routine)
            entry_label = translate_name(routine_name)
            # T079: Pass _rt and _scope for cross-routine variable visibility
            # T075e: Wrap in run_with_goto_support to handle GotoExternal from subroutine
            ctx.emitter.line("from m2py.runtime import run_with_goto_support")
            args = _generate_call_arguments(target.arguments, ctx)
            if args:
                ctx.emitter.line(
                    f"run_with_goto_support(lambda _rt, _scope=None: "
                    f"{routine_name}.{entry_label}(_rt, {args}, _scope=_scope), _rt, _scope)"
                )
            else:
                ctx.emitter.line(
                    f"run_with_goto_support({routine_name}.{entry_label}, _rt, _scope)"
                )

        # T075b: For TRAMPOLINE with dynamic locals, sync _scope back to state._locals
        # after returning from external routine so caller can see callee's modifications
        # T075k: Wrap plain values in MArray when syncing back (callee may use static state)
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
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

        # T075f: Restore runtime context after external call returns
        ctx.emitter.line("_rt._current_routine = _saved_routine")
        ctx.emitter.line("_rt._current_source_lines = _saved_source_lines")
        ctx.emitter.line("_rt._current_label_lines = _saved_label_lines")
        return

    # Get the label name and translate it
    label_name = translate_name(target.name)

    # Generate arguments if any
    args = _generate_call_arguments(target.arguments, ctx)

    # Spec 007 (T025-T028c): Handle DO with offset
    # In TRAMPOLINE strategy, call the internal function with _start_offset
    if target.offset is not None and ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Prefix with _ for internal trampoline function
        internal_func = "_" + label_name
        # Generate offset expression code
        offset_code = generate_expr(target.offset, ctx)

        # Spec 007 Phase 7 (T035-T037): Validate offset for DO as well
        # Spec 007 Phase 9 (T045-T046): Skip non-executable lines (comments/blanks)
        # Get the label's line number for validation
        if target.target is not None and target.target.line_number is not None:
            label_line = target.target.line_number
            # Spec 007: Check for negative offset (must resolve to non-negative integer)
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
                # Spec 007: Find next executable line after target (inline)
                # When offset lands on comment/blank line, continue to next executable.
                # This inline logic is equivalent to find_next_executable() but simpler.
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

        # T079: Build call with _rt, state, _scope, and _start_offset
        # T075i: Capture return value and follow trampoline loop
        # The internal function may return a label transition (e.g., when offset
        # lands at end of label block and execution should continue to next label)
        if args:
            ctx.emitter.line(
                f"_do_target, state = {internal_func}(_rt, state, _scope, {args}, _start_offset=_offset_val)"
            )
        else:
            ctx.emitter.line(
                f"_do_target, state = {internal_func}(_rt, state, _scope, _start_offset=_offset_val)"
            )
        # T075i: Follow trampoline loop if internal function returned a label
        ctx.emitter.line("while _do_target is not None:")
        with ctx.emitter.indented():
            ctx.emitter.line("_do_func = _labels[_do_target]")
            ctx.emitter.line("_do_target, state = _do_func(_rt, state, _scope)")
        return

    # T060-T062: Check callee signature for byref_outputs and generate destructuring
    callee_signature = None
    if hasattr(target, "target") and target.target:
        callee_label = target.target
        if hasattr(callee_label, "signature") and callee_label.signature:
            callee_signature = callee_label.signature

    if callee_signature and callee_signature.byref_outputs:
        # Map byref formal params to actual variables passed by reference
        # The callee returns byref params in formal_params order
        formal_params = callee_signature.formal_params
        byref_outputs = callee_signature.byref_outputs
        actual_args = target.arguments or []

        # Build list of caller variables that receive returned values
        # Only include params that are both:
        # 1. In byref_outputs (callee modifies them)
        # 2. Passed by reference at call site (.VAR syntax)
        return_vars = []
        for i, formal_name in enumerate(formal_params):
            if formal_name in byref_outputs:
                # Check if corresponding actual was passed by reference
                if i < len(actual_args):
                    actual = actual_args[i]
                    if actual.passing_mode == PassingMode.BY_REFERENCE:
                        # Get the caller's variable name
                        if actual.variable_name:
                            var_name = actual.variable_name
                            # T084: Use _scope['X'] for SIMPLE_FUNCTIONS
                            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                                return_vars.append(f"_scope[{var_name!r}]")
                            else:
                                return_vars.append(translate_name(var_name))

        if return_vars:
            # T079: Generate call and assign returned values to caller variables
            # T084: Pass _scope for cross-routine variable visibility
            # Spec 009 (T021): For SIMPLE_FUNCTIONS, use MArray.value via temp var
            if args:
                call_expr = f"{label_name}(_rt, {args}, _scope=_scope)"
            else:
                call_expr = f"{label_name}(_rt, _scope=_scope)"

            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                # Use temp variable and assign to MArray.value for each return var
                ctx.emitter.line(f"_byref_result = {call_expr}")
                if len(return_vars) == 1:
                    # Single return value
                    var_name = (
                        return_vars[0].replace("_scope[", "").replace("]", "")[1:-1]
                    )  # Extract name from "_scope['X']"
                    ctx.emitter.line(
                        f"_scope.setdefault({var_name!r}, MArray()).value = _byref_result"
                    )
                else:
                    # Tuple unpacking - assign each element
                    for i, rv in enumerate(return_vars):
                        var_name = rv.replace("_scope[", "").replace("]", "")[
                            1:-1
                        ]  # Extract name
                        ctx.emitter.line(
                            f"_scope.setdefault({var_name!r}, MArray()).value = _byref_result[{i}]"
                        )
            else:
                # TRAMPOLINE: use direct tuple destructuring
                lhs = ", ".join(return_vars)
                ctx.emitter.line(f"{lhs} = {call_expr}")
        else:
            # T079: No by-ref params at call site - just call with _rt
            # T084: Pass _scope for cross-routine variable visibility
            # T075b: For TRAMPOLINE with state_vars, sync state to _scope before call
            # and sync _scope back to state after call for intra-routine DO
            if (
                ctx.strategy == GotoStrategy.TRAMPOLINE
                and ctx.state_vars
                and not ctx.uses_dynamic_locals
            ):
                # Sync state to _scope before call
                for var_name in sorted(ctx.state_vars):
                    py_name = translate_name(var_name)
                    ctx.emitter.line(f"_scope[{var_name!r}] = state.{py_name}")
            # T075h: For TRAMPOLINE with dynamic_locals, sync state._locals to _scope
            # before internal DO calls so subroutine sees current variable values
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                ctx.emitter.line(
                    "_scope.update({k: v for k, v in state._locals.items()})"
                )
            if args:
                ctx.emitter.line(f"{label_name}(_rt, {args}, _scope=_scope)")
            else:
                ctx.emitter.line(f"{label_name}(_rt, _scope=_scope)")
            # T075b: Sync _scope back to state after call
            if (
                ctx.strategy == GotoStrategy.TRAMPOLINE
                and ctx.state_vars
                and not ctx.uses_dynamic_locals
            ):
                for var_name in sorted(ctx.state_vars):
                    py_name = translate_name(var_name)
                    ctx.emitter.line(
                        f"if {var_name!r} in _scope: state.{py_name} = _scope[{var_name!r}].value if isinstance(_scope.get({var_name!r}), MArray) else _scope[{var_name!r}]"
                    )
            # T075h: For TRAMPOLINE with dynamic_locals, sync _scope back to state._locals
            # T075k: Wrap plain values in MArray when syncing back (callee may use static state)
            elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
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
    else:
        # T079: No byref_outputs - simple call with _rt
        # T084: Pass _scope for cross-routine variable visibility
        # T075b: For TRAMPOLINE with state_vars, sync state to _scope before call
        if (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.state_vars
            and not ctx.uses_dynamic_locals
        ):
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                ctx.emitter.line(f"_scope[{var_name!r}] = state.{py_name}")
        # T075h: For TRAMPOLINE with dynamic_locals, sync state._locals to _scope
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")
        if args:
            ctx.emitter.line(f"{label_name}(_rt, {args}, _scope=_scope)")
        else:
            ctx.emitter.line(f"{label_name}(_rt, _scope=_scope)")
        # T075b: Sync _scope back to state after call
        if (
            ctx.strategy == GotoStrategy.TRAMPOLINE
            and ctx.state_vars
            and not ctx.uses_dynamic_locals
        ):
            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                ctx.emitter.line(
                    f"if {var_name!r} in _scope: state.{py_name} = _scope[{var_name!r}].value if isinstance(_scope.get({var_name!r}), MArray) else _scope[{var_name!r}]"
                )
        # T075h: For TRAMPOLINE with dynamic_locals, sync _scope back to state._locals
        # T075k: Wrap plain values in MArray when syncing back (callee may use static state)
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
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


def _generate_kill(stmt: MKillStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for KILL command.

    Spec 009 (Phase 10): KILL deletes a variable node and all its descendants.

    Supports:
    - K X → MArray.kill() on local variable X
    - K X(1,2) → MArray.kill(1, 2) on subscripted local
    - K ^G → _rt.globals.kill("G", ()) on global
    - K ^G(1,2) → _rt.globals.kill("G", ("1", "2")) on subscripted global
    - K ^(1,2) → resolve_naked then kill (naked global reference)
    - K (X,Y) → Exclusive KILL: kill all locals except X,Y (Spec 011 T073)

    NOT yet implemented:
    - K (argumentless) - kill all locals

    Args:
        stmt: MKillStatement node
        ctx: Generator context
    """
    # Handle exclusive KILL: K (X,Y) - kill all except X,Y
    if stmt.exclusive:
        # Build set of variables to keep
        keep_vars_repr = repr(set(stmt.except_list))

        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Iterate over _scope and remove non-kept variables
            ctx.emitter.line("for _var_name in list(_scope.keys()):")
            with ctx.emitter.indented():
                ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                with ctx.emitter.indented():
                    ctx.emitter.line("_scope.pop(_var_name, None)")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Spec 017 (T011): Iterate over _locals and remove non-kept variables
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
            # Clear all local variables from _scope
            ctx.emitter.line("_scope.clear()")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Spec 017 (T011): Clear _locals dict for dynamic locals mode
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
            if target.subscripts:
                subs_code = []
                for sub in target.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                subscripts_tuple = f"({', '.join(subs_code)},)"
            else:
                subscripts_tuple = "()"

            ctx.emitter.line(f'_rt.globals.kill("{global_name}", {subscripts_tuple})')

        elif isinstance(target, NakedGlobal):
            # Naked global: K ^(subs) - resolve then kill
            if target.subscripts:
                subs_code = []
                for sub in target.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                subscripts_tuple = f"({', '.join(subs_code)},)"
            else:
                subscripts_tuple = "()"

            # Resolve naked to (name, full_subscripts), then kill
            ctx.emitter.line(
                f"_naked_name, _naked_subs = _rt.globals.resolve_naked({subscripts_tuple})"
            )
            ctx.emitter.line("_rt.globals.kill(_naked_name, _naked_subs)")

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

            # For SIMPLE_FUNCTIONS strategy, use _scope
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                if subscripts_args:
                    ctx.emitter.line(
                        f"_scope.get({var_name!r}, MArray()).kill({subscripts_args})"
                    )
                else:
                    # Kill entire variable - remove from scope
                    ctx.emitter.line(f"_scope.pop({var_name!r}, None)")
            else:
                # TRAMPOLINE strategy - direct variable access
                if subscripts_args:
                    ctx.emitter.line(f"{translated}.kill({subscripts_args})")
                else:
                    # Kill entire variable - reset to empty MArray
                    ctx.emitter.line(f"{translated} = MArray()")

        elif isinstance(target, MIndirection):
            # T086, T133: Indirection target: K @A or K @A@(subs) using unified components
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

    Spec 011 (T060-T061): NEW creates a new local scope for specified variables.
    The old values are shadowed until the routine/label exits.

    Supports:
    - N → NEW all (argumentless - save and remove all locals until function exit)
    - N X → NEW X (save and remove from _scope until function exit)
    - N X,Y,Z → NEW multiple variables
    - N (X,Y) → Exclusive NEW: NEW all locals except X,Y (Spec 011 T072)

    Note: N () (empty exclusive NEW) is invalid MUMPS syntax - YDB rejects it.
    Our parser silently skips it, which is acceptable.

    When ctx.new_scope_manager_var is set, uses NewScopeManager.new_var()
    for proper save/restore semantics on function exit.
    Otherwise, uses simple _scope.pop() for within-routine NEW.

    Args:
        stmt: MNewStatement node
        ctx: Generator context
    """
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
                ctx.emitter.line(f"_keep_vars = {repr(set(string_vars))}")
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
            # All elements are strings - use static set
            keep_vars_repr = repr(set(stmt.except_list))

        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            if ctx.new_scope_manager_var:
                # Use NewScopeManager - iterate over _scope and new_var for non-kept
                ctx.emitter.line("for _var_name in list(_scope.keys()):")
                with ctx.emitter.indented():
                    ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f"{ctx.new_scope_manager_var}.new_var(_var_name)"
                        )
            else:
                # Simple pop for non-kept variables
                ctx.emitter.line("for _var_name in list(_scope.keys()):")
                with ctx.emitter.indented():
                    ctx.emitter.line(f"if _var_name not in {keep_vars_repr}:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_scope.pop(_var_name, None)")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Spec 017 (T012): Push _locals state to _new_stack (only non-kept vars)
            ctx.emitter.line(
                f"state._new_stack.append({{k: v.copy() if hasattr(v, 'copy') else v for k, v in state._locals.items() if k not in {keep_vars_repr}}})"
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
    if not stmt.variables:
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            if ctx.new_scope_manager_var:
                # Use NewScopeManager - iterate over _scope and new_var for all
                ctx.emitter.line("for _var_name in list(_scope.keys()):")
                with ctx.emitter.indented():
                    ctx.emitter.line(f"{ctx.new_scope_manager_var}.new_var(_var_name)")
            else:
                # Simple clear of all local variables
                ctx.emitter.line("_scope.clear()")
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            # Spec 017 (T012): Push _locals state to _new_stack, then clear
            # Deep copy to preserve MArray state
            ctx.emitter.line(
                "state._new_stack.append({k: v.copy() if hasattr(v, 'copy') else v for k, v in state._locals.items()})"
            )
            ctx.emitter.line("state._locals.clear()")
        else:
            # TRAMPOLINE strategy without dynamic locals - not supported
            raise NotImplementedError(
                "Argumentless NEW not supported in TRAMPOLINE strategy"
            )
        return

    # Process each variable in the new list
    for var in stmt.variables:
        # T070: Handle indirection in NEW (N @A where A contains variable name)
        if isinstance(var, MIndirection):
            from m2py.codegen.expressions import generate_expr

            if var.expression is None:
                raise ValueError("NEW indirection has no expression")

            # Get the VALUE of the indirection expression directly.
            # Unlike FOR @A which expects a single variable name, NEW @A
            # expects a comma-separated list of variable names.
            # E.g., S A="X,Y" N @A should NEW both X and Y.
            # We do NOT use resolve_for_target here because that validates
            # the result as a single variable name, which would fail for "X,Y".
            value_expr = generate_expr(var.expression, ctx)

            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                # NEW indirection can contain comma-separated variable lists
                # For example: S A="X,Y" N @A should NEW both X and Y
                # T088: Use _split_argument_list to handle subscripted vars
                # E.g., A="X(1,2),Y" should split to ["X(1,2)", "Y"], not ["X(1", "2)", "Y"]
                ctx.emitter.line(
                    f"_ind_var_list = _rt._split_argument_list(str({value_expr}))"
                )
                ctx.emitter.line("for _ind_var in _ind_var_list:")
                with ctx.emitter.indented():
                    if ctx.new_scope_manager_var:
                        # Use NewScopeManager for proper save/restore semantics
                        ctx.emitter.line(
                            f"{ctx.new_scope_manager_var}.new_var(_ind_var)"
                        )
                    else:
                        # Fallback: simple pop by resolved name
                        ctx.emitter.line("_scope.pop(_ind_var, None)")
            else:
                raise NotImplementedError(
                    "NEW indirection not supported in TRAMPOLINE strategy"
                )
        elif isinstance(var, MSpecialVariable):
            # Spec 013 Phase 12: Handle NEW for special variables ($ETRAP, $ECODE, $ZERROR)
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
                # $ESTACK is typically NEW'd together with $ETRAP
                # For now, treat as no-op since we don't have full stack tracking
                pass
            else:
                raise NotImplementedError(f"NEW ${var.name} not supported")
        else:
            # Regular variable name (string)
            var_name = var
            # For SIMPLE_FUNCTIONS strategy with NewScopeManager, use .new_var()
            # This ensures proper save/restore on function exit
            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                if ctx.new_scope_manager_var:
                    # Use NewScopeManager for proper save/restore semantics
                    ctx.emitter.line(
                        f"{ctx.new_scope_manager_var}.new_var({var_name!r})"
                    )
                else:
                    # Fallback: simple pop (used when no NewScopeManager in context)
                    translated = translate_name(var_name)
                    ctx.emitter.line(f"_scope.pop({translated!r}, None)")
            else:
                # TRAMPOLINE strategy - reset to empty MArray
                translated = translate_name(var_name)
                ctx.emitter.line(f"{translated} = MArray()")


def _generate_merge(stmt: MMergeStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for MERGE command.

    Spec 011 Phase 16: MERGE copies entire variable subtrees.

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

            if src.subscripts:
                subs_code = []
                for sub in src.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                src_subs = f"({', '.join(subs_code)},)"
            else:
                src_subs = "()"

            # Get source tree from global storage
            src_tree_expr = f'_rt.globals.get_tree("{src_name}", {src_subs})'

        elif isinstance(src, NakedGlobal):
            # Source is naked global: ^(subs)
            if src.subscripts:
                subs_code = []
                for sub in src.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                src_subs = f"({', '.join(subs_code)},)"
            else:
                src_subs = "()"

            # Resolve naked then get tree
            ctx.emitter.line(
                f"_naked_name, _naked_subs = _rt.globals.resolve_naked({src_subs})"
            )
            src_tree_expr = "_rt.globals.get_tree(_naked_name, _naked_subs)"

        elif isinstance(src, MVariable):
            # Source is local variable: A or A(subs)
            src_var_name = src.name

            if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
                if src.subscripts:
                    subs_code = []
                    for sub in src.subscripts:
                        subs_code.append(generate_expr(sub, ctx))
                    src_tree_expr = f"_scope.get({src_var_name!r}, MArray())[{', '.join(subs_code)}]"
                else:
                    src_tree_expr = f"_scope.get({src_var_name!r}, MArray())"
            else:
                # TRAMPOLINE strategy
                src_translated = translate_name(src_var_name)
                if src.subscripts:
                    subs_code = []
                    for sub in src.subscripts:
                        subs_code.append(generate_expr(sub, ctx))
                    src_tree_expr = f"{src_translated}[{', '.join(subs_code)}]"
                else:
                    src_tree_expr = src_translated

        elif isinstance(src, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
            # Source is extended global: ^|"env"|name or ^["gld"]name
            # For now, ignore environment and treat as regular global
            src_name = src.name

            if src.subscripts:
                subs_code = []
                for sub in src.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                src_subs = f"({', '.join(subs_code)},)"
            else:
                src_subs = "()"

            src_tree_expr = f'_rt.globals.get_tree("{src_name}", {src_subs})'

        elif isinstance(src, MIndirection):
            # Source is indirection: @VAR or @VAR@(subs)
            # Feature: 018-unified-variable-system (T143e)
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
            # Spec 014 Task C1: MERGE local→global and global→global
            dest_name = dest.name

            if dest.subscripts:
                subs_code = []
                for sub in dest.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                dest_subs = f"({', '.join(subs_code)},)"
            else:
                dest_subs = "()"

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
            if dest.subscripts:
                subs_code = []
                for sub in dest.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                dest_subs = f"({', '.join(subs_code)},)"
            else:
                dest_subs = "()"

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
                dest_translated = translate_name(dest_var_name)
                if dest.subscripts:
                    subs_code = []
                    for sub in dest.subscripts:
                        subs_code.append(generate_expr(sub, ctx))
                    dest_expr = f"{dest_translated}[{', '.join(subs_code)}]"
                else:
                    dest_expr = dest_translated

                ctx.emitter.line(f"_merge_src = {src_tree_expr}")
                ctx.emitter.line("if _merge_src is not None:")
                ctx.emitter.indent()
                ctx.emitter.line(f"{dest_expr}.merge_from(_merge_src)")
                ctx.emitter.dedent()

        elif isinstance(dest, MIndirection):
            # Destination is indirection: @VAR or @VAR@(subs)
            # Feature: 018-unified-variable-system (T143e)
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
            # For now, ignore environment and treat as regular global
            # (m2py uses single global namespace)
            dest_name = dest.name

            if dest.subscripts:
                subs_code = []
                for sub in dest.subscripts:
                    subs_code.append(f"str({generate_expr(sub, ctx)})")
                dest_subs = f"({', '.join(subs_code)},)"
            else:
                dest_subs = "()"

            ctx.emitter.line(f"_merge_src = {src_tree_expr}")
            ctx.emitter.line("if _merge_src is not None:")
            ctx.emitter.indent()
            ctx.emitter.line(
                f'_rt.globals.merge_tree("{dest_name}", {dest_subs}, _merge_src)'
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

    Handles basic reads, timeout reads, char reads, and indirection targets.
    For SIMPLE_FUNCTIONS strategy, stores into _scope dictionary.
    For indirection targets, uses _rt.set_var() for runtime name resolution.

    Args:
        target: MReadTarget with variable and optional timeout
        ctx: Generator context
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.codegen.indirection import generate_name_indirection_write

    if target.variable is None:
        return

    # Check if target is indirection - needs special handling with set_indirected
    is_indirection = isinstance(target.variable, MIndirectionType)

    if is_indirection:
        # Spec 018 (T041): Indirection target: R @A - uses unified set_indirected
        # Type narrowing: we know target.variable is MIndirection from is_indirection check
        ind_var = cast(MIndirectionType, target.variable)
        if target.timeout is not None:
            # Timeout read with indirection: R @A:n
            timeout_expr = generate_expr(target.timeout, ctx)
            ctx.emitter.line(f"_read_val, _test = m_read_timeout({timeout_expr})")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        elif target.is_char_read:
            # Single character read with indirection: R *@A
            ctx.emitter.line("_read_val = m_read_char()")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        else:
            # Basic read with indirection: R @A
            ctx.emitter.line("_read_val = input()")
            set_stmt = generate_name_indirection_write(ind_var, "_read_val", ctx)
            ctx.emitter.line(set_stmt)
        return

    # Get the target variable name and determine storage location
    if isinstance(target.variable, MVariable):
        var_name = translate_name(target.variable.name)
        # Determine how to store the variable based on strategy
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Spec 011 Phase 20: Store in _scope dictionary like SET does
            storage_target = f"_scope.setdefault({var_name!r}, MArray()).value"
        elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
            storage_target = f"state.{var_name}"
        else:
            storage_target = var_name
    else:
        # Could be array subscript or global - generate expression
        storage_target = generate_expr(target.variable, ctx)

    if target.timeout is not None:
        # Timeout read: R X:n
        timeout_expr = generate_expr(target.timeout, ctx)
        # Use runtime helper for timeout read - returns (value, test_flag)
        if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Need to unpack properly for scope storage
            ctx.emitter.line(f"_read_val, _test = m_read_timeout({timeout_expr})")
            ctx.emitter.line(f"{storage_target} = _read_val")
        else:
            ctx.emitter.line(
                f"{storage_target}, _test = m_read_timeout({timeout_expr})"
            )
    elif target.is_char_read:
        # Single character read: R *X
        ctx.emitter.line(f"{storage_target} = m_read_char()")
    else:
        # Basic read: R X
        ctx.emitter.line(f"{storage_target} = input()")


# =============================================================================
# Transaction Statement Generation (Spec 013 Phase 8)
# =============================================================================


def _generate_tstart(stmt: MTStartStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for TSTART command.

    Spec 013 FR-015: Begin transaction via database abstraction.

    MUMPS: TS, TSTART, TS (), TS (A,B), TS ():serial

    Generated: _rt.globals.transaction_start()

    Note: Restart variables (A,B) and restart_all (*) require transaction
    restart infrastructure that is not yet implemented.

    Args:
        stmt: MTStartStatement node
        ctx: Generator context

    Raises:
        NotImplementedError: If restart_vars or restart_all is specified
    """
    # Check for restart variables or restart_all - these require infrastructure
    # for saving and restoring variable state on TRESTART which is not implemented
    if stmt.restart_vars or stmt.restart_all:
        if stmt.restart_all:
            raise NotImplementedError(
                "TSTART (*) restart variables not implemented - "
                "transaction restart infrastructure required"
            )
        else:
            # restart_vars contains MVariable instances (which have .name)
            # Use getattr for type safety since the type annotation is MExpr
            var_names = ", ".join(getattr(v, "name", str(v)) for v in stmt.restart_vars)
            raise NotImplementedError(
                f"TSTART ({var_names}) restart variables not implemented - "
                "transaction restart infrastructure required"
            )

    # Basic implementation - call transaction_start on global storage
    ctx.emitter.line("_rt.globals.transaction_start()")


def _generate_tcommit(stmt: MTCommitStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for TCOMMIT command.

    Spec 013 FR-015: Commit transaction via database abstraction.

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


def _generate_trollback(stmt: MTRollbackStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for TROLLBACK command.

    Spec 013 FR-015: Rollback transaction via database abstraction.

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

    # Basic implementation - roll back entire transaction
    ctx.emitter.line("_rt.globals.transaction_rollback()")


# =============================================================================
# LOCK Statement Generation (Spec 013 Phase 9)
# =============================================================================


def _generate_lock(stmt: MLockStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for LOCK command.

    Spec 013 FR-019: LOCK command via database abstraction.

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
    # This happens BEFORE any locks are acquired
    if stmt_lock_type == "":
        ctx.emitter.line("_rt.globals.unlock_all()")

    # Process each target
    for target_dict in stmt.targets:
        # Extract target info from dict
        # target_dict keys: lockop, target, timeout, is_indirect, indirection, indirection_levels

        # Get lock operation from target (overrides stmt-level if present)
        target_lockop = target_dict.get("lockop", "")
        # Use target lockop if present, otherwise use stmt-level
        lock_type = target_lockop if target_lockop else stmt_lock_type
        # For exclusive lock, use "+" since we already released all above
        if lock_type == "":
            lock_type = "+"

        # Handle indirection
        if target_dict.get("is_indirect"):
            # Indirection - need runtime resolution
            # For now, emit a comment about unsupported feature
            ctx.emitter.line("# LOCK indirection not yet supported")
            continue

        # Get the target (global or local variable)
        target = target_dict.get("target")
        if target is None:
            continue

        # Extract name and subscripts from target
        # target can be GlobalVariable, NakedGlobal, or MVariable
        from m2py.parser.textx_classes import GlobalVariable as GV
        from m2py.parser.textx_classes import NakedGlobal as NG

        if isinstance(target, GV):
            name = target.name
            subscripts = target.subscripts
        elif isinstance(target, NG):
            # Naked global - YDB does not support naked reference in LOCK
            # Error: %YDB-E-LKNAMEXPECTED, An identifier is expected after a ^
            raise NotImplementedError(
                "Naked reference not supported in LOCK (YDB restriction: LKNAMEXPECTED)"
            )
        else:
            # Local variable as lock name
            name = getattr(target, "name", str(target))
            subscripts = getattr(target, "subscripts", [])

        # Generate subscript expressions
        subs_exprs = []
        for sub in subscripts:
            subs_exprs.append(generate_expr(sub, ctx))

        # Build the subscripts tuple string
        if subs_exprs:
            subs_str = f"({', '.join(subs_exprs)},)"
        else:
            subs_str = "()"

        # Get timeout from target dict
        timeout_expr = target_dict.get("timeout")

        # For parenthesized lists, timeout may be on the statement
        if timeout_expr is None and stmt.timeout is not None:
            timeout_expr = stmt.timeout

        # Generate lock call
        if timeout_expr is not None:
            # Timed lock - sets $TEST
            timeout_val = generate_expr(timeout_expr, ctx)
            if lock_type == "-":
                # LOCK -name:timeout always sets $TEST to 1
                ctx.emitter.line(
                    f'_rt.globals.lock("{name}", {subs_str}, lock_type="-")'
                )
                ctx.emitter.line("_test = True")
            else:
                # LOCK +name:timeout sets $TEST based on success/timeout
                ctx.emitter.line(
                    f'_test = _rt.globals.lock("{name}", {subs_str}, '
                    f'timeout={timeout_val}, lock_type="{lock_type}")'
                )
        else:
            # Untimed lock - does NOT modify $TEST
            ctx.emitter.line(
                f'_rt.globals.lock("{name}", {subs_str}, lock_type="{lock_type}")'
            )


# =============================================================================
# I/O Statement Generation (Spec 013 Phase 10)
# =============================================================================


def _generate_open(stmt: MOpenStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for OPEN command.

    Spec 013 Phase 10 (T091, T093): Opens devices/files for I/O.

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
        else:
            # Untimed OPEN - does NOT modify $TEST
            ctx.emitter.line(f"_rt.open_device({device_name}, {params_str})")


def _generate_close(stmt: MCloseStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for CLOSE command.

    Spec 013 Phase 10 (T092): Closes devices/files.

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

    Spec 013 Phase 10 (T089-T090): Switches current I/O device.

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

    Spec 012 Phase 4 (T024-T027): Handle XECUTE with constant strings.
    For constant string XECUTE, inline the generated Python code at transpile
    time for better performance and debuggability.

    Spec 012 Phase 5 (T032-T037): Handle XECUTE with dynamic code via runtime.
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
    from m2py.analysis.semantic_analyzer import analyze_command
    from m2py.parser.line_parser import parse_commands_from_line

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

        T075o: Handle FOR/IF/ELSE body nesting in inline XECUTE.
        MUMPS commands after FOR/IF/ELSE on the same line are the body
        of that control flow statement. We must structure the flat command
        list into proper nesting before code generation.
        """
        from m2py.parser.parser import _structure_commands_with_bodies

        # Parse the MUMPS code string
        commands = parse_commands_from_line(mumps_code)
        if isinstance(commands, MParseError):
            # T067: Include original code in error message for context
            # Emit a runtime error for parse failures in constant strings
            # This shouldn't happen in well-formed code but we handle it gracefully
            escaped_code = mumps_code.replace('"', '\\"')
            ctx.emitter.line(
                f"raise SyntaxError(\"XECUTE parse error in '{escaped_code}': {commands.message}\")"
            )
            return

        if not commands:
            # Empty string - no-op
            return

        # Convert textX commands to ASG statements
        asg_statements = []
        for textx_cmd in commands:
            asg_stmt = analyze_command(textx_cmd, None)
            if asg_stmt is not None:
                asg_statements.append(asg_stmt)

        # T075o: Structure flat list into proper FOR/IF/ELSE nesting
        structured_statements = _structure_commands_with_bodies(asg_statements)

        # Generate Python for each structured statement
        for asg_stmt in structured_statements:
            generate_statement(asg_stmt, ctx)

    def generate_inline_with_control_flow(code_strings: list) -> None:
        """Generate inline XECUTE code that contains GOTO/DO.

        T075m: GOTO/DO inside inline XECUTE needs special handling.
        We wrap the inline code in a try/except block and use _XecuteExit
        exception to exit just the XECUTE context without returning from
        the enclosing function.

        T075s: Each XECUTE argument has its own control flow scope.
        QUIT in one argument should not skip subsequent arguments.
        Generate a separate try/except for each code string.
        """
        # Set flag so GOTO/DO generate raise _XecuteExit instead of return
        old_in_inline_xecute = ctx.in_inline_xecute
        ctx.in_inline_xecute = True

        # T075s: Each code string gets its own try/except
        for code_str in code_strings:
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                generate_inline_code(code_str)
            ctx.emitter.line("except _XecuteExit:")
            with ctx.emitter.indented():
                ctx.emitter.line("pass  # GOTO/DO exited XECUTE block")

        ctx.in_inline_xecute = old_in_inline_xecute

    def generate_dynamic_xecute() -> None:
        """Generate runtime calls for dynamic XECUTE expressions.

        Spec 012 Phase 5 (T032-T034): Each code expression is evaluated
        at runtime and executed via _rt.execute_mumps() with shared _scope.

        Spec 012 Phase 6 (T038): XECUTE does NOT stack $TEST.
        After execute_mumps(), sync _test from _rt._test so mutations
        made by XECUTEd code are visible to caller.

        T075p: Pass globals() to execute_mumps so it can access module labels
        for DO/GOTO commands in dynamic XECUTE.

        T075q: Handle per-argument postconditions.

        XECUTE argument indirection: X @X where X="Y,Z" should:
        1. Resolve @X → "Y,Z"
        2. Split into ["Y", "Z"]
        3. For each: resolve @Y → code1, @Z → code2
        4. Execute each code string
        """
        from m2py.asg.expressions import MIndirection
        from m2py.codegen.indirection import (
            _count_indirection_levels_with_subscripts,
            _get_scope_expr,
        )

        # T075q: Use arguments structure (always populated by semantic analyzer)
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
                scope_expr = _get_scope_expr(ctx)

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
                    else:
                        ctx.emitter.line(
                            f"_rt.execute_mumps({expr_code}, _scope, globals())"
                        )
                        ctx.emitter.line("_test = _rt._test")
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
                else:
                    ctx.emitter.line(
                        f"_rt.execute_mumps_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg}, caller_globals=globals())"
                    )
                    ctx.emitter.line("_test = _rt._test")
            else:
                # Regular expression (variable, string, function call, etc.)
                expr_code = generate_expr(xecute_arg.expression, ctx)
                if xecute_arg.postcondition is not None:
                    # T075q: Wrap in postcondition check
                    cond_code = generate_expr(xecute_arg.postcondition, ctx)
                    ctx.emitter.line(f"if m_truth({cond_code}):")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f"_rt.execute_mumps({expr_code}, _scope, globals())"
                        )
                        ctx.emitter.line("_test = _rt._test")
                else:
                    ctx.emitter.line(
                        f"_rt.execute_mumps({expr_code}, _scope, globals())"
                    )
                    ctx.emitter.line("_test = _rt._test")

    # Check if any constant strings contain control flow
    has_control_flow = False
    if stmt.is_constant:
        for code_str in stmt.constant_values:
            if contains_control_flow(code_str):
                has_control_flow = True
                break

    # T075r: Check if any argument has a postcondition (per-argument postcond)
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
                # T075r: Per-argument postconditions - must process each individually
                _generate_xecute_args_with_postconds(
                    stmt,
                    ctx,
                    has_control_flow,
                    generate_inline_code,
                    generate_inline_with_control_flow,
                    contains_control_flow,
                )
            elif stmt.is_constant:
                # Phase 4: Inline constant strings
                if has_control_flow:
                    generate_inline_with_control_flow(stmt.constant_values)
                else:
                    for code_str in stmt.constant_values:
                        generate_inline_code(code_str)
            else:
                # Phase 5: Dynamic XECUTE - call runtime
                generate_dynamic_xecute()
    else:
        # No statement-level postcondition - generate code directly
        if has_arg_postconditions:
            # T075r: Per-argument postconditions - must process each individually
            _generate_xecute_args_with_postconds(
                stmt,
                ctx,
                has_control_flow,
                generate_inline_code,
                generate_inline_with_control_flow,
                contains_control_flow,
            )
        elif stmt.is_constant:
            # Phase 4: Inline constant strings
            if has_control_flow:
                generate_inline_with_control_flow(stmt.constant_values)
            else:
                for code_str in stmt.constant_values:
                    generate_inline_code(code_str)
        else:
            # Phase 5: Dynamic XECUTE - call runtime
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

    T075r: When XECUTE has arguments with postconditions like:
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


def _generate_job(stmt: MJobStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for JOB command.

    Spec 013 Phase 11 (T095-T097): Starts a new process executing a routine.

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
        params_parts = []
        for param in job_target.processparameters:
            param_expr = generate_expr(param, ctx)
            params_parts.append(param_expr)
        params_str = f"[{', '.join(params_parts)}]" if params_parts else "None"

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
        else:
            # Without timeout: just call start_job, don't modify $TEST
            ctx.emitter.line(
                f"_rt.start_job({label_name}, {routine_name}, {args_str}, "
                f"{params_str}, {timeout_expr})"
            )


def _generate_indirect_job(job_target: "MJobTarget", ctx: "GeneratorContext") -> None:
    """Generate Python code for indirect JOB (J @TARGET).

    Spec 015 Phase 5 (T027-T031): Generate runtime dispatch for indirect JOB.
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
    params_parts = []
    for param in job_target.processparameters:
        param_expr = generate_expr(param, ctx)
        params_parts.append(param_expr)
    params_str = f"[{', '.join(params_parts)}]" if params_parts else "None"

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
    else:
        ctx.emitter.line(
            f"_rt.start_job(_call_target.label, _call_target.routine, "
            f"{args_str}, {params_str}, {timeout_expr})"
        )


def _generate_view(stmt: MViewStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for VIEW command.

    Spec 013 Phase 17 (T123): VIEW is implementation-specific.

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

    Spec 013 Phase 17 (T125): BREAK enters debugger.

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
# Z-Commands (Phase 19)
# =============================================================================


def _generate_zwrite(stmt: MZWriteStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZWRITE command.

    Spec 013 Phase 19 (T132-T134): ZWRITE displays variables with names.

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
                if target.subscripts:
                    # Filter out wildcard subscripts (*, ranges)
                    # When * is encountered, stop - it means "show all descendants"
                    concrete_subs = []
                    for s in target.subscripts:
                        if isinstance(s, MZWriteSubscriptAll):
                            # * means all descendants from this point - stop here
                            break
                        elif isinstance(s, MZWriteSubscriptRange):
                            # TODO: Range support would need runtime filtering
                            # For now treat like * (show all)
                            break
                        else:
                            concrete_subs.append(f"str({generate_expr(s, ctx)})")
                    if concrete_subs:
                        subs = ", ".join(concrete_subs)
                        ctx.emitter.line(f"_rt.zwrite_global('{name}', ({subs},))")
                    else:
                        ctx.emitter.line(f"_rt.zwrite_global('{name}', ())")
                else:
                    ctx.emitter.line(f"_rt.zwrite_global('{name}', ())")
            elif isinstance(target, (LocalVariable, ZWriteLocal)):
                # Local variable: ZW X or ZW X(subs)
                name = target.name
                if target.subscripts:
                    # Filter out wildcard subscripts (*, ranges)
                    concrete_subs = []
                    for s in target.subscripts:
                        if isinstance(s, MZWriteSubscriptAll):
                            break
                        elif isinstance(s, MZWriteSubscriptRange):
                            break
                        else:
                            concrete_subs.append(f"str({generate_expr(s, ctx)})")
                    if concrete_subs:
                        subs = ", ".join(concrete_subs)
                        ctx.emitter.line(
                            f"_rt.zwrite_local('{name}', ({subs},), _scope)"
                        )
                    else:
                        ctx.emitter.line(f"_rt.zwrite_local('{name}', (), _scope)")
                else:
                    ctx.emitter.line(f"_rt.zwrite_local('{name}', (), _scope)")
            else:
                # Fallback - generate expression and try to write it
                ctx.emitter.line(f"pass  # ZWRITE {generate_expr(target, ctx)}")


def _generate_zkill(
    stmt: "MZKillStatement | MZWithdrawStatement", ctx: "GeneratorContext"
) -> None:
    """Generate Python code for ZKILL/ZWITHDRAW command.

    Spec 013 Phase 19 (T135-T136): ZKILL removes node value but preserves descendants.

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

    Spec 013 Phase 19 (T137-T139): ZLINK dynamically links/loads a routine.

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


def _generate_zshow(stmt: MZShowStatement, ctx: "GeneratorContext") -> None:
    """Generate Python code for ZSHOW command.

    Spec 013 Phase 19 (T140-T142): ZSHOW displays system information.

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

    Spec 013 Phase 19 (T143-T145): ZGOTO unwinds stack to specified level.

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

    Spec 013 Phase 19 (T146-T147): ZHALT terminates with exit status.

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


__all__ = [
    "generate_statement",
    "generate_scope_statements",
    "ForGenContext",
    "GotoGenContext",
    "_generate_call_arguments",
]
