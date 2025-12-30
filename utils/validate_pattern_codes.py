"""Validate pattern compiler behavior against MUMPS spec."""

import re
from m2py.analysis.pattern_compiler import compile_pattern_to_regex


def test_pattern_codes():
    """Verify pattern codes match MUMPS 1990 spec definitions."""
    print("=== Pattern Code Validation ===\n")

    # Per MUMPS 1990 spec 7.2.3:
    # C: 33 ASCII control characters, including DEL (0-31 and 127)
    # N: 10 ASCII numeric characters (0-9)
    # P: 33 ASCII punctuation characters, including SP
    # A: 52 ASCII alphabetic characters (a-zA-Z)
    # L: 26 ASCII lower-case alphabetic characters (a-z)
    # U: 26 ASCII upper-case alphabetic characters (A-Z)
    # E: Everything (the entire set of ASCII characters)

    tests = [
        # (pattern, test_string, expected_match)
        ("1N", "5", True),
        ("1N", "a", False),
        ("1A", "A", True),
        ("1A", "5", False),
        ("1L", "a", True),
        ("1L", "A", False),
        ("1U", "A", True),
        ("1U", "a", False),
        (".E", "", True),
        (".E", "anything", True),
        (".E", "with\nnewline", False),  # E with re.DOTALL would match this
        ("1P", " ", True),
        ("1P", "!", True),
        ("1P", "a", False),
        ("1C", "\x00", True),  # NUL
        ("1C", "\x7f", True),  # DEL
        ("1C", "a", False),
    ]

    for pattern, test_str, expected in tests:
        regex = compile_pattern_to_regex(pattern)
        match = re.fullmatch(regex, test_str) is not None
        status = "✓" if match == expected else "✗"
        escaped_str = repr(test_str)
        print(f"  {status} {pattern} vs {escaped_str}: {match} (expected {expected})")
        if match != expected:
            print(f"    Regex: {regex}")


def test_e_code_with_newline():
    """Specific test: E pattern code and newlines.

    MUMPS spec says E matches 'Everything (the entire set of ASCII characters)'.
    This includes newlines, so .E should match strings with newlines.
    Current implementation uses '.' without re.DOTALL flag, so newlines don't match.
    """
    print("\n=== E Code and Newlines ===\n")

    regex = compile_pattern_to_regex(".E")
    print(f"  Compiled regex for '.E': {repr(regex)}")

    test_string = "line1\nline2"
    match = re.fullmatch(regex, test_string) is not None
    print(f"  Match 'line1\\nline2': {match}")

    match_dotall = re.fullmatch(regex, test_string, re.DOTALL) is not None
    print(f"  Match with re.DOTALL: {match_dotall}")

    # Note: In generated Python code, we'd need to use re.DOTALL flag
    # for the E pattern code to be spec-compliant
    print("\n  Implication: Generated Python code needs re.DOTALL flag for E code")


def test_p_code_coverage():
    """Validate P code covers all 33 ASCII punctuation characters.

    Per MUMPS spec, P includes 'SP' (space) and 32 ASCII punctuation chars.
    ASCII punctuation: !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
    Plus space = 33 characters.
    """
    print("\n=== P Code Coverage ===\n")

    # All 33 P characters per MUMPS spec
    p_chars = " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
    print(f"  Expected P characters ({len(p_chars)}): {repr(p_chars)}")

    regex = compile_pattern_to_regex("1P")
    print(f"  Compiled regex for '1P': {repr(regex)}")

    matches = []
    non_matches = []
    for c in p_chars:
        if re.fullmatch(regex, c):
            matches.append(c)
        else:
            non_matches.append(c)

    print(f"  Matches: {len(matches)}/{len(p_chars)}")
    if non_matches:
        print(f"  Missing: {repr(''.join(non_matches))}")
    else:
        print("  ✓ All punctuation characters covered")


if __name__ == "__main__":
    test_pattern_codes()
    test_e_code_with_newline()
    test_p_code_coverage()
