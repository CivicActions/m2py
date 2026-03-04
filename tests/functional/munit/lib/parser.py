"""Parse M-Unit framework output and OSEHRA TestList files."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .models import FailureDetail, MUnitResult, TestRoutineConfig

logger = logging.getLogger(__name__)

# --- M-Unit output patterns ---

# "Checked 9 tests, with 0 failures and encountered 0 errors."
# Also handles singular: "Checked 1 test, with 1 failure and encountered 0 errors."
_SUMMARY_RE = re.compile(
    r"Checked\s+(\d+)\s+tests?,\s+with\s+(\d+)\s+failures?\s+and\s+encountered\s+(\d+)\s+errors?\.",
)

# "Ran 1 Routine(s), 5 Entry Tag(s)"
_RAN_RE = re.compile(
    r"Ran\s+(\d+)\s+Routines?\(?s?\)?,\s+(\d+)\s+Entry\s+Tags?\(?s?\)?",
)

# Failure/error line: "ENTRY^ROUTINE - TestName - message"
# The entry_tag^routine prefix is required, followed by " - "
# Dots may precede the entry tag on the same line (M-Unit writes dots without newlines)
_FAILURE_LINE_RE = re.compile(
    r"(?:^|\.)(\w+)\^(%?\w+)\s+-\s+(.*)",
    re.MULTILINE,
)

# CHKEQ sub-pattern within a failure message: "<expected> vs <actual> - message"
_CHKEQ_RE = re.compile(r"<(.*)>\s+vs\s+<(.*)>\s+-\s+(.*)")

# Error sub-pattern: "Error: ..."
_ERROR_RE = re.compile(r"Error:\s+(.*)")

# --- TestList patterns ---

# "D EN^%ut("routine",verbosity)" style invocation
_TESTLIST_UTCALL_RE = re.compile(r'D\s+EN\^%ut\("(\w+)"(?:,\d+)?\)')

# "D TAG^ROUTINE" or "D ^ROUTINE" style invocation
_TESTLIST_DO_RE = re.compile(r"D\s+(\w+\^)?\^?(\w+)")

# Package name → tier mapping
_TIER_MAP: dict[str, int] = {
    "MASH Utilities": 1,
    "M XML Parser": 2,
    "VA FileMan": 3,
    "Problem List": 4,
    "Scheduling": 4,
    "Registration": 4,
}


def parse_munit_output(raw_output: str, routine: str, package: str) -> MUnitResult:
    """Parse raw M-Unit framework output text into a structured result.

    Args:
        raw_output: Complete captured text output from a single M-Unit routine execution.
        routine: Name of the routine that was executed (e.g., "%utt1", "MXMLBLD").
        package: Package name (e.g., "MASH Utilities", "M XML Parser").

    Returns:
        MUnitResult with parsed counts, status, and failure details.
    """
    result = MUnitResult(routine=routine, package=package, raw_output=raw_output)

    if not raw_output or not raw_output.strip():
        result.status = "error"
        result.error_message = "No output captured"
        return result

    # Extract failure/error detail lines first (before summary check)
    failure_details = _extract_failure_details(raw_output, routine)
    result.failure_details = failure_details

    # Parse summary line — use the LAST match because meta-tests like %utt1
    # run nested routines that each produce their own summary line.
    summary_matches = list(_SUMMARY_RE.finditer(raw_output))
    if summary_matches:
        summary_match = summary_matches[-1]
        result.total_tests = int(summary_match.group(1))
        result.failures = int(summary_match.group(2))
        result.errors = int(summary_match.group(3))

        if result.failures == 0 and result.errors == 0 and result.total_tests > 0:
            result.status = "pass"
        elif result.failures > 0 or result.errors > 0:
            result.status = "fail"
        else:
            # 0 tests checked — unusual but not an error per se
            result.status = "pass"
    else:
        result.status = "error"
        result.error_message = "No summary line found in output"

    # Parse "Ran N Routine(s), M Entry Tag(s)" line — use the LAST match
    ran_matches = list(_RAN_RE.finditer(raw_output))
    if ran_matches:
        ran_match = ran_matches[-1]
        result.routines_ran = int(ran_match.group(1))
        result.entry_tags = int(ran_match.group(2))

    return result


def _extract_failure_details(raw_output: str, routine: str) -> list[FailureDetail]:
    """Extract failure and error detail lines from M-Unit output.

    Failure format: ENTRY^ROUTINE - TestName - <expected> vs <actual> - message
    Error format:   ENTRY^ROUTINE - TestName - Error: error_text
    CHKTF format:   ENTRY^ROUTINE - TestName - message
    """
    details: list[FailureDetail] = []

    for match in _FAILURE_LINE_RE.finditer(raw_output):
        entry_tag = match.group(1)
        routine_name = match.group(2)
        rest = match.group(3)

        # Split rest into name and message parts
        # Format: "TestName - <expected> vs <actual> - message"
        # or:     "TestName - Error: error_text"
        # or:     "TestName - message"
        parts = rest.split(" - ", 1)
        test_name = parts[0].strip() if parts else ""
        message_part = parts[1].strip() if len(parts) > 1 else ""

        # Check if it's an error
        error_match = _ERROR_RE.match(message_part)
        if error_match:
            details.append(
                FailureDetail(
                    entry_tag=entry_tag,
                    routine=routine_name,
                    test_name=test_name,
                    message=error_match.group(1),
                    kind="error",
                )
            )
            continue

        # Check if it's a CHKEQ failure with expected vs actual
        chkeq_match = _CHKEQ_RE.match(message_part)
        if chkeq_match:
            details.append(
                FailureDetail(
                    entry_tag=entry_tag,
                    routine=routine_name,
                    test_name=test_name,
                    message=chkeq_match.group(3),
                    kind="failure",
                    expected=chkeq_match.group(1),
                    actual=chkeq_match.group(2),
                )
            )
            continue

        # Otherwise it's a CHKTF failure (simple message)
        if message_part:
            details.append(
                FailureDetail(
                    entry_tag=entry_tag,
                    routine=routine_name,
                    test_name=test_name,
                    message=message_part,
                    kind="failure",
                )
            )

    return details


def parse_testlist(testlist_path: str, package_name: str) -> list[TestRoutineConfig]:
    """Parse an OSEHRA TestList file into routine configurations.

    Args:
        testlist_path: Path to TestList file.
        package_name: Package name for all routines in this list.

    Returns:
        List of TestRoutineConfig entries.

    Raises:
        FileNotFoundError: If the TestList file doesn't exist.
    """
    path = Path(testlist_path)
    if not path.exists():
        raise FileNotFoundError(f"TestList not found: {testlist_path}")

    munit_dir = path.parent
    tier = _TIER_MAP.get(package_name, 1)
    configs: list[TestRoutineConfig] = []

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue

        routine_name, invocation = _parse_testlist_line(line)
        if not routine_name:
            logger.warning("Unparseable TestList line: %s", line)
            continue

        # Locate .m source file in the same MUnit directory
        source_path = ""
        m_file = munit_dir / f"{routine_name}.m"
        if m_file.exists():
            source_path = str(m_file)
        else:
            logger.warning("Missing .m source for %s in %s", routine_name, munit_dir)

        configs.append(
            TestRoutineConfig(
                routine_name=routine_name,
                package_name=package_name,
                invocation=invocation,
                source_path=source_path,
                tier=tier,
            )
        )

    return configs


def _parse_testlist_line(line: str) -> tuple[str, str]:
    """Parse a single TestList line, returning (routine_name, invocation).

    Returns ("", "") if the line can't be parsed.
    """
    # Try "D EN^%ut("routine")" pattern first
    ut_match = _TESTLIST_UTCALL_RE.search(line)
    if ut_match:
        routine_name = ut_match.group(1)
        return routine_name, line

    # Try "D TAG^ROUTINE" or "D ^ROUTINE" pattern
    do_match = _TESTLIST_DO_RE.search(line)
    if do_match:
        routine_name = do_match.group(2)
        return routine_name, line

    return "", ""
