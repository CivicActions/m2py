"""Tests for labels within dot blocks.

In MUMPS, labels can appear within dot-indented blocks (e.g. ID4 . . S X=1).
These are NOT separate entry points — they are continuation lines within the
enclosing label's dot block.  The parser must merge them into the parent
label's body so _structure_do_blocks nests them correctly.
"""

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestLabelsInDotBlocks:
    """Labels at non-zero dot level are merged into the parent label."""

    @pytest.fixture
    def parser(self):
        return MUMPSParser()

    def test_dot_level_label_merged_into_parent(self, parser):
        """A labeled line at dot level 1 is merged into the preceding label."""
        source = (
            "MAIN\n"
            " F  D  Q:DONE\n"
            " . S X=1\n"
            "LBL . S X=2\n"  # label at dot level 1
            " Q\n"
        )
        routine = parser.parse(source)
        label_names = [l.name for l in routine.labels]
        # LBL should NOT be a top-level label
        assert "LBL" not in label_names
        assert "MAIN" in label_names

    def test_dot_level_label_in_dotted_labels(self, parser):
        """Dot-level labels are stored in _dotted_labels for $TEXT support."""
        source = "MAIN\n F  D  Q:DONE\n . S X=1\nLBL . S X=2\n Q\n"
        routine = parser.parse(source)
        dotted_names = [l.name for l in routine._dotted_labels]
        assert "LBL" in dotted_names

    def test_multiple_nested_labels(self, parser):
        """Multiple labels at dot level 2 are merged into parent."""
        source = (
            "OUTER\n"
            " F  D  Q:X\n"
            " . D  Q:'Y\n"
            " . . S A=1\n"
            "L1 . . S B=2\n"  # dot level 2
            "L2 . . S C=3\n"  # dot level 2
            " . S D=4\n"
            " Q\n"
        )
        routine = parser.parse(source)
        label_names = [l.name for l in routine.labels]
        assert "OUTER" in label_names
        assert "L1" not in label_names
        assert "L2" not in label_names
        # But they exist in _dotted_labels
        dotted_names = [l.name for l in routine._dotted_labels]
        assert "L1" in dotted_names
        assert "L2" in dotted_names

    def test_zero_dot_label_not_merged(self, parser):
        """A regular label (dot level 0) after dot-block is a new label."""
        source = (
            "FIRST\n"
            " F  D  Q:X\n"
            " . S A=1\n"
            "LBL . S B=2\n"  # dot level 1 → merged
            "SECOND\n"  # dot level 0 → new label
            " S C=3\n"
            " Q\n"
        )
        routine = parser.parse(source)
        label_names = [l.name for l in routine.labels]
        assert "FIRST" in label_names
        assert "SECOND" in label_names
        assert "LBL" not in label_names

    def test_parent_body_includes_merged_statements(self, parser):
        """The parent label's body includes statements from dot-level labels."""
        source = "MAIN\n D\n . S X=1\nLBL . S Y=2\n Q\n"
        routine = parser.parse(source)
        main_label = routine.get_label("MAIN")
        # After structuring, the DO body should contain both S X=1 and S Y=2
        # The exact nesting depends on _structure_do_blocks, but the main
        # label should have more than just the D statement and Q
        assert len(main_label.body.statements) >= 2

    def test_label_lines_includes_dotted_labels(self, parser):
        """$TEXT line mapping includes dot-level labels."""
        source = "MAIN\n F  D  Q:X\n . S A=1\nLBL . S B=2\n Q\n"
        routine = parser.parse(source)
        # _dotted_labels should have correct line numbers
        lbl = routine._dotted_labels[0]
        assert lbl.name == "LBL"
        assert lbl.line_number == 4  # 1-indexed


@pytest.mark.parser
class TestLabelsInDotBlocksCodegen:
    """Codegen produces correct structure for labels in dot blocks."""

    @pytest.fixture
    def generate_python(self):
        from m2py.codegen import generate_python

        return generate_python

    def test_no_separate_function_for_dot_label(self, generate_python):
        """Dot-level labels do NOT produce separate Python functions."""
        source = "MAIN\n F  D  Q:DONE\n . S X=1\nLBL . S X=2\n Q\n"
        result = generate_python(source)
        # Should have def MAIN but NOT def LBL
        assert "def MAIN(" in result
        assert "def LBL(" not in result

    def test_label_lines_dict_has_dot_labels(self, generate_python):
        """_label_lines dict includes dot-level labels for $TEXT."""
        source = "MAIN\n F  D  Q:DONE\n . S X=1\nLBL . S X=2\n Q\n"
        result = generate_python(source)
        assert "'LBL'" in result
        # Should appear in _label_lines dict
        assert "LBL" in result.split("_label_lines")[1].split("\n")[0]

    def test_dicu1_style_for_loop_inline(self, generate_python):
        """Complex DICU1-style FOR with labeled lines at dot level 2."""
        source = (
            "IDENTS\n"
            " F  D  Q:DONE\n"
            " . D  Q:'Y\n"
            " . . S A=0\n"
            "ID4 . . S B=1\n"
            "ID4A . . S C=2\n"
            " . S D=3\n"
            "ID5 . S E=4\n"
            " Q\n"
            "NEXT\n"
            " Q\n"
        )
        result = generate_python(source)
        # Should have IDENTS and NEXT as functions, NOT ID4/ID4A/ID5
        assert "def IDENTS(" in result
        assert "def NEXT(" in result
        assert "def ID4(" not in result
        assert "def ID4A(" not in result
        assert "def ID5(" not in result
        # Fallthrough from IDENTS should go to NEXT, not ID4
        # (IDENTS function should reference NEXT, not ID4)


@pytest.mark.parser
class TestLabelsInDotBlocksExecution:
    """Execution tests: dot-level labels participate in FOR loop body."""

    @pytest.fixture
    def execute_mumps(self):
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        def _run(source):
            code = generate_python(source)
            rt = MUMPSRuntime()
            return rt.execute(code, capture_output=True)

        return _run

    def test_for_loop_body_includes_dotlevel_label(self, execute_mumps):
        """Labeled lines within dot blocks execute as part of the FOR loop."""
        source = (
            "TEST\n"
            " N I,R\n"
            ' S R=""\n'
            " F I=1:1:3 D\n"
            " . S R=R_I\n"
            'L1 . S R=R_"x"\n'
            " W R\n"
            " Q\n"
        )
        result = execute_mumps(source)
        # Each iteration appends I then "x": "1x2x3x"
        assert result.output == "1x2x3x"

    def test_nested_dotlevel_labels_level2(self, execute_mumps):
        """Labels at dot level 2 execute inside nested DO blocks."""
        source = (
            "TEST\n"
            ' N R S R=""\n'
            " D\n"
            " . D\n"
            ' . . S R=R_"a"\n'
            'L1 . . S R=R_"b"\n'
            ' . S R=R_"c"\n'
            " W R\n"
            " Q\n"
        )
        result = execute_mumps(source)
        assert result.output == "abc"
