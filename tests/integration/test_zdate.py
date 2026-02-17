"""Integration tests for $ZDATE function.

Spec 021 Phase 10 T115: Tests transpiling $ZDATE routines and comparing
output against YottaDB.

These tests verify the full pipeline:
1. Parse MUMPS routine with $ZDATE
2. Generate Python code with m_zdate() calls
3. Execute and verify output matches expected YDB behavior
"""

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


def run_routine(mumps_code: str) -> str:
    """Transpile and run a MUMPS routine, returning captured output."""
    # Generate Python code
    python_code = generate_python(mumps_code)

    # Compile it
    compiled = compile(python_code, "<test>", "exec")

    # Create namespace and execute
    namespace = {}
    exec(compiled, namespace)

    # Get the entry function (first label)
    entry_func = namespace.get("_entry_function")
    if entry_func is None:
        raise RuntimeError("No entry function found in generated code")

    # Create runtime and call entry function
    runtime = MUMPSRuntime()
    entry_func(runtime)

    return runtime.get_output()


class TestZdateIntegration:
    """Integration tests for $ZDATE transpilation."""

    def test_zdate_default_format(self):
        """$ZD with default MM/DD/YY format."""
        mumps = """\
TEST ; Test $ZDATE default format
 W $ZD(66337),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "08/16/22"

    def test_zdate_iso_format(self):
        """$ZD with ISO YYYY-MM-DD format."""
        mumps = """\
TEST ; Test $ZDATE ISO format
 W $ZD(66337,"YYYY-MM-DD"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "2022-08-16"

    def test_zdate_dd_mon_year(self):
        """$ZD with DD MON YEAR format."""
        mumps = """\
TEST ; Test $ZDATE DD MON YEAR
 W $ZD(66337,"DD MON YEAR"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "16 AUG 2022"

    def test_zdate_with_time(self):
        """$ZD with time components from $HOROLOG seconds."""
        mumps = """\
TEST ; Test $ZDATE with time
 W $ZD("66337,45296","YYYY-MM-DD 24:60:SS"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "2022-08-16 12:34:56"

    def test_zdate_12_hour_format(self):
        """$ZD with 12-hour AM/PM format."""
        mumps = """\
TEST ; Test $ZDATE 12-hour
 W $ZD("66337,45296","12:60:SS AM"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "12:34:56 PM"

    def test_zdate_european_format(self):
        """$ZD with European DD/MM/YY format."""
        mumps = """\
TEST ; Test $ZDATE European
 W $ZD("66337,45296","DD/MM/YY 24:60:SS"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "16/08/22 12:34:56"

    def test_zdate_from_horolog_svn(self):
        """$ZD with $H (current date)."""
        mumps = """\
TEST ; Test $ZDATE with $H
 S H=66337 ; Fixed $H for testing
 W $ZD(H,"YYYY"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "2022"

    def test_zdate_individual_codes(self):
        """$ZD with individual format codes."""
        mumps = """\
TEST ; Test individual $ZDATE codes
 W $ZD(66337,"YEAR"),!
 W $ZD(66337,"MON"),!
 W $ZD(66337,"DAY"),!
 W $ZD(66337,"MM"),!
 W $ZD(66337,"DD"),!
 Q
"""
        output = run_routine(mumps)
        lines = output.strip().split("\n")
        assert lines == ["2022", "AUG", "TUE", "08", "16"]

    def test_zdate_custom_month_names(self):
        """$ZD with custom month names."""
        mumps = """\
TEST ; Test $ZDATE custom months
 W $ZD(66337,"DD MON YEAR","Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "16 Aug 2022"

    def test_zdate_four_args_custom_days(self):
        """$ZD with 4 args: custom day names."""
        mumps = """\
TEST ; Test $ZDATE with custom day names
 W $ZD(66337,"DAY DD MON","","Dom,Lun,Mar,Mie,Jue,Vie,Sab"),!
 Q
"""
        output = run_routine(mumps)
        # 66337 = Aug 16, 2022 = Tuesday = weekday index 2 (Sun=0)
        assert "Mar" in output.strip()

    def test_zdate_epoch_day_zero(self):
        """$ZD for epoch day 0 (Dec 31, 1840)."""
        mumps = """\
TEST ; Test $ZDATE epoch
 W $ZD(0,"YYYY-MM-DD"),!
 Q
"""
        output = run_routine(mumps)
        assert output.strip() == "1840-12-31"
