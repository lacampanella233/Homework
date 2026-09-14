function Invoke-HomeworkSwitch {
  param(
    [Parameter(Mandatory = $true)][string]$Branch,
    [switch]$Apply
  )

  Assert-HomeworkCleanWorktree -Operation 'switch branches'
  if (-not (Test-HomeworkGitRef -RefName "refs/heads/$Branch")) { throw "Local branch '$Branch' does not exist." }
  $currentBranch = Get-HomeworkCurrentBranch
  Write-HomeworkPlanHeader -Title "switch from $currentBranch to $Branch"
  Write-Host "  switch to $Branch and pull origin/$Branch with --ff-only"
  if (-not $Apply) { Write-Host 'Preview only; add -Apply to execute.'; return }
  if ($currentBranch -eq $Branch) { Write-Host "Already on $Branch."; return }
  [void](Invoke-HomeworkGit -Arguments @('switch', $Branch))
  [void](Invoke-HomeworkGit -Arguments @('pull', '--ff-only', 'origin', $Branch))
  Write-Host "Switched to and updated $Branch."
}
