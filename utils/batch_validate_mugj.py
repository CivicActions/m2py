#!/usr/bin/env python3
"""Batch validate all remaining MUGJ files for checklist completion."""

import sys
from pathlib import Path
from collections import defaultdict
from m2py.parser import MUMPSParser


def main():
    """Validate all MUGJ files and generate checklist updates."""
    mugj_dir = Path("tests/functional/mugj/inref")
    parser = MUMPSParser()
    
    # Get all .m files
    all_files = sorted(mugj_dir.glob("*.m"))
    
    print(f"Found {len(all_files)} MUMPS files in {mugj_dir}")
    print(f"Validating all files...\n")
    
    results = []
    failed = []
    
    for filepath in all_files:
        try:
            routine = parser.parse_file(str(filepath))
            labels = len(routine.labels)
            total_stmts = sum(len(label.body.statements) if label.body else 0 for label in routine.labels)
            
            results.append({
                'file': filepath.name,
                'labels': labels,
                'statements': total_stmts,
                'status': 'success'
            })
            
        except Exception as e:
            results.append({
                'file': filepath.name,
                'error': str(e),
                'status': 'failed'
            })
            failed.append(filepath.name)
    
    # Summary
    success_count = len([r for r in results if r['status'] == 'success'])
    fail_count = len(failed)
    
    print("=" * 80)
    print(f"VALIDATION SUMMARY:")
    print(f"  Total files:     {len(all_files)}")
    print(f"  ✓ Parsed:        {success_count}")
    print(f"  ❌ Failed:        {fail_count}")
    print("=" * 80)
    
    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  ❌ {f}")
        return 1
    
    print(f"\n🎉 All {len(all_files)} MUGJ files parse successfully!")
    print("\nDetailed results available in results dict")
    
    # Group by file pattern for checklist organization
    groups = defaultdict(list)
    for r in results:
        if r['status'] == 'success':
            filename = r['file']
            # Categorize by prefix
            if filename.startswith('V1BOA'):
                groups['Binary Ops A'].append(r)
            elif filename.startswith('V1BOB'):
                groups['Binary Ops B'].append(r)
            elif filename.startswith('V1BOC'):
                groups['Binary Ops C'].append(r)
            elif filename.startswith('V1BR'):
                groups['BREAK'].append(r)
            elif filename.startswith('V1CALL'):
                groups['CALL'].append(r)
            elif filename.startswith('V1CMT'):
                groups['Comment'].append(r)
            elif filename.startswith('V1DO'):
                groups['DO Command'].append(r)
            elif filename.startswith('V1FOR'):
                groups['FOR Loop'].append(r)
            elif filename.startswith('V1G'):
                groups['GOTO'].append(r)
            elif filename.startswith('V1FN'):
                groups['Functions'].append(r)
            elif filename.startswith('V1PAT'):
                groups['Pattern Match'].append(r)
            elif filename.startswith('V1NX'):
                groups['NEW Command'].append(r)
            elif filename.startswith('V1SVH') or filename.startswith('V1SVS'):
                groups['Special Variables'].append(r)
            elif filename.startswith('VV'):
                groups['Validation Suite'].append(r)
            else:
                groups['Other'].append(r)
    
    print("\n\nFiles by category:")
    for category in sorted(groups.keys()):
        files = groups[category]
        print(f"\n{category}: {len(files)} files")
        for r in sorted(files, key=lambda x: x['file'])[:5]:  # Show first 5
            print(f"  ✓ {r['file']:20} - {r['labels']:2} labels, {r['statements']:3} stmts")
        if len(files) > 5:
            print(f"  ... and {len(files)-5} more")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
