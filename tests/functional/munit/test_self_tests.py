"""Tier 1: M-Unit self-test routines (%utt1–%utt7, %uttcovr).

Transpiles each M-Unit self-test routine via m2py, executes it through
``EN^%ut``, and classifies the result:

- **pass**: routine completed, and all failures match expected specs
- **fail**: routine crashed, or produced unexpected/missing failures
- **xfail**: routine has known issues unrelated to intentional failures

Intentional-failure routines declare exact expected test/failure/error
counts (where deterministic) and expected failure entries (entry_tag,
routine, message substring).  The test PASSES only when all counts match,
every expected failure is present, and no unexpected failures appear.

Intentional-failure routines:
  - %utt5: tests CHKEQ/CHKTF/FAIL assertion mechanisms (5 expected failures)
  - %utt7: tests ``!TEST`` marker discovery (2 expected failures in T5)
  - %utt4: MAIN calls GT.M coverage (VIEW "TRACE") which can't run in Python
  - %utt1: meta-runner that includes %utt2/%utt4/%utt5 failures
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
#   expected_tests – exact test count (when deterministic across all
#                    execution modes: sequential, parallel, standalone)
#   min_tests      – minimum test count (when count varies, e.g. due to
#                    shared session-scoped runtime state between routines)
#   max_tests      – optional upper bound (with min_tests, prevents drift)
#   expected_failures – exact failure count (if deterministic)
#   expected_errors   – exact error count (if deterministic)
#   entries    – list of (entry_tag, routine, message_substring) that MUST
#                each match at least one FailureDetail
#   allowed_extra_tags – optional list of (entry_tag, routine) tuples for
#                failures that may appear but aren't "intentional" (e.g.
#                %utt4 coverage errors from unsupported GT.M features)
# ---------------------------------------------------------------------------
_EXPECTED_FAILURES: dict[str, dict] = {
    # GT.M baseline: 10 tests, 5 failures, 1 error.
    # m2py produces: 9 tests, 5 failures, 0 errors.
    # BADERROR (1 error in baseline) is missing: intentional syntax error
    # (`S X=`) that GT.M catches via $ETRAP as %YDB-E-EXPR.  m2py's parser
    # can't represent the invalid line, so it's dropped and the label runs
    # without error.
    "%utt5": {
        "expected_tests": 9,
        "expected_failures": 5,
        "expected_errors": 0,
        "entries": [
            ("BADCHKEQ", "%utt5", "UNEQUAL ON PURPOSE"),
            ("BADCHKTF", "%utt5", "FALSE (0) ON PURPOSE"),
            ("CALLFAIL", "%utt5", "Called FAIL to test it"),
            ("LEAKSBAD", "%utt5", "VARIABLE LEAK: X"),
            ("NVLDARG1", "%utt5", "NO VALUES INPUT TO CHKEQ"),
        ],
    },
    "%utt7": {
        "expected_tests": 5,
        "expected_failures": 2,
        "expected_errors": 0,
        "entries": [
            ("T5", "%utt7", "intentional failure"),
            ("T5", "%utt7", "Intentionally throwing a failure"),
        ],
    },
    # %utt4 MAIN calls COV^%ut which requires GT.M VIEW "TRACE" profiling
    # and %RSEL (transpiled as _pct_RSEL).  Python can't emulate hardware-level
    # line profiling, so MAIN always errors.  The parser strips the "Error:"
    # prefix, leaving the raw MUMPS error text — match on the missing module.
    #
    # Test count varies: 2 on a fresh runtime, up to 5 when running after
    # %utt1 on a shared session-scoped runtime (M-Unit globals persist).
    "%utt4": {
        "min_tests": 2,
        "max_tests": 10,
        "entries": [
            ("MAIN", "%utt4", "_pct_RSEL"),
        ],
        # MAIN produces multiple error/failure entries from retried $ETRAP handling
        "allowed_extra_tags": [("MAIN", "%utt4")],
    },
    # Meta-runner: discovers and runs %utt2–%utt7 plus its own T5 tests.
    # Always finds 113 tests.  Failure counts vary slightly depending on
    # runtime state:
    #   - Fresh runtime:  8 failures, 2 errors (FAIL^%utt2 present)
    #   - After setup:   11 failures, 1 error  (FAIL^%utt2 absent,
    #                    extra MAIN^%utt4 "no failure message" entries)
    # BADERROR is the only remaining %utt5 delta (syntax error not
    # representable in Python).
    "%utt1": {
        "expected_tests": 113,
        "entries": [
            # T5^%utt1 — intentional assertion failures
            ("T5", "%utt1", "intentional failure"),
            ("T5", "%utt1", "Intentionally throwing a failure"),
            # %utt5 — assertion mechanism tests
            ("BADCHKEQ", "%utt5", "UNEQUAL ON PURPOSE"),
            ("BADCHKTF", "%utt5", "FALSE (0) ON PURPOSE"),
            ("CALLFAIL", "%utt5", "Called FAIL to test it"),
            ("LEAKSBAD", "%utt5", "VARIABLE LEAK: X"),
            ("NVLDARG1", "%utt5", "NO VALUES INPUT TO CHKEQ"),
        ],
        # %utt4 coverage errors are expected but not "intentional" — they
        # come from unsupported GT.M features (%RSEL, VIEW "TRACE").
        # FAIL^%utt2 appears on fresh runtimes but not after prior setup.
        "allowed_extra_tags": [("MAIN", "%utt4"), ("FAIL", "%utt2")],
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
    - Test/failure/error counts don't match spec (exact or bounded)
    """
    spec = _EXPECTED_FAILURES[routine_name]

    # --- Test count validation ---
    if "expected_tests" in spec:
        assert result.total_tests == spec["expected_tests"], (
            f"{routine_name}: ran {result.total_tests} tests "
            f"(expected exactly {spec['expected_tests']})"
        )
    else:
        assert result.total_tests >= spec["min_tests"], (
            f"{routine_name}: ran only {result.total_tests} tests "
            f"(expected >= {spec['min_tests']})"
        )
        if "max_tests" in spec:
            assert result.total_tests <= spec["max_tests"], (
                f"{routine_name}: ran {result.total_tests} tests "
                f"(expected <= {spec['max_tests']})"
            )

    # --- Failure/error count validation (when exact counts specified) ---
    if "expected_failures" in spec:
        assert result.failures == spec["expected_failures"], (
            f"{routine_name}: {result.failures} failures "
            f"(expected exactly {spec['expected_failures']})"
        )
    if "expected_errors" in spec:
        assert result.errors == spec["expected_errors"], (
            f"{routine_name}: {result.errors} errors "
            f"(expected exactly {spec['expected_errors']})"
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
        assert result.status != "error", (
            f"{routine_name} crashed: {result.error_message}"
        )

        # --- Intentional-fail routines: validate expected failures ---
        if routine_name in _EXPECTED_FAILURES:
            _check_expected_failures(routine_name, result)
            return  # All expected failures present, no surprises → PASS

        # --- Routine completed (summary line found) ---
        assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"
        assert result.failures == 0 and result.errors == 0, (
            f"{routine_name}: "
            f"{result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
