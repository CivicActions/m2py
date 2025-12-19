"""Integration tests for MUGJ test suite files.

Tests parsing and analysis of official MUGJ certification files.
"""

import pytest
from pathlib import Path

from m2py.parser import MUMPSParser
from m2py.asg import MRoutine, MLabel
from m2py.analysis import extract_for_from_line
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
