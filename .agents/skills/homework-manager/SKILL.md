---
name: homework-manager
description: "Manage this Homework Git and LaTeX repository on macOS: inspect status, create or compile homework, sync assignments, switch branches, finish and merge assignments, or open related tools. Use for repository management and assignment compilation, not for solving or editing assignment content."
---

# Homework Manager

Use the standard-library Python dispatcher at `scripts/homework.py`. The default repository is resolved from the script location, so it also works when invoked outside the repository. Use `--repo-path` only for isolated tests or an explicitly selected checkout. Python 3.9 or newer, Git, and MacTeX are the runtime tools; PowerShell is not required.

Call only the dispatcher. Shared Git, path and validation logic lives in `scripts/common.py`; action implementations are allowlisted under `scripts/actions/`. Do not execute an action module directly. This macOS migration of the scripts and related documentation was AI-assisted.

## Start every request

Run `Status` and inspect the branch and every existing change. Treat pre-existing changes as user-owned. Do not clean, restore, stage or commit them merely to unblock a workflow. Identify the exact course, assignment, branch and requested remote effects. Do not infer permission to push, merge or delete branches.

```sh
python3 .agents/skills/homework-manager/scripts/homework.py Status
```

Root `homework.config.json` supplies the semester and the language fallback. New assignments inherit the latest numbered assignment's language and course display name when available; explicit options override those defaults.

## Actions

- `NewCourse --course <name>`: create a course on updated `main`, commit its `.gitkeep`, and push `main`.
- `NewHomework --course <name> [--number <n>] [--semester <term>] [--language auto|zh|en] [--display-course <name>]`: create `<course>-HW<n>`, copy root `homework.sty`, create `<n>.tex`, commit the assignment directory, and push the branch. The next number is the maximum numeric directory plus one. Use `--open` only when opening VS Code was requested.
- `Compile [--course <name>] [--number <n>]`: immediately run `latexmk -xelatex` in the assignment directory, preserve logs, and return the compiler exit code. It does not accept `--apply`. macOS supports Chinese paths directly; no drive mapping is used.
- `Sync`: stage only the matching assignment directory, commit only when needed, and push the homework branch. Refuse existing staged changes. `--course` and `--number` can identify a directory, but must match the current homework branch.
- `Switch --branch <name>`: switch a clean worktree to an existing branch and pull with `--ff-only`, including when already on that branch.
- `Finish`: push the clean current homework branch, merge into updated `main`, push `main`, then safely clean up the remote and local homework branch.
- `Open [--course <name>] [--number <n>] --tool code|finder|web|desktop`: open VS Code, Finder, GitHub in the browser, or GitHub Desktop. `explorer` remains a Finder alias. macOS uses `/usr/bin/open`; VS Code can use its `code` command when available.

Mutating actions default to preview. Inspect the exact paths and branches, then add `--apply` only when the request authorizes the action and its remote effects. A status, audit or plan request does not authorize applying it. For `Finish`, require explicit authorization to finish/merge the named or current homework branch. Re-run `Status` between state-changing actions.

```sh
python3 .agents/skills/homework-manager/scripts/homework.py NewHomework --course Analysis-1
python3 .agents/skills/homework-manager/scripts/homework.py NewHomework --course Analysis-1 --apply
python3 .agents/skills/homework-manager/scripts/homework.py Compile --course Algebra-1 --number 2
python3 .agents/skills/homework-manager/scripts/homework.py Sync --apply
python3 .agents/skills/homework-manager/scripts/homework.py Finish --apply
```

## Stop conditions

- Stop on a dirty worktree for creation, switching or finishing and report its paths. Do not discard user work.
- Stop on missing course/template/origin, invalid input, existing targets, non-fast-forward pulls, merge conflicts or failed pushes. Do not rebase or force-push.
- For compilation, stop on missing source or `latexmk`; preserve source and logs. MacTeX's `/Library/TeX/texbin` is also checked when `latexmk` is absent from PATH.
- A failed merge attempts `merge --abort` and return to the homework branch; report recovery failures. Do not improvise conflict resolution.
- If `main` was merged locally but its push fails, preserve both branches and the local merge; no cleanup runs.
- After successful `main` push, cleanup failures are warnings. Report what remains; local deletion uses `git branch -d`.

For assignment-content edits, follow repository `AGENTS.md`. Management requests do not authorize writing solutions or proofs. Generated homework PDFs are intentionally tracked so they can be viewed in the remote repository. `Sync` includes changed or newly compiled PDFs in the assignment directory; ignore only LaTeX intermediate files, never the homework PDF.

Run isolated behavioral checks after changing these scripts:

```sh
python3 -B -m unittest discover -s .agents/skills/homework-manager/tests -v
```
