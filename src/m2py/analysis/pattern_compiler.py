"""MUMPS Pattern to Python Regex Compiler.

Converts MUMPS pattern match expressions to equivalent Python regex patterns.

MUMPS pattern codes:
- A: Alphabetic characters (a-zA-Z)
- C: Control characters (ASCII 0-31 and 127)
- E: Everything (any character)
- L: Lowercase alphabetic (a-z)
- N: Numeric characters (0-9)
- P: Punctuation (space and ASCII punctuation)
- U: Uppercase alphabetic (A-Z)

MUMPS pattern syntax:
- n: Exact count (e.g., 3A = exactly 3 letters)
- n.: At least n (e.g., 1. = at least 1)
- .n: At most n (e.g., .5 = 0 to 5)
- n.m: Range (e.g., 1.3 = 1 to 3)
- .: Any number (e.g., .A = 0 or more letters)
- "string": Literal string match
- (alt1,alt2): Alternation

Examples:
- 1A.N → one letter followed by any number of digits
- 3N1"-"4N → 3 digits, dash, 4 digits (phone format)
- .E → any string (including empty)

Codegen Note:
    The E pattern code generates `.` which does NOT match newlines by default.
    Per MUMPS 1995 spec 7.2.3, E matches "any character including non-printable"
    which includes newlines. Code generators MUST use re.DOTALL flag when
    compiling patterns containing E code to ensure correct newline handling.
"""

import re
from typing import List, Optional, Tuple


# Pattern code to regex character class mapping
PATCODE_MAP = {
    "A": r"[A-Za-z]",
    "C": r"[\x00-\x1f\x7f]",
    "E": r".",  # Any character (need DOTALL for newlines)
    "L": r"[a-z]",
    "N": r"[0-9]",
    "P": r'[ !"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~]',
    "U": r"[A-Z]",
}

# Character ranges for combining multiple patcodes
# These are the raw ranges without the [] brackets
PATCODE_RANGES = {
    "A": r"A-Za-z",
    "C": r"\x00-\x1f\x7f",
    "E": None,  # Special case - matches everything
    "L": r"a-z",
    "N": r"0-9",
    "P": r' !"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~',
    "U": r"A-Z",
}


def _combine_patcodes(patcodes: List[str]) -> str:
    """Combine multiple patcodes into a single character class.

    MUMPS patcodes can be combined (e.g., AN = alphanumeric).
    The combined class matches any character from any of the codes.
    """
    # If E (everything) is included, just return .
    if "E" in patcodes:
        return r"."

    # Combine ranges for all patcodes (grammar ensures only valid codes)
    ranges = []
    for code in patcodes:
        if code in PATCODE_RANGES and PATCODE_RANGES[code]:
            ranges.append(PATCODE_RANGES[code])

    return f"[{''.join(ranges)}]"


class PatternCompileError(Exception):
    """Error during pattern compilation."""

    pass


def compile_pattern_to_regex(pattern: str) -> str:
    """Convert a MUMPS pattern to a Python regex pattern.

    Args:
        pattern: MUMPS pattern string (e.g., "1A.N", '3N"-"4N')

    Returns:
        Python regex pattern string for use with re.fullmatch()

    Raises:
        PatternCompileError: If the pattern is invalid or unsupported

    Examples:
        >>> compile_pattern_to_regex("1A.N")
        '[A-Za-z][0-9]*'
        >>> compile_pattern_to_regex("3N")
        '[0-9]{3}'
        >>> compile_pattern_to_regex(".E")
        '.*'
    """
    if not pattern:
        return ""

    result = []
    pos = 0

    while pos < len(pattern):
        # Try to parse a pattern atom
        atom_regex, new_pos = _parse_pattern_atom(pattern, pos)
        result.append(atom_regex)
        pos = new_pos

    return "".join(result)


def _parse_pattern_atom(pattern: str, pos: int) -> Tuple[str, int]:
    """Parse a single pattern atom and return its regex equivalent.

    Returns:
        Tuple of (regex_string, new_position)
    """
    start_pos = pos

    # Parse the repeat count
    min_count, max_count, pos = _parse_repeat_count(pattern, pos)

    if pos >= len(pattern):
        raise PatternCompileError(
            f"Pattern ends unexpectedly after repeat count at position {start_pos}"
        )

    # Parse what follows: patcode, string literal, or alternation
    char = pattern[pos]

    if char == '"':
        # String literal
        literal, pos = _parse_string_literal(pattern, pos)

        # Special case: empty string literal
        # Any number of empty strings is still empty string, so n"" only matches ""
        # regardless of the quantifier. Return empty regex which fullmatch matches to "".
        if literal == "":
            return "", pos

        # Wrap in non-capturing group if literal has multiple chars and quantifier needed
        escaped = re.escape(literal)
        if len(literal) > 1 and not (min_count == 1 and max_count == 1):
            base_regex = f"(?:{escaped})"
        else:
            base_regex = escaped
    elif char == "(":
        # Alternation
        alt_regex, pos = _parse_alternation(pattern, pos)
        # Always wrap group content in non-capturing group when quantified,
        # to avoid adjacent quantifiers like [0-9]{5}{2} (invalid regex)
        if not (min_count == 1 and max_count == 1):
            base_regex = f"(?:{alt_regex})"
        else:
            base_regex = alt_regex
    elif char.upper() in PATCODE_MAP:
        # Pattern code - can be multiple letters (e.g., AN = alphanumeric)
        # Each letter is a patcode and the combination means "any of these"
        patcodes = []
        while pos < len(pattern) and pattern[pos].upper() in PATCODE_MAP:
            patcodes.append(pattern[pos].upper())
            pos += 1

        if len(patcodes) == 1:
            base_regex = PATCODE_MAP[patcodes[0]]
        else:
            # Combine multiple patcodes into a single character class
            base_regex = _combine_patcodes(patcodes)
    else:
        raise PatternCompileError(
            f"Unexpected character '{char}' at position {pos} in pattern"
        )

    # Apply repeat count as regex quantifier
    quantified = _apply_quantifier(base_regex, min_count, max_count)

    return quantified, pos


def _parse_repeat_count(
    pattern: str, pos: int
) -> Tuple[Optional[int], Optional[int], int]:
    """Parse the repeat count portion of a pattern atom.

    Returns:
        Tuple of (min_count, max_count, new_position)
        - (None, None) means exactly 1
        - (n, None) means at least n
        - (None, m) means 0 to m
        - (n, m) means n to m
        - (n, n) means exactly n
    """

    # Collect first number if present
    first_num = ""
    while pos < len(pattern) and pattern[pos].isdigit():
        first_num += pattern[pos]
        pos += 1

    # Check for dot (range indicator)
    if pos < len(pattern) and pattern[pos] == ".":
        pos += 1  # consume the dot

        # Collect second number if present
        second_num = ""
        while pos < len(pattern) and pattern[pos].isdigit():
            second_num += pattern[pos]
            pos += 1

        # Interpret the range
        if first_num and second_num:
            # n.m - range from n to m
            return int(first_num), int(second_num), pos
        elif first_num:
            # n. - at least n
            return int(first_num), None, pos
        elif second_num:
            # .m - 0 to m
            return 0, int(second_num), pos
        else:
            # just . - any number (0 or more)
            return 0, None, pos
    elif first_num:
        # Just a number - exactly n
        n = int(first_num)
        return n, n, pos
    else:
        # No repeat count at all - default is exactly 1
        return 1, 1, pos


def _parse_string_literal(pattern: str, pos: int) -> Tuple[str, int]:
    """Parse a quoted string literal from the pattern.

    Returns:
        Tuple of (literal_value, new_position)
    """
    if pattern[pos] != '"':
        raise PatternCompileError(f"Expected '\"' at position {pos}")

    pos += 1  # consume opening quote
    result = []

    while pos < len(pattern):
        if pattern[pos] == '"':
            # Check for escaped quote ("")
            if pos + 1 < len(pattern) and pattern[pos + 1] == '"':
                result.append('"')
                pos += 2
            else:
                # End of string
                pos += 1
                return "".join(result), pos
        else:
            result.append(pattern[pos])
            pos += 1

    raise PatternCompileError("Unterminated string literal in pattern")


def _parse_alternation(pattern: str, pos: int) -> Tuple[str, int]:
    """Parse an alternation (alt1,alt2,...) from the pattern.

    Returns:
        Tuple of (regex_alternation, new_position)
    """
    if pattern[pos] != "(":
        raise PatternCompileError(f"Expected '(' at position {pos}")

    pos += 1  # consume opening paren
    alternatives = []
    current_alt = []

    paren_depth = 0
    while pos < len(pattern):
        char = pattern[pos]

        if char == "(":
            paren_depth += 1
            current_alt.append(char)
            pos += 1
        elif char == ")":
            if paren_depth == 0:
                # End of alternation
                if current_alt:
                    alt_pattern = "".join(current_alt)
                    alternatives.append(compile_pattern_to_regex(alt_pattern))
                pos += 1
                break
            else:
                paren_depth -= 1
                current_alt.append(char)
                pos += 1
        elif char == "," and paren_depth == 0:
            # Separator between alternatives
            alt_pattern = "".join(current_alt)
            alternatives.append(compile_pattern_to_regex(alt_pattern))
            current_alt = []
            pos += 1
        elif char == '"':
            # Handle quoted strings (may contain commas/parens)
            current_alt.append(char)
            pos += 1
            while pos < len(pattern) and pattern[pos] != '"':
                current_alt.append(pattern[pos])
                pos += 1
                # Handle escaped quotes
                if (
                    pos > 0
                    and pos < len(pattern)
                    and pattern[pos - 1] == '"'
                    and pattern[pos] == '"'
                ):
                    current_alt.append(pattern[pos])
                    pos += 1
            if pos < len(pattern):
                current_alt.append(pattern[pos])
                pos += 1
        else:
            current_alt.append(char)
            pos += 1
    else:
        raise PatternCompileError("Unterminated alternation in pattern")

    if not alternatives:
        return "", pos
    elif len(alternatives) == 1:
        return alternatives[0], pos
    else:
        return f"(?:{'|'.join(alternatives)})", pos


def _apply_quantifier(
    base_regex: str, min_count: Optional[int], max_count: Optional[int]
) -> str:
    """Apply a repeat count as a regex quantifier.

    Args:
        base_regex: The base regex pattern to quantify
        min_count: Minimum repetitions (None means unbounded below)
        max_count: Maximum repetitions (None means unbounded above)

    Returns:
        The quantified regex pattern
    """
    if min_count == 1 and max_count == 1:
        # Exactly 1 - no quantifier needed
        return base_regex
    elif min_count == 0 and max_count is None:
        # 0 or more
        return f"{base_regex}*"
    elif min_count == 1 and max_count is None:
        # 1 or more
        return f"{base_regex}+"
    elif min_count == 0 and max_count == 1:
        # 0 or 1
        return f"{base_regex}?"
    elif min_count == max_count:
        # Exactly n
        return f"{base_regex}{{{min_count}}}"
    elif min_count == 0:
        # 0 to max
        return f"{base_regex}{{0,{max_count}}}"
    elif max_count is None:
        # min or more
        return f"{base_regex}{{{min_count},}}"
    else:
        # Range
        return f"{base_regex}{{{min_count},{max_count}}}"
