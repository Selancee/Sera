param(
  [string]$Python = ".\.venv\Scripts\python.exe",
  [switch]$SkipElectronPackage,
  [switch]$SkipArtifactBuild
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$RootFull = [System.IO.Path]::GetFullPath([string]$Root)

function Stop-SeraPackagedProcesses {
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -in @("Sera.exe", "SeraBackend.exe") -and
      ([string]$_.CommandLine).Contains($RootFull)
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Stop-SeraPackagedProcesses

if (-not $SkipArtifactBuild) {
  Write-Host "Building Sera frontend..."
  Push-Location "$Root\frontend"
  npm.cmd run build
  Pop-Location

  Write-Host "Building Sera backend executable..."
  & $Python "$Root\packaging\backend\build_backend_exe.py"

  Write-Host "Building Sera desktop launcher executable..."
  & $Python "$Root\packaging\desktop\build_desktop_exe.py"
} else {
  Write-Host "Reusing already-built frontend, backend, and desktop launcher artifacts."
  foreach ($requiredArtifact in @(
    "$Root\frontend\dist\index.html",
    "$Root\dist\SeraBackend\SeraBackend.exe",
    "$Root\dist\Sera\Sera.exe"
  )) {
    if (!(Test-Path -LiteralPath $requiredArtifact -PathType Leaf)) {
      throw "Required reusable artifact is missing: $requiredArtifact"
    }
  }
}

$DesktopRoot = Join-Path $Root "dist_desktop"
$BackendOut = Join-Path $DesktopRoot "backend"
$ElectronOut = Join-Path $DesktopRoot "electron"
$FrontendOut = Join-Path $DesktopRoot "frontend\dist"
$ReleaseOut = Join-Path $DesktopRoot "release"
$DesktopLauncherExe = Join-Path $DesktopRoot "Sera.exe"
$DesktopLauncherRuntime = Join-Path $DesktopRoot "_internal"

function Reset-StagingDirectory {
  param([string]$Path)

  $desktopFull = [System.IO.Path]::GetFullPath([string]$DesktopRoot)
  $targetFull = [System.IO.Path]::GetFullPath([string]$Path)
  if (-not $targetFull.StartsWith($desktopFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to reset staging path outside dist_desktop: $targetFull"
  }
  if (Test-Path -LiteralPath $targetFull) {
    for ($attempt = 1; $attempt -le 5; $attempt++) {
      try {
        Remove-Item -LiteralPath $targetFull -Recurse -Force -ErrorAction Stop
        break
      } catch {
        if ($attempt -eq 5) {
          $remainingFiles = @(Get-ChildItem -LiteralPath $targetFull -File -Force -Recurse -ErrorAction SilentlyContinue)
          $unsafeRemainingFiles = @($remainingFiles | Where-Object {
            $_.Name -notin @("builder-debug.yml", "builder-effective-config.yaml")
          })
          if ($unsafeRemainingFiles.Count -eq 0) {
            Write-Warning "Reusing a locked but empty staging directory: $targetFull"
            break
          }
          throw
        }
        Stop-SeraPackagedProcesses
        Start-Sleep -Milliseconds 500
      }
    }
  }
  New-Item -ItemType Directory -Force -Path $targetFull | Out-Null
}

Reset-StagingDirectory $BackendOut
Reset-StagingDirectory $ElectronOut
Reset-StagingDirectory $FrontendOut
Reset-StagingDirectory $ReleaseOut
Reset-StagingDirectory $DesktopLauncherRuntime

Copy-Item -Recurse -Force "$Root\dist\SeraBackend\*" $BackendOut
Copy-Item -Recurse -Force "$Root\dist\Sera\*" $DesktopRoot
Copy-Item -Recurse -Force "$Root\electron\*" "$ElectronOut"
Copy-Item -Recurse -Force "$Root\frontend\dist\*" "$FrontendOut"

Write-Host "Desktop bundle staged at $DesktopRoot"
$electronBuildError = ""
if (-not $SkipElectronPackage) {
  Write-Host "Installing Electron packaging dependencies..."
  Push-Location "$Root\electron"
  try {
    $previousElectronSkip = $env:ELECTRON_SKIP_BINARY_DOWNLOAD
    $previousElectronCache = $env:ELECTRON_CACHE
    $previousElectronBuilderCache = $env:ELECTRON_BUILDER_CACHE
    $env:ELECTRON_SKIP_BINARY_DOWNLOAD = "1"
    $env:ELECTRON_CACHE = Join-Path $Root ".cache\electron"
    $env:ELECTRON_BUILDER_CACHE = Join-Path $Root ".cache\electron-builder"
    npm.cmd install --no-audit --no-fund --ignore-scripts
    $env:ELECTRON_SKIP_BINARY_DOWNLOAD = $previousElectronSkip
    Write-Host "Building Windows Electron executable..."
    npm.cmd run dist
  } catch {
    $electronBuildError = $_.Exception.Message
    Write-Warning "Electron packaging failed; keeping PyInstaller desktop launcher as the release exe. $electronBuildError"
  } finally {
    $env:ELECTRON_SKIP_BINARY_DOWNLOAD = $previousElectronSkip
    $env:ELECTRON_CACHE = $previousElectronCache
    $env:ELECTRON_BUILDER_CACHE = $previousElectronBuilderCache
    Pop-Location
  }
}

$releaseExe = Get-ChildItem -Path $ReleaseOut -Recurse -Filter "Sera.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
$portableExe = Get-ChildItem -Path $ReleaseOut -Filter "Sera-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
$manifest = [ordered]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  root = [string]$Root
  staged_bundle = [string]$DesktopRoot
  backend_exe = (Join-Path $BackendOut "SeraBackend.exe")
  frontend_index = (Join-Path $FrontendOut "index.html")
  desktop_launcher_exe = [string]$DesktopLauncherExe
  release_dir = [string]$ReleaseOut
  win_unpacked_exe = if ($releaseExe) { [string]$releaseExe.FullName } else { "" }
  portable_exe = if ($portableExe) { [string]$portableExe.FullName } else { "" }
  electron_packaged = [bool](-not $SkipElectronPackage -and ($releaseExe -or $portableExe))
  electron_build_error = $electronBuildError
}
$manifestPath = Join-Path $DesktopRoot "release_manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $manifestPath

Write-Host "Desktop bundle staged at $DesktopRoot"
Write-Host "Release manifest written to $manifestPath"
if (-not $SkipElectronPackage -and -not ($releaseExe -or $portableExe)) {
  throw "Electron packaging did not produce a local Sera desktop application. $electronBuildError"
}
if (!(Test-Path $DesktopLauncherExe)) {
  throw "Packaging did not produce the legacy local-server launcher used by smoke tests."
}
Write-Host "Desktop launcher exe: $DesktopLauncherExe"
if ($releaseExe) { Write-Host "Unpacked desktop exe: $($releaseExe.FullName)" }
if ($portableExe) { Write-Host "Portable desktop exe: $($portableExe.FullName)" }
