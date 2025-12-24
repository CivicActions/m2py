#!/usr/bin/env python3
"""Generate MUGJ validation checklist files, max 7 files per checklist."""

from pathlib import Path
import math

MUGJ_DIR = Path("tests/functional/mugj/inref")
CHECKLIST_DIR = Path("specs/001-textx-semantic-graph/checklists")

HEADER_TEMPLATE = """# MUGJ Validation Checklist - {group_name}

**Checklist**: {checklist_num} of {total_checklists}  
**Files**: {file_count} files ({start_idx}-{end_idx} of {total_files})

---

## Validation Instructions

**Purpose**: Systematic validation of MUGJ test files to ensure ASG accuracy and Python code generation readiness.

**Process for Each File**:
1. Parse the MUMPS source file and capture ASG output:
   ```bash
   uv run python utils/validate_asg.py tests/functional/mugj/inref/<FILENAME>.m
   ```
   
2. Read source and ASG carefully (break into sub-statements for long files)

3. Validate ASG 100% correctly captures all source details in proper structure:
   - Every MUMPS line has corresponding ASG node(s)
   - All labels, commands, expressions captured correctly
   - Postconditions, control flow, function calls properly represented

4. Cross-reference with `mumps-reference/` documentation as needed

5. Evaluate ASG from Python code generation perspective:
   - Does it capture the right semantic detail level?
   - What additional analysis would simplify code generation?
   - Are there semantic nuances missing that affect correctness?

6. Document any issues or improvements needed in `specs/001-textx-semantic-graph/tasks.md`

**CRITICAL**: Evaluate each file separately and thoroughly. Don't skip files or simplify the process.

---

## Validation Checklist

"""


def get_file_description(filename: str) -> str:
    """Get a brief description based on filename patterns."""
    name = filename.replace(".m", "")

    # Special files
    special = {
        "_": "Basic underscore label test",
        "_1A": "Label starting with underscore + alphanum",
        "_2345678": "Label with numbers",
        "_BCDEFGH": "Label with letters",
        "INSTRUCT": "Test suite instructions",
        "MAIN": "Main test driver",
        "OVERVIEW": "Test overview documentation",
        "PROC": "Procedure utilities",
        "RESTORE": "State restoration",
        "VREPORT": "Validation reporting",
        "VV1": "Validation driver",
    }

    if name in special:
        return special[name]

    # Simple label tests
    if name.startswith("V") and len(name) <= 8 and name[1:].isalnum():
        if name == "V":
            return "Single character label"
        elif name[1:].isdigit():
            return f"Label with {'digit' if len(name) == 2 else 'multiple digits'}"
        elif name[1:].isalpha():
            return f"{len(name)} character label"
        return "Label test"

    # Version 2 tests
    if name.startswith("VV2"):
        suffix = name[3:]
        if suffix.startswith("DOC"):
            num = suffix[3:] or "0"
            return f"V2 DO command test {num}"
        if suffix.startswith("FN"):
            return "V2 function tests"
        if suffix.startswith("LC"):
            return "V2 intrinsic tests"
        if suffix.startswith("LH"):
            return "V2 $LENGTH tests"
        if suffix.startswith("PAT"):
            return "V2 pattern tests"
        return "Version 2 tests"

    # VV1DOC tests
    if name.startswith("VV1DOC"):
        num = name[6:] or "0"
        return f"V2 DO command test {num}"

    # VVE tests
    if name.startswith("VVE"):
        suffix = name[3:]
        if suffix.startswith("DOC"):
            return "DO command validation"
        if suffix.startswith("FOR"):
            return "FOR validation"
        return "Extended validation"

    # VVINST tests
    if name.startswith("VVINST"):
        num = name[6:]
        return f"Instruction validation {num}"

    # VVOVER tests
    if name.startswith("VVOVER"):
        num = name[6:]
        return f"Overflow tests {num}"

    # V1 tests - main category
    if name.startswith("V1"):
        suffix = name[2:]

        # Extract category and number
        category = ""
        num = ""
        for i, c in enumerate(suffix):
            if c.isdigit():
                category = suffix[:i]
                num = suffix[i:]
                break
        else:
            category = suffix

        categories = {
            "AC": "Arithmetic conversion",
            "BOA": "Binary operators A",
            "BOB": "Binary operators B",
            "BOC": "Binary operators C",
            "BR": "BREAK command",
            "CALL": "CALL/DO command",
            "CMT": "Comment syntax",
            "DGA": "Data global A",
            "DGB": "Data global B",
            "DLA": "Data local A",
            "DLB": "Data local B",
            "DLC": "Data local C",
            "DO": "DO command",
            "FC": "Function calls",
            "FN": "Functions",
            "FNE": "$EXTRACT",
            "FNF": "$FIND",
            "FNL": "$LENGTH",
            "FNP": "$PIECE",
            "FORA": "FOR loop A",
            "FORB": "FOR loop B",
            "FORC": "FOR loop C",
            "GO": "GOTO command",
            "GVN": "Global variable names",
            "HANG": "HANG command",
            "IDARG": "Indirection arguments",
            "IDDO": "Indirection DO",
            "IDGO": "Indirection GOTO",
            "IDNM": "Indirection name",
            "IE": "IF/ELSE",
            "IO": "I/O commands",
            "JST": "$JUSTIFY",
            "LL": "Label length",
            "LVN": "Local variable names",
            "MAX": "Maximum values",
            "MJA": "Multi-job A",
            "MJB": "Multi-job B",
            "NR": "Naked references",
            "NST": "Nesting",
            "NSTE": "Nesting extended",
            "NUM": "Numeric conversion",
            "NX": "NEW command",
            "OV": "$ORDER",
            "PAT": "Pattern match",
            "PC": "Postconditions",
            "PCA": "Postconditions A",
            "PCB": "Postconditions B",
            "PO": "Peripheral OPEN",
            "PRFOR": "Priority FOR",
            "PRGD": "Priority global data",
            "PRIE": "Priority IF/ELSE",
            "PRSET": "Priority SET",
            "RANDA": "$RANDOM A",
            "RANDB": "$RANDOM B",
            "READA": "READ command A",
            "READB": "READ command B",
            "RN": "Random numbers",
            "SEQ": "Sequence",
            "SET": "SET command",
            "SVH": "$HOROLOG",
            "SVS": "$STORAGE",
            "UO": "Unary operators",
            "WR": "WRITE command",
            "XECA": "XECUTE A",
            "XECB": "XECUTE B",
            "XECAE": "XECUTE extended",
        }

        if category in categories:
            suffix_str = f" {num}" if num else ""
            return f"{categories[category]}{suffix_str}"

        return f"V1 test: {suffix}"

    return "MUMPS test file"


def main():
    """Generate all checklist files."""
    # Get all .m files sorted
    files = sorted(MUGJ_DIR.glob("*.m"), key=lambda f: f.name)
    total_files = len(files)

    print(f"Found {total_files} MUGJ files")

    # Calculate number of checklists
    files_per_checklist = 7
    total_checklists = math.ceil(total_files / files_per_checklist)

    print(f"Creating {total_checklists} checklist files")

    # Ensure directory exists
    CHECKLIST_DIR.mkdir(parents=True, exist_ok=True)

    # Generate checklist files
    for i in range(total_checklists):
        start_idx = i * files_per_checklist
        end_idx = min(start_idx + files_per_checklist, total_files)
        chunk_files = files[start_idx:end_idx]

        # Generate group name from first and last file
        first_name = chunk_files[0].stem
        last_name = chunk_files[-1].stem
        group_name = f"{first_name} to {last_name}"

        checklist_num = i + 1
        filename = f"mugj-{checklist_num:02d}.md"

        content = HEADER_TEMPLATE.format(
            group_name=group_name,
            checklist_num=checklist_num,
            total_checklists=total_checklists,
            file_count=len(chunk_files),
            start_idx=start_idx + 1,
            end_idx=end_idx,
            total_files=total_files,
        )

        # Add file entries
        for f in chunk_files:
            desc = get_file_description(f.name)
            content += f"- [ ] {f.name} - {desc}\n"

        # Write file
        checklist_path = CHECKLIST_DIR / filename
        checklist_path.write_text(content)
        print(f"  Created {filename}: {len(chunk_files)} files")

    # Generate index file
    index_content = """# MUGJ Validation Checklists - Index

**Purpose**: Systematic validation of all 376 MUGJ test files for Phase 14 preparation.

**Progress**: 0/376 files validated

---

## Checklist Files

"""

    for i in range(total_checklists):
        start_idx = i * files_per_checklist
        end_idx = min(start_idx + files_per_checklist, total_files)
        chunk_files = files[start_idx:end_idx]

        first_name = chunk_files[0].stem
        last_name = chunk_files[-1].stem

        checklist_num = i + 1
        filename = f"mugj-{checklist_num:02d}.md"

        index_content += f"- [ ] [{filename}]({filename}) - {first_name} to {last_name} ({len(chunk_files)} files)\n"

    index_path = CHECKLIST_DIR / "mugj-validation-index.md"
    index_path.write_text(index_content)
    print("\nCreated index: mugj-validation-index.md")

    print(f"\nDone! Created {total_checklists + 1} files in {CHECKLIST_DIR}")


if __name__ == "__main__":
    main()
