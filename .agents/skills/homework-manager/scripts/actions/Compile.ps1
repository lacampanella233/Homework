function Get-HomeworkCompileDriveLetter {
  $usedLetters = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach ($drive in Get-PSDrive -PSProvider FileSystem) {
    [void]$usedLetters.Add($drive.Name)
  }

  $substOutput = @(& subst.exe 2>&1)
  if ($LASTEXITCODE -ne 0) {
    throw 'Cannot inspect existing subst mappings.'
  }
  foreach ($line in $substOutput) {
    if ($line.ToString() -match '^\s*([A-Za-z]):\\:') {
      [void]$usedLetters.Add($Matches[1])
    }
  }

  for ($code = [int][char]'Z'; $code -ge [int][char]'R'; $code--) {
    $letter = [char]$code
    if (-not $usedLetters.Contains($letter.ToString()) -and
        -not (Test-Path -LiteralPath "$letter`:\" -ErrorAction SilentlyContinue)) {
      return $letter.ToString()
    }
  }
  throw 'No free drive letter is available in the range R: through Z: for the temporary compile mapping.'
}

function Invoke-HomeworkCompile {
  param(
    [string]$Course,
    [int]$Number,
    [bool]$NumberSpecified
  )

  $assignment = Get-HomeworkAssignment -Course $Course -Number $Number -NumberSpecified $NumberSpecified
  $texName = $assignment.Number.ToString() + '.tex'
  $texPath = Join-Path $assignment.AssignmentPath $texName
  if (-not (Test-Path -LiteralPath $texPath -PathType Leaf)) {
    throw "Assignment source is missing: $texPath"
  }

  $latexmk = Get-Command latexmk -CommandType Application -ErrorAction Stop | Select-Object -First 1
  $driveLetter = Get-HomeworkCompileDriveLetter
  $driveName = "$driveLetter`:"
  $driveRoot = "$driveName\"
  $mappedTexPath = $driveRoot + $texName
  $mappingCreated = $false
  $compileExit = $null
  $operationError = $null
  $cleanupError = $null

  Write-Host "Compiling $($assignment.Course) homework $($assignment.Number)"
  Write-Host "Source: $texPath"
  Write-Host "Temporary compile path: $mappedTexPath"

  try {
    $mapOutput = @(& subst.exe $driveName $assignment.AssignmentPath 2>&1)
    if ($LASTEXITCODE -ne 0) {
      $details = ($mapOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
      throw "Failed to create temporary mapping $driveName for $($assignment.AssignmentPath).`n$details"
    }
    $mappingCreated = $true

    if (-not (Test-Path -LiteralPath $mappedTexPath -PathType Leaf)) {
      throw "Temporary mapping does not expose the assignment source: $mappedTexPath"
    }

    Push-Location -LiteralPath $driveRoot
    try {
      & $latexmk.Source -pdf -interaction=nonstopmode -halt-on-error $texName
      $compileExit = $LASTEXITCODE
    } finally {
      Pop-Location
    }
  } catch {
    $operationError = $_
  } finally {
    if ($mappingCreated) {
      $unmapOutput = @(& subst.exe $driveName /D 2>&1)
      if ($LASTEXITCODE -ne 0) {
        $details = ($unmapOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
        $cleanupError = "Failed to remove temporary mapping $driveName.`n$details"
      }
    }
  }

  if ($operationError) {
    if ($cleanupError) {
      throw "$($operationError.Exception.Message)`n$cleanupError"
    }
    throw $operationError
  }
  if ($cleanupError) {
    throw $cleanupError
  }
  if ($null -eq $compileExit) {
    throw 'latexmk did not report an exit code.'
  }
  if ($compileExit -ne 0) {
    [Console]::Error.WriteLine("latexmk failed with exit code $compileExit. Logs were preserved in $($assignment.AssignmentPath).")
    exit $compileExit
  }

  Write-Host "Compiled $texPath successfully (exit code 0)."
}
