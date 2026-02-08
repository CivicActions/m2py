"""Dump generated Python for specific MVTS routines."""

import sys

sys.path.insert(0, ".")
from pathlib import Path
from m2py.codegen import generate_python

routines = ["V3DWP", "V3DWPE", "V4NAME18", "V4NAME25", "V4QSUB8"]
inref = Path("tests/functional/mvts/inref")

for name in routines:
    mfile = inref / f"{name}.m"
    if mfile.exists():
        code = mfile.read_text()
        try:
            py = generate_python(code)
            outf = Path(f"tmp/gen_{name}.py")
            outf.write_text(py)
            print(f"Generated {outf}")
        except Exception as e:
            print(f"ERROR transpiling {name}: {e}")
    else:
        print(f"File not found: {mfile}")
