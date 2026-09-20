function Invoke-HomeworkNewAssignment {
  param(
    [Parameter(Mandatory = $true)][string]$Course,
    [string]$Semester,
    [int]$Number,
    [bool]$NumberSpecified,
    [ValidateSet('auto', 'zh', 'en')][string]$Language = 'auto',
    [string]$DisplayCourse,
    [switch]$Apply,
    [switch]$Open
  )

  Assert-HomeworkCleanWorktree -Operation 'create homework'
  $defaults = Resolve-HomeworkNewAssignmentDefaults -Semester $Semester -Language $Language
  $coursePath = Get-HomeworkCoursePath -Name $Course
  $homeworkNumber = if ($NumberSpecified) { $Number } else { Get-HomeworkNextNumber -CoursePath $coursePath }
  $target = Test-HomeworkTarget -CourseName $Course -HomeworkNumber $homeworkNumber
  $profile = Get-HomeworkCourseProfile -CourseName $Course -CoursePath $coursePath -Language $defaults.Language -DisplayCourse $DisplayCourse

  Write-HomeworkPlanHeader -Title "create $Course homework $homeworkNumber"
  Write-Host '  switch to main and pull origin/main with --ff-only'
  Write-Host "  create and switch to branch $($target.Branch)"
  Write-Host "  create $Course/$homeworkNumber/$homeworkNumber.tex"
  Write-Host "  copy root homework.sty; semester=$($defaults.Semester); language=$($profile.Language); course label=$($profile.DisplayCourse)"
  Write-Host "  commit and push $($target.Branch) with upstream"
  if ($Open) { Write-Host '  open the assignment directory in VS Code after push' }
  if (-not $Apply) { Write-Host 'Preview only; add -Apply to execute.'; return }

  [void](Invoke-HomeworkGit -Arguments @('switch', 'main'))
  [void](Invoke-HomeworkGit -Arguments @('pull', '--ff-only', 'origin', 'main'))
  Assert-HomeworkCleanWorktree -Operation 'create homework'
  $defaults = Resolve-HomeworkNewAssignmentDefaults -Semester $Semester -Language $Language
  $coursePath = Get-HomeworkCoursePath -Name $Course
  if (-not $NumberSpecified) { $homeworkNumber = Get-HomeworkNextNumber -CoursePath $coursePath }
  $target = Test-HomeworkTarget -CourseName $Course -HomeworkNumber $homeworkNumber
  $profile = Get-HomeworkCourseProfile -CourseName $Course -CoursePath $coursePath -Language $defaults.Language -DisplayCourse $DisplayCourse

  [void](Invoke-HomeworkGit -Arguments @('switch', '-c', $target.Branch))
  [void](New-Item -ItemType Directory -Path $target.AssignmentPath)
  $styleSource = Resolve-HomeworkRepoChild -Segments @('homework.sty')
  if (-not (Test-Path -LiteralPath $styleSource -PathType Leaf)) { throw 'Root homework.sty is missing.' }
  Copy-Item -LiteralPath $styleSource -Destination (Join-Path $target.AssignmentPath 'homework.sty')
  $texPath = Join-Path $target.AssignmentPath ($homeworkNumber.ToString() + '.tex')
  $escapedSemester = ConvertTo-HomeworkLatexText -Value $defaults.Semester
  $texContent = @"
\documentclass{article}
\usepackage[$($profile.Language)]{homework}

\config{$($profile.DisplayCourse)}{$escapedSemester}{$homeworkNumber}

\begin{document}



\end{document}
"@
  Set-Content -LiteralPath $texPath -Value $texContent -Encoding UTF8
  [void](Invoke-HomeworkGit -Arguments @('add', '--', (ConvertTo-HomeworkGitPath -Path $target.AssignmentPath)))
  [void](Invoke-HomeworkGit -Arguments @('commit', '-m', "Initialize $($target.Branch)"))
  [void](Invoke-HomeworkGit -Arguments @('push', '--set-upstream', 'origin', $target.Branch))
  Write-Host "Created and pushed $($target.Branch)."
  if ($Open) {
    Start-Process -FilePath 'code' -ArgumentList @($target.AssignmentPath)
  }
}
