Go through all of the 006 spec, plan documents and tasks and compare to the work done (both the chat backlog and git branch commits).
Identify if there are any items that were clearly in scope for 006 but were skipped, simplified or not implemented completely. Consider all gaps - even if they are noted as "rarely used", "complex" omitted "by design" etc.
Don't address any gaps now, just list them.

Double check all of our codegen code systematically one more time and identify if we implemented anything in codegen that should really have been implemented in the analysis/ASG layer instead (simplifying codegen). We don't want to encode code generation details in the ASG, but we do want to capture all of the semantic elements.

Validate each approach relative to what is needed for spec 005+
