"""Check KillCommand grammar structure."""

from m2py.parser.line_parser import parse_line_content

# Test various KILL patterns
tests = ["K", "K X", "K (X,Y)", "K X,Y"]
for test in tests:
    result = parse_line_content(test)
    if result and result.commands:
        cmd = result.commands[0].cmd
        print(f"{test!r}:")
        attrs = [a for a in dir(cmd) if not a.startswith("_")]
        print(f"  attrs: {attrs}")
        has_targets = hasattr(cmd, "targets")
        has_exclusive = hasattr(cmd, "exclusive")
        has_vars = hasattr(cmd, "vars")
        print(f"  has targets: {has_targets}")
        print(f"  has exclusive: {has_exclusive}")
        print(f"  has vars: {has_vars}")
        if has_targets and cmd.targets:
            print(f"  targets count: {len(cmd.targets)}")
    else:
        print(f"{test!r}: failed to parse")
    print()
