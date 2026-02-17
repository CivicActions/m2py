"""Unit tests for m2py.runtime.job_runner module.

Tests the JOB subprocess entry point including:
- _import_routine() module import strategies
- main() argument parsing, setup, and execution flow
"""

from __future__ import annotations

import sys
import types
from unittest.mock import patch

import pytest

from m2py.runtime.job_runner import _import_routine, main


class TestImportRoutine:
    """Tests for _import_routine() helper function."""

    def test_import_existing_module(self):
        """Imports a standard library module by name."""
        mod = _import_routine("json")
        assert mod is not None
        assert hasattr(mod, "dumps")

    def test_import_nonexistent_returns_none(self):
        """Returns None for module that doesn't exist."""
        result = _import_routine("nonexistent_module_xyz_12345")
        assert result is None

    def test_import_pct_fallback(self):
        """Falls back to _pct_ prefix for % routines."""
        # Create a fake _pct_ module
        mod = types.ModuleType("_pct_TESTROUTINE")
        mod.TEST = lambda: None
        sys.modules["_pct_TESTROUTINE"] = mod
        try:
            result = _import_routine("TESTROUTINE")
            assert result is mod
        finally:
            del sys.modules["_pct_TESTROUTINE"]

    def test_import_direct_success_no_pct_fallback(self):
        """Direct import succeeds — does not try _pct_ prefix."""
        mod = types.ModuleType("DIRECTMOD")
        sys.modules["DIRECTMOD"] = mod
        try:
            result = _import_routine("DIRECTMOD")
            assert result is mod
        finally:
            del sys.modules["DIRECTMOD"]

    def test_import_both_fail_returns_none(self):
        """Returns None when both direct and _pct_ imports fail."""
        result = _import_routine("NOSUCHMOD99")
        assert result is None


class TestMain:
    """Tests for main() entry point."""

    def test_main_runs_entry_function(self):
        """main() imports routine and calls entry function via run_with_goto_support."""
        # Create fake routine module
        fake_module = types.ModuleType("FAKEJOB")
        call_log = []

        def fake_entry(rt, _scope=None):
            call_log.append("called")
            rt.write("hello from job")

        fake_module.ENTRY = fake_entry
        fake_module._source_lines = ['ENTRY W "hello" Q']
        fake_module._label_lines = {"ENTRY": 0}
        sys.modules["FAKEJOB"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "FAKEJOB",
                    "--label",
                    "ENTRY",
                    "--db-path",
                    ":memory:",
                    "--args",
                    "[]",
                ],
            ):
                main()
            assert len(call_log) == 1
        finally:
            del sys.modules["FAKEJOB"]

    def test_main_missing_module_exits_nonzero(self):
        """main() raises SystemExit(1) when routine module not found.

        In the real subprocess, sys.exit(1) terminates with exit code 1.
        Non-zero SystemExit propagates so the parent detects failure.
        """
        with patch(
            "sys.argv",
            [
                "job_runner",
                "--routine",
                "NONEXISTENT_ROUTINE_XYZ",
                "--label",
                "TEST",
                "--db-path",
                ":memory:",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_missing_label_exits_nonzero(self):
        """main() raises SystemExit(1) when entry label not found in module."""
        fake_module = types.ModuleType("NOLABEL")
        sys.modules["NOLABEL"] = fake_module
        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "NOLABEL",
                    "--label",
                    "MISSING",
                    "--db-path",
                    ":memory:",
                ],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
        finally:
            del sys.modules["NOLABEL"]

    def test_main_with_actual_args(self):
        """main() passes JSON-decoded args to entry function."""
        received_args = []
        fake_module = types.ModuleType("ARGMOD")

        def fake_entry(rt, _scope=None, _args=None):
            if _args:
                received_args.extend(_args)

        # run_with_goto_support passes _args, which gets forwarded
        fake_module.ARGENTRY = fake_entry
        fake_module._source_lines = []
        fake_module._label_lines = {}
        sys.modules["ARGMOD"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "ARGMOD",
                    "--label",
                    "ARGENTRY",
                    "--db-path",
                    ":memory:",
                    "--args",
                    '["hello", "42"]',
                ],
            ):
                main()
        finally:
            del sys.modules["ARGMOD"]

    def test_main_halt_in_child_is_silent(self):
        """SystemExit in child process (HALT) is silently caught."""
        fake_module = types.ModuleType("HALTMOD")

        def fake_entry(rt, _scope=None):
            raise SystemExit(0)

        fake_module.HALTENTRY = fake_entry
        fake_module._source_lines = []
        fake_module._label_lines = {}
        sys.modules["HALTMOD"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "HALTMOD",
                    "--label",
                    "HALTENTRY",
                    "--db-path",
                    ":memory:",
                ],
            ):
                # Should not raise — SystemExit is caught
                main()
        finally:
            del sys.modules["HALTMOD"]

    def test_main_exception_in_child_is_silent(self):
        """Exceptions in child process are silently caught."""
        fake_module = types.ModuleType("ERRMOD")

        def fake_entry(rt, _scope=None):
            raise RuntimeError("Something went wrong")

        fake_module.ERRENTRY = fake_entry
        fake_module._source_lines = []
        fake_module._label_lines = {}
        sys.modules["ERRMOD"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "ERRMOD",
                    "--label",
                    "ERRENTRY",
                    "--db-path",
                    ":memory:",
                ],
            ):
                # Should not raise
                main()
        finally:
            del sys.modules["ERRMOD"]

    def test_main_sets_child_device(self):
        """main() sets $PRINCIPAL to /dev/null/{pid} for child."""
        runtime_ref = []
        fake_module = types.ModuleType("DEVMOD")

        def fake_entry(rt, _scope=None):
            runtime_ref.append(rt)

        fake_module.DEVENTRY = fake_entry
        fake_module._source_lines = []
        fake_module._label_lines = {}
        sys.modules["DEVMOD"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "DEVMOD",
                    "--label",
                    "DEVENTRY",
                    "--db-path",
                    ":memory:",
                ],
            ):
                main()
            assert len(runtime_ref) == 1
            rt = runtime_ref[0]
            assert rt._principal.startswith("/dev/null/")
        finally:
            del sys.modules["DEVMOD"]

    def test_main_with_output_redirection(self, tmp_path):
        """main() handles --output flag for I/O redirection."""
        output_file = tmp_path / "output.txt"
        fake_module = types.ModuleType("OUTMOD")

        def fake_entry(rt, _scope=None):
            pass

        fake_module.OUTENTRY = fake_entry
        fake_module._source_lines = []
        fake_module._label_lines = {}
        sys.modules["OUTMOD"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "OUTMOD",
                    "--label",
                    "OUTENTRY",
                    "--db-path",
                    ":memory:",
                    "--output",
                    str(output_file),
                ],
            ):
                main()
        finally:
            del sys.modules["OUTMOD"]

    def test_main_with_input_redirection(self, tmp_path):
        """main() handles --input flag for I/O redirection."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("test input\n")
        fake_module = types.ModuleType("INMOD")

        def fake_entry(rt, _scope=None):
            pass

        fake_module.INENTRY = fake_entry
        fake_module._source_lines = []
        fake_module._label_lines = {}
        sys.modules["INMOD"] = fake_module

        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "INMOD",
                    "--label",
                    "INENTRY",
                    "--db-path",
                    ":memory:",
                    "--input",
                    str(input_file),
                ],
            ):
                main()
        finally:
            del sys.modules["INMOD"]

    def test_main_uncallable_label_exits_nonzero(self):
        """main() raises SystemExit(1) when label attr is not callable."""
        fake_module = types.ModuleType("UNCALLMOD")
        fake_module.NOTFUNC = "just a string"
        sys.modules["UNCALLMOD"] = fake_module
        try:
            with patch(
                "sys.argv",
                [
                    "job_runner",
                    "--routine",
                    "UNCALLMOD",
                    "--label",
                    "NOTFUNC",
                    "--db-path",
                    ":memory:",
                ],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
        finally:
            del sys.modules["UNCALLMOD"]
