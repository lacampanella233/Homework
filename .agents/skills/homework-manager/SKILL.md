---
name: homework-manager
description: "Manage the D:\\程昊一\\Homework Git and LaTeX repository: inspect status, create course or homework scaffolds, sync an assignment, switch branches, finish and merge an assignment, or open related tools. Use for repository-management requests; do not use for solving or editing assignment content unless the user separately asks for that work."
---

# Homework Manager

Manage this repository through the deterministic PowerShell dispatcher at `scripts/homework.ps1`. Resolve relative paths from this Skill directory, and use the repository root `D:\程昊一\Homework` unless the user explicitly selects another checkout.

Map the user's request to exactly one public `Action` and call only the dispatcher. The dispatcher imports `scripts/Homework.Common.psm1` and loads the matching file under `scripts/actions/`; do not execute an action file directly because that bypasses repository initialization and the stable parameter contract.

## Use proportionate checks

Check only what can change the decision or catch a concrete failure. Avoid repeating `Status`, previews, permission explanations, or equivalent read-only commands when their result is already current and unambiguous.

For a mutating request, normally run `Status` once at the start and inspect the current branch plus every existing change. Treat pre-existing changes as user-owned: do not clean, restore, stage or commit them merely to unblock a workflow. Identify the exact course, assignment number, semester, branch, and requested remote effects. Infer a missing assignment number from the repository; do not infer permission to push, merge, or delete a branch. Once the current request explicitly grants a required permission, do not ask for it again unless the scope changes.

```powershell
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Status
```

## Choose the action

- `NewCourse -Course <name>`: create a course directory on updated `main`, commit its `.gitkeep`, and push `main`.
- `NewHomework -Course <name> -Semester <term> [-Number <n>]`: create `<course>-HW<n>`, copy `homework.sty`, create `<n>.tex`, commit, and push the new branch. Language and course display name default to the latest assignment in that course. Add `-Open` only when the user asked to open VS Code.
- `Sync`: on a homework branch, stage only its matching assignment directory, create a commit when needed, and push the branch. Supply `-Course` and `-Number` only if the branch name cannot identify the directory.
- `Switch -Branch <name>`: switch a clean worktree to an existing local branch and pull it with `--ff-only`.
- `Finish`: push the clean current homework branch, merge it into updated `main`, push `main`, then safely clean up the remote and local homework branch.
- `Open [-Course <name>] [-Number <n>] -Tool code|explorer|web|desktop`: open a local target or repository tool without changing Git state.

If a request spans multiple actions, execute them in the order implied by the request. Re-run `Status` between actions only when the preceding result is ambiguous, an external or concurrent change is plausible, a failure occurred, or the next action has a clean-worktree or branch precondition that the preceding output did not establish. Do not add intermediate checks mechanically.

Mutating actions default to preview, and every `-Apply` invocation prints its plan before changing state. For routine `NewCourse`, `NewHomework`, `Sync`, or `Switch` requests with explicit, unambiguous parameters and all required permissions, invoke `-Apply` directly after the initial state check; a separate preview invocation is optional and should be used only when it could reveal a meaningful mistake. Preview first for inferred or suspicious targets, unclear parameters, or when the user asks to review the plan. For `Finish`, preview first and require an explicit request to finish or merge the named/current branch because it pushes `main` and attempts remote branch deletion.

After mutation, perform one concise final verification when needed to establish the promised outcome. Prefer the action's own success output; add `Status` only when branch, synchronization, or worktree cleanliness is not already established. Do not repeat equivalent Git checks or retry a successful verification without a concrete reason.

## Examples

```powershell
# Preview, then perform a new assignment.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 NewHomework -Course Analysis-0 -Semester "2026 秋季"
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 NewHomework -Course Analysis-0 -Semester "2026 秋季" -Apply -Open

# Preview, then sync only the assignment associated with the current branch.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Sync
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Sync -Apply

# Preview, then finish the current homework branch after explicit authorization.
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Finish
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 Finish -Apply
```

## Stop conditions

- Stop on a dirty worktree for course creation, homework creation, switching or finishing. Report the existing paths and let the user decide how to handle them.
- Stop on missing `origin`, missing course/template, an existing target folder/branch, invalid input, non-fast-forward pull, merge conflict or failed push.
- If a merge conflicts, the script aborts the merge and returns to the homework branch when possible. Do not improvise conflict resolution unless the user asks.
- If `main` was merged locally but its push fails, preserve the branch and local merge commit; report the exact state and do not clean up.
- After a successful `main` push, branch-cleanup failures are warnings. Report that the merge succeeded and name what remains.

For assignment-content edits, leave this management workflow and follow the repository `AGENTS.md`; do not use a management request as permission to solve coursework.
