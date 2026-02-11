"""Tests for m_zdate() runtime helper function.

Spec 021 Phase 10: $ZDATE function tests.

T066: Unit tests for m_zdate() basic formats
T067: Unit tests for m_zdate() edge cases
"""

from m2py.runtime.helpers import m_zdate


class TestZdateDefaultFormat:
    """T066: Test m_zdate() default format (MM/DD/YY)."""

    def test_default_format_august_16_2022(self):
        """$ZD(66337) returns 08/16/22 (August 16, 2022)."""
        result = m_zdate("66337")
        assert result == "08/16/22"

    def test_default_format_epoch_day_0(self):
        """$ZD(0) returns 12/31/40 (Dec 31, 1840 - epoch day 0)."""
        result = m_zdate("0")
        assert result == "12/31/40"

    def test_default_format_epoch_day_1(self):
        """$ZD(1) returns 01/01/41 (Jan 1, 1841)."""
        result = m_zdate("1")
        assert result == "01/01/41"

    def test_default_format_unix_epoch(self):
        """$ZD(47117) returns 01/01/70 (Jan 1, 1970 - Unix epoch)."""
        result = m_zdate("47117")
        assert result == "01/01/70"

    def test_default_format_year_2100(self):
        """$ZD(94675) returns 03/18/00 (March 18, 2100)."""
        result = m_zdate("94675")
        assert result == "03/18/00"


class TestZdateISOFormat:
    """T066: Test m_zdate() ISO format (YYYY-MM-DD)."""

    def test_iso_format_august_16_2022(self):
        """$ZD(66337,"YYYY-MM-DD") returns 2022-08-16."""
        result = m_zdate("66337", "YYYY-MM-DD")
        assert result == "2022-08-16"

    def test_iso_format_epoch_day_0(self):
        """$ZD(0,"YYYY-MM-DD") returns 1840-12-31."""
        result = m_zdate("0", "YYYY-MM-DD")
        assert result == "1840-12-31"

    def test_iso_format_year_2100(self):
        """$ZD(94675,"YYYY-MM-DD") returns 2100-03-18."""
        result = m_zdate("94675", "YYYY-MM-DD")
        assert result == "2100-03-18"


class TestZdateDDMonYearFormat:
    """T066: Test m_zdate() DD MON YEAR format."""

    def test_dd_mon_year_august_16_2022(self):
        """$ZD(66337,"DD MON YEAR") returns 16 AUG 2022."""
        result = m_zdate("66337", "DD MON YEAR")
        assert result == "16 AUG 2022"

    def test_dd_mon_year_january(self):
        """Test DD MON YEAR in January."""
        result = m_zdate("47117", "DD MON YEAR")
        assert result == "01 JAN 1970"


class TestZdateIndividualDateCodes:
    """T066: Test individual date format codes."""

    def test_year_full(self):
        """$ZD(66337,"YEAR") returns 2022."""
        result = m_zdate("66337", "YEAR")
        assert result == "2022"

    def test_yyyy(self):
        """$ZD(66337,"YYYY") returns 2022."""
        result = m_zdate("66337", "YYYY")
        assert result == "2022"

    def test_yy(self):
        """$ZD(66337,"YY") returns 22."""
        result = m_zdate("66337", "YY")
        assert result == "22"

    def test_mm(self):
        """$ZD(66337,"MM") returns 08."""
        result = m_zdate("66337", "MM")
        assert result == "08"

    def test_dd(self):
        """$ZD(66337,"DD") returns 16."""
        result = m_zdate("66337", "DD")
        assert result == "16"

    def test_mon(self):
        """$ZD(66337,"MON") returns AUG."""
        result = m_zdate("66337", "MON")
        assert result == "AUG"

    def test_day(self):
        """$ZD(66337,"DAY") returns TUE (August 16, 2022 was Tuesday)."""
        result = m_zdate("66337", "DAY")
        assert result == "TUE"


class TestZdateTimeFormats:
    """T066/T070: Test m_zdate() time format codes."""

    def test_time_24_60_ss(self):
        """$ZD("66337,45296","24:60:SS") returns 12:34:56."""
        result = m_zdate("66337,45296", "24:60:SS")
        assert result == "12:34:56"

    def test_time_12_am(self):
        """$ZD("66337,45296","12:60:SS AM") returns 12:34:56 PM."""
        result = m_zdate("66337,45296", "12:60:SS AM")
        assert result == "12:34:56 PM"

    def test_time_am_morning(self):
        """$ZD("66337,3661","12:60:SS AM") returns 01:01:01 AM."""
        result = m_zdate("66337,3661", "12:60:SS AM")
        assert result == "01:01:01 AM"

    def test_time_24_code_only(self):
        """$ZD("66337,45296","24") returns 12 (hour in 24-hour format)."""
        result = m_zdate("66337,45296", "24")
        assert result == "12"

    def test_time_12_code_only(self):
        """$ZD("66337,45296","12") returns 12 (hour in 12-hour format)."""
        result = m_zdate("66337,45296", "12")
        assert result == "12"

    def test_time_60_code_only(self):
        """$ZD("66337,45296","60") returns 34 (minutes)."""
        result = m_zdate("66337,45296", "60")
        assert result == "34"

    def test_time_ss_code_only(self):
        """$ZD("66337,45296","SS") returns 56 (seconds)."""
        result = m_zdate("66337,45296", "SS")
        assert result == "56"

    def test_time_am_code_only(self):
        """$ZD("66337,45296","AM") returns PM."""
        result = m_zdate("66337,45296", "AM")
        assert result == "PM"

    def test_time_without_seconds_in_horolog(self):
        """$ZD(66337,"24:60:SS") uses 0 for missing seconds component."""
        result = m_zdate("66337", "24:60:SS")
        assert result == "00:00:00"


class TestZdateCombinedDateTime:
    """T070: Test combined date + time formats."""

    def test_full_datetime(self):
        """$ZD("66337,45296","YYYY-MM-DD 24:60:SS") returns 2022-08-16 12:34:56."""
        result = m_zdate("66337,45296", "YYYY-MM-DD 24:60:SS")
        assert result == "2022-08-16 12:34:56"

    def test_european_date_time(self):
        """$ZD("66337,45296","DD/MM/YY 24:60:SS") returns 16/08/22 12:34:56."""
        result = m_zdate("66337,45296", "DD/MM/YY 24:60:SS")
        assert result == "16/08/22 12:34:56"

    def test_time_only(self):
        """$ZD("66337,45296","24:60") returns 12:34."""
        result = m_zdate("66337,45296", "24:60")
        assert result == "12:34"


class TestZdateCustomNames:
    """T067: Test m_zdate() with custom month/day names."""

    def test_custom_month_names(self):
        """$ZD with custom month names uses them for MON code."""
        result = m_zdate(
            "66337",
            "DD MON YEAR",
            "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
        )
        assert result == "16 Aug 2022"

    def test_custom_day_names(self):
        """$ZD with custom day names uses them for DAY code."""
        result = m_zdate(
            "66337",
            "DD MON YEAR",
            "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
            "Sun,Mon,Tue,Wed,Thu,Fri,Sat",
        )
        assert result == "16 Aug 2022"

    def test_custom_full_month_names(self):
        """$ZD with full month names."""
        result = m_zdate(
            "66337",
            "DD MON YEAR",
            "January,February,March,April,May,June,July,August,September,October,November,December",
        )
        assert result == "16 August 2022"


class TestZdateBoundaryDates:
    """T067: Test boundary dates and edge cases."""

    def test_epoch_day_negative(self):
        """$ZD(-1) returns 12/30/40 (Dec 30, 1840 - day before epoch)."""
        result = m_zdate("-1")
        assert result == "12/30/40"

    def test_midnight_seconds(self):
        """$ZD("66337,0","24:60:SS") returns 00:00:00."""
        result = m_zdate("66337,0", "24:60:SS")
        assert result == "00:00:00"

    def test_end_of_day_seconds(self):
        """$ZD("66337,86399","24:60:SS") returns 23:59:59."""
        result = m_zdate("66337,86399", "24:60:SS")
        assert result == "23:59:59"

    def test_numeric_horolog(self):
        """m_zdate() accepts numeric $HOROLOG values."""
        result = m_zdate(66337)
        assert result == "08/16/22"

    def test_non_numeric_string_defaults_to_epoch(self):
        """$ZD("abc") with invalid horolog treats as 0 (YDB behavior)."""
        result = m_zdate("abc")
        assert result == "12/31/40"


class TestZdateLeapYears:
    """T067: Test leap year handling."""

    def test_leap_year_feb_29_2000(self):
        """Feb 29, 2000 (leap year) is correctly formatted."""
        # Feb 29, 2000 is $H = 58133
        result = m_zdate("58133", "DD MON YYYY")
        assert result == "29 FEB 2000"

    def test_leap_year_feb_29_2024(self):
        """Feb 29, 2024 (leap year) is correctly formatted."""
        # Feb 29, 2024 is $H = 66899
        result = m_zdate("66899", "DD MON YYYY")
        assert result == "29 FEB 2024"
