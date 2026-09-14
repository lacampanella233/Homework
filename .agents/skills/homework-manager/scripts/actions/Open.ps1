function Invoke-HomeworkOpen {
  param(
    [string]$Course,
    [int]$Number,
    [bool]$NumberSpecified,
    [ValidateSet('code', 'explorer', 'web', 'desktop')][string]$Tool = 'code'
  )

  $repoRoot = Get-HomeworkRepositoryRoot
  $targetPath = $repoRoot
  if ($Course) {
    $coursePath = Get-HomeworkCoursePath -Name $Course
    $targetPath = $coursePath
    if ($NumberSpecified) {
      $targetPath = Resolve-HomeworkRepoChild -Segments @($Course, $Number.ToString())
      if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
        throw "Assignment directory does not exist: $targetPath"
      }
    }
  }

  switch ($Tool) {
    'code' { Start-Process -FilePath 'code' -ArgumentList @($targetPath) }
    'explorer' { Start-Process -FilePath 'explorer.exe' -ArgumentList @($targetPath) }
    'web' {
      $url = Get-HomeworkGitText -Arguments @('remote', 'get-url', 'origin')
      if ($url -match '^git@github\.com:(.+)$') { $url = 'https://github.com/' + $Matches[1] }
      $url = $url -replace '\.git$', ''
      if ($url -notmatch '^https://github\.com/') { throw "Unsupported GitHub remote URL: $url" }
      Start-Process $url
    }
    'desktop' {
      try {
        Start-Process -FilePath 'github-desktop' -ArgumentList @($repoRoot)
      } catch {
        $encodedPath = [Uri]::EscapeDataString($repoRoot.Replace('\', '/'))
        Start-Process "github-windows://openLocalRepo/$encodedPath"
      }
    }
  }
  Write-Host "Opened $Tool for $targetPath"
}
