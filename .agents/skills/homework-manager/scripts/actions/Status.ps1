function Invoke-HomeworkStatus {
  Write-Host "Repository: $(Get-HomeworkRepositoryRoot)"
  Write-Host "Current branch: $(Get-HomeworkCurrentBranch)"
  $remote = Get-HomeworkGitText -Arguments @('remote', 'get-url', 'origin')
  Write-Host "Origin: $remote"
  Write-Host 'Courses:'
  foreach ($directory in Get-HomeworkCourseDirectories) {
    $nextNumber = Get-HomeworkNextNumber -CoursePath $directory.FullName
    Write-Host "  $($directory.Name) (next: $nextNumber)"
  }
  Write-Host 'Local branches:'
  foreach ($branchName in Invoke-HomeworkGit -Arguments @('branch', '--format=%(refname:short)')) {
    Write-Host "  $branchName"
  }
  Write-Host 'Git status:'
  foreach ($line in Get-HomeworkStatusLines) {
    Write-Host "  $line"
  }
}
