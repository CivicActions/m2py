Go through all of the current spec, plan documents and tasks and compare to the work done (both the chat backlog and git branch commits).
Identify if there are any items that were clearly in scope for the current spec but were skipped, simplified or not implemented completely. Consider all gaps - even if they are noted as "rarely used", "complex" omitted "by design" etc.
Don't address any gaps now, just list them.

Double check all of our codegen code systematically one more time and identify if we implemented anything in codegen that should really have been implemented in the analysis/ASG layer instead (simplifying codegen). We don't want to encode code generation details in the ASG, but we do want to capture all of the semantic elements.

Validate each approach relative to what is needed for spec 005+

Go through all of the 007 spec, plan documents, tasks, chat backlog and git branch commits, then identify if there are any documentation changes needed. Document the current state only - avoid "change" language.
Then, check the codegen-plan and make any corrections or important notes needed for spec 008+ there - make changes in context, avoiding "change" language.