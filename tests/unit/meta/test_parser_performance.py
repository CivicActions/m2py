"""Tests for parser performance characteristics.

Verifies parser handles large/complex routines within acceptable time limits.

MUMPS 1995 Reference: §6.1 Routine Structure
"""

import time

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.quality
class TestParserPerformance:
    """Test parser performance characteristics."""

    @pytest.mark.slow
    def test_large_routine_performance(self, tmp_path):
        """Parser should handle large routines (1000+ lines) in reasonable time."""
        # Generate a large routine
        lines = ["LARGE\n"]
        for i in range(1000):
            lines.append(f"\tS X{i}={i}\n")
        lines.append("\tQ\n")

        large_file = tmp_path / "LARGE.m"
        large_file.write_text("".join(lines))

        parser = MUMPSParser()

        start = time.time()
        routine = parser.parse_file(large_file)
        elapsed = time.time() - start

        # Should complete in under 5 seconds (generous for CI)
        assert elapsed < 5.0, f"Parsing took {elapsed:.2f}s"
        assert len(routine.labels) == 1
        # The label should have 1000 SET statements + 1 QUIT
        assert len(routine.labels[0].body.statements) >= 1000

    @pytest.mark.slow
    def test_many_labels_performance(self, tmp_path):
        """Parser should handle routines with many labels (500+) efficiently."""
        # Generate routine with many labels
        lines = []
        for i in range(500):
            lines.append(f"L{i}\tS X={i}\n")

        many_labels_file = tmp_path / "MANYLBL.m"
        many_labels_file.write_text("".join(lines))

        parser = MUMPSParser()

        start = time.time()
        routine = parser.parse_file(many_labels_file)
        elapsed = time.time() - start

        # Should complete in under 10 seconds (generous for CI)
        assert elapsed < 10.0, f"Parsing took {elapsed:.2f}s"
        assert len(routine.labels) == 500
