Find any gaps that should have been 005 (rarely used etc)

Double check all of our codegen code systematically one more time and identify if we implemented anything in codegen that should really have been implemented in the analysis/ASG layer instead (simplifying codegen). We don't want to encode code generation details in the ASG, but we do want to capture all of the semantic elements.

Validate each approach relative to what is needed for spec 005+

Remove all task/T or phase references from comments in code, tests or documentation
