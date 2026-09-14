[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet('Status', 'NewCourse', 'NewHomework', 'Sync', 'Switch', 'Finish', 'Open')]
  [string]$Action,

  [string]$Course,

  [ValidateRange(1, [int]::MaxValue)]
  [int]$Number,

  [string]$Semester,

  [ValidateSet('auto', 'zh', 'en')]
  [string]$Language = 'auto',

  [string]$DisplayCourse,
  [string]$Branch,
  [string]$Message,

  [ValidateSet('code', 'explorer', 'web', 'desktop')]
  [string]$Tool = 'code',

  [string]$RepoPath = (Get-Location).Path,
  [switch]$Apply,
  [switch]$Open
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$numberSpecified = $PSBoundParameters.ContainsKey('Number')
$scriptsRoot = $PSScriptRoot
$commonModule = Join-Path $scriptsRoot 'Homework.Common.psm1'
$actionFiles = @{
  Status = 'Status.ps1'
  NewCourse = 'NewCourse.ps1'
  NewHomework = 'NewHomework.ps1'
  Sync = 'Sync.ps1'
  Switch = 'Switch.ps1'
  Finish = 'Finish.ps1'
  Open = 'Open.ps1'
}

if (-not (Test-Path -LiteralPath $commonModule -PathType Leaf)) {
  throw "Required common module is missing: $commonModule"
}
$actionFile = Join-Path (Join-Path $scriptsRoot 'actions') $actionFiles[$Action]
if (-not (Test-Path -LiteralPath $actionFile -PathType Leaf)) {
  throw "Required action module is missing: $actionFile"
}

Import-Module -Name $commonModule -Force -DisableNameChecking -ErrorAction Stop
[void](Initialize-HomeworkRepository -RepoPath $RepoPath)
. $actionFile

switch ($Action) {
  'Status' {
    Invoke-HomeworkStatus
  }
  'NewCourse' {
    if (-not $Course) { throw 'NewCourse requires -Course.' }
    Invoke-HomeworkNewCourse -Course $Course -Apply:$Apply
  }
  'NewHomework' {
    if (-not $Course) { throw 'NewHomework requires -Course.' }
    if (-not $Semester) { throw 'NewHomework requires a single-line -Semester of 100 characters or fewer.' }
    Invoke-HomeworkNewAssignment -Course $Course -Semester $Semester -Number $Number -NumberSpecified $numberSpecified -Language $Language -DisplayCourse $DisplayCourse -Apply:$Apply -Open:$Open
  }
  'Sync' {
    Invoke-HomeworkSync -Course $Course -Number $Number -NumberSpecified $numberSpecified -Message $Message -Apply:$Apply
  }
  'Switch' {
    if (-not $Branch) { throw 'Switch requires -Branch.' }
    Invoke-HomeworkSwitch -Branch $Branch -Apply:$Apply
  }
  'Finish' {
    Invoke-HomeworkFinish -Apply:$Apply
  }
  'Open' {
    Invoke-HomeworkOpen -Course $Course -Number $Number -NumberSpecified $numberSpecified -Tool $Tool
  }
}
