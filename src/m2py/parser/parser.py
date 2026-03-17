"""MUMPS Parser implementation using textX.

Provides the MUMPSParser class that parses MUMPS source code and
produces an Abstract Semantic Graph (ASG).
"""

from pathlib import Path
from typing import List, Optional, Union

from textx import metamodel_from_file
from textx.exceptions import TextXSyntaxError

from m2py.parser.line_parser import (
    extract_comment,
    parse_commands_from_line,
    parse_line_content,
)
from m2py.analysis.for_analysis import analyze_for_loops as _analyze_for_loops
from m2py.analysis.for_analysis import analyze_quit_context as _analyze_quit_context
from m2py.analysis.goto_analysis import classify_gotos as _classify_gotos
from m2py.analysis.resolver import resolve_references as _resolve_references
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.analysis.variables import (
    FunctionSignature,
    ScopeVariables,
    analyze_variables as _analyze_variables,
    compute_transitive_inputs as _compute_transitive_inputs,
)
from m2py.asg import MLabel, MRoutine, MScope, MParseError
from m2py.asg.statements import (
    MDoStatement,
    MElseStatement,
    MForStatement,
    MIfStatement,
    MParseErrorStatement,
    MStatement,
)
from m2py.asg.type_helpers import get_body_scope
from m2py.parser.exceptions import MUMPSSyntaxError


def _set_line_number_recursive(stmt: MStatement, line_number: int) -> None:
    """Set line_number on a statement and all its nested statements.

    This ensures that statements inside IF/FOR/ELSE blocks have the same
    line_number as their parent, which is needed for GOTO analysis.

    Args:
        stmt: The statement to set line_number on
        line_number: The source line number
    """
    stmt.line_number = line_number

    # Recursively set on nested scopes (using getattr since scope attributes are optional)
    then_scope = getattr(stmt, "then_scope", None)
    if then_scope is not None:
        for child in then_scope.statements:
            _set_line_number_recursive(child, line_number)

    body = getattr(stmt, "body", None)
    if body is not None:
        for child in body.statements:
            _set_line_number_recursive(child, line_number)

    else_scope = getattr(stmt, "else_scope", None)
    if else_scope is not None:
        for child in else_scope.statements:
            _set_line_number_recursive(child, line_number)


def _structure_commands_with_bodies(statements: List[MStatement]) -> List[MStatement]:
    """Structure a flat list of statements into proper control flow nesting.

    In MUMPS, commands following FOR/IF/ELSE on the same line are the body
    of that control flow statement. This function reorganizes a flat list
    of statements to properly nest them.

    For example: [FOR, SET, WRITE] becomes [FOR(body=[SET, WRITE])]

    Handles nested control flow recursively:
    [FOR, FOR, SET] becomes [FOR(body=[FOR(body=[SET])])]

    Args:
        statements: Flat list of parsed statements

    Returns:
        List with proper control flow nesting
    """
    result = []
    i = 0

    while i < len(statements):
        stmt = statements[i]

        # Check if this is a control flow statement that captures remaining line
        if isinstance(stmt, MForStatement):
            # FOR captures all remaining statements as its body (recursively)
            remaining = statements[i + 1 :]
            if remaining:
                # Recursively structure the remaining statements
                stmt.body.statements = _structure_commands_with_bodies(remaining)
                for child in stmt.body.statements:
                    child.scope = stmt.body
            result.append(stmt)
            break  # FOR consumed all remaining statements

        elif isinstance(stmt, MIfStatement):
            # IF captures all remaining statements as its then_scope (recursively)
            remaining = statements[i + 1 :]
            if remaining:
                stmt.then_scope.statements = _structure_commands_with_bodies(remaining)
                for child in stmt.then_scope.statements:
                    child.scope = stmt.then_scope
            result.append(stmt)
            break  # IF consumed all remaining statements

        elif isinstance(stmt, MElseStatement):
            # ELSE captures all remaining statements as its body (recursively)
            remaining = statements[i + 1 :]
            if remaining:
                stmt.body.statements = _structure_commands_with_bodies(remaining)
                for child in stmt.body.statements:
                    child.scope = stmt.body
            result.append(stmt)
            break  # ELSE consumed all remaining statements

        else:
            # Regular statement, add to result and continue
            result.append(stmt)
            i += 1

    return result


def _find_argumentless_do_for_dot_lines(stmt: MStatement) -> Optional[MDoStatement]:
    """Find an argumentless DO that should capture following dot-lines.

    In MUMPS, dot-indented lines following a line with an argumentless DO
    belong to that DO's block, regardless of what commands follow the DO
    on the same line.

    For example, in:
        F  D  Q:X=0
        . S X=X-1

    The dot line belongs to the D, not the Q. The execution order is:
    1. FOR loops
    2. D executes the dot block (increasing execution level)
    3. Q:X=0 is checked after D returns

    This function searches for an argumentless DO that doesn't yet have
    any body statements (i.e., hasn't been given its dot-lines yet).

    Args:
        stmt: Statement to search

    Returns:
        An argumentless DO without body statements, or None
    """
    # For a FOR statement, search all body statements for an argumentless DO
    if isinstance(stmt, MForStatement) and stmt.body and stmt.body.statements:
        for body_stmt in stmt.body.statements:
            # Check if this statement itself is an argumentless DO without body
            if (
                isinstance(body_stmt, MDoStatement)
                and not body_stmt.targets
                and not body_stmt.body.statements
            ):
                return body_stmt
            # Recursively check nested structures
            nested = _find_argumentless_do_for_dot_lines(body_stmt)
            if nested:
                return nested

    # For IF statement, check then_scope
    if (
        isinstance(stmt, MIfStatement)
        and stmt.then_scope
        and stmt.then_scope.statements
    ):
        for body_stmt in stmt.then_scope.statements:
            if (
                isinstance(body_stmt, MDoStatement)
                and not body_stmt.targets
                and not body_stmt.body.statements
            ):
                return body_stmt
            nested = _find_argumentless_do_for_dot_lines(body_stmt)
            if nested:
                return nested

    # For ELSE statement, check body
    if isinstance(stmt, MElseStatement) and stmt.body and stmt.body.statements:
        for body_stmt in stmt.body.statements:
            if (
                isinstance(body_stmt, MDoStatement)
                and not body_stmt.targets
                and not body_stmt.body.statements
            ):
                return body_stmt
            nested = _find_argumentless_do_for_dot_lines(body_stmt)
            if nested:
                return nested

    # Direct check for argumentless DO without body
    if isinstance(stmt, MDoStatement) and not stmt.targets and not stmt.body.statements:
        return stmt

    return None


def _structure_do_blocks(statements: List[MStatement]) -> List[MStatement]:
    """Collect dot-indented lines into argumentless DO block bodies.

    In MUMPS, an argumentless DO starts a block, and following lines
    with dot prefixes belong to that block:

    D
    . S X=1  ; dot_level=1, belongs to DO
    . W X    ; dot_level=1, belongs to DO
    S Y=2    ; dot_level=0, outside DO

    Also handles DO inside control flow:

    I cond D
    . S X=1  ; belongs to the DO inside IF

    This function processes statements that have _dot_level markers
    and restructures them so dot-indented lines are inside the DO body.

    Args:
        statements: List of statements with _dot_level markers

    Returns:
        List with DO blocks properly nested
    """
    result = []
    i = 0

    while i < len(statements):
        stmt = statements[i]

        # Check if this is an argumentless DO (block start) at this level
        if isinstance(stmt, MDoStatement) and not stmt.targets:
            # Find all following statements with dot_level > 0
            block_stmts = []
            post_do_same_line = []  # Same-line statements after the DO
            j = i + 1

            # When a MUMPS line has: DO  S V=V_$Q Q V
            # followed by: .S V=V_$Q
            # The parser produces same-line statements (S V=V_$Q, Q V) between
            # the argumentless DO and its dot-body. Skip past them to find the
            # dot-body, then re-insert them after the DO in the output.
            do_line = getattr(stmt, "line_number", None)
            while j < len(statements):
                next_stmt = statements[j]
                dot_level = getattr(next_stmt, "_dot_level", 0)
                next_line = getattr(next_stmt, "line_number", None)
                if dot_level == 0 and next_line == do_line:
                    post_do_same_line.append(next_stmt)
                    j += 1
                else:
                    break

            while j < len(statements):
                next_stmt = statements[j]
                dot_level = getattr(next_stmt, "_dot_level", 0)

                if dot_level > 0:
                    # This statement belongs to the DO block
                    # Decrement dot level (in case of nested DO blocks)
                    if dot_level == 1:
                        delattr(next_stmt, "_dot_level")
                    else:
                        next_stmt._dot_level = dot_level - 1
                    block_stmts.append(next_stmt)
                    j += 1
                else:
                    # Not part of DO block
                    break

            # Add collected statements to DO body
            if block_stmts:
                # Recursively process for nested DO blocks
                stmt.body.statements = _structure_do_blocks(block_stmts)
                for child in stmt.body.statements:
                    child.scope = stmt.body
                # Mark this as an inline block now that it has body statements
                stmt.is_inline_block = True

                # MUMPS: all argumentless DOs on the same line share the
                # same dot-block.  E.g. ``D  F …  D`` — the trailing D
                # inside the FOR must execute the same block as the leading D.
                for pds in post_do_same_line:
                    nested_do = _find_argumentless_do_for_dot_lines(pds)
                    if nested_do:
                        nested_do.body.statements = list(stmt.body.statements)
                        for child in nested_do.body.statements:
                            child.scope = nested_do.body
                        nested_do.is_inline_block = True

            result.append(stmt)
            # Re-insert same-line post-DO statements after the DO block
            result.extend(post_do_same_line)
            i = j  # Skip past the block statements

        else:
            # Check if there are following dot-level statements that need
            # to be attached to an argumentless DO nested inside this statement
            j = i + 1
            block_stmts = []

            while j < len(statements):
                next_stmt = statements[j]
                dot_level = getattr(next_stmt, "_dot_level", 0)
                if dot_level > 0:
                    if dot_level == 1:
                        delattr(next_stmt, "_dot_level")
                    else:
                        next_stmt._dot_level = dot_level - 1
                    block_stmts.append(next_stmt)
                    j += 1
                else:
                    break

            if block_stmts:
                # Find the argumentless DO inside this statement's nested scopes
                target_do = _find_argumentless_do_for_dot_lines(stmt)
                if target_do:
                    # Attach the dot-statements to this DO's body
                    target_do.body.statements = _structure_do_blocks(block_stmts)
                    for child in target_do.body.statements:
                        child.scope = target_do.body
                    # Mark this as an inline block now that it has body statements
                    target_do.is_inline_block = True
                    result.append(stmt)
                    i = j  # Skip past the block statements
                else:
                    # No owning DO found. Per MUMPS spec (1995 ANSI section 6.3):
                    # "Lines which have a LEVEL greater than the current execution
                    # level are ignored, i.e., not executed."
                    # Mark orphaned dot-lines as unreachable but preserve them in ASG.
                    result.append(stmt)
                    for orphan in block_stmts:
                        orphan.is_unreachable = True
                        result.append(orphan)
                    i = j  # Skip past the orphaned statements
            else:
                result.append(stmt)
                i += 1

    return result


def _mark_unreachable_statements(statements: List[MStatement]) -> None:
    """Mark statements after unconditional QUIT/GOTO as unreachable.

    In MUMPS, statements after an unconditional QUIT, GOTO, or HALT cannot
    be reached. This function sets is_unreachable=True on those statements
    for downstream analysis. Statements on the same line after an
    unconditional exit are already separate ASG nodes, so they are marked
    the same way as cross-line unreachable statements.

    Args:
        statements: List of statements to analyze (modified in place)
    """
    from m2py.asg.statements import MQuitStatement, MGotoStatement, MHaltStatement

    unreachable = False

    for stmt in statements:
        if unreachable:
            stmt.is_unreachable = True

        # Check if this statement is an unconditional exit
        if isinstance(stmt, (MQuitStatement, MGotoStatement, MHaltStatement)):
            # Unconditional = no postcondition on the statement itself
            if stmt.postcondition is None:
                # For GOTO, also check target-level postconditions.
                # G N:A="" has stmt.postcondition=None but target.postcondition set.
                # If ALL targets have postconditions, the GOTO is effectively
                # conditional (none of the conditions may be true) and execution
                # can fall through to the next statement.
                if (
                    isinstance(stmt, MGotoStatement)
                    and stmt.targets
                    and all(t.postcondition is not None for t in stmt.targets)
                ):
                    pass  # Effectively conditional — don't mark unreachable
                else:
                    unreachable = True

        # Recursively check nested scopes (FOR body, IF then_scope, etc.)
        # But don't propagate unreachable flag INTO nested scopes - each scope
        # has its own control flow
        if isinstance(stmt, MForStatement) and stmt.body and stmt.body.statements:
            _mark_unreachable_statements(stmt.body.statements)
        if (
            isinstance(stmt, MIfStatement)
            and stmt.then_scope
            and stmt.then_scope.statements
        ):
            _mark_unreachable_statements(stmt.then_scope.statements)
        if isinstance(stmt, MElseStatement) and stmt.body and stmt.body.statements:
            _mark_unreachable_statements(stmt.body.statements)
        if isinstance(stmt, MDoStatement) and stmt.body and stmt.body.statements:
            _mark_unreachable_statements(stmt.body.statements)
        # Generic catch using type helper
        body = get_body_scope(stmt)
        if (
            body is not None
            and body.statements
            and not isinstance(
                stmt, (MForStatement, MIfStatement, MElseStatement, MDoStatement)
            )
        ):
            _mark_unreachable_statements(body.statements)


class MUMPSParser:
    """Parser for MUMPS source code.

    Uses textX to parse MUMPS source and produce an ASG representation.
    The parser performs:
    1. Lexical and syntactic analysis via textX grammar
    2. ASG construction with proper parent/child relationships
    3. Source location tracking for error reporting

    Usage:
        parser = MUMPSParser()
        routine = parser.parse(source_code)
        # or
        routine = parser.parse_file("routine.m")
    """

    def __init__(self):
        """Initialize the parser with the MUMPS grammar.

        Loads the textX grammar file and prepares the metamodel
        for parsing MUMPS source code.
        """
        # Locate the grammar file relative to this module
        grammar_dir = Path(__file__).parent.parent / "grammar"
        grammar_file = grammar_dir / "mumps.tx"

        if not grammar_file.exists():
            raise FileNotFoundError(f"Grammar file not found: {grammar_file}")

        # Create the textX metamodel.
        # skipws=False because MUMPS is whitespace-sensitive (tabs separate
        # labels from commands, spaces separate arguments).
        # classes=[] because this parser only handles routine structure
        # (labels, lines); line content is parsed separately by line_parser.py
        # with its own custom classes. See docs/architecture.md.
        self._metamodel = metamodel_from_file(
            str(grammar_file),
            classes=[],
            skipws=False,  # Don't auto-skip whitespace
        )

        # Track source file for error reporting
        self._current_file: Optional[str] = None

    def parse(
        self,
        source: str,
        filename: Optional[str] = None,
        analyze_variables: bool = False,
        compute_signatures: bool = False,
    ) -> MRoutine:
        """Parse MUMPS source code and return an ASG.

        Args:
            source: The MUMPS source code to parse
            filename: Optional filename for error reporting
            analyze_variables: If True, run variable analysis after parsing
                to populate input_variables, output_variables, etc. on labels
            compute_signatures: If True, compute function signatures for each
                label (implies analyze_variables=True)

        Returns:
            An MRoutine containing the parsed ASG

        Raises:
            MUMPSSyntaxError: If the source contains syntax errors
        """
        self._current_file = filename

        # Normalize source: ensure it ends with a newline
        # MUMPS files should end with a newline, but many editors/sources omit it
        if source and not source.endswith("\n"):
            source = source + "\n"

        try:
            # Parse using textX
            model = self._metamodel.model_from_str(source)

            # Convert textX model to our ASG
            routine = self._build_routine(model, filename)

            # Populate source_lines for $TEXT function support
            routine.source_lines = source.splitlines()

            # Run optional analysis passes
            # resolve_references must be called before analyze_variables with
            # compute_transitive=True, because transitive closure needs resolved
            # call targets to build the call graph
            label_vars = None
            if compute_signatures or analyze_variables:
                self.resolve_references(routine)
                label_vars = self.analyze_variables(routine, compute_transitive=True)
            if compute_signatures:
                from ..analysis.variables import compute_all_signatures

                compute_all_signatures(routine, label_vars)

            return routine

        except TextXSyntaxError as e:
            # Extract line/column from textX exception for better error reporting
            raise MUMPSSyntaxError(
                message=str(e),
                line=e.line,
                column=e.col,
                source_file=filename,
            ) from e
        except Exception as e:
            # Convert other exceptions to our exception type
            raise MUMPSSyntaxError(
                message=str(e),
                source_file=filename,
            ) from e

    def parse_file(
        self,
        filepath: Union[str, Path],
        analyze_variables: bool = False,
        compute_signatures: bool = False,
    ) -> MRoutine:
        """Parse a MUMPS source file and return an ASG.

        Args:
            filepath: Path to the .m file to parse
            analyze_variables: If True, run variable analysis after parsing
                to populate input_variables, output_variables, etc. on labels
            compute_signatures: If True, compute function signatures for each
                label (implies analyze_variables=True)

        Returns:
            An MRoutine containing the parsed ASG

        Raises:
            FileNotFoundError: If the file does not exist
            MUMPSSyntaxError: If the file contains syntax errors
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"MUMPS source file not found: {filepath}")

        # Try UTF-8 first, then fall back to Latin-1 for legacy VistA files
        # Some VistA files contain Latin-1/CP1252 encoded characters (°, ö, §, ÷)
        # that fail to decode as UTF-8. Latin-1 is a superset that handles all bytes.
        try:
            source = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = filepath.read_text(encoding="latin-1")

        # Ensure source ends with newline for proper parsing of last line
        if source and not source.endswith("\n"):
            source += "\n"

        routine_name = filepath.stem  # Use filename without extension as routine name

        routine = self.parse(source, filename=str(filepath))
        routine.name = routine_name
        routine.source_file = str(filepath)

        # Run optional analysis passes after name/source_file are set
        label_vars = None
        if compute_signatures or analyze_variables:
            self.resolve_references(routine)
            label_vars = self.analyze_variables(routine, compute_transitive=True)
        if compute_signatures:
            from ..analysis.variables import compute_all_signatures

            compute_all_signatures(routine, label_vars)

        # Store original source lines for $TEXT function support
        routine.source_lines = source.splitlines()

        return routine

    def _build_routine(self, model, filename: Optional[str]) -> MRoutine:
        """Convert textX parse model to MRoutine ASG.

        Transforms the raw textX parse tree into an Abstract Semantic Graph,
        processing LabelLines (named entry points), ContLines (continuation
        lines), and creating a synthetic preamble label for any lines that
        appear before the first named label.

        Parse errors are collected in routine.parse_errors for error-tolerant
        parsing. Lines that fail to parse are skipped but reported.

        Args:
            model: The textX parse model
            filename: Source filename for location tracking

        Returns:
            An MRoutine ASG node
        """
        routine = MRoutine(source_file=filename)

        # Track current label for continuation line association
        current_label: Optional[MLabel] = None

        # Synthetic preamble label for lines before first named label
        # Created lazily if needed
        preamble_label: Optional[MLabel] = None

        # Track line number for $TEXT support (1-indexed)
        line_number = 0

        # Build labels from parsed lines
        if hasattr(model, "lines") and model.lines:
            for line in model.lines:
                line_number += 1
                cls_name = line.__class__.__name__

                # LabelLine has a label attribute - creates new label
                if cls_name == "LabelLine" and hasattr(line, "label") and line.label:
                    label = self._build_label(line, line_number, routine)
                    label.line_number = line_number  # Track source line for $TEXT

                    # Labels at non-zero dot level (e.g. "ID4 . . S X=1") are
                    # continuation lines within the containing label's dot block,
                    # NOT separate entry points. Merge their statements into the
                    # current label's body so _structure_do_blocks nests them
                    # correctly within the enclosing FOR/DO.  We still record
                    # the label in _dotted_labels for $TEXT(LABEL+offset) lookup.
                    if label._dot_level is not None and current_label is not None:
                        routine._dotted_labels.append(label)
                        for stmt in label.body.statements:
                            stmt.scope = current_label.body
                            current_label.body.statements.append(stmt)
                    else:
                        routine.add_label(label)
                        current_label = label

                # ContLine - continuation line for current label
                elif cls_name == "ContLine":
                    if current_label is not None:
                        self._add_continuation_to_label(
                            line, current_label, line_number, routine
                        )
                    else:
                        # Labelless line before first label - create synthetic preamble
                        rest = getattr(line, "rest", "")
                        if rest and rest.strip():
                            if preamble_label is None:
                                preamble_label = MLabel(name="", body=MScope())
                                preamble_label.line_number = line_number
                                routine.add_label(preamble_label)
                                current_label = preamble_label
                            self._add_continuation_to_label(
                                line, preamble_label, line_number, routine
                            )

        # Post-process: structure DO blocks with dot-indented lines
        for label in routine.labels:
            if label.body.statements:
                label.body.statements = _structure_do_blocks(label.body.statements)
                for stmt in label.body.statements:
                    stmt.scope = label.body

        # Post-process: mark unreachable statements after unconditional QUIT/GOTO
        for label in routine.labels:
            if label.body.statements:
                _mark_unreachable_statements(label.body.statements)

        return routine

    def _add_continuation_to_label(
        self, cont_line, label: MLabel, line_number: int, routine: MRoutine
    ) -> None:
        """Add continuation line commands to a label's body.

        Continuation lines (starting with tab or space) belong to the
        preceding label. Their commands are added to that label's body.

        Dotted lines (`. command`) indicate block scope nesting.
        The _dot_level marker is set here and later processed by
        _structure_do_blocks to properly nest into DO bodies.

        Parse errors are collected in routine.parse_errors.

        Args:
            cont_line: The textX ContLine model
            label: The MLabel to add statements to
            line_number: Source line number for error reporting
            routine: The MRoutine to collect parse errors in
        """
        rest = getattr(cont_line, "rest", "")
        if not rest or not rest.strip():
            return

        # Handle dotted block continuation (`. S X=1`)
        # Strip the leading dot(s) and space(s)
        stripped_rest = rest.strip()
        dot_level = 0
        while stripped_rest.startswith("."):
            dot_level += 1
            stripped_rest = stripped_rest[1:].lstrip()

        # Parse the continuation line content
        commands = parse_commands_from_line(stripped_rest, line_number)

        # Check for parse error — emit MParseErrorStatement so codegen
        # generates a runtime error instead of silently dropping the line
        if isinstance(commands, MParseError):
            routine.parse_errors.append(commands)
            error_stmt = MParseErrorStatement(
                line_number=line_number,
                error_message=commands.message,
                line_content=commands.line_content,
            )
            error_stmt.scope = label.body
            if dot_level > 0:
                error_stmt._dot_level = dot_level
            label.body.statements.append(error_stmt)
            return

        # Convert to ASG statements and add to label body
        if commands:
            flat_statements = [
                s for s in (analyze_command(cmd) for cmd in commands) if s is not None
            ]
            # Structure with proper control flow nesting
            structured_statements = _structure_commands_with_bodies(flat_statements)
            # Extract inline comment from source and attach to first statement
            if structured_statements:
                comment = extract_comment(rest)
                if comment:
                    structured_statements[0].comment = comment
            for stmt in structured_statements:
                stmt.scope = label.body
                # Track source line number for GOTO analysis and error reporting
                # Propagate to all nested statements (IF then_scope, FOR body, etc.)
                _set_line_number_recursive(stmt, line_number)
                # Store the nesting level for later analysis
                if dot_level > 0:
                    stmt._dot_level = dot_level
                label.body.statements.append(stmt)

    def _build_label(self, line, line_number: int, routine: MRoutine) -> MLabel:
        """Convert textX LabelLine to MLabel ASG.

        Parse errors are collected in routine.parse_errors.

        Args:
            line: The textX LabelLine model
            line_number: Source line number for error reporting
            routine: The MRoutine to collect parse errors in

        Returns:
            An MLabel ASG node
        """
        label = MLabel(name=line.label if line.label else "")

        # Parse formal parameters from FormalList if present
        if hasattr(line, "formal_list") and line.formal_list:
            formal_list = line.formal_list
            if hasattr(formal_list, "params") and formal_list.params:
                # Strip whitespace from each parameter name
                label.formal_list = [p.strip() for p in formal_list.params]

        # Store raw line content for comment extraction
        label._line_rest = getattr(line, "rest", "")

        # Parse line content using textX command grammar.
        # Parsed commands are stored for later ASG building.
        # Handle dotted block continuation (`. S X=1`) - strip leading dots
        label_parse_error: Optional[MParseError] = None
        if label._line_rest:
            line_content = label._line_rest.strip()
            dot_level = 0
            while line_content.startswith("."):
                dot_level += 1
                line_content = line_content[1:].lstrip()

            # Store dot level for later DO block structuring
            label._dot_level = dot_level if dot_level > 0 else None

            if line_content:
                parsed_content = parse_line_content(line_content, line_number)
                if isinstance(parsed_content, MParseError):
                    routine.parse_errors.append(parsed_content)
                    label._parsed_content = None
                    label._parsed_commands = []
                    label_parse_error = parsed_content
                else:
                    label._parsed_content = parsed_content
                    # Get commands from parsed content
                    label._parsed_commands = [
                        lc.cmd
                        for lc in (
                            parsed_content.commands
                            if parsed_content is not None and parsed_content.commands
                            else []
                        )
                        if lc.cmd
                    ]
            else:
                label._parsed_content = None
                label._parsed_commands = []
        else:
            label._parsed_content = None
            label._parsed_commands = []
            label._dot_level = None

        # Build the body scope
        label.body = MScope()
        label.body.parent = label

        # Convert parsed commands to ASG statements and populate body
        if label._parsed_commands:
            flat_statements = [
                s
                for s in (analyze_command(cmd) for cmd in label._parsed_commands)
                if s is not None
            ]
            # Structure with proper control flow nesting
            structured_statements = _structure_commands_with_bodies(flat_statements)
            # Extract inline comment from source and attach to first statement
            if structured_statements and label._line_rest:
                comment = extract_comment(label._line_rest)
                if comment:
                    structured_statements[0].comment = comment
            for stmt in structured_statements:
                stmt.scope = label.body
                # Track source line number for GOTO analysis and error reporting
                # Propagate to all nested statements (IF then_scope, FOR body, etc.)
                _set_line_number_recursive(stmt, line_number)
                # Mark with dot level if this is a dot-indented labeled line
                if label._dot_level is not None:
                    stmt._dot_level = label._dot_level
                label.body.statements.append(stmt)
        elif label_parse_error is not None:
            # Label line had a parse error — emit MParseErrorStatement
            error_stmt = MParseErrorStatement(
                line_number=line_number,
                error_message=label_parse_error.message,
                line_content=label_parse_error.line_content,
            )
            error_stmt.scope = label.body
            if label._dot_level is not None:
                error_stmt._dot_level = label._dot_level
            label.body.statements.append(error_stmt)

        return label

    def resolve_references(self, routine: MRoutine) -> None:
        """Resolve all MCall references in a routine to their targets.

        This method connects GOTO and DO targets to their actual label
        definitions. It populates:
        - MCall.target with the resolved MLabel
        - MCall.is_resolved = True for successful resolutions
        - MLabel.callers with back-references from DO calls
        - MLabel.goto_sources with back-references from GOTO jumps

        External calls (label^routine) are marked but not resolved
        since they reference other routines.

        Args:
            routine: The MRoutine to resolve references in

        Side Effects:
            Modifies routine's MCall and MLabel objects in place
        """
        _resolve_references(routine)

    def classify_gotos(self, routine: MRoutine) -> None:
        """Classify all GOTO statements in a routine.

        Analyzes each MGotoStatement using its resolved MCall.target
        (requires resolve_references() to have been called first) and:
        1. Sets goto_type based on target and context
        2. Populates exits_loops with enclosing FOR loops exited
        3. Sets has_internal_goto=True on enclosing FOR loops
        4. Populates exit_points on FOR loops (bidirectional link)

        Args:
            routine: The MRoutine to classify GOTOs in

        Side Effects:
            - Sets MGotoStatement.goto_type for each GOTO
            - Sets MGotoStatement.exits_loops for loop exits
            - Sets MForStatement.has_internal_goto for loops with GOTOs
            - Populates MForStatement.exit_points bidirectionally
        """
        _classify_gotos(routine)

    def analyze_for_loops(
        self, routine: MRoutine, signatures: dict[str, FunctionSignature] | None = None
    ) -> None:
        """Analyze all FOR loops in a routine.

        This method scans each MForStatement and:
        1. Detects if loop variable is modified inside the body
        2. Sets loop_var_modified_in_body accordingly

        When signatures are provided (from analyze_variables/compute_signatures),
        the by-ref detection is precise: only flags modification if the callee
        actually writes to the formal parameter. Without signatures, falls back
        to conservative detection (any by-ref = potentially modified).

        Args:
            routine: The MRoutine to analyze
            signatures: Optional function signatures for precise by-ref detection

        Side Effects:
            - Sets MForStatement.loop_var_modified_in_body for each FOR
        """
        _analyze_for_loops(routine, signatures)

    def analyze_quit_context(self, routine: MRoutine) -> None:
        """Analyze QUIT statement context for all QUITs in a routine.

        This method walks through all statements and sets context fields
        on each MQuitStatement:
        - exits_for: Set to enclosing MForStatement if QUIT is inside a FOR loop
        - exits_do_block: Set to enclosing MDoStatement if QUIT is inside an inline DO block

        This enables codegen to use ASG fields directly instead of runtime tracking.

        Args:
            routine: The MRoutine to analyze

        Side Effects:
            - Sets MQuitStatement.exits_for for QUITs inside FOR loops
            - Sets MQuitStatement.exits_do_block for QUITs inside DO blocks
        """
        _analyze_quit_context(routine)

    def analyze_variables(
        self, routine: MRoutine, compute_transitive: bool = False
    ) -> dict[str, ScopeVariables]:
        """Analyze variable usage across all labels in a routine.

        This method scans each label for variable reads, writes, and NEW
        commands to determine:
        - input_variables: Variables read before first write (inputs)
        - output_variables: Variables written and visible to caller (outputs)
        - newed: Variables scoped by NEW command

        It also populates the corresponding fields on each MLabel object.

        Args:
            routine: The MRoutine to analyze
            compute_transitive: If True, compute transitive inputs through
                call chains (requires resolve_references() to be called first)

        Returns:
            Dictionary mapping label names to ScopeVariables

        Side Effects:
            Populates MLabel.variables_read, variables_written, variables_newed,
            input_variables, and output_variables fields
        """
        label_vars = _analyze_variables(routine)

        if compute_transitive:
            # Compute transitive closure through call chains
            transitive_inputs = _compute_transitive_inputs(routine, label_vars)

            # Update input_variables with transitive inputs
            for label in routine.labels:
                if label.name in transitive_inputs:
                    label.input_variables = transitive_inputs[label.name]
                    if label.name in label_vars:
                        label_vars[label.name].input_variables = transitive_inputs[
                            label.name
                        ]

        return label_vars

    def compute_signatures(self, routine: MRoutine) -> dict[str, FunctionSignature]:
        """Compute function signatures for all labels in a routine.

        This method combines formal parameters, variable analysis, and QUIT
        analysis to determine each label's interface for Python code generation.

        Function signatures enable generating Python functions with proper
        arguments and return values instead of runtime get_local()/set_local().

        Args:
            routine: The MRoutine to analyze (should have resolve_references
                called first for full accuracy)

        Returns:
            Dictionary mapping label names to FunctionSignature objects

        Side Effects:
            Populates MLabel.signature field for each label
            Also calls analyze_variables() if not already done
        """
        from ..analysis.variables import compute_all_signatures

        return compute_all_signatures(routine)
