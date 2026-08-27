param(
  [string]$BackendExe = "$(Resolve-Path (Join-Path $PSScriptRoot '..\dist_desktop\release\win-unpacked\resources\backend\SeraBackend.exe'))"
)

$ErrorActionPreference = "Stop"
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testLeaf = "SeraPackageConfigTest_$([guid]::NewGuid().ToString('N'))"
$testDir = Join-Path $tempRoot $testLeaf
$runtimeDir = Join-Path $testDir "runtime"
$configFile = Join-Path $testDir "llm.env"
$backendPath = [System.IO.Path]::GetFullPath($BackendExe)

if (!(Test-Path -LiteralPath $backendPath -PathType Leaf)) {
  throw "Packaged backend was not found: $backendPath"
}
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

$previousRuntimeDir = $env:SERA_RUNTIME_DIR
$previousConfigFile = $env:SERA_LLM_ENV_FILE
$env:SERA_RUNTIME_DIR = $runtimeDir
$env:SERA_LLM_ENV_FILE = $configFile
$process = Start-Process `
  -FilePath $backendPath `
  -WindowStyle Hidden `
  -PassThru `
  -WorkingDirectory (Split-Path $backendPath -Parent)

try {
  $baseUrl = $null
  $health = $null
  for ($attempt = 0; $attempt -lt 120; $attempt++) {
    $portFile = Join-Path $runtimeDir "backend_port.json"
    if (Test-Path -LiteralPath $portFile) {
      $portInfo = Get-Content -LiteralPath $portFile -Raw | ConvertFrom-Json
      try {
        $health = Invoke-RestMethod "$($portInfo.base_url)/health"
        if ($health.status -eq "ok") {
          $baseUrl = [string]$portInfo.base_url
          break
        }
      }
      catch {
        # Frozen backends can need another cycle during cold start.
      }
    }
    Start-Sleep -Milliseconds 500
  }
  if (!$baseUrl) {
    throw "Packaged backend did not become healthy."
  }

  $dummyKey = "sera-packaged-dummy-secret-not-a-key"
  $body = @{
    provider = "openai"
    model = "packaged-test-model"
    base_url = "https://api.example.test/v1"
    api_key = $dummyKey
    fallback_local = $true
    reasoning_effort = "low"
  } | ConvertTo-Json
  $saved = Invoke-RestMethod `
    -Method Put `
    -Uri "$baseUrl/sera-edit/provider-configuration" `
    -ContentType "application/json" `
    -Body ([Text.Encoding]::UTF8.GetBytes($body))
  $stored = Get-Content -LiteralPath $configFile -Raw
  if ($stored.Contains($dummyKey)) {
    throw "Plaintext API key was written to disk."
  }
  if (!$stored.Contains("SERA_LLM_API_KEY_ENCRYPTED=")) {
    throw "Encrypted credential was not written."
  }
  if ($saved.status.credential_storage -ne "windows_dpapi" -or !$saved.status.available) {
    throw "Packaged credential status is invalid."
  }

  $cleared = Invoke-RestMethod -Method Delete -Uri "$baseUrl/sera-edit/provider-configuration"
  $afterClear = Get-Content -LiteralPath $configFile -Raw
  if ($afterClear.Contains("SERA_LLM_API_KEY_ENCRYPTED=")) {
    throw "Encrypted credential was not removed."
  }

  [ordered]@{
    backend_version = [string]$health.version
    save_available = [bool]$saved.status.available
    credential_storage = [string]$saved.status.credential_storage
    plaintext_on_disk = $stored.Contains($dummyKey)
    cleared_provider = [string]$cleared.status.provider
    encrypted_removed = !$afterClear.Contains("SERA_LLM_API_KEY_ENCRYPTED=")
  } | ConvertTo-Json
}
finally {
  if (!$process.HasExited) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  }
  $env:SERA_RUNTIME_DIR = $previousRuntimeDir
  $env:SERA_LLM_ENV_FILE = $previousConfigFile
  $resolvedTestDir = [System.IO.Path]::GetFullPath($testDir)
  if (
    $resolvedTestDir.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
    (Split-Path $resolvedTestDir -Leaf).StartsWith("SeraPackageConfigTest_")
  ) {
    Remove-Item -LiteralPath $resolvedTestDir -Recurse -Force -ErrorAction SilentlyContinue
  }
}
