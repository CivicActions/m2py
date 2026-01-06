"""Cross-cutting tests for timeout syntax (§8.2.10, §8.2.12, §8.2.15, §8.2.17).

Timeouts are a language feature that spans multiple commands:
- OPEN device:timeout - device open timeout
- READ var:timeout - read input timeout
- JOB entry::timeout - job start timeout
- LOCK name:timeout - lock acquisition timeout

All timeout commands modify $TEST on timeout (§7.1.4.10):
- Success: $TEST=1
- Timeout: $TEST=0

Reference: MUMPS 1995 ANSI Standard, Sections 8.2.10, 8.2.12, 8.2.15, 8.2.17
See also: FR-005 (cross-cutting features need dedicated tests)
         FR-047 ($TEST modification by timeout commands)
"""

import pytest

from m2py.parser import MUMPSParser


# =============================================================================
# OPEN Timeout Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestOpenTimeoutParser:
    """Parser tests for OPEN command timeout syntax.

    OPEN device:timeout or OPEN device:(params):timeout format.
    Reference: §8.2.15
    """

    def test_open_with_timeout(self):
        """OPEN DEV:5 parses timeout (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV:5\n"
        routine = parser.parse(source)

        open_stmt = routine.labels[0].body.statements[0]
        assert open_stmt.__class__.__name__ == "MOpenStatement"
        # OPEN uses devices list with MOpenDevice
        assert len(open_stmt.devices) == 1
        assert open_stmt.devices[0].timeout is not None
        assert open_stmt.devices[0].timeout.value == 5

    # NOTE: test_open_with_params_and_timeout moved to:
    # tests/unit/asg/s8_commands/test_s8_2_15_open.py::TestOpenCommandAnalysis::test_open_with_params_and_timeout

    def test_open_without_timeout(self):
        """OPEN DEV parses without timeout (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV\n"
        routine = parser.parse(source)

        open_stmt = routine.labels[0].body.statements[0]
        assert open_stmt.__class__.__name__ == "MOpenStatement"
        assert len(open_stmt.devices) == 1
        assert open_stmt.devices[0].timeout is None


# =============================================================================
# READ Timeout Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestReadTimeoutParser:
    """Parser tests for READ command timeout syntax.

    READ var:timeout format.
    Reference: §8.2.17
    """

    # NOTE: test_read_with_timeout moved to:
    # tests/unit/asg/s8_commands/test_s8_2_17_read.py::TestReadCommandAnalysis::test_read_timeout

    def test_read_with_timeout_expression(self):
        """READ X:T parses timeout expression (§8.2.17)."""
        parser = MUMPSParser()
        source = "LABEL\tR X:T\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert target.timeout is not None
        # Variable name in timeout expression
        assert target.timeout.name == "T"

    def test_read_fixed_length_with_timeout(self):
        """READ X#10:5 parses fixed length with timeout (§8.2.17)."""
        parser = MUMPSParser()
        source = "LABEL\tR X#10:5\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert target.fixed_length is not None
        assert target.fixed_length.value == 10
        assert target.timeout is not None
        assert target.timeout.value == 5

    def test_read_char_with_timeout(self):
        """READ *X:5 parses character read with timeout (§8.2.17)."""
        parser = MUMPSParser()
        source = "LABEL\tR *X:5\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert target.is_char_read is True
        assert target.timeout is not None
        assert target.timeout.value == 5

    def test_read_without_timeout(self):
        """READ X parses without timeout (§8.2.17)."""
        parser = MUMPSParser()
        source = "LABEL\tR X\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert target.timeout is None


# =============================================================================
# JOB Timeout Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestJobTimeoutParser:
    """Parser tests for JOB command timeout syntax.

    JOB entry:(params):timeout format (double colon ::timeout for timeout only).
    Reference: §8.2.10
    """

    def test_job_with_timeout(self):
        """JOB ROUTINE::5 parses timeout (§8.2.10)."""
        parser = MUMPSParser()
        # JOB uses :: for timeout when no process params
        source = "LABEL\tJ ROUTINE::5\n"
        routine = parser.parse(source)

        job_stmt = routine.labels[0].body.statements[0]
        assert job_stmt.__class__.__name__ == "MJobStatement"

    def test_job_with_params_and_timeout(self):
        """JOB ROUTINE:(params):10 parses params and timeout (§8.2.10)."""
        parser = MUMPSParser()
        source = 'LABEL\tJ ROUTINE:("STACK=4096"):10\n'
        routine = parser.parse(source)

        job_stmt = routine.labels[0].body.statements[0]
        assert job_stmt.__class__.__name__ == "MJobStatement"

    def test_job_without_timeout(self):
        """JOB ROUTINE parses without timeout (§8.2.10)."""
        parser = MUMPSParser()
        source = "LABEL\tJ ROUTINE\n"
        routine = parser.parse(source)

        job_stmt = routine.labels[0].body.statements[0]
        assert job_stmt.__class__.__name__ == "MJobStatement"


# =============================================================================
# LOCK Timeout Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestLockTimeoutParser:
    """Parser tests for LOCK command timeout syntax.

    LOCK name:timeout format.
    Reference: §8.2.12

    Note: MLockStatement.targets is a list of dicts with keys:
    - 'target' or 'indirection'
    - 'timeout' (optional)
    - 'lockop' (optional - '+' or '-')
    """

    # NOTE: test_lock_with_timeout moved to:
    # tests/unit/asg/s8_commands/test_s8_2_12_lock.py::TestLockCommandAnalysis::test_lock_timeout

    def test_lock_with_timeout_expression(self):
        """LOCK ^DATA:T parses timeout expression (§8.2.12)."""
        parser = MUMPSParser()
        source = "LABEL\tL ^DATA:T\n"
        routine = parser.parse(source)

        lock_stmt = routine.labels[0].body.statements[0]
        target = lock_stmt.targets[0]
        assert target.get("timeout") is not None
        assert target["timeout"].name == "T"

    def test_lock_incremental_with_timeout(self):
        """LOCK +^DATA:5 parses incremental lock with timeout (§8.2.12)."""
        parser = MUMPSParser()
        source = "LABEL\tL +^DATA:5\n"
        routine = parser.parse(source)

        lock_stmt = routine.labels[0].body.statements[0]
        target = lock_stmt.targets[0]
        assert target.get("lockop") == "+"
        assert target.get("timeout") is not None
        assert target["timeout"].value == 5

    def test_lock_parenthesized_with_timeout(self):
        """LOCK (^A,^B):5 parses list lock with timeout (§8.2.12)."""
        parser = MUMPSParser()
        source = "LABEL\tL (^A,^B):5\n"
        routine = parser.parse(source)

        lock_stmt = routine.labels[0].body.statements[0]
        # MLockStatement.timeout stores parenthesized list timeout
        assert lock_stmt.timeout is not None
        assert lock_stmt.timeout.value == 5

    def test_lock_without_timeout(self):
        """LOCK ^DATA parses without timeout (§8.2.12)."""
        parser = MUMPSParser()
        source = "LABEL\tL ^DATA\n"
        routine = parser.parse(source)

        lock_stmt = routine.labels[0].body.statements[0]
        target = lock_stmt.targets[0]
        assert target.get("timeout") is None


# =============================================================================
# Timeout Tests (ASG Level)
# =============================================================================


@pytest.mark.asg
class TestTimeoutsASG:
    """ASG tests for timeout semantic analysis.

    ASG analysis must identify timeout expressions and track
    that command modifies $TEST.
    Reference: §8.2.10, §8.2.12, §8.2.15, §8.2.17
    """

    def test_read_timeout_in_asg(self):
        """READ timeout is captured in MReadTarget (§8.2.17)."""
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR X:10\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.timeout is not None
        assert target.timeout.value == 10

    def test_read_timeout_expression_analyzed(self):
        """READ timeout expression is analyzed (§8.2.17)."""
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR X:T*2\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.timeout is not None
        # Expression type is MBinaryOp for T*2
        assert target.timeout.__class__.__name__ == "MBinaryOp"
        assert target.timeout.operator == "*"

    def test_lock_timeout_in_asg(self):
        """LOCK timeout is captured in MLockStatement.targets dict (§8.2.12)."""
        parser = MUMPSParser()
        source = "LABEL\tL ^DATA:5\n"
        routine = parser.parse(source)

        lock_stmt = routine.labels[0].body.statements[0]
        assert lock_stmt.__class__.__name__ == "MLockStatement"
        target = lock_stmt.targets[0]
        # targets is a list of dicts
        assert isinstance(target, dict)
        assert target.get("timeout") is not None
        assert target["timeout"].value == 5

    def test_open_timeout_in_asg(self):
        """OPEN timeout is captured in MOpenDevice (§8.2.15)."""
        from m2py.asg import MOpenDevice

        parser = MUMPSParser()
        source = "LABEL\tO DEV:10\n"
        routine = parser.parse(source)

        open_stmt = routine.labels[0].body.statements[0]
        device = open_stmt.devices[0]
        assert isinstance(device, MOpenDevice)
        assert device.timeout is not None
        assert device.timeout.value == 10

    def test_job_parses_with_timeout(self):
        """JOB with timeout parses to MJobStatement (§8.2.10)."""
        parser = MUMPSParser()
        source = "LABEL\tJ ROUTINE::5\n"
        routine = parser.parse(source)

        job_stmt = routine.labels[0].body.statements[0]
        assert job_stmt.__class__.__name__ == "MJobStatement"

    def test_negative_timeout_parsed(self):
        """Negative timeout value (R X:-1) is preserved as unary op (§8.2.17)."""
        from m2py.asg import MReadTarget, MUnaryOp

        parser = MUMPSParser()
        source = "LABEL\tR X:-1\n"
        routine = parser.parse(source)

        read_stmt = routine.labels[0].body.statements[0]
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.timeout is not None
        assert isinstance(target.timeout, MUnaryOp)
        assert target.timeout.operator == "-"
        assert target.timeout.operand.value == 1


# =============================================================================
# Timeout Tests (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestTimeoutsCodegen:
    """Codegen tests for timeout execution.

    Generated Python must correctly implement timeout semantics
    and $TEST modification (§7.1.4.10).

    Per the 1995 MUMPS spec:
    - $TEST contains the truthvalue resulting from OPEN, LOCK, JOB,
      or READ commands with timeout arguments
    - Success: $TEST=1, Timeout: $TEST=0

    Reference: §8.2.10, §8.2.12, §8.2.15, §8.2.17, FR-047
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_read_timeout_sets_test_false(self):
        """READ timeout sets $TEST=0 (§8.2.17, FR-047).

        READ X:0  ; Immediate timeout
        ; $TEST should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_read_success_sets_test_true(self):
        """READ success sets $TEST=1 (§8.2.17, FR-047).

        ; With input available
        READ X:5
        ; $TEST should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_lock_timeout_sets_test_false(self):
        """LOCK timeout sets $TEST=0 (§8.2.12, FR-047).

        ; When lock unavailable
        LOCK ^BUSY:0
        ; $TEST should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_lock_success_sets_test_true(self):
        """LOCK success sets $TEST=1 (§8.2.12, FR-047).

        LOCK ^AVAIL:5
        ; $TEST should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_open_timeout_sets_test_false(self):
        """OPEN timeout sets $TEST=0 (§8.2.15, FR-047)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_job_timeout_sets_test_false(self):
        """JOB timeout sets $TEST=0 (§8.2.10, FR-047)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_timeout_expression_evaluated(self):
        """Timeout expression is evaluated at runtime (§8.2.17).

        SET T=5 READ X:T  ; T evaluated to get timeout value
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_zero_timeout_is_immediate(self):
        """Timeout of 0 is immediate/non-blocking (§8.2.17).

        Per spec: timeout of 0 means immediate (non-blocking) attempt.
        """
        pytest.fail("Stub - implement test")
