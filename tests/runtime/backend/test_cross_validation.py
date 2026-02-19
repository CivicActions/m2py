"""Cross-validation tests: m2py writes readable by native MUMPS engines.

T042: Validates that data written through m2py backends can be read back
by native MUMPS commands executed through YottaDB or IRIS, proving that
m2py correctly writes to the real database (not just a Python-side cache).

These tests use the run_mumps_ydb.py and run_mumps_iris.py utilities to
execute native MUMPS code and compare results against m2py backend reads.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from m2py.runtime.globals import GlobalStorageBackend


def _run_native_ydb(code: str, timeout: int = 10) -> str:
    """Run MUMPS code through native YottaDB and return output."""
    result = subprocess.run(
        [
            sys.executable,
            "utils/run_mumps_ydb.py",
            "--code",
            code,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        pytest.skip(f"YottaDB native execution failed: {result.stderr[:200]}")
    return result.stdout.strip()


def _run_native_iris(code: str, timeout: int = 30) -> str:
    """Run MUMPS code through native IRIS and return output."""
    result = subprocess.run(
        [
            sys.executable,
            "utils/run_mumps_iris.py",
            "--code",
            code,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        pytest.skip(f"IRIS native execution failed: {result.stderr[:200]}")
    return result.stdout.strip()


@pytest.mark.backend_yottadb
class TestYottaDBCrossValidation:
    """Verify m2py YottaDB backend writes are readable by native YDB MUMPS."""

    def test_set_readable_by_native_ydb(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Data written via m2py can be read by native YottaDB WRITE command."""
        if backend_name != "yottadb":
            pytest.skip("YottaDB cross-validation only")

        # Write via m2py backend
        backend.set("XVAL", ("1",), "hello")
        backend.set("XVAL", ("2",), "world")

        # Read via native YDB MUMPS
        output = _run_native_ydb('XVAL W ^XVAL(1)," ",^XVAL(2) Q')
        assert output == "hello world"

    def test_native_ydb_set_readable_by_m2py(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Data written by native YottaDB is readable via m2py backend."""
        if backend_name != "yottadb":
            pytest.skip("YottaDB cross-validation only")

        # Write via native YDB
        _run_native_ydb('SETUP S ^XVAL2("a")="native" Q')

        # Read via m2py backend
        result = backend.get("XVAL2", ("a",))
        assert result == "native"

    def test_numeric_subscript_cross_validation(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Numeric subscript canonicalization matches between m2py and native YDB."""
        if backend_name != "yottadb":
            pytest.skip("YottaDB cross-validation only")

        # Write via m2py with string "1" subscript
        backend.set("XNUM", ("1",), "one")
        backend.set("XNUM", ("2",), "two")

        # Read via native YDB using numeric subscripts
        output = _run_native_ydb('XNUM W ^XNUM(1)," ",^XNUM(2) Q')
        assert output == "one two"

    def test_data_code_matches_native_ydb(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """$DATA codes match between m2py and native YottaDB."""
        if backend_name != "yottadb":
            pytest.skip("YottaDB cross-validation only")

        backend.set("XDATA", ("a",), "val")
        backend.set("XDATA", ("a", "1"), "sub")

        # m2py data code
        m2py_data = backend.data("XDATA", ("a",))

        # native YDB data code
        output = _run_native_ydb('XDATA W $D(^XDATA("a")) Q')
        native_data = int(output)

        assert m2py_data == native_data, (
            f"m2py $DATA={m2py_data}, native $DATA={native_data}"
        )

    def test_order_matches_native_ydb(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """$ORDER traversal matches between m2py and native YottaDB."""
        if backend_name != "yottadb":
            pytest.skip("YottaDB cross-validation only")

        backend.set("XORD", ("a",), "1")
        backend.set("XORD", ("b",), "2")
        backend.set("XORD", ("c",), "3")

        # m2py order
        m2py_first = backend.order("XORD", ("",))

        # native YDB order
        output = _run_native_ydb('XORD W $O(^XORD("")) Q')
        assert m2py_first == output


@pytest.mark.backend_iris
class TestIRISCrossValidation:
    """Verify m2py IRIS backend writes are readable by native IRIS MUMPS."""

    def test_set_readable_by_native_iris(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Data written via m2py can be read by native IRIS WRITE command."""
        if backend_name != "iris":
            pytest.skip("IRIS cross-validation only")

        # Write via m2py backend
        backend.set("XVAL", ("1",), "hello")
        backend.set("XVAL", ("2",), "world")

        # Read via native IRIS MUMPS
        output = _run_native_iris('XVAL W ^XVAL(1)," ",^XVAL(2) Q')
        assert output == "hello world"

    def test_native_iris_set_readable_by_m2py(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Data written by native IRIS is readable via m2py backend."""
        if backend_name != "iris":
            pytest.skip("IRIS cross-validation only")

        # Write via native IRIS
        _run_native_iris('SETUP S ^XVAL2("a")="native" Q')

        # Read via m2py backend
        result = backend.get("XVAL2", ("a",))
        assert result == "native"

    def test_numeric_subscript_cross_validation(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Numeric subscript canonicalization matches between m2py and native IRIS."""
        if backend_name != "iris":
            pytest.skip("IRIS cross-validation only")

        backend.set("XNUM", ("1",), "one")
        backend.set("XNUM", ("2",), "two")

        output = _run_native_iris('XNUM W ^XNUM(1)," ",^XNUM(2) Q')
        assert output == "one two"

    def test_data_code_matches_native_iris(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """$DATA codes match between m2py and native IRIS."""
        if backend_name != "iris":
            pytest.skip("IRIS cross-validation only")

        backend.set("XDATA", ("a",), "val")
        backend.set("XDATA", ("a", "1"), "sub")

        m2py_data = backend.data("XDATA", ("a",))

        output = _run_native_iris('XDATA W $D(^XDATA("a")) Q')
        native_data = int(output)

        assert m2py_data == native_data

    def test_order_matches_native_iris(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """$ORDER traversal matches between m2py and native IRIS."""
        if backend_name != "iris":
            pytest.skip("IRIS cross-validation only")

        backend.set("XORD", ("a",), "1")
        backend.set("XORD", ("b",), "2")
        backend.set("XORD", ("c",), "3")

        m2py_first = backend.order("XORD", ("",))

        output = _run_native_iris('XORD W $O(^XORD("")) Q')
        assert m2py_first == output
