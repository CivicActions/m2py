"""Tests for codegen/routine.py validation functions."""

import pytest


pytestmark = pytest.mark.codegen


class TestAnalysisNotCompleteError:
    """Tests for AnalysisNotCompleteError and validate_analysis_complete."""

    def test_error_creation(self):
        """AnalysisNotCompleteError stores field and pass names."""
        from m2py.codegen.routine import AnalysisNotCompleteError

        err = AnalysisNotCompleteError("loop_type", "analyze_for_loops", "line 5")
        assert err.missing_field == "loop_type"
        assert err.required_pass == "analyze_for_loops"
        assert "loop_type" in str(err)
        assert "analyze_for_loops" in str(err)
        assert "line 5" in str(err)

    def test_error_without_context(self):
        """AnalysisNotCompleteError works without context string."""
        from m2py.codegen.routine import AnalysisNotCompleteError

        err = AnalysisNotCompleteError("goto_type", "classify_gotos")
        assert "goto_type" in str(err)
        assert " in " not in str(err)

    def test_validate_empty_routine(self):
        """validate_analysis_complete on empty routine doesn't raise."""
        from m2py.codegen.routine import validate_analysis_complete
        from m2py.asg.elements import MRoutine

        routine = MRoutine(name="TEST")
        validate_analysis_complete(routine)  # Should not raise

    def test_validate_unanalyzed_for(self):
        """validate_analysis_complete raises for unanalyzed FOR."""
        from m2py.codegen.routine import (
            AnalysisNotCompleteError,
            validate_analysis_complete,
        )
        from m2py.asg.statements import MForStatement
        from m2py.asg.elements import MLabel, MRoutine, MScope

        # Manually construct a FOR with loop_type=None (unanalyzed)
        for_stmt = MForStatement()
        for_stmt.line_number = 2
        scope = MScope()
        scope.statements = [for_stmt]
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST")
        routine.labels = [label]
        with pytest.raises(AnalysisNotCompleteError) as exc_info:
            validate_analysis_complete(routine)
        assert exc_info.value.missing_field == "loop_type"

    def test_validate_unanalyzed_goto(self):
        """validate_analysis_complete raises for unanalyzed GOTO."""
        from m2py.codegen.routine import (
            AnalysisNotCompleteError,
            validate_analysis_complete,
        )
        from m2py.asg.statements import MGotoStatement
        from m2py.asg.elements import MLabel, MRoutine, MScope

        # Manually construct a GOTO with goto_type=None (unanalyzed)
        goto_stmt = MGotoStatement()
        goto_stmt.line_number = 2
        scope = MScope()
        scope.statements = [goto_stmt]
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST")
        routine.labels = [label]
        with pytest.raises(AnalysisNotCompleteError) as exc_info:
            validate_analysis_complete(routine)
        assert exc_info.value.missing_field == "goto_type"

    def test_validate_complete_passes(self):
        """validate_analysis_complete passes when analysis is done."""
        from m2py.codegen.routine import validate_analysis_complete
        from m2py.parser import MUMPSParser
        from m2py.analysis import analyze_for_loops, classify_gotos, resolve_references
        from m2py.analysis.for_analysis import analyze_quit_context

        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tF I=1:1:5 W I\n\tQ\n")
        resolve_references(routine)
        classify_gotos(routine)
        analyze_for_loops(routine)
        analyze_quit_context(routine)
        validate_analysis_complete(routine)  # Should not raise


# =============================================================================
# _fix_empty_blocks post-processing
# =============================================================================


class TestFixEmptyBlocks:
    """Tests for _fix_empty_blocks post-processing function."""

    def _fix(self, code: str) -> str:
        from m2py.codegen.routine import _fix_empty_blocks

        return _fix_empty_blocks(code)

    def test_empty_if_block(self):
        """Empty if block gets 'pass' inserted."""
        code = "if x:\nfoo()"
        result = self._fix(code)
        assert result == "if x:\n    pass\nfoo()"

    def test_empty_elif_block(self):
        """Empty elif block gets 'pass' inserted."""
        code = "if x:\n    do_x()\nelif y:\nelse:\n    do_else()"
        result = self._fix(code)
        assert "elif y:\n    pass\n" in result

    def test_empty_else_block(self):
        """Empty else block at end of code gets 'pass' inserted."""
        code = "if x:\n    do_x()\nelse:"
        result = self._fix(code)
        assert result == "if x:\n    do_x()\nelse:\n    pass"

    def test_nested_empty_blocks(self):
        """Nested empty if blocks both get 'pass'."""
        code = "    if a:\n        if b:\n    c()"
        result = self._fix(code)
        assert "        if b:\n            pass\n" in result

    def test_blank_lines_between_if_and_next(self):
        """Blank lines between if and next code are ignored."""
        code = "if x:\n\n\nfoo()"
        result = self._fix(code)
        assert "    pass" in result

    def test_multiple_consecutive_empty_blocks(self):
        """Multiple consecutive empty blocks all get 'pass'."""
        code = "if a:\nelif b:\nelse:\nfoo()"
        result = self._fix(code)
        assert result.count("pass") == 3

    def test_non_empty_block_unchanged(self):
        """Non-empty if block is not modified."""
        code = "if x:\n    do_thing()\nfoo()"
        result = self._fix(code)
        assert result == code

    def test_indented_empty_block(self):
        """Empty block inside function body (indented) works."""
        code = "def f():\n    if x:\n    return 0"
        result = self._fix(code)
        assert "        pass" in result

    def test_if_with_condition_containing_colon_no_false_positive(self):
        """Lines with colons in conditions but not ending with colon are skipped."""
        code = 'x = {"a": 1}\nfoo()'
        result = self._fix(code)
        assert result == code

    def test_preserves_existing_body(self):
        """If block with proper indented body is not altered."""
        code = "if cond:\n    x = 1\n    y = 2\nz = 3"
        result = self._fix(code)
        assert result == code

    def test_empty_block_at_eof_no_trailing_lines(self):
        """Empty if block at very end of file gets pass."""
        code = "if x:"
        result = self._fix(code)
        assert result == "if x:\n    pass"

    def test_real_codegen_pattern_conditional_do(self):
        """Pattern from MUMPS conditional DO: if at same indent level."""
        code = "    if m_truth(var):\n    _scope['X'] = MArray(value=1)\n"
        result = self._fix(code)
        assert "        pass\n" in result


class TestFixEmptyBlocksIntegration:
    """Integration tests: transpile real MUMPS patterns that produce empty blocks."""

    def test_conditional_do_end_of_line(self, generate_python):
        """Conditional DO at end of line should not produce empty if block."""
        source = "TEST\n S X=1 D:X SUB\n Q\nSUB W X,!\n Q\n"
        code = generate_python(source)
        import ast

        ast.parse(code)

    def test_if_at_end_of_line(self, generate_python):
        """IF at end of MUMPS line should not produce empty if block."""
        source = 'TEST\n S X=1 I X\n W "yes",!\n Q\n'
        code = generate_python(source)
        import ast

        ast.parse(code)

    def test_for_quit_if_goto_pattern(self, generate_python):
        """FOR+QUIT+IF+GOTO pattern (PSAPUR-like) produces valid Python."""
        source = (
            "TEST\n"
            ' F  S X=$O(^DATA(X)) Q:\'X  I $P(^DATA(X,0),U,2)="P" D\n'
            " .S Y=0\n"
            " .F  S Y=$O(^DATA(X,1,Y)) Q:'Y  I Y>0 G DONE\n"
            " Q\n"
            "DONE Q\n"
        )
        result = generate_python(source)
        assert result
        import ast

        ast.parse(result)

    def test_multi_label_goto_pattern(self, generate_python):
        """G LABEL1:cond,LABEL2:cond pattern (XINDX10-like) produces valid Python."""
        source = (
            'TEST\n S X=9.4\n G A:X=9.4,B:X=9.7\n Q\nA W "pkg",! Q\nB W "next",! Q\n'
        )
        result = generate_python(source)
        assert result
        import ast

        ast.parse(result)


# =============================================================================
# _fix_import_in_elif_chain post-processing
# =============================================================================


class TestFixImportInElifChain:
    """Tests for _fix_import_in_elif_chain post-processing function."""

    def _fix(self, code: str) -> str:
        from m2py.codegen.routine import _fix_import_in_elif_chain

        return _fix_import_in_elif_chain(code)

    def test_import_between_if_and_elif(self):
        """Import between if and elif is hoisted above the if."""
        code = "if a:\n    return 1\nimport foo\nelif b:\n    return 2\n"
        result = self._fix(code)
        lines = result.split("\n")
        import_idx = next(i for i, l in enumerate(lines) if l.strip() == "import foo")
        if_idx = next(i for i, l in enumerate(lines) if l.strip().startswith("if a:"))
        assert import_idx < if_idx

    def test_import_between_if_and_else(self):
        """Import between if block and else is hoisted."""
        code = "if a:\n    return 1\nimport bar\nelse:\n    return 2\n"
        result = self._fix(code)
        lines = result.split("\n")
        import_idx = next(i for i, l in enumerate(lines) if l.strip() == "import bar")
        if_idx = next(i for i, l in enumerate(lines) if l.strip().startswith("if a:"))
        assert import_idx < if_idx

    def test_import_not_breaking_chain_unchanged(self):
        """Import not between if/elif is left in place."""
        code = "import foo\nif a:\n    return 1\n"
        result = self._fix(code)
        assert result == code

    def test_indented_import_elif_chain(self):
        """Indented import breaking elif chain is hoisted."""
        code = (
            "    if a:\n"
            "        return 1\n"
            "    import baz\n"
            "    elif b:\n"
            "        return 2\n"
        )
        result = self._fix(code)
        lines = result.split("\n")
        import_idx = next(i for i, l in enumerate(lines) if "import baz" in l)
        if_idx = next(i for i, l in enumerate(lines) if "if a:" in l)
        assert import_idx < if_idx

    def test_import_hoisting_with_goto_pattern(self, generate_python):
        """Routine with GOTOs producing import between if/elif (XMCTLK pattern)."""
        source = (
            "TEST\n"
            ' I \'$D(DUZ) W "no DUZ",! Q\n'
            " S X=1 G:X A\n"
            " I X=2 G B\n"
            " Q\n"
            'A W "A",! Q\n'
            'B W "B",! Q\n'
        )
        result = generate_python(source)
        assert result
        import ast

        ast.parse(result)

    def test_from_import_also_hoisted(self):
        """'from X import Y' breaking chain is also hoisted."""
        code = (
            "if a:\n"
            "    return 1\n"
            "from m2py.runtime import LabelNotFoundError\n"
            "elif b:\n"
            "    return 2\n"
        )
        result = self._fix(code)
        lines = result.split("\n")
        import_idx = next(i for i, l in enumerate(lines) if "from m2py.runtime" in l)
        if_idx = next(i for i, l in enumerate(lines) if l.strip().startswith("if a:"))
        assert import_idx < if_idx


# =============================================================================
# helpers.py: m_range edge cases
# =============================================================================
