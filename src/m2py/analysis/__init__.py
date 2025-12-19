"""ASG analysis passes for reference resolution, classification, and variable analysis."""

from m2py.analysis.classifier import (
    classify_for_loop,
    extract_for_from_line,
    ForPattern,
)

__all__ = [
    "classify_for_loop",
    "extract_for_from_line",
    "ForPattern",
]
