"""ASG analysis passes for reference resolution, classification, and variable analysis."""

from m2py.analysis.classifier import (
    classify_for_loop,
    extract_for_from_line,
    parse_for_statement,
    parse_set_statement,
    parse_write_statement,
    parse_quit_statement,
    parse_if_statement,
    parse_goto_statement,
    extract_set_from_line,
    extract_write_from_line,
    extract_quit_from_line,
    extract_if_from_line,
    extract_goto_from_line,
    classify_gotos,
    get_loop_exiting_gotos,
    get_gotos_by_type,
    ForPattern,
)

from m2py.analysis.resolver import (
    resolve_references,
    get_unresolved_calls,
    get_external_calls,
)

__all__ = [
    "classify_for_loop",
    "extract_for_from_line",
    "parse_for_statement",
    "parse_set_statement",
    "parse_write_statement",
    "parse_quit_statement",
    "parse_if_statement",
    "parse_goto_statement",
    "extract_set_from_line",
    "extract_write_from_line",
    "extract_quit_from_line",
    "extract_if_from_line",
    "extract_goto_from_line",
    "classify_gotos",
    "get_loop_exiting_gotos",
    "get_gotos_by_type",
    "ForPattern",
    "resolve_references",
    "get_unresolved_calls",
    "get_external_calls",
]

