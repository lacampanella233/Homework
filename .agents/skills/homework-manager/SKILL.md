---
name: homework-manager
description: "Manage this Homework Git and LaTeX repository on macOS: inspect status, compare local assignment snapshots, manage assignment bindings, create or compile homework, sync assignments, switch branches, finish and merge assignments, or open related tools. Use for repository management and assignment compilation, not for solving or editing assignment content."
---

# Homework Manager

Use the standalone program at `tools/homework/scripts/homework.py`. This Skill contains AI invocation and authorization rules; implementation, tests, dependencies, and the [business workflow and CLI manual](../../../tools/homework/README.md) live in `tools/homework/`. The separation and these instructions were AI-assisted.

Follow repository [AGENTS.md](../../../AGENTS.md). Run commands from the repository root, or use the absolute entry path from another directory. The program resolves its default repository from its own location. Use `--repo-path` only for isolated tests or an explicitly selected checkout. Invoke public Actions through the dispatcher, never execute internal `scripts/actions/` modules.

## Start every request

Run `Status` and inspect the branch and every existing change. Treat pre-existing changes as user-owned. Do not clean, restore, stage or commit them merely to unblock a workflow. Identify the exact course, assignment, branch and requested remote effects; do not infer permission to push, merge or delete branches beyond the standing authorization below.

```sh
python3 tools/homework/scripts/homework.py Status
python3 tools/homework/scripts/homework.py --help
```

## Select and authorize an Action

Read the [CLI manual](../../../tools/homework/README.md) for arguments and business behavior. Available Actions are `Status`, `CompareAssignments`, `BindAssignment`, `NewCourse`, `NewHomework`, `Compile`, `Sync`, `Switch`, `Finish`, and `Open`.

- `Status` and `CompareAssignments` are read-only and do not accept `--apply`.
- `NewCourse`, `NewHomework`, `BindAssignment`, `Sync`, `Switch`, and `Finish` default to preview. Inspect exact paths, branches, overwrite notices and remote effects; add `--apply` only when authorized. A status, audit or plan request does not authorize applying it. Re-run `Status` between state-changing actions.
- `NewCourse` commits and pushes `main`; `NewHomework` creates, commits and pushes an assignment branch; `Sync` commits and pushes the current assignment. `BindAssignment` backs up and saves the confirmed relation without Git mutations.
- `Finish --apply` pushes the assignment branch, merges into updated `main`, pushes `main`, then attempts remote and local branch cleanup. Require explicit authorization to finish/merge the named or current assignment, and especially verify the previewed branch.
- `Compile` immediately runs `latexmk -xelatex`, accepts no `--apply`, and returns its exit code. Preserve source, PDF and logs; compilation success does not establish content correctness.
- `Open` is only for a user request to open VS Code, Finder, GitHub or GitHub Desktop.

Management requests do not authorize editing assignment questions, answers, proofs or layout. Configuration defaults and numbering are computed by the program; inspect its output rather than hard-coding the next number. Consult the [automation plan](../../../AUTOMATION_PLAN.md) for current platform capabilities before developing or attempting real access.

## Finish after review

When the user says “完成作业” after reviewing the current assignment, treat it as explicit authorization to commit the reviewed assignment changes, merge its branch into `main`, and push. Do not ask for the same authorization again. Run `Sync`, then `Finish` once the worktree is clean, inspecting both previews and the exact branch. Handle separately authorized rule or Skill changes in a separate scoped commit; exclude unrelated changes. This does not authorize editing assignment content.

## Preserve assignment sources

Whenever creating homework, copy user-provided original problem files into `<course>/<number>/` after `NewHomework` creates it, including files supplied later. Preserve filenames where possible and avoid collisions with existing files, including `<number>.tex` and `<number>.pdf`. Reuse an identical copy; otherwise choose a distinct filename without overwriting. Verify source and copy match. Problem PDFs remain local and ignored; preserve them independently of Git.

## Clean up completed homework branches

After an authorized merge and successful push of `main`, the user authorizes local branch cleanup without further confirmation. `Finish` already performs this.

- Verify the branch tip is contained in `main` using `git merge-base --is-ancestor <branch> main`; disappearing upstream refs or matching files do not prove this.
- Use only `git branch -d`. Preserve unmerged, current, or worktree-checked-out branches; if `main` was not successfully pushed, preserve both branches.
- Cleanup failure is a warning after successful merge/push. Report remaining branches without misreporting the merge as failed.
- Inspection alone does not authorize deleting existing branches. Remote deletion requires explicit authorization. Branch cleanup does not authorize deleting ignored PDFs, build files or assignment directories.

## Stop conditions

- Stop on dirty worktrees for creation, switching or finishing; report paths without discarding changes.
- Stop on missing prerequisites, existing targets, invalid input, non-fast-forward pulls, conflicts or failed pushes. Do not rebase, force-push or improvise conflict resolution.
- A failed merge attempts abort and return to the assignment branch; report any recovery failures. If only the push of merged `main` fails, preserve the local merge and both branches without cleanup.
- For compilation failure, preserve source and logs. The program also checks MacTeX's `/Library/TeX/texbin` when `latexmk` is absent from PATH.
- Follow existing PDF tracking rules: track only the compiled main assignment PDF; preserve ignored originals and figures locally. Never use `git add -f` or broad numeric exceptions to bypass them.

For automation development, follow `AUTOMATION_PLAN.md`, update the program's manual alongside public behavior changes, and run isolated tests from the repository root:

```sh
python3 -B -m unittest discover -s tools/homework/tests -v
```
