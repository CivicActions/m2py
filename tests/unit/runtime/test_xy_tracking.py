"""Tests for $X and $Y position tracking in MUMPSRuntime.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25 (WRITE command)

$X (horizontal position): Current column position (0-based)
$Y (vertical position): Current line position (0-based)

These special variables track the cursor position and are modified by:
- Writing characters: $X increments by 1 for each character
- Writing newline (!): $X resets to 0, $Y increments by 1
- Writing form feed (#): $X resets to 0, $Y resets to 0
- Writing tab (?n): $X moves to column n (if n > $X)
"""

import pytest

from m2py.runtime import MUMPSRuntime


@pytest.mark.runtime
class TestXTracking:
    """Tests for $X (horizontal column position) tracking."""

    def test_x_starts_at_zero(self):
        """$X starts at 0 for new runtime."""
        rt = MUMPSRuntime()
        assert rt._x == 0

    def test_x_increments_per_character(self):
        """$X increments by 1 for each character written."""
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("A")
        assert rt._x == 1

        rt.write("BC")
        assert rt._x == 3

        rt.write("DEFGH")
        assert rt._x == 8

    def test_x_resets_on_newline(self):
        """$X resets to 0 when newline format control is used.

        Note: This tests the W ! format control behavior via write_newline(),
        not embedded newlines in strings (which don't reset $X).
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("ABC")
        assert rt._x == 3

        rt.write_newline()  # W ! format control
        assert rt._x == 0

    def test_x_resets_on_formfeed(self):
        """$X resets to 0 when form feed is written."""
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("ABC")
        assert rt._x == 3

        rt.write_formfeed()
        assert rt._x == 0


@pytest.mark.runtime
class TestYTracking:
    """Tests for $Y (vertical line position) tracking."""

    def test_y_starts_at_zero(self):
        """$Y starts at 0 for new runtime."""
        rt = MUMPSRuntime()
        assert rt._y == 0

    def test_y_increments_on_newline(self):
        """$Y increments by 1 for each newline format control.

        Note: This tests the W ! format control behavior via write_newline(),
        not embedded newlines in strings (which don't affect $Y).
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write_newline()  # W !
        assert rt._y == 1

        rt.write_newline()  # W !
        assert rt._y == 2

        rt.write_newline()  # W !
        rt.write_newline()  # W !
        rt.write_newline()  # W !
        assert rt._y == 5

    def test_y_unchanged_by_regular_chars(self):
        """$Y is not affected by writing regular characters."""
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("Hello World")
        assert rt._y == 0

    def test_y_after_formfeed(self):
        """$Y is reset to 0 after form feed.

        YDB verified: After form feed, $Y=0.
        Form feed resets both $X and $Y to 0.
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write_formfeed()
        # Form feed resets $Y to 0
        assert rt._y == 0


@pytest.mark.runtime
class TestFormFeedBehavior:
    """Tests for form feed (#) output and position tracking."""

    def test_formfeed_output_at_start_of_line(self):
        """Form feed at $X=0 outputs just form feed character.

        YDB verified: W # at start outputs \x0c (no preceding newline,
        no trailing newline).
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write_formfeed()
        output = rt.get_output()

        # Should output just form feed character
        assert output == "\x0c"

    def test_formfeed_output_mid_line(self):
        """Form feed at $X>0 outputs newline before form feed.

        YDB verified: W "A",# outputs A\n\x0c (newline before form feed
        to complete current line before page break, no trailing newline).
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("A")
        rt.write_formfeed()
        output = rt.get_output()

        # Should output A + conditional newline + form feed
        assert output == "A\n\x0c"

    def test_formfeed_consecutive(self):
        """Consecutive form feeds: each outputs just form feed.

        YDB verified: W ## outputs \x0c\x0c (two form feeds, no newlines
        between them since $X=0 after each form feed).
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write_formfeed()
        rt.write_formfeed()
        output = rt.get_output()

        # Both form feeds at $X=0, so just two \x0c
        assert output == "\x0c\x0c"

    def test_formfeed_after_newline(self):
        """Form feed after newline: no extra newline added.

        YDB verified: W !,# outputs \n\x0c (newline, then form feed without
        extra newline since $X=0).
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write_newline()  # W ! format control
        rt.write_formfeed()
        output = rt.get_output()

        # Newline + form feed (no trailing newline)
        assert output == "\n\x0c"


@pytest.mark.runtime
class TestConditionalFormFeed:
    """Tests for conditional form feed pattern W:$Y>N #.

    This is a common MUMPS pagination pattern used in MUGJ tests.
    """

    def test_conditional_formfeed_not_triggered(self):
        """Form feed not written when $Y <= threshold.

        Pattern: W:$Y>55 # - only writes form feed when $Y > 55.
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        # Simulate 10 lines of output using format control newlines
        for _ in range(10):
            rt.write("Line")
            rt.write_newline()  # W ! format control

        assert rt._y == 10

        # Conditional check: should NOT trigger form feed
        if rt._y > 55:
            rt.write_formfeed()

        output = rt.get_output()
        assert "\x0c" not in output

    def test_conditional_formfeed_triggered(self):
        """Form feed written when $Y > threshold.

        Pattern: W:$Y>55 # - writes form feed when $Y > 55.
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        # Simulate 56 lines of output using format control newlines
        for _ in range(56):
            rt.write("Line")
            rt.write_newline()  # W ! format control

        assert rt._y == 56

        # Conditional check: should trigger form feed
        if rt._y > 55:
            rt.write_formfeed()

        output = rt.get_output()
        assert "\x0c" in output

    def test_conditional_formfeed_resets_y(self):
        """After form feed triggers, $Y resets for next page.

        This ensures subsequent $Y checks work correctly.
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        # Simulate 56 lines to trigger form feed using format control newlines
        for _ in range(56):
            rt.write("Line")
            rt.write_newline()  # W ! format control

        assert rt._y == 56

        # Trigger form feed
        rt.write_formfeed()

        # $Y should reset to 0 (YDB verified)
        assert rt._y == 0

        # More lines should increment from there
        rt.write("Next page line 1")
        rt.write_newline()  # W ! format control
        assert rt._y == 1


@pytest.mark.runtime
class TestTabColumnTracking:
    """Tests for tab (?n) and its effect on $X."""

    def test_tab_forward(self):
        """Tab to column ahead of current position."""
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("AB")  # $X = 2
        rt.write_tab(10)  # Tab to column 10

        assert rt._x == 10

    def test_tab_no_effect_past_column(self):
        """Tab has no effect when already past target column."""
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("HELLO")  # $X = 5
        rt.write_tab(3)  # Tab to column 3 (already past)

        # $X unchanged
        assert rt._x == 5

    def test_tab_output_spaces(self):
        """Tab outputs correct number of spaces."""
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("AB")  # $X = 2
        rt.write_tab(5)  # Tab to column 5

        output = rt.get_output()
        # "AB" + 3 spaces to reach column 5
        assert output == "AB   "


@pytest.mark.runtime
class TestIntegratedWriteTracking:
    """Integration tests combining multiple writes and format controls."""

    def test_complex_write_sequence(self):
        """Complex write sequence with multiple format controls.

        MUMPS: W "Line1",!,"Line2",!,!,"After blank",!
        Uses write_newline() for W ! format control.
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        rt.write("Line1")
        assert rt._x == 5
        assert rt._y == 0

        rt.write_newline()  # W !
        assert rt._x == 0
        assert rt._y == 1

        rt.write("Line2")
        assert rt._x == 5
        assert rt._y == 1

        rt.write_newline()  # W !
        rt.write_newline()  # W ! (blank line)
        assert rt._x == 0
        assert rt._y == 3

        rt.write("After blank")
        assert rt._x == 11
        assert rt._y == 3

    def test_formfeed_mid_output(self):
        """Form feed in middle of output stream.

        Simulates pagination break in middle of test output.
        Uses write_newline() for W ! format control.
        """
        rt = MUMPSRuntime()
        rt._capture_output = True

        # First page content
        rt.write("Page 1 content")
        rt.write_newline()  # W !
        rt.write("More content")
        rt.write_newline()  # W !
        assert rt._y == 2

        # Page break
        rt.write_formfeed()
        assert rt._y == 0  # Reset after form feed (YDB verified)
        assert rt._x == 0

        # Second page content
        rt.write("Page 2 content")
        rt.write_newline()  # W !
        assert rt._y == 1
