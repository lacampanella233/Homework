function Invoke-HomeworkFinish {
  param([switch]$Apply)

  Assert-HomeworkCleanWorktree -Operation 'finish homework'
  $featureBranch = Get-HomeworkCurrentBranch
  if ($featureBranch -eq 'main') { throw 'Finish must run from a homework branch, not main.' }
  Write-HomeworkPlanHeader -Title "finish and merge $featureBranch"
  Write-Host "  push origin/$featureBranch"
  Write-Host '  switch to main and pull origin/main with --ff-only'
  Write-Host "  merge $featureBranch into main with --no-ff and push main"
  Write-Host "  after successful main push, delete origin/$featureBranch and local $featureBranch"
  if (-not $Apply) { Write-Host 'Preview only; add -Apply after explicit merge authorization.'; return }

  [void](Invoke-HomeworkGit -Arguments @('push', 'origin', $featureBranch))
  try {
    [void](Invoke-HomeworkGit -Arguments @('switch', 'main'))
    [void](Invoke-HomeworkGit -Arguments @('pull', '--ff-only', 'origin', 'main'))
  } catch {
    if ((Get-HomeworkCurrentBranch) -ne $featureBranch) {
      try { [void](Invoke-HomeworkGit -Arguments @('switch', $featureBranch)) } catch { }
    }
    throw
  }

  try {
    $mergeMessage = "Merge homework branch $featureBranch to main (via homework-manager skill)"
    [void](Invoke-HomeworkGit -Arguments @('merge', '--no-ff', $featureBranch, '-m', $mergeMessage))
  } catch {
    $repoRoot = Get-HomeworkRepositoryRoot
    & git -C $repoRoot merge --abort 2>$null
    & git -C $repoRoot switch $featureBranch 2>$null
    throw "Merge failed and was aborted. The homework branch was preserved.`n$($_.Exception.Message)"
  }

  try {
    [void](Invoke-HomeworkGit -Arguments @('push', 'origin', 'main'))
  } catch {
    throw "The merge exists locally on main, but pushing main failed. No branch was deleted.`n$($_.Exception.Message)"
  }

  $warnings = [Collections.Generic.List[string]]::new()
  try {
    [void](Invoke-HomeworkGit -Arguments @('push', 'origin', '--delete', $featureBranch))
  } catch {
    $warnings.Add("Remote branch remains: $($_.Exception.Message)")
  }
  try {
    [void](Invoke-HomeworkGit -Arguments @('branch', '-d', $featureBranch))
  } catch {
    $warnings.Add("Local branch remains: $($_.Exception.Message)")
  }

  Write-Host "Merged and pushed $featureBranch to main."
  foreach ($warning in $warnings) { Write-Warning $warning }
}
