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
# helpers.py: m_range edge cases
# =============================================================================
