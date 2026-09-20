---
name: homework-problem-importer
description: "Faithfully transcribe assignment problems from images or PDFs into an existing D:\\程昊一\\Homework LaTeX assignment, translating only when the source and target document languages differ, applying an explicitly supplied problem prefix, and reproducing necessary figures with TikZ or cropped graphics. Use for problem entry only; do not solve, correct, or paraphrase the assignment."
---

# Homework Problem Importer

Import problem statements into one existing `<course>/<number>/<number>.tex` file. Treat the source image or PDF as authoritative. This workflow authorizes faithful problem entry, not solutions, corrections, explanations, or unrelated repository changes. Do not stage, commit, push, create a homework branch, or create an assignment unless the user separately requests that action.

## Establish the exact task

1. Run `git status --short --branch` and record all pre-existing changes as user-owned.
2. Identify the source image or PDF, the exact target `.tex` file, and the requested source problems or pages. If any of these is ambiguous in a way that changes what would be inserted, ask the user before editing.
3. When the user selects only some of the visible problems, parse a comma-separated selection as follows: each item is either one problem number or an inclusive numeric range whose two integer endpoints are separated by a hyphen. Expand every range to all consecutive integers, deduplicate overlaps, and import only the selected problems, still in their order in the source. Ignore all unselected problems even when they appear between selected ones in the same screenshot or PDF page. Treat a hyphen as range syntax only when both sides are integer endpoints in this selection context; if it might instead be part of a compound problem identifier, ask the user rather than guessing. Report any selected number that is missing or unreadable in the supplied source.
4. Read the target `.tex` preamble and the existing local formatting around its last problems. Do not reread `homework.sty` during an ordinary import; its relevant interface is documented below.
5. Determine the target language from the package option:
   - `\usepackage[zh]{homework}` means Chinese.
   - `\usepackage[en]{homework}` means English.
   - No language option means Chinese, the package default.
6. Compare each source problem's prose language with the target language. If they match, do not translate. If they differ, translate the prose faithfully into the target language. Preserve mathematical notation, labels, names, units, and logical meaning; do not improve or repair the problem.
7. Use a prefix only when the user explicitly supplies one. Preserve it exactly except for TeX escaping that is necessary to render literal text.

If the target assignment does not exist, stop and explain that creating it is a separate repository-management action handled by `$homework-manager` after explicit authorization.

## Transcribe the problems

- Treat OCR as a draft, never as the source of truth. Compare the finished transcription visually against the source, including signs, superscripts, subscripts, accents, primes, bounds, matrices, cases, units, option labels, and problem numbers.
- Append one `problem` environment per source problem, in source order, immediately before `\end{document}`. Do not insert solutions or answer text.
- Preserve the wording and structure except for the required translation and punctuation normalization. Do not silently correct apparent typos or mathematical inconsistencies; report them without changing them.
- Convert Chinese/full-width punctuation in the transcribed prose to the corresponding English/ASCII punctuation. Do not perform blind character replacement inside LaTeX commands or mathematics.
- Match the target file's local LaTeX conventions when they do not change content: math delimiters, indentation, list labels, unit formatting, and display-math style.
- For a multi-line centered display, use one `gather*` environment with `\\` between lines; do not use consecutive `\[...\]` blocks. The homework template customizes vertical display spacing, so consecutive display blocks produce unattractively compressed spacing.
- For bold text inside a `problem` environment, format Chinese runs with `\heiti` and Latin-letter runs with `\textbf`. Split mixed-language bold text by script, for example `{\heiti 反变函子}(\textbf{contravariant functor})`; do not put Chinese text directly in `\textbf`, because this document style renders it as an unattractive bold Kai face.
- Use semantic LaTeX for text, mathematics, tables, and ordinary lists. Never insert a screenshot of an entire problem merely to avoid transcription.
- If a symbol or word remains genuinely unreadable after inspecting the highest-quality source, do not guess. Continue with other unambiguous problems when safe and ask the user about the exact unresolved location before inserting fabricated content.

## `problem` environment interface

The environment automatically increments and prints its own sequential problem number. Its optional argument is displayed after that number as a parenthesized title.

Without a user-supplied prefix, ignore the source problem number as an environment title:

```latex
\begin{problem}
  <faithful problem text>
\end{problem}
```

With an explicit prefix, combine it with the problem number shown in the source using exactly one hyphen:

```latex
\begin{problem}[<prefix>-<source-number>]
  <faithful problem text>
\end{problem}
```

For example, prefix `7C` and source problem `18` produce `\begin{problem}[7C-18]`. Do not invent a prefix or use the source number alone when no prefix was supplied.

The environment uses a shaded background named `shadecolor`, defined as `RGB(241,241,255)` (`#F1F1FF`). `homework.sty` already loads `graphicx`, `float`, and `xcolor`; it does not load TikZ.

## Reproduce figures

Reproduce only figures that are part of a problem. Choose the least costly method that can preserve the source reliably.

### TikZ

Use TikZ for simple diagrams such as basic geometry, coordinate axes, vectors, small graphs, or schematic line drawings when their geometry and labels can be reproduced confidently.

- Add `\usepackage{tikz}` to the preamble only if TikZ is actually used and not already loaded. Add only the libraries required by the drawing.
- Keep the TikZ canvas transparent so the `problem` background shows through. Avoid `fill=white`; when a fill must visually merge with the box, use `fill=shadecolor`.
- Preserve all meaningful labels, orientations, arrow directions, relative positions, solid/dashed distinctions, and stated scale relationships. Do not add decorative detail not present in the source.

### Cropped graphic

Use a cropped image for complex textbook art, detailed plots, photographs, or any figure whose faithful TikZ reconstruction would be fragile or disproportionately expensive.

- Crop to the figure and its necessary labels; exclude surrounding problem prose, page headers, answers, and unrelated marks.
- Store each resulting input asset in the target assignment directory with a short, filesystem-safe, descriptive name. Do not overwrite an existing asset.
- Prefer a transparent exterior background. Otherwise use `RGB(241,241,255)` (`#F1F1FF`) for flat exterior background or padding. Preserve meaningful white regions, fine antialiasing, and all photograph pixels; for a photograph, crop tightly and change only any added surrounding canvas.
- Keep enough resolution for labels and thin lines to remain legible in the compiled PDF.
- Insert the graphic directly inside `problem`, without a floating `figure` environment, because the problem is inside a shaded framed box. For example:

```latex
\begin{center}
  \includegraphics[width=0.72\linewidth]{problem-3-figure-1.png}
\end{center}
```

Choose the width by visual inspection. Keep the filename relative to the assignment directory.

## Verify the result

1. Re-read every inserted problem against the source at high resolution. Confirm the translation decision and every optional argument.
2. Review the scoped diff and new assets only; ensure existing answers and unrelated files are unchanged.
3. From the assignment directory, run:

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error <number>.tex
```

4. Report the exit code and key error if compilation fails. Preserve the source and log for diagnosis.
5. Inspect the compiled pages containing the new problems. Check ordering, line breaks, clipping, figure legibility, TikZ fidelity, and any visible seam against the shaded background. Compilation alone does not verify transcription or translation accuracy.
6. Run `git status --short --branch` again. Report the target `.tex`, added image assets, and which changes predated this task. Do not stage or commit unless explicitly requested.

In the final report, state which problems were imported, whether and into which language they were translated, whether a prefix was used, how each figure was handled, the compilation result, and any source ambiguity that remains.
