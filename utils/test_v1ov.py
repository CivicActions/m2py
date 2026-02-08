#!/usr/bin/env python3
"""Test V1OV with external routine V1OV1."""

import sys
import types
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime

# Read both files
v1ov_path = Path(__file__).parent.parent / "tests/functional/mugj/inref/V1OV.m"
v1ov1_path = Path(__file__).parent.parent / "tests/functional/mugj/inref/V1OV1.m"
vreport_path = Path(__file__).parent.parent / "tests/functional/mugj/inref/VREPORT.m"

v1ov_source = v1ov_path.read_text()
v1ov1_source = v1ov1_path.read_text()

# Check for VREPORT
has_vreport = vreport_path.exists()

# Generate Python for both
try:
    v1ov_py = generate_python(v1ov_source)
    print("=== V1OV Python ===")
    print(v1ov_py[:3000])
    print("...")
except Exception as e:
    print(f"Error generating V1OV: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

try:
    v1ov1_py = generate_python(v1ov1_source)
    print("\n=== V1OV1 Python ===")
    print(v1ov1_py[:3000])
    print("...")
except Exception as e:
    print(f"Error generating V1OV1: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Execute V1OV
print("\n=== Executing V1OV ===")
runtime = MUMPSRuntime()

# Preload V1OV1 into the runtime's module cache
v1ov1_module = types.ModuleType("V1OV1")
# Execute into the module's __dict__ so attributes are set properly
exec(v1ov1_py, v1ov1_module.__dict__)
sys.modules["V1OV1"] = v1ov1_module

# Now execute V1OV
try:
    result = runtime.execute(v1ov_py, capture_output=True)
    print(f"Success: {result.success}")
    print(f"Output:\n{result.output}")
    if result.error:
        print(f"Error: {result.error}")
except Exception as e:
    print(f"Execution error: {e}")
    import traceback

    traceback.print_exc()
