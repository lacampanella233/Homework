---
name: homework-manager
description: "Manage the D:\\程昊一\\Homework Git and LaTeX repository: inspect status, create or compile homework, sync assignments, switch branches, finish and merge assignments, or open related tools. Use for repository-management and assignment compilation requests; do not use for solving or editing assignment content unless the user separately asks for that work."
---

# Homework Manager

Manage this repository through the deterministic PowerShell dispatcher at `scripts/homework.ps1`. Resolve relative paths from this Skill directory, and use the repository root `D:\程昊一\Homework` unless the user explicitly selects another checkout.

Map the user's request to exactly one public `Action` and call only the dispatcher. The dispatcher imports `scripts/Homework.Common.psm1` and loads the matching file under `scripts/actions/`; do not execute an action file directly because that bypasses repository initialization and the stable parameter contract.

## Start every request

1. Run `Status` and inspect the current branch plus every existing change.
2. Treat pre-existing changes as user-owned. Do not clean, restore, stage or commit them merely to unblock a workflow.
3. Identify the exact course, assignment number, semester, branch and requested remote effects. Infer a missing assignment number from the repository; do not infer permission to push, merge or delete a branch.

```powershell
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Status
```

## Choose the action

- `NewCourse -Course <name>`: create a course directory on updated `main`, commit its `.gitkeep`, and push `main`.
- `NewHomework -Course <name> -Semester <term> [-Number <n>]`: create `<course>-HW<n>`, copy `homework.sty`, create `<n>.tex`, commit, and push the new branch. Language and course display name default to the latest assignment in that course. Add `-Open` only when the user asked to open VS Code.
- `Compile [-Course <name>] [-Number <n>]`: compile the selected assignment through a temporary ASCII drive mapping so Windows `latexmk` can handle a repository or course path containing non-ASCII characters. It runs immediately without `-Apply`, preserves logs on failure, and removes only the mapping it created.
- `Sync`: on a homework branch, stage only its matching assignment directory, create a commit when needed, and push the branch. Supply `-Course` and `-Number` only if the branch name cannot identify the directory.
- `Switch -Branch <name>`: switch a clean worktree to an existing local branch and pull it with `--ff-only`.
- `Finish`: push the clean current homework branch, merge it into updated `main`, push `main`, then safely clean up the remote and local homework branch.
- `Open [-Course <name>] [-Number <n>] -Tool code|explorer|web|desktop`: open a local target or repository tool without changing Git state.

If a request spans multiple actions, execute them in the order implied by the request and re-run `Status` between state-changing actions. Do not combine actions merely for convenience or infer authorization for a later action from an earlier one.

Mutating actions default to preview. Run the preview first and inspect its exact paths and branches. Add `-Apply` only when the current user request explicitly authorizes that action and the preview matches. A request that only asks what would happen, asks for status, or asks for a plan does not authorize `-Apply`. For `Finish`, the user must explicitly request finishing or merging the named/current branch because it pushes `main` and attempts remote branch deletion.

## Examples

```powershell
# Preview, then perform a new assignment.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 NewHomework -Course Analysis-0 -Semester "2026 秋季"
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 NewHomework -Course Analysis-0 -Semester "2026 秋季" -Apply -Open

# Preview, then sync only the assignment associated with the current branch.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Sync
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Sync -Apply

# Compile the assignment associated with the current branch.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Compile

# Preview, then finish the current homework branch after explicit authorization.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Finish
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Finish -Apply
```

## Stop conditions

- Stop on a dirty worktree for course creation, homework creation, switching or finishing. Report the existing paths and let the user decide how to handle them.
- Stop on missing `origin`, missing course/template, an existing target folder/branch, invalid input, non-fast-forward pull, merge conflict or failed push.
- For `Compile`, stop on a missing assignment source, missing `latexmk`, no free drive letter from `R:` through `Z:`, or failure to create/remove the temporary mapping. Preserve LaTeX logs and return the compiler's nonzero exit code.
- If a merge conflicts, the script aborts the merge and returns to the homework branch when possible. Do not improvise conflict resolution unless the user asks.
- If `main` was merged locally but its push fails, preserve the branch and local merge commit; report the exact state and do not clean up.
- After a successful `main` push, branch-cleanup failures are warnings. Report that the merge succeeded and name what remains.

For assignment-content edits, leave this management workflow and follow the repository `AGENTS.md`; do not use a management request as permission to solve coursework.
