"""FOR loop classification and statement parsing.

Classifies FOR loops into the five categories defined in data-model.md:
- BOUNDED: FOR var=start:step:end (deterministic termination)  
- OPEN_ENDED: FOR var=start:step (no end condition)
- STRING_LIST: FOR var="A","B","C" (string value list)
- MIXED: FOR var="A",1:1:5 (combination of patterns)
- ARGUMENTLESS: FOR (infinite loop, requires explicit exit)

Also provides parsing functions for building statement ASG nodes:
- parse_for_statement() - Parse FOR command into MForStatement
- parse_set_statement() - Parse SET command into MSetStatement  
- parse_write_statement() - Parse WRITE command into MWriteStatement
- parse_quit_statement() - Parse QUIT command into MQuitStatement
- parse_if_statement() - Parse IF command into MIfStatement
"""

import re
from typing import List, Optional, Tuple
from ..asg.enums import ForLoopType, ForParamType, LiteralType
from ..asg.statements import (
    MForStatement, MForParameter, 
    MSetStatement, MAssignment,
    MWriteStatement, MQuitStatement, MIfStatement
)
from ..asg.elements import MScope
from ..asg.expressions import MLiteral, MVariable


class ForPattern:
    """Represents a parsed FOR loop forparameter pattern."""
    
    def __init__(self, 
                 loop_var: Optional[str] = None,
                 param_type: ForParamType = ForParamType.RANGE):
        self.loop_var = loop_var
        self.param_type = param_type
        self.forparams: list = []  # List of individual forparameter patterns


def classify_for_loop(for_content: str) -> Tuple[ForLoopType, Optional[str]]:
    """Classify a FOR loop from its content string.
    
    Args:
        for_content: The content after 'FOR ' or 'F ' command
        
    Returns:
        Tuple of (ForLoopType, loop_variable_name or None)
    
    Examples:
        >>> classify_for_loop("I=1:1:10 W I")
        (ForLoopType.BOUNDED, "I")
        >>> classify_for_loop("I=1:1 W I")
        (ForLoopType.OPEN_ENDED, "I")
        >>> classify_for_loop(' W "hello"')
        (ForLoopType.ARGUMENTLESS, None)
    """
    content = for_content.strip()
    
    # Empty content after FOR = argumentless FOR
    if not content or content[0] in (' ', '\t') or content.startswith(';'):
        return ForLoopType.ARGUMENTLESS, None
    
    # Check if it starts with a space (argumentless FOR - commands follow)
    # Actually argumentless FOR has NO arguments, just FOR followed by space and commands
    # Need to distinguish "F  W X" (argumentless) from "F I=1 W X" (bounded/etc)
    
    # Try to extract loop variable assignment
    # Pattern: var=value or var=start:step:end
    match = re.match(r'^([A-Za-z%][A-Za-z0-9]*|[A-Za-z%])=', content)
    if not match:
        # No variable assignment = argumentless FOR
        return ForLoopType.ARGUMENTLESS, None
    
    loop_var = match.group(1)
    after_var = content[len(match.group(0)):]
    
    # Now parse the forparameter(s) - may be comma-separated
    # First forparameter starts right after =
    forparams = _parse_forparams(after_var)
    
    if not forparams:
        # Single value (e.g., F I=7)
        return ForLoopType.STRING_LIST, loop_var
    
    # Classify based on forparams
    has_range = any(fp == ForParamType.RANGE for fp in forparams)
    has_open_range = any(fp == ForParamType.OPEN_RANGE for fp in forparams)
    has_value = any(fp == ForParamType.VALUE for fp in forparams)
    
    if len(forparams) > 1:
        # Multiple forparams = check for mixed
        types = set(forparams)
        if len(types) > 1:
            return ForLoopType.MIXED, loop_var
        if has_value:
            return ForLoopType.STRING_LIST, loop_var
        if has_range:
            return ForLoopType.BOUNDED, loop_var
        if has_open_range:
            return ForLoopType.OPEN_ENDED, loop_var
    else:
        # Single forparam
        fp = forparams[0]
        if fp == ForParamType.RANGE:
            return ForLoopType.BOUNDED, loop_var
        elif fp == ForParamType.OPEN_RANGE:
            return ForLoopType.OPEN_ENDED, loop_var
        else:
            return ForLoopType.STRING_LIST, loop_var
    
    # Default fallback
    return ForLoopType.BOUNDED, loop_var


def _parse_forparams(content: str) -> list[ForParamType]:
    """Parse forparameters from content after 'var='.
    
    Returns list of ForParamType for each forparameter.
    """
    result = []
    
    # Simple parsing: look for colons to determine type
    # Bounded: has 2 colons (start:step:end)
    # Open-ended: has 1 colon (start:step)
    # Value: no colons (literal value)
    
    # Split by comma but respect strings and parentheses
    forparams = _split_forparams(content)
    
    for fp in forparams:
        fp = fp.strip()
        if not fp:
            continue
        
        # Count colons (simple approach - may need refinement for nested expressions)
        colon_count = fp.count(':')
        
        if colon_count >= 2:
            result.append(ForParamType.RANGE)
        elif colon_count == 1:
            result.append(ForParamType.OPEN_RANGE)
        else:
            result.append(ForParamType.VALUE)
    
    return result


def _split_forparams(content: str) -> list[str]:
    """Split content by commas, respecting strings and parentheses.
    
    Returns list of forparameter strings.
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    
    i = 0
    while i < len(content):
        char = content[i]
        
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            result.append(current)
            current = ""
        elif char == ' ' and paren_depth == 0 and not current.strip():
            # Leading space in forparam - skip
            pass
        elif char == ' ' and paren_depth == 0:
            # Space after forparam marks end of FOR arguments
            result.append(current)
            current = ""  # Clear to prevent duplicate append
            break
        else:
            current += char
        
        i += 1
    
    if current:
        result.append(current)
    
    return result


def extract_for_from_line(line_rest: str) -> Optional[Tuple[ForLoopType, str, str]]:
    """Extract FOR loop information from a line's content.
    
    Args:
        line_rest: The rest of the line after the label (or full line for continuation)
        
    Returns:
        Tuple of (ForLoopType, loop_var, remaining_content) if FOR found, None otherwise
        
    Note:
        FOR can appear anywhere in a line after other commands.
        Example: "S X=1 F I=1:1:10 W I"
    """
    content = line_rest
    
    # Simple heuristic: find FOR commands that appear as separate tokens
    # Look for whitespace+F/FOR+whitespace pattern, avoiding matches inside strings
    # Pattern: space or tab, then F or FOR, then space
    
    # First, try to find FOR at position that's not inside a string
    # Simple approach: scan for ' F ' or '\tF ' or ' FOR ' or '\tFOR '
    # checking if the position is not after an odd number of quotes
    
    for match in re.finditer(r'(?:^|\s)(FOR|F)\s+', content, re.IGNORECASE):
        pos = match.start()
        
        # Count quotes before this position
        quote_count = content[:pos].count('"')
        
        # If odd number of quotes, we're inside a string - skip
        if quote_count % 2 == 1:
            continue
        
        # Valid FOR command found
        after_for = content[match.end():]
        
        # Check for argumentless FOR
        if not after_for.strip() or after_for[0] in (' ', '\t'):
            return ForLoopType.ARGUMENTLESS, "", after_for.lstrip()
        
        # Classify the FOR loop
        loop_type, loop_var = classify_for_loop(after_for)
        
        return loop_type, loop_var or "", after_for
    
    return None


def parse_for_statement(for_content: str) -> MForStatement:
    """Parse FOR command content into an MForStatement ASG node.
    
    This is the primary function for building FOR statement ASG nodes.
    It extracts the loop variable, parses all forparameters into
    MForParameter objects, classifies the loop type, builds
    the complete MForStatement, and detects QUIT exit points.
    
    Args:
        for_content: The content after 'FOR ' or 'F ' command.
                    Example: "I=1:1:10 W I" or '"A","B","C" W I'
        
    Returns:
        MForStatement with:
        - loop_var: The loop variable name (or None for argumentless)
        - parameters: List of MForParameter objects
        - loop_type: Classification of the FOR loop
        - body: Empty MScope (to be populated by parser)
        - has_internal_quit: True if QUIT detected in FOR body
        
    Examples:
        >>> stmt = parse_for_statement("I=1:1:10 W I")
        >>> stmt.loop_var
        'I'
        >>> stmt.loop_type
        ForLoopType.BOUNDED
        >>> len(stmt.parameters)
        1
        >>> stmt.parameters[0].param_type
        ForParamType.RANGE
    """
    stmt = MForStatement()
    stmt.body = MScope()
    
    content = for_content.strip()
    
    # Check for argumentless FOR
    if not content or content[0] in (' ', '\t') or content.startswith(';'):
        stmt.loop_type = ForLoopType.ARGUMENTLESS
        stmt.loop_var = None
        # Argumentless FOR still needs QUIT detection in the body
        body_content = content.lstrip()
        stmt.has_internal_quit = _detect_quit_in_body(body_content)
        return stmt
    
    # Try to extract loop variable assignment
    match = re.match(r'^([A-Za-z%][A-Za-z0-9]*|[A-Za-z%])=', content)
    if not match:
        # No variable assignment = argumentless FOR
        stmt.loop_type = ForLoopType.ARGUMENTLESS
        stmt.loop_var = None
        stmt.has_internal_quit = _detect_quit_in_body(content)
        return stmt
    
    stmt.loop_var = match.group(1)
    after_var = content[len(match.group(0)):]
    
    # Parse forparameters and get remaining body content
    forparam_strs, body_content = _split_forparams_with_body(after_var)
    
    for fp_str in forparam_strs:
        fp_str = fp_str.strip()
        if not fp_str:
            continue
        
        param = _parse_single_forparam(fp_str)
        stmt.parameters.append(param)
    
    # Classify based on parameters
    stmt.loop_type = _classify_from_parameters(stmt.parameters)
    
    # Detect QUIT exit points in the body
    stmt.has_internal_quit = _detect_quit_in_body(body_content)
    
    return stmt


def _split_forparams_with_body(content: str) -> Tuple[list[str], str]:
    """Split content by commas, respecting strings and parentheses.
    
    Returns tuple of (list of forparameter strings, remaining body content).
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    body_start = len(content)  # Index where body starts
    
    i = 0
    while i < len(content):
        char = content[i]
        
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            result.append(current)
            current = ""
        elif char == ' ' and paren_depth == 0 and not current.strip():
            # Leading space in forparam - skip
            pass
        elif char == ' ' and paren_depth == 0:
            # Space after forparam marks end of FOR arguments
            result.append(current)
            current = ""  # Clear to prevent duplicate append
            body_start = i + 1  # Body starts after this space
            break
        else:
            current += char
        
        i += 1
    
    if current:
        result.append(current)
    
    body_content = content[body_start:] if body_start < len(content) else ""
    return result, body_content


def _detect_quit_in_body(body_content: str) -> bool:
    """Detect if QUIT command exists in FOR body content.
    
    Looks for QUIT (Q) command, including postconditioned QUIT (Q:cond).
    Does not count QUIT inside strings.
    
    Args:
        body_content: The commands following the FOR parameters
        
    Returns:
        True if QUIT is found in the body
    """
    if not body_content:
        return False
    
    # Look for Q or QUIT as a command (not inside strings)
    # Pattern: whitespace or start, Q or QUIT, followed by space, colon, or end
    # Must account for strings
    
    in_string = False
    i = 0
    content = body_content
    
    while i < len(content):
        char = content[i]
        
        if char == '"':
            in_string = not in_string
            i += 1
            continue
        
        if in_string:
            i += 1
            continue
        
        # Check for Q or QUIT command at this position
        # Command must be preceded by whitespace (or start) and followed by whitespace, :, or end
        rest = content[i:]
        
        # Check for QUIT (full word)
        if rest.upper().startswith('QUIT'):
            # Check what follows
            after = rest[4:]
            if not after or after[0] in (' ', '\t', ':', '\n'):
                # Valid QUIT command
                return True
        # Check for Q (abbreviated)
        elif rest.upper().startswith('Q') and (len(rest) == 1 or rest[1] in (' ', '\t', ':', '\n')):
            # Q followed by space, tab, colon, or end = QUIT command
            # But not if it's part of a longer word
            if i == 0 or content[i-1] in (' ', '\t'):
                return True
        
        i += 1
    
    return False


def _parse_single_forparam(fp_str: str) -> MForParameter:
    """Parse a single forparameter string into MForParameter.
    
    Args:
        fp_str: Single forparameter like "1:1:10" or '"ABC"' or "1:1"
        
    Returns:
        MForParameter with appropriate type and values
    """
    param = MForParameter()
    
    # Count colons (outside of strings)
    colon_positions = _find_colons(fp_str)
    
    if len(colon_positions) >= 2:
        # RANGE: start:step:end
        param.param_type = ForParamType.RANGE
        # Extract start, step, end
        start_str = fp_str[:colon_positions[0]]
        step_str = fp_str[colon_positions[0]+1:colon_positions[1]]
        end_str = fp_str[colon_positions[1]+1:]
        
        param.start = _make_literal(start_str.strip())
        param.step = _make_literal(step_str.strip())
        param.end = _make_literal(end_str.strip())
        
    elif len(colon_positions) == 1:
        # OPEN_RANGE: start:step
        param.param_type = ForParamType.OPEN_RANGE
        start_str = fp_str[:colon_positions[0]]
        step_str = fp_str[colon_positions[0]+1:]
        
        param.start = _make_literal(start_str.strip())
        param.step = _make_literal(step_str.strip())
        
    else:
        # VALUE: single expression
        param.param_type = ForParamType.VALUE
        param.value = _make_literal(fp_str.strip())
    
    return param


def _find_colons(s: str) -> List[int]:
    """Find positions of colons outside of strings.
    
    Returns list of indices where colons appear (not inside quotes).
    """
    positions = []
    in_string = False
    paren_depth = 0
    
    for i, char in enumerate(s):
        if char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ':' and paren_depth == 0:
                positions.append(i)
    
    return positions


def _make_literal(expr_str: str) -> MLiteral:
    """Create an MLiteral from an expression string.
    
    For now, we capture expressions as raw text in an MLiteral.
    A more complete implementation would parse full expressions.
    
    Args:
        expr_str: Expression string like "1", '"ABC"', or "X+1"
        
    Returns:
        MLiteral with the raw expression
    """
    from ..asg.enums import LiteralType
    
    literal = MLiteral()
    literal.raw_value = expr_str
    
    # Determine literal type
    if expr_str.startswith('"') and expr_str.endswith('"'):
        literal.literal_type = LiteralType.STRING
        literal.value = expr_str[1:-1]  # Remove quotes
    else:
        # Try to parse as number
        try:
            if '.' in expr_str or 'E' in expr_str.upper():
                literal.value = float(expr_str)
                literal.literal_type = LiteralType.DECIMAL
            else:
                literal.value = int(expr_str)
                literal.literal_type = LiteralType.INTEGER
        except ValueError:
            # Not a simple literal - it's an expression
            literal.literal_type = LiteralType.STRING
            literal.value = expr_str
    
    return literal


def _classify_from_parameters(params: List[MForParameter]) -> ForLoopType:
    """Classify FOR loop type from its parameters.
    
    Args:
        params: List of MForParameter objects
        
    Returns:
        ForLoopType classification
    """
    if not params:
        return ForLoopType.ARGUMENTLESS
    
    types = set(p.param_type for p in params)
    
    if len(types) > 1:
        return ForLoopType.MIXED
    
    single_type = list(types)[0]
    
    if single_type == ForParamType.RANGE:
        return ForLoopType.BOUNDED
    elif single_type == ForParamType.OPEN_RANGE:
        return ForLoopType.OPEN_ENDED
    else:  # VALUE
        return ForLoopType.STRING_LIST


# =============================================================================
# SET Statement Parsing (T041)
# =============================================================================

def parse_set_statement(set_content: str) -> MSetStatement:
    """Parse SET command content into an MSetStatement ASG node.
    
    Args:
        set_content: The content after 'SET ' or 'S ' command.
                    Example: "X=1", "A=1,B=2", "(A,B)=C"
        
    Returns:
        MSetStatement with assignments list populated
        
    Examples:
        >>> stmt = parse_set_statement("X=1")
        >>> len(stmt.assignments)
        1
        >>> stmt.assignments[0].target.name
        'X'
    """
    stmt = MSetStatement()
    content = set_content.strip()
    
    if not content:
        return stmt
    
    # Parse assignments (comma-separated)
    assignments = _split_set_assignments(content)
    
    for assign_str in assignments:
        assign_str = assign_str.strip()
        if not assign_str:
            continue
        
        assignment = _parse_single_assignment(assign_str)
        if assignment:
            stmt.assignments.append(assignment)
    
    return stmt


def _split_set_assignments(content: str) -> List[str]:
    """Split SET content into individual assignments.
    
    Handles: X=1,Y=2 and (A,B)=C patterns.
    Respects parentheses and strings.
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    
    i = 0
    while i < len(content):
        char = content[i]
        
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            # Check if this comma separates assignments
            # Need to look at context - is this after = ?
            if '=' in current:
                result.append(current)
                current = ""
            else:
                current += char
        elif char == ' ' and paren_depth == 0 and '=' in current:
            # Space after complete assignment = end of SET arguments
            result.append(current)
            break
        else:
            current += char
        
        i += 1
    
    if current:
        result.append(current)
    
    return result


def _parse_single_assignment(assign_str: str) -> Optional[MAssignment]:
    """Parse a single assignment like 'X=1' or '(A,B)=C'.
    
    Returns MAssignment with target and value.
    """
    # Find the = sign (not inside parens or strings)
    eq_pos = _find_equals(assign_str)
    
    if eq_pos == -1:
        return None
    
    target_str = assign_str[:eq_pos].strip()
    value_str = assign_str[eq_pos+1:].strip()
    
    assignment = MAssignment()
    
    # Parse target - could be simple var, subscripted var, or (A,B) group
    if target_str.startswith('('):
        # Multiple targets - for now, capture as first variable
        # TODO: Handle (A,B)=C properly
        inner = target_str[1:].split(')')[0].split(',')[0].strip()
        assignment.target = _make_variable(inner)
    else:
        assignment.target = _make_variable(target_str)
    
    # Parse value
    assignment.value = _make_literal(value_str)
    
    return assignment


def _find_equals(s: str) -> int:
    """Find the position of = sign (not in strings or parens)."""
    in_string = False
    paren_depth = 0
    
    for i, char in enumerate(s):
        if char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '=' and paren_depth == 0:
                return i
    
    return -1


def _make_variable(var_str: str) -> MVariable:
    """Create an MVariable from a variable string.
    
    Handles simple variables and subscripted variables.
    """
    var = MVariable()
    var_str = var_str.strip()
    
    # Check for subscripts
    paren_pos = var_str.find('(')
    if paren_pos != -1:
        var.name = var_str[:paren_pos]
        # TODO: Parse subscripts properly
        var.subscripts = []
    else:
        var.name = var_str
    
    return var


# =============================================================================
# WRITE Statement Parsing (T042)
# =============================================================================

def parse_write_statement(write_content: str) -> MWriteStatement:
    """Parse WRITE command content into an MWriteStatement ASG node.
    
    Args:
        write_content: The content after 'WRITE ' or 'W ' command.
                      Example: '"Hello"', '!,X', '?10,"Text"'
        
    Returns:
        MWriteStatement with arguments list populated
        
    Examples:
        >>> stmt = parse_write_statement('"Hello, World"')
        >>> len(stmt.arguments)
        1
    """
    stmt = MWriteStatement()
    content = write_content.strip()
    
    if not content:
        return stmt
    
    # Parse arguments (comma-separated, with format controls)
    args = _split_write_arguments(content)
    
    for arg_str in args:
        arg_str = arg_str.strip()
        if not arg_str:
            continue
        
        # Check for format controls
        if arg_str == '!':
            # New line
            stmt.arguments.append({'type': 'newline'})
        elif arg_str == '#':
            # Form feed / page break
            stmt.arguments.append({'type': 'formfeed'})
        elif arg_str.startswith('?'):
            # Tab to column
            stmt.arguments.append({'type': 'tab', 'column': arg_str[1:]})
        else:
            # Expression
            stmt.arguments.append(_make_literal(arg_str))
    
    return stmt


def _split_write_arguments(content: str) -> List[str]:
    """Split WRITE content into individual arguments.
    
    Respects strings and parentheses.
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    
    i = 0
    while i < len(content):
        char = content[i]
        
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            result.append(current)
            current = ""
        elif char == ' ' and paren_depth == 0:
            # Space might end WRITE arguments
            result.append(current)
            break
        else:
            current += char
        
        i += 1
    
    if current:
        result.append(current)
    
    return result


# =============================================================================
# QUIT Statement Parsing (T042)
# =============================================================================

def parse_quit_statement(quit_content: str) -> MQuitStatement:
    """Parse QUIT command content into an MQuitStatement ASG node.
    
    Args:
        quit_content: The content after 'QUIT ' or 'Q ' command.
                     Example: "", "X*2", ":X>10" (postcondition)
        
    Returns:
        MQuitStatement with optional return_value
        
    Examples:
        >>> stmt = parse_quit_statement("")
        >>> stmt.return_value is None
        True
        >>> stmt = parse_quit_statement("X*2")
        >>> stmt.return_value is not None
        True
    """
    from ..asg.statements import MQuitStatement
    
    stmt = MQuitStatement()
    content = quit_content.strip()
    
    if not content:
        return stmt
    
    # Check for postcondition at start (Q:cond or Q:cond value)
    if content.startswith(':'):
        # Postcondition - parse condition
        # Find end of condition (space or end of string)
        space_pos = content.find(' ', 1)
        if space_pos != -1:
            cond_str = content[1:space_pos]
            value_str = content[space_pos+1:].strip()
            stmt.postcondition = _make_literal(cond_str)
            if value_str:
                stmt.return_value = _make_literal(value_str)
        else:
            stmt.postcondition = _make_literal(content[1:])
    else:
        # No postcondition - entire content is return value
        stmt.return_value = _make_literal(content)
    
    return stmt


# =============================================================================
# IF Statement Parsing (T043)
# =============================================================================

def parse_if_statement(if_content: str) -> MIfStatement:
    """Parse IF command content into an MIfStatement ASG node.
    
    Args:
        if_content: The content after 'IF ' or 'I ' command.
                   Example: "X=1 W Y", "X>0", "" (uses $TEST)
        
    Returns:
        MIfStatement with condition and then_scope
        
    Examples:
        >>> stmt = parse_if_statement("X=1 W Y")
        >>> stmt.condition is not None
        True
        >>> stmt = parse_if_statement("")
        >>> stmt.condition is None
        True
    """
    stmt = MIfStatement()
    stmt.then_scope = MScope()
    
    content = if_content.strip()
    
    if not content:
        # Argumentless IF - uses $TEST
        stmt.condition = None
        return stmt
    
    # The first token is the condition, rest goes in then_scope
    # Condition ends at first space (unless in parens/strings)
    cond_str, body_content = _split_if_condition(content)
    
    if cond_str:
        stmt.condition = _make_literal(cond_str)
    
    # Store raw body content for later parsing
    stmt._body_content = body_content
    
    return stmt


def _split_if_condition(content: str) -> Tuple[str, str]:
    """Split IF content into condition and body.
    
    Returns tuple of (condition_string, body_string).
    """
    paren_depth = 0
    in_string = False
    
    i = 0
    while i < len(content):
        char = content[i]
        
        if char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ' ' and paren_depth == 0:
                # Found end of condition
                return content[:i], content[i+1:]
        
        i += 1
    
    # No space found - entire content is condition
    return content, ""


# =============================================================================
# Command Extraction Functions
# =============================================================================

def extract_set_from_line(line_rest: str) -> Optional[Tuple[str, str]]:
    """Extract SET command from a line.
    
    Returns tuple of (set_content, remaining_content) if SET found, None otherwise.
    """
    for match in re.finditer(r'(?:^|\s)(SET|S)\s+', line_rest, re.IGNORECASE):
        pos = match.start()
        
        # Check not inside string
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        after_set = line_rest[match.end():]
        return after_set, ""
    
    return None


def extract_write_from_line(line_rest: str) -> Optional[Tuple[str, str]]:
    """Extract WRITE command from a line.
    
    Returns tuple of (write_content, remaining_content) if WRITE found, None otherwise.
    """
    for match in re.finditer(r'(?:^|\s)(WRITE|W)\s+', line_rest, re.IGNORECASE):
        pos = match.start()
        
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        after_write = line_rest[match.end():]
        return after_write, ""
    
    return None


def extract_quit_from_line(line_rest: str) -> Optional[Tuple[str, str]]:
    """Extract QUIT command from a line.
    
    Returns tuple of (quit_content, remaining_content) if QUIT found, None otherwise.
    """
    for match in re.finditer(r'(?:^|\s)(QUIT|Q)(?:\s+|:|$)', line_rest, re.IGNORECASE):
        pos = match.start()
        
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        after_quit = line_rest[match.end()-1:] if line_rest[match.end()-1:].startswith(':') else line_rest[match.end():]
        return after_quit.strip(), ""
    
    return None


def extract_if_from_line(line_rest: str) -> Optional[Tuple[str, str]]:
    """Extract IF command from a line.
    
    Returns tuple of (if_content, remaining_content) if IF found, None otherwise.
    """
    for match in re.finditer(r'(?:^|\s)(IF|I)\s+', line_rest, re.IGNORECASE):
        pos = match.start()
        
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        after_if = line_rest[match.end():]
        return after_if, ""
    
    return None


# =============================================================================
# GOTO Statement Parsing (T065-T067 - Phase 5)
# =============================================================================

def parse_goto_statement(goto_content: str) -> "MGotoStatement":
    """Parse GOTO command content into an MGotoStatement ASG node.
    
    Args:
        goto_content: The content after 'GOTO ' or 'G ' command.
                     Example: "LABEL", "LABEL^ROUTINE", "A,B,C", "LABEL+2"
        
    Returns:
        MGotoStatement with targets list populated
        
    Examples:
        >>> stmt = parse_goto_statement("LABEL")
        >>> len(stmt.targets)
        1
        >>> stmt.targets[0].name
        'LABEL'
        
        >>> stmt = parse_goto_statement("LABEL^ROUTINE")
        >>> stmt.targets[0].routine
        'ROUTINE'
    """
    from ..asg.statements import MGotoStatement
    from ..asg.elements import MCall
    
    stmt = MGotoStatement()
    content = goto_content.strip()
    
    if not content:
        return stmt
    
    # Split by comma for multiple targets
    target_strs = _split_goto_targets(content)
    
    for target_str in target_strs:
        target_str = target_str.strip()
        if not target_str:
            continue
        
        call = _parse_goto_target(target_str)
        if call:
            stmt.targets.append(call)
    
    return stmt


def _split_goto_targets(content: str) -> List[str]:
    """Split GOTO content by commas, respecting parentheses.
    
    Returns list of target strings.
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    
    for char in content:
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            result.append(current)
            current = ""
        elif char == ' ' and paren_depth == 0 and not in_string:
            # Space ends the target list
            result.append(current)
            break
        else:
            current += char
    
    if current:
        result.append(current)
    
    return result


def _parse_goto_target(target_str: str) -> Optional["MCall"]:
    """Parse a single GOTO target into an MCall.
    
    GOTO targets can be:
    - label             Local label
    - label+offset      Label with offset
    - label^routine     External routine
    - ^routine          External routine entry point
    - label:condition   Postconditioned target
    
    Args:
        target_str: Single target like "LABEL", "A+2", "X^ROUTINE"
        
    Returns:
        MCall with name, routine, offset, postcondition populated
    """
    from ..asg.elements import MCall
    
    if not target_str:
        return None
    
    call = MCall()
    content = target_str
    
    # Check for postcondition (: after label, not inside offset expression)
    # Need to find colon that's NOT part of an offset expression
    postcond_pos = _find_postcondition_colon(content)
    if postcond_pos >= 0:
        call.postcondition = _make_literal(content[postcond_pos+1:])
        content = content[:postcond_pos]
    
    # Check for external routine (^)
    caret_pos = content.find('^')
    if caret_pos >= 0:
        # External routine
        label_part = content[:caret_pos]
        routine_part = content[caret_pos+1:]
        call.routine = routine_part.strip()
        content = label_part
    
    # Check for offset (+)
    plus_pos = _find_offset_plus(content)
    if plus_pos >= 0:
        call.name = content[:plus_pos].strip()
        offset_str = content[plus_pos+1:].strip()
        call.offset = _make_literal(offset_str)
    else:
        call.name = content.strip()
    
    return call


def _find_postcondition_colon(content: str) -> int:
    """Find the position of a postcondition colon.
    
    Returns -1 if no postcondition, or the index of the colon.
    The colon must come after the label/routine (not part of offset).
    """
    # Postcondition colon appears at the end, after label+offset^routine
    # Pattern: target:condition
    # We need to find colon that's NOT inside parentheses
    paren_depth = 0
    
    for i, char in enumerate(content):
        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif char == ':' and paren_depth == 0:
            # Check if this looks like a postcondition
            # Postcondition comes AFTER the target, so no ^ or + after it
            rest = content[i+1:]
            # If there's no ^ or + in rest (outside parens), it's a postcondition
            if '^' not in rest and '+' not in rest.split('(')[0]:
                return i
    
    return -1


def _find_offset_plus(content: str) -> int:
    """Find the position of an offset + sign.
    
    Returns -1 if no offset, or the index of the +.
    """
    # Offset + comes between label and offset expression
    # Must be outside parentheses
    paren_depth = 0
    
    for i, char in enumerate(content):
        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif char == '+' and paren_depth == 0:
            return i
    
    return -1


def extract_goto_from_line(line_rest: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Extract GOTO command from a line.
    
    Args:
        line_rest: The rest of the line content
        
    Returns:
        Tuple of (target_name, routine, offset) if GOTO found, None otherwise.
        Only returns the first target for simple extraction.
    """
    for match in re.finditer(r'(?:^|\s)(GOTO|G)\s+', line_rest, re.IGNORECASE):
        pos = match.start()
        
        # Check not inside string
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        after_goto = line_rest[match.end():]
        
        # Parse the first target
        stmt = parse_goto_statement(after_goto)
        if stmt.targets:
            target = stmt.targets[0]
            offset_str = target.offset.raw_value if target.offset else None
            return target.name, target.routine, offset_str
        
        return None
    
    return None


# =============================================================================
# GOTO Classification (T080-T087 - Phase 5)
# =============================================================================

def classify_gotos(routine: "MRoutine") -> None:
    """Classify all GOTO statements in a routine.
    
    This function analyzes each MGotoStatement in the routine and:
    1. Sets the goto_type based on target and context
    2. Populates exits_loops with enclosing FOR loops exited
    
    Must be called AFTER resolve_references() so MCall.target is populated.
    
    Args:
        routine: The MRoutine to classify GOTOs in
        
    Side Effects:
        - Sets MGotoStatement.goto_type for each GOTO
        - Sets MGotoStatement.exits_loops for loop exits
    """
    from ..asg.statements import MGotoStatement, MForStatement
    from ..asg.enums import GotoType
    
    # Build a position map for labels (for forward/backward detection)
    label_positions = {}
    for i, label in enumerate(routine.labels):
        label_positions[label.name] = i
    
    # Process each label's statements
    for label_idx, label in enumerate(routine.labels):
        _classify_gotos_in_scope(
            label.body,
            label_idx,
            label,
            label_positions,
            routine,
            enclosing_fors=[]
        )


def _classify_gotos_in_scope(
    scope: "MScope",
    current_label_idx: int,
    current_label: "MLabel",
    label_positions: dict,
    routine: "MRoutine",
    enclosing_fors: List["MForStatement"]
) -> None:
    """Classify GOTOs within a scope, tracking enclosing FORs.
    
    Args:
        scope: The scope to scan for GOTOs
        current_label_idx: Index of current label in routine
        current_label: The MLabel containing this scope
        label_positions: Label name -> position mapping
        routine: The containing routine
        enclosing_fors: Stack of enclosing FOR loops (innermost last)
    """
    from ..asg.statements import MGotoStatement, MForStatement
    from ..asg.enums import GotoType
    
    for stmt in scope.statements:
        if isinstance(stmt, MGotoStatement):
            _classify_single_goto(
                stmt,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )
        elif isinstance(stmt, MForStatement):
            # Recurse into FOR body with this FOR added to enclosing stack
            if stmt.body:
                _classify_gotos_in_scope(
                    stmt.body,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors + [stmt]
                )
        # Recurse into other nested scopes
        elif hasattr(stmt, 'then_scope') and stmt.then_scope:
            _classify_gotos_in_scope(
                stmt.then_scope,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )
        elif hasattr(stmt, 'else_scope') and stmt.else_scope:
            _classify_gotos_in_scope(
                stmt.else_scope,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )
        elif hasattr(stmt, 'body') and stmt.body:
            _classify_gotos_in_scope(
                stmt.body,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )


def _classify_single_goto(
    stmt: "MGotoStatement",
    current_label_idx: int,
    current_label: "MLabel",
    label_positions: dict,
    routine: "MRoutine",
    enclosing_fors: List["MForStatement"]
) -> None:
    """Classify a single GOTO statement.
    
    Sets stmt.goto_type and stmt.exits_loops based on:
    - Target resolution status
    - Target location relative to source
    - Enclosing control structures
    
    Args:
        stmt: The MGotoStatement to classify
        current_label_idx: Index of current label
        current_label: The containing MLabel
        label_positions: Label name -> position mapping
        routine: The containing routine
        enclosing_fors: Stack of enclosing FOR loops
    """
    from ..asg.enums import GotoType
    
    # Check each target (usually just one, but GOTO can have multiple)
    for call in stmt.targets:
        # External call (^routine)
        if call.routine is not None:
            stmt.goto_type = GotoType.EXTERNAL
            continue
        
        # Unresolved reference
        if not call.is_resolved or call.target is None:
            stmt.goto_type = GotoType.UNRESOLVED
            continue
        
        target_label = call.target
        target_label_idx = label_positions.get(target_label.name, -1)
        
        # Same label = forward or backward within label
        if target_label.name == current_label.name:
            # Within same label - need line numbers to determine direction
            # For now, use a heuristic: if target line < source line = backward
            # If no line info, assume forward
            source_line = stmt.line_number or 0
            # For targets within same label, we'd need to track statement order
            # Simplify: treat as FORWARD for now
            stmt.goto_type = GotoType.FORWARD_JUMP
        else:
            # Different label = cross-label jump
            if target_label_idx < current_label_idx:
                # Jumping backward to earlier label
                stmt.goto_type = GotoType.BACKWARD_JUMP
            else:
                # Jumping forward to later label
                stmt.goto_type = GotoType.FORWARD_JUMP
        
        # If inside FOR loops, this is a loop exit
        if enclosing_fors:
            if len(enclosing_fors) == 1:
                stmt.goto_type = GotoType.LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)
            else:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)
        
        # If jumping to different label while inside FOR, it's a cross-label exit
        if enclosing_fors and target_label.name != current_label.name:
            if len(enclosing_fors) > 1:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
            else:
                stmt.goto_type = GotoType.LOOP_EXIT
            stmt.exits_loops = list(enclosing_fors)


def get_loop_exiting_gotos(routine: "MRoutine") -> List["MGotoStatement"]:
    """Get all GOTOs that exit FOR loops.
    
    Args:
        routine: The MRoutine to scan
        
    Returns:
        List of MGotoStatement objects that have exits_loops populated
    """
    from ..asg.statements import MGotoStatement
    
    result = []
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.exits_loops:
                    result.append(stmt)
    return result


def get_gotos_by_type(routine: "MRoutine", goto_type: "GotoType") -> List["MGotoStatement"]:
    """Get all GOTOs of a specific type.
    
    Args:
        routine: The MRoutine to scan
        goto_type: The GotoType to filter by
        
    Returns:
        List of MGotoStatement objects with matching goto_type
    """
    from ..asg.statements import MGotoStatement
    
    result = []
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.goto_type == goto_type:
                    result.append(stmt)
    return result


# =============================================================================
# NEW Statement Parsing (T088-T089, T093 - Phase 6)
# =============================================================================

def parse_new_statement(new_content: str) -> "MNewStatement":
    """Parse NEW command content into an MNewStatement ASG node.
    
    NEW command creates new local scope for variables:
    - N X          - NEW single variable
    - N X,Y,Z      - NEW multiple variables
    - N (X)        - Exclusive NEW (all except X)
    - N (X,Y)      - Exclusive NEW (all except X and Y)
    - N            - Argumentless NEW (rare)
    
    Args:
        new_content: The content after 'NEW ' or 'N ' command.
                    Example: "X", "X,Y,Z", "(X,Y)"
        
    Returns:
        MNewStatement with variables list and exclusive flag
        
    Examples:
        >>> stmt = parse_new_statement("X,Y,Z")
        >>> stmt.variables
        ['X', 'Y', 'Z']
        >>> stmt.exclusive
        False
        
        >>> stmt = parse_new_statement("(X)")
        >>> stmt.exclusive
        True
        >>> stmt.except_list
        ['X']
    """
    from ..asg.statements import MNewStatement
    
    stmt = MNewStatement()
    content = new_content.strip()
    
    if not content:
        # Argumentless NEW - rare but valid
        return stmt
    
    # Check for exclusive NEW: (var) or (var1,var2)
    if content.startswith('('):
        stmt.exclusive = True
        # Find matching close paren
        paren_end = content.find(')')
        if paren_end > 0:
            inner = content[1:paren_end]
            # Parse exception list
            stmt.except_list = _parse_variable_list(inner)
        return stmt
    
    # Regular NEW: parse variable list
    stmt.variables = _parse_variable_list(content)
    
    return stmt


def _parse_variable_list(content: str) -> List[str]:
    """Parse comma-separated variable list.
    
    Args:
        content: Comma-separated variables like "X,Y,Z"
        
    Returns:
        List of variable names
    """
    result = []
    current = ""
    paren_depth = 0
    
    for char in content:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            if current.strip():
                result.append(current.strip())
            current = ""
        elif char == ' ' and paren_depth == 0 and not current.strip():
            # Leading whitespace
            pass
        elif char == ' ' and paren_depth == 0:
            # Space ends the list
            if current.strip():
                result.append(current.strip())
            break
        else:
            current += char
    
    if current.strip():
        result.append(current.strip())
    
    return result


def extract_new_from_line(line_rest: str) -> Optional[Tuple[str, str]]:
    """Extract NEW command from a line.
    
    Returns tuple of (new_content, remaining_content) if NEW found, None otherwise.
    """
    for match in re.finditer(r'(?:^|\s)(NEW|N)\s+', line_rest, re.IGNORECASE):
        pos = match.start()
        
        # Check not inside string
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        # Make sure it's not $N (intrinsic)
        if pos > 0 and line_rest[pos-1] == '$':
            continue
        
        after_new = line_rest[match.end():]
        return after_new, ""
    
    return None


# =============================================================================
# DO Statement Parsing (T090, T094-T097 - Phase 6)
# =============================================================================

def parse_do_statement(do_content: str) -> "MDoStatement":
    """Parse DO command content into an MDoStatement ASG node.
    
    DO command calls subroutines:
    - D LABEL           - Call local label
    - D LABEL^ROUTINE   - Call external routine
    - D LABEL(args)     - Call with arguments
    - D A,B,C           - Multiple targets
    - D                 - Argumentless DO (block start)
    
    Args:
        do_content: The content after 'DO ' or 'D ' command.
                   Example: "LABEL", "A^ROUTINE", "SUB(X,Y)"
        
    Returns:
        MDoStatement with targets list populated
        
    Examples:
        >>> stmt = parse_do_statement("LABEL")
        >>> len(stmt.targets)
        1
        >>> stmt.targets[0].name
        'LABEL'
    """
    from ..asg.statements import MDoStatement, MDoBlockStatement
    from ..asg.elements import MCall
    
    content = do_content.strip()
    
    # Check for argumentless DO (block start)
    if not content or content.startswith('.') or content[0] in ('\n', '\r'):
        # This is actually MDoBlockStatement but we return MDoStatement for now
        # The parser will handle the block structure
        return MDoStatement()
    
    stmt = MDoStatement()
    
    # Split by comma for multiple targets
    target_strs = _split_do_targets(content)
    
    for target_str in target_strs:
        target_str = target_str.strip()
        if not target_str:
            continue
        
        call = _parse_do_target(target_str)
        if call:
            stmt.targets.append(call)
    
    return stmt


def _split_do_targets(content: str) -> List[str]:
    """Split DO content by commas, respecting parentheses.
    
    Returns list of target strings.
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    
    for char in content:
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            result.append(current)
            current = ""
        elif char == ' ' and paren_depth == 0 and not in_string:
            # Space ends the target list (postcondition or next command)
            result.append(current)
            break
        else:
            current += char
    
    if current:
        result.append(current)
    
    return result


def _parse_do_target(target_str: str) -> Optional["MCall"]:
    """Parse a single DO target into an MCall.
    
    DO targets can be:
    - label             Local label
    - label+offset      Label with offset
    - label^routine     External routine
    - ^routine          External routine entry point
    - label(args)       Call with arguments
    - label:condition   Postconditioned target
    
    Args:
        target_str: Single target like "LABEL", "SUB(X)", "X^ROUTINE"
        
    Returns:
        MCall with name, routine, offset, arguments, postcondition populated
    """
    from ..asg.elements import MCall
    
    if not target_str:
        return None
    
    call = MCall()
    content = target_str
    
    # Check for postcondition (: after everything else)
    postcond_pos = _find_do_postcondition(content)
    if postcond_pos >= 0:
        call.postcondition = _make_literal(content[postcond_pos+1:])
        content = content[:postcond_pos]
    
    # Check for arguments (...)
    args_start = content.find('(')
    if args_start >= 0:
        args_end = content.rfind(')')
        if args_end > args_start:
            args_str = content[args_start+1:args_end]
            call.arguments = _parse_argument_list(args_str)
            content = content[:args_start]
    
    # Check for external routine (^)
    caret_pos = content.find('^')
    if caret_pos >= 0:
        label_part = content[:caret_pos]
        routine_part = content[caret_pos+1:]
        call.routine = routine_part.strip()
        content = label_part
    
    # Check for offset (+)
    plus_pos = _find_offset_plus(content)
    if plus_pos >= 0:
        call.name = content[:plus_pos].strip()
        offset_str = content[plus_pos+1:].strip()
        call.offset = _make_literal(offset_str)
    else:
        call.name = content.strip()
    
    return call


def _find_do_postcondition(content: str) -> int:
    """Find the position of a postcondition colon in DO target.
    
    Returns -1 if no postcondition, or the index of the colon.
    """
    paren_depth = 0
    
    for i, char in enumerate(content):
        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif char == ':' and paren_depth == 0:
            # Check if this looks like a postcondition
            # (not part of arguments or offset)
            rest = content[i+1:]
            if '^' not in rest and '+' not in rest.split('(')[0]:
                return i
    
    return -1


def _parse_argument_list(args_str: str) -> List:
    """Parse comma-separated argument list.
    
    Args:
        args_str: Arguments inside parentheses, like "X,Y,1+2"
        
    Returns:
        List of MLiteral objects (for now - will be MExpr in full implementation)
    """
    result = []
    current = ""
    paren_depth = 0
    in_string = False
    
    for char in args_str:
        if char == '"':
            in_string = not in_string
            current += char
        elif in_string:
            current += char
        elif char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            if current.strip():
                result.append(_make_literal(current.strip()))
            current = ""
        else:
            current += char
    
    if current.strip():
        result.append(_make_literal(current.strip()))
    
    return result


def extract_do_from_line(line_rest: str) -> Optional[Tuple[str, str]]:
    """Extract DO command from a line.
    
    Returns tuple of (do_content, remaining_content) if DO found, None otherwise.
    """
    for match in re.finditer(r'(?:^|\s)(DO|D)\s+', line_rest, re.IGNORECASE):
        pos = match.start()
        
        # Check not inside string
        quote_count = line_rest[:pos].count('"')
        if quote_count % 2 == 1:
            continue
        
        # Make sure it's not $D (intrinsic)
        if pos > 0 and line_rest[pos-1] == '$':
            continue
        
        after_do = line_rest[match.end():]
        return after_do, ""
    
    return None


# =============================================================================
# Unreachable Code Detection
# =============================================================================


def detect_unreachable_code(lines: List[str]) -> List[Tuple[int, str]]:
    """Detect unreachable code after unconditional GOTO or QUIT.
    
    Scans a list of MUMPS lines and identifies lines that cannot be
    reached because they follow an unconditional GOTO or QUIT command.
    
    According to FR-053, unreachable code should be flagged during analysis.
    
    Args:
        lines: List of MUMPS source lines
        
    Returns:
        List of (line_number, reason) tuples for unreachable lines
        Line numbers are 1-indexed
    """
    unreachable = []
    after_unconditional_exit = False
    unconditional_exit_line = 0
    
    for i, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        
        # Skip empty lines and comment lines
        if not line_stripped or line_stripped.startswith(';'):
            continue
        
        # Check if this is a label line (starts with non-space)
        # Labels reset reachability since they can be GOTO targets
        if line and line[0] not in ' \t':
            after_unconditional_exit = False
            continue
        
        # If we're after an unconditional exit, this code is unreachable
        if after_unconditional_exit:
            unreachable.append((i, f"unreachable after unconditional exit on line {unconditional_exit_line}"))
            continue
        
        # Check for unconditional GOTO (G/GOTO without postcondition)
        if _is_unconditional_goto(line_stripped):
            after_unconditional_exit = True
            unconditional_exit_line = i
            continue
        
        # Check for unconditional QUIT (Q/QUIT without postcondition)
        if _is_unconditional_quit(line_stripped):
            after_unconditional_exit = True
            unconditional_exit_line = i
            continue
    
    return unreachable


def _is_unconditional_goto(line: str) -> bool:
    """Check if a line contains an unconditional GOTO command.
    
    An unconditional GOTO is one without a postcondition (:condition).
    It must be the last command on the line for subsequent code to be unreachable.
    
    Args:
        line: The line content (stripped)
        
    Returns:
        True if line ends with an unconditional GOTO
    """
    line_upper = line.upper()
    
    # Match GOTO/G at end of meaningful content
    # Pattern: GOTO target or G target (with optional spaces)
    # Not followed by more commands
    
    # Find GOTO/G commands
    matches = list(re.finditer(r'\b(GOTO|G)\s+(\S+)', line_upper))
    if not matches:
        return False
    
    # Get the last GOTO match
    last_match = matches[-1]
    target = last_match.group(2)
    
    # Check if there's a postcondition (target:condition)
    if ':' in target:
        # Split to check - could be label:condition or just target with :
        parts = target.split(':')
        if len(parts) > 1 and parts[1]:
            # Has postcondition, not unconditional
            return False
    
    # Check if this GOTO is the last thing on the line (ignoring comments)
    after_goto = line[last_match.end():].strip()
    
    # Remove trailing comment
    if ';' in after_goto:
        after_goto = after_goto[:after_goto.index(';')].strip()
    
    # If nothing after GOTO target, it's unconditional
    return not after_goto


def _is_unconditional_quit(line: str) -> bool:
    """Check if a line contains an unconditional QUIT command.
    
    An unconditional QUIT is one without a postcondition (:condition).
    It must be the last command on the line for subsequent code to be unreachable.
    
    Args:
        line: The line content (stripped)
        
    Returns:
        True if line ends with an unconditional QUIT
    """
    line_upper = line.upper()
    
    # Match QUIT/Q patterns
    # Q (bare quit), Q value (with return value)
    # But not Q:condition (conditional quit)
    
    # Find QUIT/Q commands
    matches = list(re.finditer(r'\b(QUIT|Q)(?:\s+(\S+)|\s*$)', line_upper))
    if not matches:
        return False
    
    # Get the last QUIT match
    last_match = matches[-1]
    
    # Check the original line (not uppercased) for postcondition
    original_segment = line[last_match.start():last_match.end()]
    
    # Look for postcondition pattern: Q:cond or QUIT:cond
    quit_prefix = line[last_match.start():].lstrip()
    
    if quit_prefix.upper().startswith('QUIT:') or quit_prefix.upper().startswith('Q:'):
        # Has postcondition
        return False
    
    # Check if this QUIT is the last thing on the line (ignoring comments)
    after_quit = line[last_match.end():].strip()
    
    # Remove trailing comment
    if ';' in after_quit:
        after_quit = after_quit[:after_quit.index(';')].strip()
    
    # If nothing after QUIT, it's unconditional
    return not after_quit

