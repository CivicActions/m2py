"""MUMPS parser implementation using textX."""

from m2py.parser.parser import MUMPSParser, ForPatternResult, dump_asg_json
from m2py.parser.exceptions import MUMPSSyntaxError
from m2py.parser.line_parser import (
    parse_line_content,
    parse_commands_from_line,
    extract_for_commands,
    classify_for_command,
    detect_quit_after_for,
)

__all__ = [
    "MUMPSParser",
    "ForPatternResult",
    "MUMPSSyntaxError",
    "dump_asg_json",
    # Line parsing
    "parse_line_content",
    "parse_commands_from_line",
    "extract_for_commands",
    "classify_for_command",
    "detect_quit_after_for",
]
