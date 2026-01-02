"""Tests for parser performance (SC-005).

Reference: M2PY Parser architecture
Migrated from: tests/unit/test_parser.py::TestParserPerformance

SC-005: Parser should complete in <2 seconds for a 500-line routine.
"""

import time

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.parser
@pytest.mark.slow
class TestParserPerformance:
    """Test parser performance meets SC-005 requirements.

    SC-005: Parser should complete in <2 seconds for a 500-line routine.

    Migrated from: tests/unit/test_parser.py::TestParserPerformance
    """

    def test_500_line_synthetic_routine(self):
        """T333/T334: Parse 500-line synthetic routine in <2 seconds."""
        # Build a synthetic 500-line routine with realistic content
        lines = ["SYNTH\t;Synthetic 500-line routine for performance testing"]

        # Add SET commands with various expressions
        for i in range(100):
            lines.append(f'\tS X{i}={i},Y{i}=X{i}+1,Z{i}=$P(STR,",",{i + 1})')

        # Add FOR loops
        for i in range(50):
            lines.append(f"\tF I{i}=1:1:100 S TOTAL=TOTAL+I{i}")

        # Add IF/ELSE blocks
        for i in range(50):
            lines.append(f"\tI X{i}>50 S FLAG{i}=1")
            lines.append(f"\tE  S FLAG{i}=0")

        # Add WRITE commands
        for i in range(50):
            lines.append(f'\tW !,"Result ",X{i},": ",Y{i}')

        # Add DO commands
        for i in range(50):
            lines.append(f"\tD HELPER(X{i})")

        # Add GOTO commands
        for i in range(25):
            lines.append(f"\tG:X{i}=0 EXIT")

        # Pad to 498 lines with comments
        while len(lines) < 498:
            lines.append(f"\t;Line {len(lines) + 1}")

        # Add final statements
        lines.append("\tQ")
        lines.append("EXIT\tQ")

        # Join with newlines and add trailing newline
        source = "\n".join(lines) + "\n"

        # Verify we have ~500 lines
        line_count = len(source.strip().split("\n"))
        assert line_count >= 500, f"Only {line_count} lines generated"

        # Time the parse
        parser = MUMPSParser()
        start = time.perf_counter()
        result = parser.parse(source)
        elapsed = time.perf_counter() - start

        # Verify it parsed correctly
        assert result is not None
        # First label should be SYNTH
        assert len(result.labels) >= 1
        assert result.labels[0].name == "SYNTH"

        # SC-005: Must complete in <2 seconds
        assert elapsed < 2.0, f"Parse took {elapsed:.2f}s, exceeds 2s limit"

    def test_combined_mugj_files_performance(self, mugj_inref_dir):
        """T333: Parse combined MUGJ content (500+ lines) for performance.

        Combines multiple real MUGJ files to create a realistic 500+ line
        test case using actual MUMPS patterns.
        """
        # Read and combine content from multiple MUGJ files
        combined_lines = []
        files_to_combine = [
            "V1NST1.m",
            "V1OV.m",
            "V1GO1.m",
            "V1DO3.m",
            "V1DO2.m",
            "V1CALL.m",
        ]

        for filename in files_to_combine:
            filepath = mugj_inref_dir / filename
            if filepath.exists():
                with open(filepath) as f:
                    lines = f.read().strip().split("\n")
                    # Add as a new label block (simulate multi-label routine)
                    for line in lines:
                        combined_lines.append(line)
            if len(combined_lines) >= 500:
                break

        # Verify we have enough content
        assert len(combined_lines) >= 400, f"Only {len(combined_lines)} lines available"

        # Parse individual files and time it (since combining requires label adjustment)
        parser = MUMPSParser()
        total_lines = 0
        start = time.perf_counter()

        for filename in files_to_combine:
            filepath = mugj_inref_dir / filename
            if filepath.exists():
                parser.parse_file(filepath)  # Parse to verify, result unused
                with open(filepath) as f:
                    total_lines += len(f.readlines())

        elapsed = time.perf_counter() - start

        # Calculate lines per second
        lines_per_second = total_lines / elapsed if elapsed > 0 else float("inf")

        # Should parse at least 250 lines/second (2 seconds for 500 lines)
        assert lines_per_second > 250, f"Too slow: {lines_per_second:.0f} lines/sec"
        assert elapsed < 3.0, f"Combined parse took {elapsed:.2f}s"
