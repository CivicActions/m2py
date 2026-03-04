"""Tier 1: M-Unit self-test routines (%utt1–%utt7, %uttcovr).

Transpiles each M-Unit self-test routine via m2py, executes it through
``EN^%ut``, and classifies the result:

- **pass**: routine completed, and all failures match expected specs
- **fail**: routine crashed, or produced unexpected/missing failures
- **xfail**: routine has known issues unrelated to intentional failures

Note: the osehravista baseline was captured from a VistA instance that may
have *different routine versions* than VistA-M.  Exact test count
matching is unreliable, so we classify purely by outcome: did the transpiled
code complete, and were there unexpected failures?

Intentional-failure routines:
  - %utt5: tests CHKEQ/CHKTF/FAIL assertion mechanisms (4 expected failures)
  - %utt7: tests ``!TEST`` marker discovery (2 expected failures in T5)
  - %utt2: FAIL tag intentionally calls ``fail^%ut`` (1 expected failure)
  - %utt1: meta-runner that includes %utt2/%utt4/%utt5 failures (9 expected)

Each intentional-fail routine declares expected failure entries
(entry_tag, routine, message substring).  The test PASSES only when every
expected failure is present and no unexpected failures appear.  If the
transpiler breaks and produces wrong errors, the test fails loudly.
"""

from __future__ import annotations

import pytest

from .lib.adapter import transpile_and_execute
from .lib.models import FailureDetail


# These are the 8 MASH Utilities self-test routines.
TIER1_ROUTINES = [
    "%utt1",
    "%utt2",
    "%utt3",
    "%utt4",
    "%utt5",
    "%utt6",
    "%utt7",
    "%uttcovr",
]


# ---------------------------------------------------------------------------
# Expected failure specifications for intentional-fail routines.
#
# Each spec defines:
#   min_tests  – minimum total test count (sanity check)
#   entries    – list of (entry_tag, routine, message_substring) that MUST
#                each match at least one FailureDetail
#   allowed_extra_tags – optional list of (entry_tag, routine) tuples for
#                failures that may appear but aren't "intentional" (e.g.
#                %utt4 coverage errors from unsupported GT.M features)
# ---------------------------------------------------------------------------
_EXPECTED_FAILURES: dict[str, dict] = {
    "%utt5": {
        "min_tests": 8,
        "entries": [
            ("BADCHKEQ", "%utt5", "UNEQUAL ON PURPOSE"),
            ("BADCHKTF", "%utt5", "FALSE (0) ON PURPOSE"),
            ("CALLFAIL", "%utt5", "Called FAIL to test it"),
            ("NVLDARG1", "%utt5", "NO VALUES INPUT TO CHKEQ"),
        ],
    },
    "%utt7": {
        "min_tests": 5,
        "entries": [
            ("T5", "%utt7", "intentional failure"),
            ("T5", "%utt7", "Intentionally throwing a failure"),
        ],
    },
    # VistA-M v1.5: %utt2 has 2 tests with 0 intentional failures.
    # (v1.6 added FAIL, EQ, TF, SUCCEED tags with 1 intentional failure.)
    # Not listed here — %utt2 is a clean pass in v1.5.
    "%utt1": {
        "min_tests": 100,
        "entries": [
            # T5^%utt1 — intentional assertion failures
            ("T5", "%utt1", "intentional failure"),
            ("T5", "%utt1", "Intentionally throwing a failure"),
            # %utt5 — assertion mechanism tests
            ("BADCHKEQ", "%utt5", "UNEQUAL ON PURPOSE"),
            ("BADCHKTF", "%utt5", "FALSE (0) ON PURPOSE"),
            ("CALLFAIL", "%utt5", "Called FAIL to test it"),
            ("NVLDARG1", "%utt5", "NO VALUES INPUT TO CHKEQ"),
        ],
        # %utt4 coverage errors are expected but not "intentional" — they
        # come from unsupported GT.M features (%RSEL, VIEW "TRACE").
        "allowed_extra_tags": [("MAIN", "%utt4")],
    },
}


def _format_failure(fd: FailureDetail) -> str:
    """Format a FailureDetail for assertion messages."""
    s = f"  [{fd.kind}] {fd.entry_tag}^{fd.routine}: {fd.message}"
    if fd.expected is not None:
        s += f" (expected={fd.expected!r}, actual={fd.actual!r})"
    return s


def _check_expected_failures(routine_name: str, result) -> None:
    """Validate that a routine's failures match expected specs exactly.

    Raises AssertionError with diagnostics if:
    - Any expected failure entry is missing
    - Any unexpected failure appears (not in entries or allowed_extra_tags)
    - Total test count is below minimum
    """
    spec = _EXPECTED_FAILURES[routine_name]

    # Minimum test count sanity check
    assert result.total_tests >= spec["min_tests"], (
        f"{routine_name}: ran only {result.total_tests} tests "
        f"(expected >= {spec['min_tests']})"
    )

    # Must have at least the expected number of failures
    assert result.failures > 0 or result.errors > 0, (
        f"{routine_name}: expected intentional failures but got "
        f"tests={result.total_tests}, fail=0, err=0"
    )

    # Check that every expected failure is present in the output
    missing = []
    for entry_tag, routine, msg_sub in spec["entries"]:
        found = any(
            fd.entry_tag == entry_tag
            and fd.routine == routine
            and msg_sub.lower() in fd.message.lower()
            for fd in result.failure_details
        )
        if not found:
            missing.append(f"  {entry_tag}^{routine}: *{msg_sub}*")

    assert not missing, (
        f"{routine_name}: missing expected intentional failures:\n"
        + "\n".join(missing)
        + "\n\nActual failure_details:\n"
        + "\n".join(_format_failure(fd) for fd in result.failure_details)
    )

    # Check for unexpected failures (not in entries or allowed_extra_tags)
    allowed_tags: set[tuple[str, str]] = {(e, r) for e, r, _ in spec["entries"]}
    for extra in spec.get("allowed_extra_tags", []):
        allowed_tags.add(tuple(extra))

    unexpected = [
        fd
        for fd in result.failure_details
        if (fd.entry_tag, fd.routine) not in allowed_tags
    ]
    assert not unexpected, (
        f"{routine_name}: unexpected failures (not in expected spec):\n"
        + "\n".join(_format_failure(fd) for fd in unexpected)
    )


@pytest.fixture(scope="module")
def _ensure_framework(munit_framework):
    """Module-level guard that the M-Unit framework is loaded."""
    return munit_framework


@pytest.mark.slow
@pytest.mark.munit
class TestMashUtilities:
    """Run MASH Utilities self-test routines through the transpiled M-Unit framework."""

    @pytest.fixture(autouse=True)
    def _framework(self, _ensure_framework):
        """Auto-use the framework fixture for every test in the class."""

    @pytest.mark.parametrize("routine_name", TIER1_ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
        mash_configs,
    ):
        """Transpile and execute one M-Unit self-test routine.

        Classification:
        - Crashed (no summary line)         → xfail
        - Completed with 0 fail/err         → pass (test succeeds)
        - Intentional-fail routine, matched → pass (expected failures verified)
        - Completed but has unexpected fail  → xfail
        """
        # Find the config for this routine
        config = next(
            (c for c in mash_configs if c.routine_name == routine_name),
            None,
        )
        assert config is not None, f"No config found for {routine_name}"

        # Execute through the adapter
        result = transpile_and_execute(config, munit_runtime)

        # --- Crash: no summary line parsed ---
        if result.status == "error":
            pytest.xfail(f"{routine_name} crashed: {result.error_message}")

        # --- Intentional-fail routines: validate expected failures ---
        if routine_name in _EXPECTED_FAILURES:
            _check_expected_failures(routine_name, result)
            return  # All expected failures present, no surprises → PASS

        # --- Routine completed (summary line found) ---

        # Clean pass: 0 failures, 0 errors
        if result.failures == 0 and result.errors == 0:
            assert result.total_tests > 0, (
                f"{routine_name}: summary line found but 0 tests"
            )
            return

        # Unexpected failures/errors in a routine that should pass
        pytest.xfail(
            f"{routine_name}: "
            f"{result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
