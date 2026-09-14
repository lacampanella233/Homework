function Invoke-HomeworkNewCourse {
  param(
    [Parameter(Mandatory = $true)][string]$Course,
    [switch]$Apply
  )

  Assert-HomeworkCourseName -Name $Course
  Assert-HomeworkCleanWorktree -Operation 'create a course'
  $coursePath = Resolve-HomeworkRepoChild -Segments @($Course)
  if (Test-Path -LiteralPath $coursePath) { throw "Course '$Course' already exists." }

  Write-HomeworkPlanHeader -Title "create course '$Course'"
  Write-Host '  switch to main and pull origin/main with --ff-only'
  Write-Host "  create $Course/.gitkeep"
  Write-Host '  commit and push main'
  if (-not $Apply) { Write-Host 'Preview only; add -Apply to execute.'; return }

  [void](Invoke-HomeworkGit -Arguments @('switch', 'main'))
  [void](Invoke-HomeworkGit -Arguments @('pull', '--ff-only', 'origin', 'main'))
  Assert-HomeworkCleanWorktree -Operation 'create a course'
  if (Test-Path -LiteralPath $coursePath) { throw "Course '$Course' already exists after updating main." }
  [void](New-Item -ItemType Directory -Path $coursePath)
  $keepPath = Join-Path $coursePath '.gitkeep'
  [void](New-Item -ItemType File -Path $keepPath)
  [void](Invoke-HomeworkGit -Arguments @('add', '--', (ConvertTo-HomeworkGitPath -Path $keepPath)))
  [void](Invoke-HomeworkGit -Arguments @('commit', '-m', "Add new course: $Course"))
  [void](Invoke-HomeworkGit -Arguments @('push', 'origin', 'main'))
  Write-Host "Created and pushed course '$Course'."
}
