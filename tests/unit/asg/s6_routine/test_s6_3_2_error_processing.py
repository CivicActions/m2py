"""Tests for Error Processing ASG analysis (§6.3.2).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.2

§6.3.2 defines the error processing model:
- $ETRAP: Special variable set to code invoked when $ECODE becomes non-empty
- $ECODE: Comma-surrounded list of error conditions
- Error processing transfers control when $ECODE changes from empty to non-empty
- NEW $ETRAP stacks error handlers for nested error handling

The ASG must capture:
- $ETRAP assignments (error handler code)
- $ECODE assignments (setting/clearing error state)
- Special variable references in write/other statements
- NEW $ETRAP for stacked error handlers
"""

import pytest

from m2py.asg.expressions import MSpecialVariable
from m2py.asg.statements import MNewStatement, MSetStatement, MWriteStatement
from m2py.parser.textx_classes import StringLiteral


@pytest.mark.asg
class TestErrorProcessingAnalysis:
    """ASG-level tests for error processing analysis (§6.3.2)."""

    def test_etrap_analysis(self, analyze_routine):
        """$ETRAP settings are tracked in ASG (§6.3.2).

        Per §6.3.2: $ETRAP may be set to code to be invoked when $ECODE
        becomes non-empty. The ASG must capture the target as MSpecialVariable
        with name 'ETRAP' and the value as the handler code.
        """
        routine = analyze_routine("""\
TEST
 S $ETRAP="D ERR^HANDLER"
 S X=1
ERR
 W "Error handler"
 Q
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        # First statement sets $ETRAP
        etrap_set = statements[0]
        assert isinstance(etrap_set, MSetStatement)

        # Target should be $ETRAP special variable
        target = etrap_set.assignments[0].target
        assert isinstance(target, MSpecialVariable)
        assert target.name == "ETRAP"

        # Value should be string with handler code
        value = etrap_set.assignments[0].value
        assert isinstance(value, StringLiteral)
        assert value.value == "D ERR^HANDLER"

    def test_ecode_analysis(self, analyze_routine):
        """$ECODE modifications are tracked in ASG (§6.3.2).

        Per §6.3.2: $ECODE provides information about error conditions.
        It's a comma-surrounded list that can be set or cleared via SET.
        The ASG must capture both setting and clearing $ECODE.
        """
        routine = analyze_routine("""\
TEST
 S $ECODE=",M9,"
 W $ECODE
 S $ECODE=""
 Q
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        # First statement sets $ECODE to error condition
        ecode_set = statements[0]
        assert isinstance(ecode_set, MSetStatement)
        target = ecode_set.assignments[0].target
        assert isinstance(target, MSpecialVariable)
        assert target.name == "ECODE"
        value = ecode_set.assignments[0].value
        assert isinstance(value, StringLiteral)
        assert value.value == ",M9,"  # MUMPS error codes are comma-surrounded

        # Second statement writes $ECODE
        write_stmt = statements[1]
        assert isinstance(write_stmt, MWriteStatement)
        assert len(write_stmt.arguments) >= 1
        write_arg = write_stmt.arguments[0]
        assert isinstance(write_arg, MSpecialVariable)
        assert write_arg.name == "ECODE"

        # Third statement clears $ECODE
        ecode_clear = statements[2]
        assert isinstance(ecode_clear, MSetStatement)
        clear_target = ecode_clear.assignments[0].target
        assert isinstance(clear_target, MSpecialVariable)
        assert clear_target.name == "ECODE"
        clear_value = ecode_clear.assignments[0].value
        assert isinstance(clear_value, StringLiteral)
        assert clear_value.value == ""

    def test_error_handler_scope(self, analyze_routine):
        """NEW $ETRAP stacks error handlers for scope (§6.3.2).

        Per §6.3.2: Stacking of $ETRAP is performed via the NEW command.
        This allows nested error handling where inner handlers don't
        affect outer handlers.
        """
        routine = analyze_routine("""\
TEST
 S $ETRAP="D OUTER"
 N $ETRAP S $ETRAP="D INNER"
 D WORK
 Q
WORK
 S X=1
 Q
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        # First: SET $ETRAP to outer handler
        outer_set = statements[0]
        assert isinstance(outer_set, MSetStatement)

        # Second: NEW $ETRAP (stacks the value)
        new_stmt = statements[1]
        assert isinstance(new_stmt, MNewStatement)
        # NEW should include $ETRAP
        new_vars = [
            v.name if hasattr(v, "name") else str(v) for v in new_stmt.variables
        ]
        assert "ETRAP" in new_vars

        # Third: SET $ETRAP to inner handler
        inner_set = statements[2]
        assert isinstance(inner_set, MSetStatement)
        inner_target = inner_set.assignments[0].target
        assert isinstance(inner_target, MSpecialVariable)
        assert inner_target.name == "ETRAP"

    def test_etrap_abbreviated(self, analyze_routine):
        """$ET abbreviation for $ETRAP is recognized (§6.3.2).

        Per §7.1.4.10: $ET is the abbreviation for $ETRAP.
        The ASG preserves the original form while identifying it as the same variable.
        """
        routine = analyze_routine("""\
TEST
 S $ET="D ERR"
 Q
""")
        label = routine.get_label("TEST")
        stmt = label.body.statements[0]

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MSpecialVariable)
        # ASG preserves abbreviated form (ET maps to ETRAP)
        assert target.name in ("ET", "ETRAP")

    def test_ecode_abbreviated(self, analyze_routine):
        """$EC abbreviation for $ECODE is recognized (§6.3.2).

        Per §7.1.4.10: $EC is the abbreviation for $ECODE.
        The ASG preserves the original form while identifying it as the same variable.
        """
        routine = analyze_routine("""\
TEST
 S $EC=""
 Q
""")
        label = routine.get_label("TEST")
        stmt = label.body.statements[0]

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MSpecialVariable)
        # ASG preserves abbreviated form (EC maps to ECODE)
        assert target.name in ("EC", "ECODE")

    def test_estack_special_variable(self, analyze_routine):
        """$ESTACK counts stack levels for error handling (§6.3.2).

        Per §6.3.2: $ESTACK counts stack levels since $ESTACK was last NEWed.
        """
        routine = analyze_routine("""\
TEST
 N $ESTACK
 W $ESTACK
 Q
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        # NEW $ESTACK
        new_stmt = statements[0]
        assert isinstance(new_stmt, MNewStatement)
        new_vars = [
            v.name if hasattr(v, "name") else str(v) for v in new_stmt.variables
        ]
        assert "ESTACK" in new_vars

        # WRITE $ESTACK
        write_stmt = statements[1]
        assert isinstance(write_stmt, MWriteStatement)
        write_arg = write_stmt.arguments[0]
        assert isinstance(write_arg, MSpecialVariable)
        assert write_arg.name == "ESTACK"
