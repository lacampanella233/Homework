Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:RepoRoot = $null

function Get-HomeworkRepositoryRoot {
  if (-not $script:RepoRoot) {
    throw 'Homework repository has not been initialized.'
  }
  return $script:RepoRoot
}

function Invoke-HomeworkGit {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Arguments
  )

  $repoRoot = Get-HomeworkRepositoryRoot
  $output = @(& git -C $repoRoot @Arguments 2>&1)
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    $command = 'git ' + ($Arguments -join ' ')
    $details = ($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    if ($details) {
      throw "$command failed with exit code $exitCode`n$details"
    }
    throw "$command failed with exit code $exitCode"
  }

  return @($output | ForEach-Object { $_.ToString() })
}

function Get-HomeworkGitText {
  param([Parameter(Mandatory = $true)][string[]]$Arguments)
  return ((Invoke-HomeworkGit -Arguments $Arguments) -join "`n").Trim()
}

function Test-HomeworkGitRef {
  param([Parameter(Mandatory = $true)][string]$RefName)
  $repoRoot = Get-HomeworkRepositoryRoot
  & git -C $repoRoot show-ref --verify --quiet $RefName
  return $LASTEXITCODE -eq 0
}

function Get-HomeworkCurrentBranch {
  $branchName = Get-HomeworkGitText -Arguments @('branch', '--show-current')
  if (-not $branchName) {
    throw 'Cannot continue from a detached HEAD.'
  }
  return $branchName
}

function Get-HomeworkStatusLines {
  return @(Invoke-HomeworkGit -Arguments @('status', '--short', '--branch'))
}

function Assert-HomeworkCleanWorktree {
  param([Parameter(Mandatory = $true)][string]$Operation)

  $changes = @(Invoke-HomeworkGit -Arguments @('status', '--porcelain', '--untracked-files=all'))
  if ($changes.Count -gt 0) {
    $details = $changes -join [Environment]::NewLine
    throw "Cannot $Operation because the worktree is not clean:`n$details"
  }
}

function Assert-HomeworkCourseName {
  param([Parameter(Mandatory = $true)][string]$Name)

  if ($Name -ne $Name.Trim() -or -not $Name) {
    throw 'Course name cannot be empty or have leading/trailing whitespace.'
  }
  if ($Name.Length -gt 100 -or $Name.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0) {
    throw 'Course name is too long or contains characters invalid in a Windows folder name.'
  }
  if ($Name -in @('.', '..') -or $Name -match '^(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$') {
    throw "Course name '$Name' is reserved or unsafe."
  }
}

function Resolve-HomeworkRepoChild {
  param([Parameter(Mandatory = $true)][string[]]$Segments)

  $repoRoot = Get-HomeworkRepositoryRoot
  $target = $repoRoot
  foreach ($segment in $Segments) {
    $target = Join-Path $target $segment
  }
  $target = [IO.Path]::GetFullPath($target)
  $rootPrefix = $repoRoot.TrimEnd('\') + '\'
  if ($target -ne $repoRoot -and -not $target.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Path escapes the repository: $target"
  }
  return $target
}

function ConvertTo-HomeworkGitPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  $repoRoot = Get-HomeworkRepositoryRoot
  return [IO.Path]::GetRelativePath($repoRoot, $Path).Replace('\', '/')
}

function Get-HomeworkCourseDirectories {
  $repoRoot = Get-HomeworkRepositoryRoot
  return @(Get-ChildItem -LiteralPath $repoRoot -Directory -Force |
    Where-Object { -not $_.Name.StartsWith('.') } |
    Sort-Object Name)
}

function Get-HomeworkCoursePath {
  param([Parameter(Mandatory = $true)][string]$Name)
  Assert-HomeworkCourseName -Name $Name
  $coursePath = Resolve-HomeworkRepoChild -Segments @($Name)
  if (-not (Test-Path -LiteralPath $coursePath -PathType Container)) {
    throw "Course '$Name' does not exist."
  }
  return $coursePath
}

function Get-HomeworkNextNumber {
  param([Parameter(Mandatory = $true)][string]$CoursePath)

  $maximum = 0
  foreach ($directory in Get-ChildItem -LiteralPath $CoursePath -Directory -Force) {
    if ($directory.Name -match '^\d+$') {
      $value = [int]$directory.Name
      if ($value -gt $maximum) {
        $maximum = $value
      }
    }
  }
  return $maximum + 1
}

function ConvertTo-HomeworkLatexText {
  param([Parameter(Mandatory = $true)][string]$Value)

  $replacements = @{
    '\' = '\textbackslash{}'
    '{' = '\{'
    '}' = '\}'
    '$' = '\$'
    '&' = '\&'
    '#' = '\#'
    '%' = '\%'
    '_' = '\_'
    '~' = '\textasciitilde{}'
    '^' = '\textasciicircum{}'
  }
  $builder = [Text.StringBuilder]::new()
  foreach ($character in $Value.ToCharArray()) {
    $key = [string]$character
    if ($replacements.ContainsKey($key)) {
      [void]$builder.Append($replacements[$key])
    } else {
      [void]$builder.Append($character)
    }
  }
  return $builder.ToString()
}

function Get-HomeworkCourseProfile {
  param(
    [Parameter(Mandatory = $true)][string]$CourseName,
    [Parameter(Mandatory = $true)][string]$CoursePath,
    [ValidateSet('auto', 'zh', 'en')][string]$Language = 'auto',
    [string]$DisplayCourse
  )

  $profileLanguage = if ($Language -eq 'auto') { 'zh' } else { $Language }
  $profileCourse = if ($DisplayCourse) {
    ConvertTo-HomeworkLatexText -Value $DisplayCourse
  } else {
    ConvertTo-HomeworkLatexText -Value $CourseName
  }

  if ($Language -eq 'auto' -or -not $DisplayCourse) {
    $latestFiles = @(Get-ChildItem -LiteralPath $CoursePath -Directory -Force |
      Where-Object { $_.Name -match '^\d+$' } |
      Sort-Object { [int]$_.Name } -Descending |
      ForEach-Object {
        $candidate = Join-Path $_.FullName ($_.Name + '.tex')
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { Get-Item -LiteralPath $candidate }
      })

    if ($latestFiles.Count -gt 0) {
      $content = Get-Content -LiteralPath $latestFiles[0].FullName -Raw -Encoding UTF8
      if ($Language -eq 'auto') {
        $languageMatch = [regex]::Match($content, '\\usepackage\[(zh|en)\]\{homework\}')
        if ($languageMatch.Success) {
          $profileLanguage = $languageMatch.Groups[1].Value
        }
      }
      if (-not $DisplayCourse) {
        $configMatch = [regex]::Match($content, '\\config\{([^}]*)\}\{[^}]*\}\{[^}]*\}')
        if ($configMatch.Success) {
          $profileCourse = $configMatch.Groups[1].Value
        }
      }
    }
  }

  return [PSCustomObject]@{
    Language = $profileLanguage
    DisplayCourse = $profileCourse
  }
}

function Get-HomeworkAssignment {
  param(
    [string]$Course,
    [int]$Number,
    [bool]$NumberSpecified
  )

  $currentBranch = Get-HomeworkCurrentBranch
  $courseName = $Course
  $homeworkNumber = if ($NumberSpecified) { $Number } else { 0 }

  if ((-not $courseName -or $homeworkNumber -eq 0) -and $currentBranch -match '^(.+)-HW([1-9]\d*)$') {
    if (-not $courseName) { $courseName = $Matches[1] }
    if ($homeworkNumber -eq 0) { $homeworkNumber = [int]$Matches[2] }
  }
  if (-not $courseName -or $homeworkNumber -eq 0) {
    throw 'Cannot infer the assignment from the current branch. Supply -Course and -Number.'
  }

  $coursePath = Get-HomeworkCoursePath -Name $courseName
  $assignmentPath = Resolve-HomeworkRepoChild -Segments @($courseName, $homeworkNumber.ToString())
  if (-not (Test-Path -LiteralPath $assignmentPath -PathType Container)) {
    throw "Assignment directory does not exist: $assignmentPath"
  }

  return [PSCustomObject]@{
    Branch = $currentBranch
    Course = $courseName
    Number = $homeworkNumber
    CoursePath = $coursePath
    AssignmentPath = $assignmentPath
    GitPath = ConvertTo-HomeworkGitPath -Path $assignmentPath
  }
}

function Write-HomeworkPlanHeader {
  param([Parameter(Mandatory = $true)][string]$Title)
  Write-Host "PLAN: $Title"
  Write-Host "Repository: $(Get-HomeworkRepositoryRoot)"
  Write-Host "Current branch: $(Get-HomeworkCurrentBranch)"
}

function Test-HomeworkTarget {
  param(
    [Parameter(Mandatory = $true)][string]$CourseName,
    [Parameter(Mandatory = $true)][int]$HomeworkNumber
  )

  $assignmentPath = Resolve-HomeworkRepoChild -Segments @($CourseName, $HomeworkNumber.ToString())
  $branchName = "$CourseName-HW$HomeworkNumber"
  [void](Invoke-HomeworkGit -Arguments @('check-ref-format', '--branch', $branchName))
  if (Test-Path -LiteralPath $assignmentPath) { throw "Assignment path already exists: $assignmentPath" }
  if (Test-HomeworkGitRef -RefName "refs/heads/$branchName") { throw "Local branch '$branchName' already exists." }
  if (Test-HomeworkGitRef -RefName "refs/remotes/origin/$branchName") { throw "Remote-tracking branch 'origin/$branchName' already exists." }
  return [PSCustomObject]@{ AssignmentPath = $assignmentPath; Branch = $branchName }
}

function Initialize-HomeworkRepository {
  param([Parameter(Mandatory = $true)][string]$RepoPath)

  $resolvedInput = (Resolve-Path -LiteralPath $RepoPath).Path
  $rootOutput = @(& git -C $resolvedInput rev-parse --show-toplevel 2>&1)
  if ($LASTEXITCODE -ne 0 -or $rootOutput.Count -eq 0) {
    throw "Not inside a Git repository: $resolvedInput"
  }
  $script:RepoRoot = [IO.Path]::GetFullPath($rootOutput[0].ToString().Trim())
  if (-not (Test-Path -LiteralPath (Join-Path $script:RepoRoot '.git'))) {
    throw "Git root is not accessible: $script:RepoRoot"
  }
  if (-not (Test-HomeworkGitRef -RefName 'refs/heads/main')) {
    throw "Required local main branch is missing in $script:RepoRoot"
  }
  return $script:RepoRoot
}

Export-ModuleMember -Function @(
  'Assert-HomeworkCleanWorktree',
  'Assert-HomeworkCourseName',
  'ConvertTo-HomeworkGitPath',
  'ConvertTo-HomeworkLatexText',
  'Get-HomeworkAssignment',
  'Get-HomeworkCourseDirectories',
  'Get-HomeworkCoursePath',
  'Get-HomeworkCourseProfile',
  'Get-HomeworkCurrentBranch',
  'Get-HomeworkGitText',
  'Get-HomeworkNextNumber',
  'Get-HomeworkRepositoryRoot',
  'Get-HomeworkStatusLines',
  'Initialize-HomeworkRepository',
  'Invoke-HomeworkGit',
  'Resolve-HomeworkRepoChild',
  'Test-HomeworkGitRef',
  'Test-HomeworkTarget',
  'Write-HomeworkPlanHeader'
)
