param(
  [string]$BundleDir = "$(Resolve-Path (Join-Path $PSScriptRoot '..\..'))\dist_desktop",
  [string]$ReleaseDir = "",
  [switch]$SkipDesktopExe
)

$ErrorActionPreference = "Stop"
$BackendExe = Join-Path $BundleDir "backend\SeraBackend.exe"
$FrontendIndex = Join-Path $BundleDir "frontend\dist\index.html"
$DesktopLauncherExe = Join-Path $BundleDir "Sera.exe"
if ([string]::IsNullOrWhiteSpace($ReleaseDir)) {
  $ReleaseDir = Join-Path $BundleDir "release"
} else {
  $bundleFull = [System.IO.Path]::GetFullPath($BundleDir)
  $releaseFull = [System.IO.Path]::GetFullPath($ReleaseDir)
  if (-not $releaseFull.StartsWith($bundleFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to smoke-test a release outside the bundle root: $releaseFull"
  }
  $ReleaseDir = $releaseFull
}
$ElectronExe = Join-Path $ReleaseDir "win-unpacked\Sera.exe"
$ElectronBackendExe = Join-Path $ReleaseDir "win-unpacked\resources\backend\SeraBackend.exe"

if (!(Test-Path $BackendExe)) { throw "Backend executable missing: $BackendExe" }
if (!(Test-Path $FrontendIndex)) { throw "Frontend index missing: $FrontendIndex" }
if (!(Test-Path $DesktopLauncherExe)) { throw "Desktop launcher executable missing: $DesktopLauncherExe" }

function Stop-PackagedBackendProcesses {
  $backendPaths = @(
    [System.IO.Path]::GetFullPath($BackendExe),
    [System.IO.Path]::GetFullPath($ElectronBackendExe)
  )
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "SeraBackend.exe" -and
      $backendPaths -contains [string]$_.ExecutablePath
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-DesktopProcesses {
  $desktopFull = [System.IO.Path]::GetFullPath($ElectronExe)
  $launcherFull = [System.IO.Path]::GetFullPath($DesktopLauncherExe)
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "Sera.exe" -and (
        ([string]$_.CommandLine).Contains($desktopFull) -or
        ([string]$_.CommandLine).Contains($launcherFull)
      )
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Wait-BackendHealthFromPortFile {
  param(
    [string]$PortFile,
    [int]$TimeoutSeconds = 120
  )

  $health = $null
  $portInfo = $null
  for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
    if ((Test-Path $PortFile) -and $null -eq $portInfo) {
      $portInfo = Get-Content $PortFile -Raw | ConvertFrom-Json
    }
    if ($null -ne $portInfo) {
      try {
        $health = Invoke-RestMethod "$($portInfo.base_url)/health"
        if ($health.status -eq "ok") {
          return @{ portInfo = $portInfo; health = $health }
        }
      } catch {
        Start-Sleep -Seconds 1
      }
    } else {
      Start-Sleep -Seconds 1
    }
  }
  if ($null -eq $portInfo) { throw "Backend port file was not created: $PortFile" }
  throw "Backend health failed at $($portInfo.base_url)."
}

$RuntimeDir = Join-Path $BundleDir "runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$portFile = Join-Path $RuntimeDir "backend_port.json"
if (Test-Path $portFile) { Remove-Item -LiteralPath $portFile -Force }
$previousRuntimeDir = $env:SERA_RUNTIME_DIR
$previousLlmProvider = $env:SERA_LLM_PROVIDER
$previousLlmEnvFile = $env:SERA_LLM_ENV_FILE
$env:SERA_RUNTIME_DIR = $RuntimeDir
$env:SERA_LLM_PROVIDER = "local_rule"
$env:SERA_LLM_ENV_FILE = Join-Path $RuntimeDir "offline-smoke-llm.env"
if (Test-Path -LiteralPath $env:SERA_LLM_ENV_FILE) {
  Remove-Item -LiteralPath $env:SERA_LLM_ENV_FILE -Force
}
$process = Start-Process -FilePath $BackendExe -WindowStyle Hidden -PassThru -WorkingDirectory $BundleDir
try {
  $result = Wait-BackendHealthFromPortFile -PortFile $portFile -TimeoutSeconds 120
  if ($process.HasExited) { throw "Backend process exited before health check succeeded." }
  $reviewSummary = Invoke-RestMethod "$($result.portInfo.base_url)/sera-edit/review/summary"
  if ($reviewSummary.total -ne 120) {
    throw "Frozen review summary returned $($reviewSummary.total) tasks instead of 120."
  }
  if (-not $reviewSummary.runtime_acceptance.available -or
      $reviewSummary.runtime_acceptance.experiment_id -ne "runtime_acceptance_core_bilingual_r3_v4_20260826" -or
      $reviewSummary.runtime_acceptance.tasks_passed -ne 120 -or
      $reviewSummary.runtime_acceptance.tasks_failed -ne 0 -or
      $reviewSummary.runtime_acceptance.runs -ne 720) {
    throw "Frozen product-runtime evidence is missing or incomplete."
  }
  $runtimeLatest = Invoke-RestMethod "$($result.portInfo.base_url)/sera-edit/review/tasks?runtime_status=passed"
  if ($runtimeLatest.items.Count -ne 120) {
    throw "Frozen runtime filter returned $($runtimeLatest.items.Count) passed tasks instead of 120."
  }
  $reviewDetail = Invoke-RestMethod "$($result.portInfo.base_url)/sera-edit/review/tasks/pitch_001"
  if (-not $reviewDetail.runtime_acceptance.host_outputs.zh) {
    throw "Frozen Chinese runtime host output is unavailable for pitch_001."
  }
  $reviewArtifact = Invoke-RestMethod -Method Post "$($result.portInfo.base_url)/sera-edit/review/tasks/pitch_001/artifacts/runtime_zh"
  if (-not $reviewArtifact.prepared -or -not (Test-Path -LiteralPath $reviewArtifact.path)) {
    throw "Frozen runtime review artifact could not be prepared."
  }
  $projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
  $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
  $scopeVerifier = Join-Path $projectRoot "scripts\verify_packaged_host_scope.py"
  if (!(Test-Path -LiteralPath $pythonExe) -or !(Test-Path -LiteralPath $scopeVerifier)) {
    throw "Frozen host-scope verifier runtime is unavailable."
  }
  & $pythonExe $scopeVerifier --base-url $result.portInfo.base_url
  if ($LASTEXITCODE -ne 0) {
    throw "Frozen compound_001 host-scope regression failed."
  }
  $meterVerifier = Join-Path $projectRoot "scripts\verify_packaged_meter_roundtrip.py"
  & $pythonExe $meterVerifier --base-url $result.portInfo.base_url
  if ($LASTEXITCODE -ne 0) {
    throw "Frozen meter_001 source-preserving host round-trip failed."
  }
  $voiceVerifier = Join-Path $projectRoot "scripts\verify_packaged_voice_roundtrip.py"
  & $pythonExe $voiceVerifier --base-url $result.portInfo.base_url
  if ($LASTEXITCODE -ne 0) {
    throw "Frozen voice_010/voice_004 staff-local host round-trip failed."
  }
  Write-Host "Staged backend smoke passed at $($result.portInfo.base_url); frontend bundle exists."
  Write-Host "Frozen review evidence smoke passed: 120/120 tasks, 720 runs, Chinese host output prepared."
  Write-Host "Frozen host-scope smoke passed: compound_001 host M2-M3 resolved to M2 only."
  Write-Host "Frozen voice smoke passed: only staff-1 measure 3 moved; staff-2 voice 5/6 lanes stayed stable."
}
finally {
  if (!$process.HasExited) { Stop-Process -Id $process.Id -Force }
  Stop-PackagedBackendProcesses
  $env:SERA_RUNTIME_DIR = $previousRuntimeDir
  $env:SERA_LLM_PROVIDER = $previousLlmProvider
  $env:SERA_LLM_ENV_FILE = $previousLlmEnvFile
}

if (-not $SkipDesktopExe) {
  Stop-DesktopProcesses
  $launcherRuntime = Join-Path $BundleDir "runtime_desktop_launcher"
  New-Item -ItemType Directory -Force -Path $launcherRuntime | Out-Null
  $launcherPortFile = Join-Path $launcherRuntime "backend_port.json"
  if (Test-Path $launcherPortFile) { Remove-Item -LiteralPath $launcherPortFile -Force }
  $previousRuntimeDir = $env:SERA_RUNTIME_DIR
  $previousNoBrowser = $env:SERA_DESKTOP_NO_BROWSER
  $previousDesktopPort = $env:SERA_DESKTOP_PORT
  $env:SERA_RUNTIME_DIR = $launcherRuntime
  $env:SERA_DESKTOP_NO_BROWSER = "1"
  $env:SERA_DESKTOP_PORT = "8100"
  $desktopProcess = Start-Process -FilePath $DesktopLauncherExe -PassThru -WorkingDirectory $BundleDir
  try {
    $launcherResult = Wait-BackendHealthFromPortFile -PortFile $launcherPortFile -TimeoutSeconds 120
    if ($desktopProcess.HasExited) { throw "Desktop launcher process exited before health check succeeded." }
    Write-Host "Desktop launcher exe smoke passed at $($launcherResult.portInfo.base_url)."
  }
  finally {
    if (!$desktopProcess.HasExited) { Stop-Process -Id $desktopProcess.Id -Force -ErrorAction SilentlyContinue }
    Stop-DesktopProcesses
    Stop-PackagedBackendProcesses
    $env:SERA_RUNTIME_DIR = $previousRuntimeDir
    $env:SERA_DESKTOP_NO_BROWSER = $previousNoBrowser
    $env:SERA_DESKTOP_PORT = $previousDesktopPort
  }

  if (Test-Path $ElectronExe) {
    Stop-DesktopProcesses
    $desktopRuntime = Join-Path $env:APPDATA "sera-desktop-shell\runtime"
    New-Item -ItemType Directory -Force -Path $desktopRuntime | Out-Null
    $desktopPortFile = Join-Path $desktopRuntime "backend_port.json"
    if (Test-Path $desktopPortFile) { Remove-Item -LiteralPath $desktopPortFile -Force }
    $electronProcess = Start-Process -FilePath $ElectronExe -PassThru -WorkingDirectory (Split-Path $ElectronExe -Parent)
    try {
      $desktopResult = Wait-BackendHealthFromPortFile -PortFile $desktopPortFile -TimeoutSeconds 120
      if ($electronProcess.HasExited) { throw "Electron desktop process exited before health check succeeded." }
      Write-Host "Electron desktop exe smoke passed at $($desktopResult.portInfo.base_url)."
    }
    finally {
      if (!$electronProcess.HasExited) {
        [void]$electronProcess.CloseMainWindow()
        if (!$electronProcess.WaitForExit(10000)) {
          Stop-Process -Id $electronProcess.Id -Force -ErrorAction SilentlyContinue
        }
      }
      Start-Sleep -Milliseconds 500
      Stop-DesktopProcesses
      Stop-PackagedBackendProcesses
    }
    $leftoverBackends = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
      $_.Name -eq "SeraBackend.exe" -and
      [string]$_.ExecutablePath -eq [System.IO.Path]::GetFullPath($ElectronBackendExe)
    })
    if ($leftoverBackends.Count -ne 0) {
      throw "Electron backend process tree was not released after desktop shutdown."
    }
    if (Test-Path -LiteralPath $desktopPortFile) {
      throw "Electron runtime port file was not removed after desktop shutdown: $desktopPortFile"
    }
  } else {
    throw "Required Electron desktop exe not present: $ElectronExe"
  }
}

Write-Host "Smoke test passed: packaged backend, frontend bundle, and desktop launcher runtime are healthy."
