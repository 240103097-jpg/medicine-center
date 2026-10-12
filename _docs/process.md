# Development Process

## Backlog
- GitHub Issues are the only active backlog.
- Work on one issue at a time.
- Respect task dependencies.
- Retain _docs/tasks.md as the initial planning record.
- Read acceptance criteria before starting and before closing.
- Commit meaningful changes regularly.

## Roles
- PM refines issues using _docs/team/pm.md.
- Engineer implements issues using _docs/team/software-engineer.md.
- QA verifies results using _docs/team/qa-engineer.md.

## Orchestrator
The main agent session coordinates the work.
It delegates refinement, implementation and verification
to separate PM, Engineer and QA subagents.

The orchestrator does not perform those roles itself.

## Lifecycle
1. Select the next open issue whose dependencies are complete.
2. Ask PM to refine it using _docs/task-template.md.
3. Review the refined requirements against the specification.
4. Ask Engineer to implement the issue and commit the changes.
5. Ask QA to independently verify every acceptance criterion.
6. On FAIL, return the findings to Engineer, then repeat QA.
7. On PASS, ensure the verified commits are pushed and close
   the issue with links to implementation and QA evidence.
8. Continue until the MVP backlog is complete.

## Evidence
- PM updates the issue with checkable acceptance criteria.
- Engineer posts a summary, commit references and test results.
- QA posts PASS or FAIL for every acceptance criterion,
  including commands run and actual results.
- Never invent test results or claim unperformed checks.

## Rules
- Do not skip PM refinement.
- Engineer must not change acceptance criteria independently.
- Engineer must not close issues.
- QA reports problems without fixing application code.
- Close an issue only after QA PASS.
- Avoid automatic issue-closing keywords before QA PASS.
- Record blockers in the issue when work cannot proceed.
- Create and link follow-up issues for deferred requirements.

## Stop Condition
All MVP issues have QA PASS, their verified changes are
committed and pushed, and the issues are closed.

If blocked, report the blocker instead of claiming completion.
