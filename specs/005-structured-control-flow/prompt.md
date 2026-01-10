/speckit.implement Implement the next phase only.

Research (docs/, mumps-reference, docker ydb, validate.py) as needed to understand correct semantics and current behaviour first, then refresh your memory on the specific task scope before implementing. Ensure we implement ONLY the specified scope - this is a phased approach.

Don't delete existing test stubs - make a surgical edit to add the test content to an existing stub or (only if no existing stub matches what we need) then add a new stub, following the pattern.

In addition to tests, run additional M code with validate.py to test behaviour and check for any edge cases - you can also use this to debug any issues. Make sure to stick closely to the scope relevant to the current phase - don't fix issues that are part of later spec/phase scope!

When you are done:
1) Run coverage_check.py
2) `git add` and `pre-commit run` - fix any issues that are not automatically fixed
3) Commit - review previous commit messages for format