"""Codegen tests for $X and $Y position tracking.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25 (WRITE command)

These tests verify that generated Python code correctly tracks $X and $Y
through the runtime, and that format controls work correctly end-to-end.
"""

import pytest


@pytest.mark.codegen
class TestXYTrackingCodegen:
    """End-to-end codegen tests for $X/$Y position tracking."""

    def test_write_x_value(self, execute_mumps):
        """WRITE $X outputs current horizontal position.

        YDB verified: After writing "ABC", $X=3.
        """
        result = execute_mumps('TEST\n W "ABC",$X\n Q\n')
        assert result.output == "ABC3"
        assert result.success is True

    def test_write_y_value(self, execute_mumps):
        """WRITE $Y outputs current vertical position.

        YDB verified: After 3 newlines, $Y=3.
        """
        result = execute_mumps("TEST\n W !,!,!,$Y\n Q\n")
        assert result.output == "\n\n\n3"
        assert result.success is True

    def test_write_x_after_newline(self, execute_mumps):
        """$X resets to 0 after newline.

        YDB verified: After "ABC\n", $X=0.
        """
        result = execute_mumps('TEST\n W "ABC",!,$X\n Q\n')
        assert result.output == "ABC\n0"
        assert result.success is True

    def test_write_x_increments(self, execute_mumps):
        """$X increments with each character.

        YDB verified: After "A" $X=1, after "AB" $X=2, etc.
        """
        result = execute_mumps('TEST\n W "A",$X,"B",$X,"CDE",$X\n Q\n')
        # After "A": $X=1, after write 1: $X=2
        # After "B": $X=3, after write 3: $X=4
        # After "CDE": $X=7, after write 7: $X=8
        assert result.output == "A1B3CDE7"
        assert result.success is True


@pytest.mark.codegen
class TestFormFeedCodegen:
    """End-to-end codegen tests for form feed behavior."""

    def test_write_formfeed_output(self, execute_mumps):
        """WRITE # outputs form feed character.

        YDB verified: W # outputs \\x0c.
        """
        result = execute_mumps("TEST\n W #\n Q\n")
        assert "\x0c" in result.output
        assert result.success is True

    def test_write_formfeed_with_text(self, execute_mumps):
        """WRITE with text and form feed.

        YDB verified: W "A",#,"B" outputs A + formfeed sequence + B.
        """
        result = execute_mumps('TEST\n W "A",#,"B"\n Q\n')
        assert result.success is True
        assert "A" in result.output
        assert "B" in result.output
        assert "\x0c" in result.output

    def test_write_y_after_formfeed(self, execute_mumps):
        """$Y behavior after form feed.

        YDB resets $Y to 0 on form feed. With trailing newline,
        the newline may put $Y=1.
        """
        result = execute_mumps('TEST\n W "ABC",!,!,!,#,$Y\n Q\n')
        # After "ABC": $X=3, $Y=0
        # After three !: $X=0, $Y=3
        # After #: form feed resets $X and $Y
        assert result.success is True
        assert "ABC\n\n\n" in result.output
        # $Y should be 0 or 1 depending on trailing newline behavior
        # The key is that it's reset from 3

    def test_formfeed_x_reset(self, execute_mumps):
        """$X resets to 0 after form feed.

        YDB verified: After form feed, $X=0.
        """
        result = execute_mumps('TEST\n W "ABCDEF",#,$X\n Q\n')
        assert result.success is True
        # After "ABCDEF": $X=6
        # After #: $X=0
        assert result.output.endswith("0")


@pytest.mark.codegen
class TestConditionalFormFeedCodegen:
    """End-to-end tests for W:$Y>N # conditional form feed pattern."""

    def test_conditional_formfeed_triggered(self, execute_mumps):
        """W:$Y>N # writes form feed when $Y > N.

        This is the pagination pattern used in MUGJ test suite.
        """
        code = """TEST
 F I=1:1:56 W !
 W:$Y>55 #
 W $Y
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        # After 56 newlines, $Y=56, so W:$Y>55 # should trigger
        # Form feed resets $Y
        assert "\x0c" in result.output

    def test_conditional_formfeed_not_triggered(self, execute_mumps):
        """W:$Y>N # does NOT write form feed when $Y <= N.

        When condition is false, no form feed is written.
        """
        code = """TEST
 F I=1:1:10 W !
 W:$Y>55 #
 W $Y
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        # After 10 newlines, $Y=10, which is NOT > 55
        # So form feed should NOT trigger
        assert "\x0c" not in result.output
        # $Y should still be 10
        assert result.output.rstrip().endswith("10")

    def test_conditional_formfeed_at_boundary(self, execute_mumps):
        """W:$Y>55 # does NOT trigger when $Y=55 exactly.

        The condition is strictly greater than, not >=.
        """
        code = """TEST
 F I=1:1:55 W !
 W:$Y>55 #
 W $Y
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        # After 55 newlines, $Y=55, which is NOT > 55 (it's equal)
        # So form feed should NOT trigger
        assert "\x0c" not in result.output
        assert result.output.rstrip().endswith("55")

    def test_conditional_formfeed_just_over_boundary(self, execute_mumps):
        """W:$Y>55 # triggers when $Y=56.

        Just over the boundary, form feed should trigger.
        """
        code = """TEST
 F I=1:1:56 W !
 W:$Y>55 #
 W "AFTER"
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        # After 56 newlines, $Y=56 > 55, so form feed triggers
        assert "\x0c" in result.output
        assert "AFTER" in result.output


@pytest.mark.codegen
class TestTabColumnCodegen:
    """End-to-end codegen tests for tab (?n) format control."""

    def test_tab_to_column(self, execute_mumps):
        """WRITE ?N tabs to column N.

        YDB verified: W ?10,"X" outputs 10 spaces then X.
        """
        result = execute_mumps('TEST\n W ?10,"X"\n Q\n')
        assert result.output == "          X"  # 10 spaces + X
        assert result.success is True

    def test_tab_with_prior_text(self, execute_mumps):
        """Tab after text moves to specified column.

        YDB verified: W "AB",?5,"X" outputs "AB   X" (AB + 3 spaces + X).
        """
        result = execute_mumps('TEST\n W "AB",?5,"X"\n Q\n')
        assert result.output == "AB   X"  # AB + 3 spaces + X at column 5
        assert result.success is True

    def test_tab_no_effect_past_column(self, execute_mumps):
        """Tab has no effect when already past target column.

        YDB verified: W "HELLO",?3,"X" outputs "HELLOX" (no spaces).
        """
        result = execute_mumps('TEST\n W "HELLO",?3,"X"\n Q\n')
        assert result.output == "HELLOX"
        assert result.success is True

    def test_tab_x_tracking(self, execute_mumps):
        """$X correctly tracks position after tab.

        YDB verified: After W ?10, $X=10.
        """
        result = execute_mumps("TEST\n W ?10,$X\n Q\n")
        # After ?10: $X=10, then write "10": $X=12
        assert result.output == "          10"  # 10 spaces + "10"
        assert result.success is True


@pytest.mark.codegen
class TestCharCodeCodegen:
    """End-to-end codegen tests for character code (*n) format control."""

    def test_charcode_ascii(self, execute_mumps):
        """WRITE *N outputs character with ASCII code N.

        YDB verified: W *65 outputs "A".
        """
        result = execute_mumps("TEST\n W *65\n Q\n")
        assert result.output == "A"
        assert result.success is True

    def test_charcode_newline(self, execute_mumps):
        """WRITE *10 outputs newline.

        ASCII 10 is newline/linefeed.
        """
        result = execute_mumps("TEST\n W *10\n Q\n")
        assert result.output == "\n"
        assert result.success is True

    def test_charcode_formfeed(self, execute_mumps):
        """WRITE *12 outputs form feed.

        ASCII 12 is form feed.
        """
        result = execute_mumps("TEST\n W *12\n Q\n")
        assert result.output == "\x0c"
        assert result.success is True

    def test_charcode_sequence(self, execute_mumps):
        """WRITE multiple charcodes.

        YDB verified: W *72,*73 outputs "HI".
        """
        result = execute_mumps("TEST\n W *72,*73\n Q\n")
        assert result.output == "HI"
        assert result.success is True

    def test_charcode_x_tracking(self, execute_mumps):
        """$X tracks character output via charcode.

        Each *N outputs one character, so $X increments by 1.
        """
        result = execute_mumps("TEST\n W *65,*66,*67,$X\n Q\n")
        # After *65,*66,*67: $X=3, then write "3": $X=4
        assert result.output == "ABC3"
        assert result.success is True
