#!/usr/bin/env python3
"""Check VV2CS.m label 5 parsing."""
from m2py.parser import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("tests/functional/mugj/inref/VV2CS.m")

# Find label 5 (II-5 test)
for label in routine.labels:
    if label.name == "5":
        print(f"Label 5 has {len(label.body.statements)} statements:")
        for i, stmt in enumerate(label.body.statements):
            print(f"  [{i}] {stmt.__class__.__name__}", end="")
            if hasattr(stmt, "loop_var") and stmt.loop_var:
                print(f" loop_var={stmt.loop_var}", end="")
                if hasattr(stmt, "parameters") and stmt.parameters:
                    p = stmt.parameters[0]
                    print(f" start={p.start.value if p.start else None} step={p.step.value if p.step else None} end={p.end.value if p.end else None}", end="")
            if hasattr(stmt, "postcondition") and stmt.postcondition:
                print(f" postcond={stmt.postcondition}", end="")
            print()
            
            # Check FOR body
            if hasattr(stmt, "body") and stmt.body and stmt.body.statements:
                for j, sub in enumerate(stmt.body.statements):
                    print(f"      body[{j}]: {sub.__class__.__name__}", end="")
                    if hasattr(sub, "postcondition") and sub.postcondition:
                        print(f" postcond=YES", end="")
                    if hasattr(sub, "targets") and sub.targets:
                        for k, t in enumerate(sub.targets):
                            print(f" target={t.name}", end="")
                            if hasattr(t, "postcondition") and t.postcondition:
                                print(f" arg_postcond=YES", end="")
                    print()
