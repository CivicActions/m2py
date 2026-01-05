"""Tests for Routine Head ASG analysis (§6.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.1
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MRoutine, MLabel


@pytest.mark.asg
class TestRoutineHeadAnalysis:
    """ASG-level tests for routine head analysis (§6.1).

    The routine head contains the routinename and optional formal parameter list.
    The first label in a routine serves as the routine head, with its name
    being the routine name and its formal_list containing any parameters.
    """

    def test_routine_name_extraction(self):
        """Routine name is correctly extracted to ASG (§6.1).

        The first label in the routine defines the routine head,
        and its name becomes the entry point for the routine.
        """
        parser = MUMPSParser()
        source = """MYROUTINE
\tS X=1
"""
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        assert len(routine.labels) >= 1
        # First label is the routine head
        head_label = routine.labels[0]
        assert isinstance(head_label, MLabel)
        assert head_label.name == "MYROUTINE"

    def test_formal_parameter_list(self):
        """Formal parameter list is correctly analyzed (§6.1).

        Parameters in the routine head are captured in the label's formal_list.
        These define the interface for calling the routine as an entry point.
        """
        parser = MUMPSParser()
        source = """CALC(X,Y,Z)
\tS R=X+Y+Z
\tQ R
"""
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        head_label = routine.labels[0]
        assert head_label.name == "CALC"
        # Formal parameters are captured in formal_list
        assert head_label.formal_list == ["X", "Y", "Z"]

    def test_routine_metadata(self):
        """Routine metadata is captured in ASG (§6.1).

        The routine ASG node captures metadata including labels,
        global references, and source information.
        """
        parser = MUMPSParser()
        source = """TEST
\tS ^GLOBAL=1
\tD SUB
\tQ
SUB\tW "Hello"
\tQ
"""
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        # Routine has multiple labels
        assert len(routine.labels) == 2
        label_names = [label.name for label in routine.labels]
        assert "TEST" in label_names
        assert "SUB" in label_names
        # Global references are tracked
        assert hasattr(routine, "global_refs")
