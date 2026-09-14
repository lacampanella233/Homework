function Invoke-HomeworkSync {
  param(
    [string]$Course,
    [int]$Number,
    [bool]$NumberSpecified,
    [string]$Message,
    [switch]$Apply
  )

  $assignment = Get-HomeworkAssignment -Course $Course -Number $Number -NumberSpecified $NumberSpecified
  Write-HomeworkPlanHeader -Title "sync $($assignment.Course) homework $($assignment.Number)"
  Write-Host "  stage only $($assignment.GitPath)"
  Write-Host '  commit if that directory has changes, then push the current branch'
  Write-Host 'Current status:'
  foreach ($line in Get-HomeworkStatusLines) { Write-Host "  $line" }
  if (-not $Apply) { Write-Host 'Preview only; add -Apply to execute.'; return }

  $existingStaged = @(Invoke-HomeworkGit -Arguments @('diff', '--cached', '--name-only'))
  if ($existingStaged.Count -gt 0) {
    throw "Refusing to mix with already staged changes:`n$($existingStaged -join [Environment]::NewLine)"
  }
  [void](Invoke-HomeworkGit -Arguments @('add', '--', $assignment.GitPath))
  $repoRoot = Get-HomeworkRepositoryRoot
  & git -C $repoRoot diff --cached --quiet -- $assignment.GitPath
  $diffExitCode = $LASTEXITCODE
  if ($diffExitCode -eq 1) {
    $commitMessage = if ($Message) { $Message } else { "Update homework branch $($assignment.Branch)" }
    [void](Invoke-HomeworkGit -Arguments @('commit', '-m', $commitMessage))
  } elseif ($diffExitCode -ne 0) {
    throw "git diff --cached failed with exit code $diffExitCode"
  }
  [void](Invoke-HomeworkGit -Arguments @('push', 'origin', $assignment.Branch))
  Write-Host "Synced $($assignment.Branch); unrelated working-tree changes were not staged."
}
