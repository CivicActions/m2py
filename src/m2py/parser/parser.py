"""MUMPS Parser implementation using textX.

Provides the MUMPSParser class that parses MUMPS source code and
produces an Abstract Semantic Graph (ASG).
"""

import json
from pathlib import Path
from typing import Optional, Union, List

from textx import metamodel_from_file

from m2py.asg import MRoutine, MLabel, MScope
from m2py.asg.enums import ForLoopType
from m2py.asg.statements import (
    MForStatement, MIfStatement, MElseStatement, MDoStatement,
    MStatement,
)
from m2py.parser.exceptions import MUMPSSyntaxError
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.analysis.command_parser import (
    parse_line_content, 
    parse_commands_from_line,
    extract_for_commands,
    classify_for_from_textx,
    parse_for_command_to_asg,
    detect_quit_after_for,
)
from m2py.analysis.resolver import resolve_references as _resolve_references
from m2py.analysis.variables import (
    analyze_variables as _analyze_variables,
    compute_transitive_inputs as _compute_transitive_inputs,
    ScopeVariables,
)


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
    if not statements:
        return []
    
    result = []
    i = 0
    
    while i < len(statements):
        stmt = statements[i]
        # print(f"DEBUG: Processing {type(stmt).__name__} at index {i}")
        
        # Check if this is a control flow statement that captures remaining line
        if isinstance(stmt, MForStatement):
            # FOR captures all remaining statements as its body (recursively)
            remaining = statements[i + 1:]
            if remaining:
                # Recursively structure the remaining statements
                stmt.body.statements = _structure_commands_with_bodies(remaining)
                for child in stmt.body.statements:
                    child.scope = stmt.body
            result.append(stmt)
            break  # FOR consumed all remaining statements
            
        elif isinstance(stmt, MIfStatement):
            # IF captures all remaining statements as its then_scope (recursively)
            remaining = statements[i + 1:]
            if remaining:
                stmt.then_scope.statements = _structure_commands_with_bodies(remaining)
                for child in stmt.then_scope.statements:
                    child.scope = stmt.then_scope
            result.append(stmt)
            break  # IF consumed all remaining statements
            
        elif isinstance(stmt, MElseStatement):
            # ELSE captures all remaining statements as its body (recursively)
            remaining = statements[i + 1:]
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


def _find_last_argumentless_do(stmt: MStatement) -> Optional[MDoStatement]:
    """Find the last argumentless DO in a statement's nested scopes.
    
    Recursively searches through then_scope, else_scope, and body
    to find the trailing argumentless DO that should capture dot-lines.
    
    Args:
        stmt: Statement to search
        
    Returns:
        The last argumentless DO found, or None
    """
    # Check nested scopes in order: then_scope, else_scope, body
    # Return the DO from the deepest/last position
    
    if isinstance(stmt, MIfStatement) and stmt.then_scope and stmt.then_scope.statements:
        last = stmt.then_scope.statements[-1]
        # Recursively search in the last statement
        nested = _find_last_argumentless_do(last)
        if nested:
            return nested
        # Check if last statement itself is argumentless DO
        if isinstance(last, MDoStatement) and not last.targets:
            return last
    
    if isinstance(stmt, MElseStatement) and stmt.body and stmt.body.statements:
        last = stmt.body.statements[-1]
        nested = _find_last_argumentless_do(last)
        if nested:
            return nested
        if isinstance(last, MDoStatement) and not last.targets:
            return last
    
    if isinstance(stmt, MForStatement) and stmt.body and stmt.body.statements:
        last = stmt.body.statements[-1]
        nested = _find_last_argumentless_do(last)
        if nested:
            return nested
        if isinstance(last, MDoStatement) and not last.targets:
            return last
    
    # Direct check for argumentless DO
    if isinstance(stmt, MDoStatement) and not stmt.targets:
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
    if not statements:
        return []
    
    result = []
    i = 0
    
    while i < len(statements):
        stmt = statements[i]
        
        # Check if this is an argumentless DO (block start) at this level
        if isinstance(stmt, MDoStatement) and not stmt.targets:
            # Find all following statements with dot_level > 0
            block_stmts = []
            j = i + 1
            
            while j < len(statements):
                next_stmt = statements[j]
                dot_level = getattr(next_stmt, '_dot_level', 0)
                
                if dot_level > 0:
                    # This statement belongs to the DO block
                    # Decrement dot level (in case of nested DO blocks)
                    if dot_level == 1:
                        delattr(next_stmt, '_dot_level')
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
            
            result.append(stmt)
            i = j  # Skip past the block statements
            
        else:
            # Check if there are following dot-level statements that need
            # to be attached to an argumentless DO nested inside this statement
            j = i + 1
            block_stmts = []
            
            while j < len(statements):
                next_stmt = statements[j]
                dot_level = getattr(next_stmt, '_dot_level', 0)
                if dot_level > 0:
                    if dot_level == 1:
                        delattr(next_stmt, '_dot_level')
                    else:
                        next_stmt._dot_level = dot_level - 1
                    block_stmts.append(next_stmt)
                    j += 1
                else:
                    break
            
            if block_stmts:
                # Find the argumentless DO inside this statement's nested scopes
                target_do = _find_last_argumentless_do(stmt)
                if target_do:
                    # Attach the dot-statements to this DO's body
                    target_do.body.statements = _structure_do_blocks(block_stmts)
                    for child in target_do.body.statements:
                        child.scope = target_do.body
                    result.append(stmt)
                    i = j  # Skip past the block statements
                else:
                    # No DO found - this is an error case, but keep statements
                    result.append(stmt)
                    i += 1
            else:
                result.append(stmt)
                i += 1
    
    return result


def _mark_unreachable_statements(statements: List[MStatement]) -> None:
    """Mark statements after unconditional QUIT/GOTO as unreachable.
    
    In MUMPS, statements on subsequent lines after an unconditional
    QUIT or GOTO cannot be reached. This function sets is_unreachable=True
    on those statements for downstream analysis.
    
    Note: This operates on the same physical line as well as subsequent lines.
    Within a single line, code after QUIT is also unreachable, but the parser
    already captures those as separate statements.
    
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
            # Unconditional = no postcondition
            if stmt.postcondition is None:
                unreachable = True
        
        # Recursively check nested scopes (FOR body, IF then_scope, etc.)
        # But don't propagate unreachable flag INTO nested scopes - each scope
        # has its own control flow
        if isinstance(stmt, MForStatement) and stmt.body and stmt.body.statements:
            _mark_unreachable_statements(stmt.body.statements)
        if isinstance(stmt, MIfStatement) and stmt.then_scope and stmt.then_scope.statements:
            _mark_unreachable_statements(stmt.then_scope.statements)
        if isinstance(stmt, MElseStatement) and stmt.body and stmt.body.statements:
            _mark_unreachable_statements(stmt.body.statements)
        if hasattr(stmt, 'body') and stmt.body and hasattr(stmt.body, 'statements') and stmt.body.statements:
            # Catch MDoBlockStatement and others
            if not isinstance(stmt, (MForStatement, MIfStatement, MElseStatement)):
                _mark_unreachable_statements(stmt.body.statements)


def dump_asg_json(routine: MRoutine, include_position: bool = False, indent: int = 2) -> str:
    """Serialize an ASG to JSON for debugging.
    
    Args:
        routine: The MRoutine to serialize
        include_position: Include source position information
        indent: JSON indentation level (None for compact)
        
    Returns:
        JSON string representation of the ASG
    """
    return json.dumps(routine.to_dict(include_position=include_position), indent=indent)


class ForPatternResult:
    """Result of FOR loop pattern classification.
    
    Represents a classified FOR loop found in the source code.
    """
    
    def __init__(self, 
                 label_name: str,
                 loop_type: ForLoopType,
                 loop_var: str,
                 line_content: str,
                 statement: Optional[MForStatement] = None):
        self.label_name = label_name
        self.loop_type = loop_type
        self.loop_var = loop_var
        self.line_content = line_content
        self.statement = statement  # The actual ASG node
    
    def __repr__(self):
        return f"ForPatternResult({self.label_name}, {self.loop_type.name}, var={self.loop_var!r})"


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
        
        # Create the textX metamodel
        # IMPORTANT: skipws=False because MUMPS is whitespace-sensitive
        # (tabs separate labels from commands, spaces separate arguments)
        self._metamodel = metamodel_from_file(
            str(grammar_file),
            # Custom classes will be registered here as ASG types are implemented
            classes=[],
            skipws=False,  # Don't auto-skip whitespace
        )
        
        # Track source file for error reporting
        self._current_file: Optional[str] = None
    
    def parse(self, source: str, filename: Optional[str] = None) -> MRoutine:
        """Parse MUMPS source code and return an ASG.
        
        Args:
            source: The MUMPS source code to parse
            filename: Optional filename for error reporting
            
        Returns:
            An MRoutine containing the parsed ASG
            
        Raises:
            MUMPSSyntaxError: If the source contains syntax errors
        """
        self._current_file = filename
        
        try:
            # Parse using textX
            model = self._metamodel.model_from_str(source)
            
            # Convert textX model to our ASG
            routine = self._build_routine(model, filename)
            
            return routine
            
        except Exception as e:
            # Convert textX exceptions to our exception type
            raise MUMPSSyntaxError(
                message=str(e),
                source_file=filename,
            ) from e
    
    def parse_file(self, filepath: Union[str, Path]) -> MRoutine:
        """Parse a MUMPS source file and return an ASG.
        
        Args:
            filepath: Path to the .m file to parse
            
        Returns:
            An MRoutine containing the parsed ASG
            
        Raises:
            FileNotFoundError: If the file does not exist
            MUMPSSyntaxError: If the file contains syntax errors
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"MUMPS source file not found: {filepath}")
        
        source = filepath.read_text(encoding="utf-8")
        
        # Ensure source ends with newline for proper parsing of last line
        if source and not source.endswith('\n'):
            source += '\n'
            
        routine_name = filepath.stem  # Use filename without extension as routine name
        
        routine = self.parse(source, filename=str(filepath))
        routine.name = routine_name
        routine.source_file = str(filepath)
        
        # Store original source lines for $TEXT function support
        # Lines are stored 0-indexed, but $TEXT uses 1-indexed line references
        routine.source_lines = source.splitlines()
        
        return routine
    
    def _build_routine(self, model, filename: Optional[str]) -> MRoutine:
        """Convert textX parse model to MRoutine ASG.
        
        This is a placeholder that will be expanded as we implement
        more ASG element mappings.
        
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
        if hasattr(model, 'lines') and model.lines:
            for line in model.lines:
                line_number += 1
                cls_name = line.__class__.__name__
                
                # LabelLine has a label attribute - creates new label
                if cls_name == 'LabelLine' and hasattr(line, 'label') and line.label:
                    label = self._build_label(line)
                    label.line_number = line_number  # Track source line for $TEXT
                    routine.add_label(label)
                    current_label = label
                
                # ContLine - continuation line for current label
                elif cls_name == 'ContLine':
                    if current_label is not None:
                        self._add_continuation_to_label(line, current_label)
                    else:
                        # Labelless line before first label - create synthetic preamble
                        rest = getattr(line, 'rest', '')
                        if rest and rest.strip():
                            if preamble_label is None:
                                preamble_label = MLabel(name='', body=MScope())
                                preamble_label.line_number = line_number
                                routine.add_label(preamble_label)
                                current_label = preamble_label
                            self._add_continuation_to_label(line, preamble_label)
        
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
    
    def _add_continuation_to_label(self, cont_line, label: MLabel) -> None:
        """Add continuation line commands to a label's body.
        
        Continuation lines (starting with tab or space) belong to the
        preceding label. Their commands are added to that label's body.
        
        Dotted lines (`. command`) indicate block scope nesting.
        The _dot_level marker is set here and later processed by
        _structure_do_blocks to properly nest into DO bodies.
        
        Args:
            cont_line: The textX ContLine model
            label: The MLabel to add statements to
        """
        rest = getattr(cont_line, 'rest', '')
        if not rest or not rest.strip():
            return
        
        # Handle dotted block continuation (`. S X=1`)
        # Strip the leading dot(s) and space(s)
        stripped_rest = rest.strip()
        dot_level = 0
        while stripped_rest.startswith('.'):
            dot_level += 1
            stripped_rest = stripped_rest[1:].lstrip()
        
        # Parse the continuation line content
        commands = parse_commands_from_line(stripped_rest)
        
        # Convert to ASG statements and add to label body
        if commands:
            flat_statements = [s for s in (analyze_command(cmd) for cmd in commands) if s is not None]
            # Structure with proper control flow nesting
            structured_statements = _structure_commands_with_bodies(flat_statements)
            for stmt in structured_statements:
                stmt.scope = label.body
                # Store the nesting level for later analysis
                if dot_level > 0:
                    stmt._dot_level = dot_level
                label.body.statements.append(stmt)

    def _build_label(self, line) -> MLabel:
        """Convert textX LabelLine to MLabel ASG.
        
        Args:
            line: The textX LabelLine model
            
        Returns:
            An MLabel ASG node
        """
        label = MLabel(name=line.label if line.label else "")
        
        # Parse formal parameters from FormalList if present
        if hasattr(line, 'formal_list') and line.formal_list:
            formal_list = line.formal_list
            if hasattr(formal_list, 'params') and formal_list.params:
                # Strip whitespace from each parameter name
                label.formal_list = [p.strip() for p in formal_list.params]
        
        # Store line content for pattern classification methods
        label._line_rest = getattr(line, 'rest', '')
        
        # Parse line content using textX grammar (new approach)
        # This stores the parsed commands for later ASG building
        if label._line_rest:
            label._parsed_content = parse_line_content(label._line_rest)
            label._parsed_commands = parse_commands_from_line(label._line_rest)
        else:
            label._parsed_content = None
            label._parsed_commands = []
        
        # Build the body scope
        label.body = MScope()
        label.body.parent = label
        
        # Convert parsed commands to ASG statements and populate body
        if label._parsed_commands:
            flat_statements = [s for s in (analyze_command(cmd) for cmd in label._parsed_commands) if s is not None]
            # Structure with proper control flow nesting
            structured_statements = _structure_commands_with_bodies(flat_statements)
            for stmt in structured_statements:
                stmt.scope = label.body
                label.body.statements.append(stmt)
        
        return label
    
    def classify_patterns(self, source: str, filename: Optional[str] = None) -> list[ForPatternResult]:
        """Parse source and classify FOR loop patterns.
        
        This is a convenience method that parses the source and then
        extracts and classifies all FOR loops found in the routine.
        
        Uses textX grammar-based parsing to extract FOR commands.
        
        Args:
            source: The MUMPS source code to parse
            filename: Optional filename for error reporting
            
        Returns:
            List of ForPatternResult objects describing each FOR loop found
        """
        # Parse to get the model directly (we need line content)
        self._current_file = filename
        
        try:
            model = self._metamodel.model_from_str(source)
        except Exception as e:
            raise MUMPSSyntaxError(
                message=str(e),
                source_file=filename,
            ) from e
        
        results = []
        current_label = None
        
        if hasattr(model, 'lines') and model.lines:
            for line in model.lines:
                # Track current label for association
                if hasattr(line, 'label') and line.label:
                    current_label = line.label
                
                # Get line content (rest attribute for LabelLine, ContLine)
                line_rest = getattr(line, 'rest', '')
                
                if not line_rest:
                    continue
                
                # Use textX grammar to extract FOR commands
                for_commands = extract_for_commands(line_rest)
                
                # Detect if QUIT appears after FOR on this line
                has_quit = detect_quit_after_for(line_rest)
                
                for for_cmd in for_commands:
                    # Classify the FOR command using textX
                    loop_type, loop_var = classify_for_from_textx(for_cmd)
                    
                    # Build MForStatement from textX ForCommand
                    statement = parse_for_command_to_asg(for_cmd)
                    statement.has_internal_quit = has_quit
                    
                    results.append(ForPatternResult(
                        label_name=current_label or "",
                        loop_type=loop_type,
                        loop_var=loop_var,
                        line_content=line_rest,
                        statement=statement,
                    ))
        
        return results
    
    def classify_patterns_from_file(self, filepath: Union[str, Path]) -> list[ForPatternResult]:
        """Parse a file and classify FOR loop patterns.
        
        Args:
            filepath: Path to the .m file to parse
            
        Returns:
            List of ForPatternResult objects describing each FOR loop found
            
        Raises:
            FileNotFoundError: If the file does not exist
            MUMPSSyntaxError: If the file contains syntax errors
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"MUMPS source file not found: {filepath}")
        
        source = filepath.read_text(encoding="utf-8")
        return self.classify_patterns(source, filename=str(filepath))
    
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
    
    def analyze_variables(self, routine: MRoutine, compute_transitive: bool = False) -> dict[str, ScopeVariables]:
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
                        label_vars[label.name].input_variables = transitive_inputs[label.name]
        
        return label_vars
