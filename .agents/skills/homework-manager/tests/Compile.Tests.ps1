$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-TestCondition {
  param(
    [Parameter(Mandatory = $true)][bool]$Condition,
    [Parameter(Mandatory = $true)][string]$Message
  )
  if (-not $Condition) { throw $Message }
}

function Invoke-TestGit {
  param(
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )
  $output = @(& git -C $Repository @Arguments 2>&1)
  if ($LASTEXITCODE -ne 0) {
    throw "git $($Arguments -join ' ') failed:`n$($output -join [Environment]::NewLine)"
  }
}

function Get-SubstSnapshot {
  return ((@(& subst.exe 2>&1) | ForEach-Object { $_.ToString() }) -join "`n")
}

$skillRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dispatcher = Join-Path $skillRoot 'scripts\homework.ps1'
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$testRoot = Join-Path $tempBase ('homework-compile-test-' + [guid]::NewGuid().ToString('N'))
$repoPath = Join-Path $testRoot 'repo'
$fakeBin = Join-Path $testRoot 'bin'
$marker = Join-Path $testRoot 'compile-cwd.txt'
$oldPath = $env:PATH
$oldExit = $env:HOMEWORK_COMPILE_TEST_EXIT
$oldMarker = $env:HOMEWORK_COMPILE_TEST_MARKER

try {
  [void](New-Item -ItemType Directory -Path (Join-Path $repoPath '中文课程\1') -Force)
  [void](New-Item -ItemType Directory -Path $fakeBin -Force)
  Set-Content -LiteralPath (Join-Path $repoPath '中文课程\1\1.tex') -Value '\documentclass{article}\begin{document}test\end{document}' -Encoding UTF8
  Set-Content -LiteralPath (Join-Path $repoPath 'README.md') -Value 'compile test repository' -Encoding UTF8
  Set-Content -LiteralPath (Join-Path $fakeBin 'latexmk.cmd') -Encoding ASCII -Value @(
    '@echo off'
    '> "%HOMEWORK_COMPILE_TEST_MARKER%" echo %CD%'
    'exit /b %HOMEWORK_COMPILE_TEST_EXIT%'
  )

  Invoke-TestGit -Repository $repoPath -Arguments @('init', '-b', 'main')
  Invoke-TestGit -Repository $repoPath -Arguments @('config', 'user.name', 'Homework Compile Test')
  Invoke-TestGit -Repository $repoPath -Arguments @('config', 'user.email', 'compile-test@example.invalid')
  Invoke-TestGit -Repository $repoPath -Arguments @('add', '--', 'README.md', '中文课程/1/1.tex')
  Invoke-TestGit -Repository $repoPath -Arguments @('commit', '-m', 'Initialize compile fixture')
  Invoke-TestGit -Repository $repoPath -Arguments @('switch', '-c', '中文课程-HW1')

  $env:PATH = "$fakeBin;$oldPath"
  $env:HOMEWORK_COMPILE_TEST_MARKER = $marker
  $substBefore = Get-SubstSnapshot

  $env:HOMEWORK_COMPILE_TEST_EXIT = '0'
  $successOutput = @(& pwsh -NoProfile -File $dispatcher Compile -RepoPath $repoPath 2>&1)
  $successExit = $LASTEXITCODE
  Assert-TestCondition -Condition ($successExit -eq 0) -Message "Compile success case returned $successExit`n$($successOutput -join [Environment]::NewLine)"
  Assert-TestCondition -Condition (Test-Path -LiteralPath $marker -PathType Leaf) -Message 'Fake latexmk did not run.'
  $compileCwd = (Get-Content -LiteralPath $marker -Raw).Trim()
  Assert-TestCondition -Condition ($compileCwd -match '^[R-Z]:\\$') -Message "Compile did not run from a temporary drive root: $compileCwd"
  Assert-TestCondition -Condition ((Get-SubstSnapshot) -eq $substBefore) -Message 'Compile success case left a subst mapping behind.'

  $env:HOMEWORK_COMPILE_TEST_EXIT = '7'
  $failureOutput = @(& pwsh -NoProfile -File $dispatcher Compile -RepoPath $repoPath 2>&1)
  $failureExit = $LASTEXITCODE
  Assert-TestCondition -Condition ($failureExit -eq 7) -Message "Compile failure case returned $failureExit instead of 7.`n$($failureOutput -join [Environment]::NewLine)"
  Assert-TestCondition -Condition ((Get-SubstSnapshot) -eq $substBefore) -Message 'Compile failure case left a subst mapping behind.'

  Write-Host 'Compile action tests passed.'
} finally {
  $env:PATH = $oldPath
  if ($null -eq $oldExit) { Remove-Item Env:HOMEWORK_COMPILE_TEST_EXIT -ErrorAction SilentlyContinue } else { $env:HOMEWORK_COMPILE_TEST_EXIT = $oldExit }
  if ($null -eq $oldMarker) { Remove-Item Env:HOMEWORK_COMPILE_TEST_MARKER -ErrorAction SilentlyContinue } else { $env:HOMEWORK_COMPILE_TEST_MARKER = $oldMarker }

  if (Test-Path -LiteralPath $testRoot) {
    $resolvedTestRoot = [IO.Path]::GetFullPath($testRoot)
    $expectedPrefix = $tempBase + '\homework-compile-test-'
    if (-not $resolvedTestRoot.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
      throw "Refusing to remove unexpected test path: $resolvedTestRoot"
    }
    Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
  }
}
