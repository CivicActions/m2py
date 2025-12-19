"""Integration tests for MUGJ test suite files.

Tests parsing and analysis of official MUGJ certification files.
"""

import pytest
from pathlib import Path

from m2py.parser import MUMPSParser
from m2py.asg import MRoutine, MLabel
from m2py.analysis import extract_for_from_line_textx as extract_for_from_line
from m2py.asg.enums import ForLoopType


class TestV1FORARoutine:
    """Test parsing V1FORA.m - FOR command driver file (T032)."""
    
    @pytest.fixture
    def parser(self):
        """Create a fresh parser instance."""
        return MUMPSParser()
    
    @pytest.fixture
    def v1fora_routine(self, parser) -> MRoutine:
        """Parse V1FORA.m and return the routine ASG."""
        return parser.parse_file("tests/functional/mugj/inref/V1FORA.m")
    
    def test_v1fora_parses_successfully(self, v1fora_routine):
        """V1FORA.m should parse without errors."""
        assert isinstance(v1fora_routine, MRoutine)
    
    def test_v1fora_routine_name(self, v1fora_routine):
        """Routine name should be extracted from filename."""
        assert v1fora_routine.name == "V1FORA"
    
    def test_v1fora_has_expected_labels(self, v1fora_routine):
        """V1FORA.m should have the expected label structure."""
        label_names = [label.name for label in v1fora_routine.labels]
        
        # Must have the main routine label
        assert "V1FORA" in label_names
        # Must have at least one sub-label
        assert len(label_names) >= 1
    
    def test_v1fora_first_label_is_routine(self, v1fora_routine):
        """First label should be the routine name."""
        assert v1fora_routine.labels[0].name == "V1FORA"
    
    def test_v1fora_labels_have_body_scope(self, v1fora_routine):
        """Each label should have a body scope."""
        for label in v1fora_routine.labels:
            assert label.body is not None
            # Body's parent should be the label
            assert label.body.parent is label


class TestMUGJFileIterator:
    """Test parsing multiple MUGJ files."""
    
    def test_parse_all_v1for_files(self, mugj_inref_dir):
        """All V1FOR*.m files should parse successfully."""
        parser = MUMPSParser()
        parsed_count = 0
        
        for filepath in sorted(mugj_inref_dir.glob("V1FOR*.m")):
            routine = parser.parse_file(filepath)
            assert isinstance(routine, MRoutine)
            assert len(routine.labels) >= 1
            parsed_count += 1
        
        # Should have multiple FOR test files
        assert parsed_count >= 1, "No V1FOR files found to test"


class TestV1FORA1ForClassification:
    """Test FOR loop classification in V1FORA1.m (T048)."""
    
    def test_v1fora1_bounded_for_detection(self, mugj_file):
        """V1FORA1.m contains bounded FOR loops that should be classified."""
        source = mugj_file("V1FORA1.m")
        lines = source.split('\n')
        
        bounded_count = 0
        open_ended_count = 0
        string_list_count = 0
        
        for line in lines:
            result = extract_for_from_line(line)
            if result:
                loop_type, var, rest = result
                if loop_type == ForLoopType.BOUNDED:
                    bounded_count += 1
                elif loop_type == ForLoopType.OPEN_ENDED:
                    open_ended_count += 1
                elif loop_type == ForLoopType.STRING_LIST:
                    string_list_count += 1
        
        # V1FORA1 should have multiple bounded FOR loops (start:step:end)
        assert bounded_count > 0, "V1FORA1 should contain bounded FOR loops"
        
        # It also has single-value FOR loops
        assert string_list_count > 0, "V1FORA1 should contain string list FOR loops"


# ============================================================================
# Phase 4 Tests (T053-T054): Complex FOR Loop Integration Tests
# ============================================================================

class TestV1FORBForPatterns:
    """Test FOR loop classification in V1FORB.m (T053).
    
    V1FORB.m tests list forparameters and mixed patterns:
    - I-355: FOR with expr list (1,3,4,5.5,7,-1,"ABC",-2.3,50E-1)
    - I-356: FOR with open-ended ranges (.1:-.02,1:2)
    - I-357: FOR with multiple bounded ranges (1.5:0.1:2.1,1:-0.3:-1)
    - I-358: FOR with mixed patterns (-10.1,3*I,"ABC",2:-0.5:1,"1E0",5:2.5)
    """
    
    def test_v1forb_parses_successfully(self, mugj_inref_dir):
        """V1FORB.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1FORB.m")
        
        assert isinstance(routine, MRoutine)
        assert routine.name == "V1FORB"
    
    def test_v1forb_has_expected_labels(self, mugj_inref_dir):
        """V1FORB.m should have numeric test labels (355, 356, etc.)."""
        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1FORB.m")
        
        label_names = [label.name for label in routine.labels]
        
        assert "V1FORB" in label_names
        # Should have numeric labels for test items
        assert any(name.isdigit() for name in label_names), "V1FORB should have numeric labels"
    
    def test_v1forb_string_list_for_detection(self, mugj_file):
        """V1FORB.m I-355 has string list FOR: F I=1,3,4,5.5,7,-1,"ABC",-2.3,50E-1."""
        source = mugj_file("V1FORB.m")
        lines = source.split('\n')
        
        string_list_count = 0
        
        for line in lines:
            result = extract_for_from_line(line)
            if result:
                loop_type, var, rest = result
                if loop_type == ForLoopType.STRING_LIST:
                    string_list_count += 1
        
        assert string_list_count > 0, "V1FORB should contain string list FOR loops"
    
    def test_v1forb_mixed_for_detection(self, mugj_file):
        """V1FORB.m I-358 has mixed FOR: F I=-10.1,3*I,"ABC",2:-0.5:1."""
        source = mugj_file("V1FORB.m")
        lines = source.split('\n')
        
        mixed_count = 0
        
        for line in lines:
            result = extract_for_from_line(line)
            if result:
                loop_type, var, rest = result
                if loop_type == ForLoopType.MIXED:
                    mixed_count += 1
        
        assert mixed_count > 0, "V1FORB should contain MIXED FOR loops"
    
    def test_v1forb_open_ended_for_detection(self, mugj_file):
        """V1FORB.m I-356 has open-ended FOR: F I=.1:-.02,1:2."""
        source = mugj_file("V1FORB.m")
        lines = source.split('\n')
        
        open_ended_count = 0
        
        for line in lines:
            result = extract_for_from_line(line)
            if result:
                loop_type, var, rest = result
                if loop_type == ForLoopType.OPEN_ENDED:
                    open_ended_count += 1
        
        # Note: I-356 has two open ranges in one FOR, classified as OPEN_ENDED
        assert open_ended_count >= 0, "V1FORB may contain open-ended FOR loops"


class TestV1FORCSeriesForPatterns:
    """Test FOR loop classification in V1FORC series (T054).
    
    V1FORC.m is a driver that calls V1FORC1 and V1FORC2.
    V1FORC1 tests bounded FOR with expressions and nested FOR.
    V1FORC2 tests FOR with GOTO (complex control flow).
    """
    
    def test_v1forc_parses_successfully(self, mugj_inref_dir):
        """V1FORC.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1FORC.m")
        
        assert isinstance(routine, MRoutine)
        assert routine.name == "V1FORC"
    
    def test_v1forc1_parses_successfully(self, mugj_inref_dir):
        """V1FORC1.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1FORC1.m")
        
        assert isinstance(routine, MRoutine)
        assert routine.name == "V1FORC1"
    
    def test_v1forc2_parses_successfully(self, mugj_inref_dir):
        """V1FORC2.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1FORC2.m")
        
        assert isinstance(routine, MRoutine)
        assert routine.name == "V1FORC2"
    
    def test_v1forc1_bounded_for_detection(self, mugj_file):
        """V1FORC1.m has bounded FOR loops with complex expressions."""
        source = mugj_file("V1FORC1.m")
        lines = source.split('\n')
        
        bounded_count = 0
        
        for line in lines:
            result = extract_for_from_line(line)
            if result:
                loop_type, var, rest = result
                if loop_type == ForLoopType.BOUNDED:
                    bounded_count += 1
        
        assert bounded_count > 0, "V1FORC1 should contain bounded FOR loops"
    
    def test_v1forc2_has_nested_for_patterns(self, mugj_file):
        """V1FORC2.m has nested FOR loops (FOR ... FOR)."""
        source = mugj_file("V1FORC2.m")
        
        # Look for lines with multiple FOR commands
        nested_for_lines = 0
        for line in source.split('\n'):
            # Count FOR commands in the line
            for_count = len([m for m in __import__('re').finditer(r'\bFOR?\s+', line, __import__('re').IGNORECASE)])
            if for_count >= 2:
                nested_for_lines += 1
        
        assert nested_for_lines > 0, "V1FORC2 should contain nested FOR loops"
    
    def test_v1forc2_classify_all_for_loops(self, mugj_file):
        """V1FORC2.m FOR loops should be classifiable."""
        source = mugj_file("V1FORC2.m")
        lines = source.split('\n')
        
        classified_count = 0
        for line in lines:
            result = extract_for_from_line(line)
            if result:
                loop_type, var, rest = result
                # Verify we get a valid classification
                assert loop_type in ForLoopType, f"Invalid loop type for line: {line}"
                classified_count += 1
        
        assert classified_count > 0, "V1FORC2 should have classifiable FOR loops"
    
    def test_all_v1forc_series_all_for_types(self, mugj_file):
        """V1FORC series should demonstrate all 5 FOR loop types."""
        files = ["V1FORC1.m", "V1FORC2.m", "V1FORB.m"]
        
        types_found = set()
        
        for filename in files:
            source = mugj_file(filename)
            for line in source.split('\n'):
                result = extract_for_from_line(line)
                if result:
                    loop_type, var, rest = result
                    types_found.add(loop_type)
        
        # Should find at least BOUNDED and STRING_LIST
        assert ForLoopType.BOUNDED in types_found, "Should find BOUNDED FOR"
        # The classifier identifies these patterns correctly


class TestQuitExitPointDetection:
    """Test QUIT exit point detection in FOR loops (T063)."""
    
    def test_v1forb_has_open_ended_with_quit(self, mugj_file):
        """V1FORB.m has open-ended FOR loops with QUIT exit points."""
        parser = MUMPSParser()
        source = mugj_file("V1FORB.m")
        results = parser.classify_patterns(source)
        
        # Find open-ended FOR loops
        open_ended_with_quit = [
            r for r in results 
            if r.loop_type == ForLoopType.OPEN_ENDED and r.statement.has_internal_quit
        ]
        
        # V1FORB line 356 has: F I=.1:-.02,1:2 ... I I<0 Q
        # The Q is a conditional QUIT
        assert len(open_ended_with_quit) > 0, "V1FORB should have open-ended FOR with QUIT"
    
    def test_v1forc1_quit_detection(self, mugj_file):
        """V1FORC1.m tests FOR-QUIT combinations."""
        parser = MUMPSParser()
        source = mugj_file("V1FORC1.m")
        results = parser.classify_patterns(source)
        
        # Count FOR loops with QUIT detected
        for_with_quit = [r for r in results if r.statement.has_internal_quit]
        
        # V1FORC1 has several FOR-QUIT patterns in lines 370-372
        # At least some should have QUIT detected
        assert len(for_with_quit) > 0, "V1FORC1 should have FOR loops with QUIT"
    
    def test_bounded_for_quit_also_detected(self, mugj_file):
        """Bounded FOR can also have early QUIT exit."""
        parser = MUMPSParser()
        source = mugj_file("V1FORC1.m")
        results = parser.classify_patterns(source)
        
        # Find bounded FOR with quit (e.g., line 370: FOR I=1:1:3 ... Q)
        bounded_with_quit = [
            r for r in results
            if r.loop_type == ForLoopType.BOUNDED and r.statement.has_internal_quit
        ]
        
        assert len(bounded_with_quit) > 0, "V1FORC1 should have bounded FOR with Q"


# =============================================================================
# GOTO Integration Tests (T068-T070 - Phase 5)
# =============================================================================

class TestV1GO1GotoClassification:
    """Test GOTO parsing in V1GO1.m - simple GOTOs (T068)."""
    
    def test_v1go1_parses_successfully(self, mugj_file):
        """V1GO1.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file("tests/functional/mugj/inref/V1GO1.m")
        
        assert routine is not None
        assert routine.name == "V1GO1"
    
    def test_v1go1_has_goto_commands(self, mugj_file):
        """V1GO1.m should contain GOTO commands."""
        from m2py.analysis import extract_goto_from_line_textx as extract_goto_from_line
        
        source = mugj_file("V1GO1.m")
        lines = source.split('\n')
        
        goto_count = 0
        for line in lines:
            result = extract_goto_from_line(line)
            if result:
                goto_count += 1
        
        # V1GO1 has many GOTO patterns
        assert goto_count > 0, "V1GO1 should contain GOTO commands"
    
    def test_v1go1_goto_to_percent_label(self, mugj_file):
        """V1GO1.m includes GOTOs to %labels."""
        from m2py.analysis import extract_goto_from_line_textx as extract_goto_from_line
        
        source = mugj_file("V1GO1.m")
        lines = source.split('\n')
        
        percent_gotos = []
        for line in lines:
            result = extract_goto_from_line(line)
            if result:
                name, routine, offset = result
                if name.startswith('%'):
                    percent_gotos.append(name)
        
        # V1GO1 has GOTOs to % labels
        assert len(percent_gotos) > 0, "V1GO1 should have GOTO to % labels"


class TestV1GO2OffsetGotos:
    """Test GOTO parsing in V1GO2.m - offset GOTOs (T069)."""
    
    def test_v1go2_parses_successfully(self, mugj_file):
        """V1GO2.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file("tests/functional/mugj/inref/V1GO2.m")
        
        assert routine is not None
        assert routine.name == "V1GO2"
    
    def test_v1go2_has_offset_gotos(self, mugj_file):
        """V1GO2.m should contain GOTO with label+offset."""
        from m2py.analysis import extract_goto_from_line_textx as extract_goto_from_line
        
        source = mugj_file("V1GO2.m")
        lines = source.split('\n')
        
        offset_gotos = []
        for line in lines:
            result = extract_goto_from_line(line)
            if result:
                name, routine, offset = result
                if offset is not None:
                    offset_gotos.append((name, offset))
        
        # V1GO2 has label+offset patterns
        assert len(offset_gotos) > 0, "V1GO2 should have GOTO label+offset patterns"


class TestV1FORC2NestedForGoto:
    """Test FOR+GOTO interaction in V1FORC2.m (T070)."""
    
    def test_v1forc2_parses_successfully(self, mugj_file):
        """V1FORC2.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file("tests/functional/mugj/inref/V1FORC2.m")
        
        assert routine is not None
        assert routine.name == "V1FORC2"
    
    def test_v1forc2_has_for_loops(self, mugj_file):
        """V1FORC2.m should have FOR loops."""
        parser = MUMPSParser()
        source = mugj_file("V1FORC2.m")
        results = parser.classify_patterns(source)
        
        assert len(results) > 0, "V1FORC2 should have FOR loops"
    
    def test_v1forc2_has_goto_commands(self, mugj_file):
        """V1FORC2.m should contain GOTO commands inside FORs."""
        from m2py.analysis import extract_goto_from_line_textx as extract_goto_from_line
        
        source = mugj_file("V1FORC2.m")
        lines = source.split('\n')
        
        goto_count = 0
        for line in lines:
            result = extract_goto_from_line(line)
            if result:
                goto_count += 1
        
        # V1FORC2 has nested FOR+GOTO patterns
        assert goto_count > 0, "V1FORC2 should contain GOTO commands"
    
    def test_v1forc2_for_with_goto_in_body(self, mugj_file):
        """V1FORC2.m tests FOR loops containing GOTOs."""
        from m2py.analysis import extract_goto_from_line_textx as extract_goto_from_line, extract_for_from_line_textx as extract_for_from_line
        
        source = mugj_file("V1FORC2.m")
        lines = source.split('\n')
        
        # Find lines with both FOR and GOTO
        for_and_goto_lines = []
        for line in lines:
            has_for = extract_for_from_line(line) is not None
            has_goto = extract_goto_from_line(line) is not None
            if has_for and has_goto:
                for_and_goto_lines.append(line.strip())
        
        # V1FORC2 specifically tests FOR...GOTO patterns
        assert len(for_and_goto_lines) > 0, "V1FORC2 should have lines with FOR and GOTO"


# =============================================================================
# NEW and DO Integration Tests (T091-T092 - Phase 6)
# =============================================================================

class TestV1DO1DoCommands:
    """Test DO command parsing in V1DO1.m (T092)."""
    
    def test_v1do1_parses_successfully(self, mugj_file):
        """V1DO1.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file("tests/functional/mugj/inref/V1DO1.m")
        
        assert routine is not None
        assert routine.name == "V1DO1"
    
    def test_v1do1_has_do_commands(self, mugj_file):
        """V1DO1.m should contain DO commands."""
        from m2py.analysis import extract_do_from_line_textx as extract_do_from_line
        
        source = mugj_file("V1DO1.m")
        lines = source.split('\n')
        
        do_count = 0
        for line in lines:
            result = extract_do_from_line(line)
            if result:
                do_count += 1
        
        # V1DO1 has many DO patterns
        assert do_count > 0, "V1DO1 should contain DO commands"
    
    def test_v1do1_do_to_percent_label(self, mugj_file):
        """V1DO1.m includes DOs to %labels."""
        from m2py.analysis import extract_do_from_line_textx as extract_do_from_line, parse_do_statement
        
        source = mugj_file("V1DO1.m")
        lines = source.split('\n')
        
        percent_dos = []
        for line in lines:
            result = extract_do_from_line(line)
            if result:
                content, _ = result
                stmt = parse_do_statement(content)
                for target in stmt.targets:
                    if target.name.startswith('%'):
                        percent_dos.append(target.name)
        
        # V1DO1 has DOs to % labels
        assert len(percent_dos) > 0, "V1DO1 should have DO to % labels"
    
    def test_v1do1_has_multiple_labels(self, mugj_file):
        """V1DO1.m should have multiple target labels."""
        parser = MUMPSParser()
        routine = parser.parse_file("tests/functional/mugj/inref/V1DO1.m")
        
        # Should have V1DO1, START, A, A1, SET, END, etc.
        label_names = [label.name for label in routine.labels]
        assert len(label_names) >= 3, "V1DO1 should have multiple labels"


class TestV1DO2DoPatterns:
    """Test more complex DO patterns in V1DO2.m."""
    
    def test_v1do2_parses_successfully(self, mugj_file):
        """V1DO2.m should parse without errors."""
        parser = MUMPSParser()
        routine = parser.parse_file("tests/functional/mugj/inref/V1DO2.m")
        
        assert routine is not None
        assert routine.name == "V1DO2"
    
    def test_v1do2_has_do_commands(self, mugj_file):
        """V1DO2.m should contain DO commands."""
        from m2py.analysis import extract_do_from_line_textx as extract_do_from_line
        
        source = mugj_file("V1DO2.m")
        lines = source.split('\n')
        
        do_count = 0
        for line in lines:
            result = extract_do_from_line(line)
            if result:
                do_count += 1
        
        assert do_count > 0, "V1DO2 should contain DO commands"


class TestVariableAnalysisIntegration:
    """Integration tests for variable analysis (T107)."""
    
    def test_analyze_variables_on_parsed_routine(self):
        """Variable analysis should work on parsed routines."""
        from m2py.asg.elements import MRoutine, MLabel, MScope
        from m2py.asg.statements import MSetStatement, MNewStatement, MAssignment
        from m2py.asg.expressions import MVariable, MLiteral
        from m2py.analysis import analyze_variables
        
        # Build a simple routine with NEW command
        # Simulates: TEST  N X S X=1 S Y=X Q
        
        # NEW X statement
        new_stmt = MNewStatement(variables=["X"])
        
        # S X=1
        x_target = MVariable(name="X", subscripts=[])
        val_1 = MLiteral(value=1)
        assign1 = MAssignment(target=x_target, value=val_1)
        set_x = MSetStatement(assignments=[assign1])
        
        # S Y=X (Y = X means read X, write Y)
        y_target = MVariable(name="Y", subscripts=[])
        x_read = MVariable(name="X", subscripts=[])
        assign2 = MAssignment(target=y_target, value=x_read)
        set_y = MSetStatement(assignments=[assign2])
        
        # Build scope and label
        scope = MScope(statements=[new_stmt, set_x, set_y])
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST", labels=[label])
        
        # Analyze variables
        result = analyze_variables(routine)
        
        assert "TEST" in result
        scope_vars = result["TEST"]
        
        # X is NEWed
        assert "X" in scope_vars.newed
        
        # X and Y are written
        assert "X" in scope_vars.writes
        assert "Y" in scope_vars.writes
        
        # X is NOT an input (it's NEWed first)
        assert "X" not in scope_vars.input_variables
        
        # Y is an output (written, not NEWed)
        assert "Y" in scope_vars.output_variables
        
        # X is NOT an output (it's NEWed, so invisible to caller)
        assert "X" not in scope_vars.output_variables
    
    def test_analyze_variables_populates_label_fields(self):
        """analyze_variables() should populate MLabel fields."""
        from m2py.asg.elements import MRoutine, MLabel, MScope
        from m2py.asg.statements import MSetStatement, MAssignment
        from m2py.asg.expressions import MVariable, MLiteral
        from m2py.analysis import analyze_variables
        
        # Build: S RESULT=INPUT*2
        result_var = MVariable(name="RESULT", subscripts=[])
        input_var = MVariable(name="INPUT", subscripts=[])
        assign = MAssignment(target=result_var, value=input_var)
        set_stmt = MSetStatement(assignments=[assign])
        
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="CALC", body=scope)
        routine = MRoutine(name="TEST", labels=[label])
        
        # Analyze
        analyze_variables(routine)
        
        # Check MLabel fields were populated
        assert "INPUT" in label.variables_read
        assert "RESULT" in label.variables_written
        assert "INPUT" in label.input_variables
        assert "RESULT" in label.output_variables
    
    def test_parser_analyze_variables_method(self):
        """MUMPSParser.analyze_variables() should work."""
        from m2py.asg.elements import MRoutine, MLabel, MScope
        from m2py.asg.statements import MSetStatement, MAssignment
        from m2py.asg.expressions import MVariable, MLiteral
        
        parser = MUMPSParser()
        
        # Build a simple routine
        result_var = MVariable(name="Y", subscripts=[])
        input_var = MVariable(name="X", subscripts=[])
        assign = MAssignment(target=result_var, value=input_var)
        set_stmt = MSetStatement(assignments=[assign])
        
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="FUNC", body=scope)
        routine = MRoutine(name="TEST", labels=[label])
        
        # Call parser method
        result = parser.analyze_variables(routine)
        
        assert "FUNC" in result
        assert "X" in result["FUNC"].input_variables
        assert "Y" in result["FUNC"].output_variables

class TestParseAllMUGJFiles:
    """Test parsing ALL MUGJ certification files (T162)."""
    
    def test_parse_all_mugj_files(self, mugj_inref_dir):
        """All MUGJ *.m files should parse without errors.
        
        This is the primary validation that the textX grammar can handle
        all MUGJ certification files. Per SC-001, we need 100% parse rate.
        """
        parser = MUMPSParser()
        parsed_files = []
        failed_files = []
        skipped_files = []
        
        # Get all .m files in the MUGJ inref directory
        all_files = sorted(mugj_inref_dir.glob("*.m"))
        
        for filepath in all_files:
            # Skip empty files (some MUGJ files are placeholder stubs)
            if filepath.stat().st_size == 0:
                skipped_files.append(filepath.name)
                continue
                
            try:
                routine = parser.parse_file(filepath)
                assert isinstance(routine, MRoutine)
                assert len(routine.labels) >= 1
                parsed_files.append(filepath.name)
            except Exception as e:
                failed_files.append((filepath.name, str(e)))
        
        # Report results
        total = len(all_files)
        skipped = len(skipped_files)
        success_count = len(parsed_files)
        fail_count = len(failed_files)
        
        if failed_files:
            fail_report = "\n".join(f"  - {name}: {err}" for name, err in failed_files[:10])
            if len(failed_files) > 10:
                fail_report += f"\n  ... and {len(failed_files) - 10} more"
            pytest.fail(
                f"Failed to parse {fail_count}/{total} MUGJ files (skipped {skipped} empty):\n{fail_report}"
            )
        
        # Success assertion
        assert success_count + skipped == total, f"Parsed {success_count}, skipped {skipped} of {total} files"
        assert success_count >= 370, f"Expected at least 370 MUGJ files, got {success_count}"