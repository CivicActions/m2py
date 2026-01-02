from m2py.parser.parser import MUMPSParser

parser = MUMPSParser()

test_cases = [
    ("SET $X", "S $X=0"),
    ("TSTART Empty", "TS ()"),
    ("OPEN Mnemonic", 'O 1::"MNE"'),
    ("SSV Device", "W ^$DEVICE"),
    ("ISV IOReference", "W $IOReference"),
]

print("Running parsing tests for identified gaps...\n")

for name, code in test_cases:
    print(f"Testing {name}: `{code}`")
    try:
        parser.parse(code)
        print("  -> PARSED (Unexpectedly?)")
    except Exception as e:
        print(f"  -> FAILED as expected: {e}")
    print("-" * 40)
