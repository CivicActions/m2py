Go through all of the current spec, plan documents and tasks and compare to the work done (both the chat backlog and git branch commits).
Identify if there are any items that were clearly in scope for the current spec but were skipped, simplified or not implemented completely. Consider all gaps - even if they are noted as "rarely used", "complex" omitted "by design" etc.
Don't address any gaps now, just list them.

Double check all of our codegen code systematically one more time and identify if we implemented anything in codegen that should really have been implemented in the analysis/ASG layer instead (simplifying codegen). We don't want to encode code generation details in the ASG, but we do want to capture all of the semantic elements.

Go through all of the current spec, plan documents, tasks, chat backlog and git branch commits, then identify if there are any documentation changes needed. Document the current state only - avoid "change" language.
Then, check the codegen-plan and make any corrections or important notes needed for subsequent specs there - make changes in context, avoiding "change" language.

We have an objective to minimize the runtime where possible - are there any elements in the runtime that could be removed and replaced with direct simple python code if we did a bit more in the analysis phase? Note that we are not concerned about runtime performance per-se, but rather simplicity of the resulting code and how easily it can be refactored into "normal" python code. In your recommendations, consider risks - if we are not confident that we can implement these 100% correctly it would be safer to wait, then we can test the changes with a large production codebase.