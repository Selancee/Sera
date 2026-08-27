param(
  [string]$SourcePath = "D:\Desktop\2026\121.mxl",
  [string]$BackendExe = "$(Resolve-Path (Join-Path $PSScriptRoot '..\dist_desktop\release\win-unpacked\resources\backend\SeraBackend.exe'))",
  [int]$ExpectedChangedEvents = 16
)

$ErrorActionPreference = "Stop"
$runtimeDir = Join-Path (Split-Path $BackendExe -Parent) "source_preservation_runtime"
$portFile = Join-Path $runtimeDir "backend_port.json"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
if (Test-Path -LiteralPath $portFile) {
  Remove-Item -LiteralPath $portFile -Force
}

function Invoke-JsonPost {
  param(
    [string]$Uri,
    [object]$Payload
  )

  $json = $Payload | ConvertTo-Json -Depth 100 -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  Invoke-RestMethod -Method Post -Uri $Uri -ContentType "application/json; charset=utf-8" -Body $bytes
}

function Get-MusicXmlCounts {
  param([xml]$Document)

  [ordered]@{
    notes = @($Document.SelectNodes("//note")).Count
    rests = @($Document.SelectNodes("//note/rest")).Count
    note_dynamics = @($Document.SelectNodes("//note/notations/dynamics/*")).Count
    direction_dynamics = @($Document.SelectNodes("//direction/direction-type/dynamics/*")).Count
    defaults = @($Document.SelectNodes("//defaults")).Count
    page_layout = @($Document.SelectNodes("//page-layout")).Count
    prints = @($Document.SelectNodes("//print")).Count
    system_layout = @($Document.SelectNodes("//system-layout")).Count
  }
}

if (!(Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
  throw "Source score was not found: $SourcePath"
}
if (!(Test-Path -LiteralPath $BackendExe -PathType Leaf)) {
  throw "Packaged backend was not found: $BackendExe"
}

$previousRuntimeDir = $env:SERA_RUNTIME_DIR
$env:SERA_RUNTIME_DIR = $runtimeDir
$process = Start-Process -FilePath $BackendExe -WindowStyle Hidden -PassThru -WorkingDirectory (Split-Path $BackendExe -Parent)

try {
  $baseUrl = $null
  for ($attempt = 0; $attempt -lt 120; $attempt++) {
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
        # The frozen backend can need another second during cold start.
      }
    }
    Start-Sleep -Seconds 1
  }
  if (!$baseUrl) {
    throw "Packaged backend did not become healthy."
  }

  $providerStatus = Invoke-RestMethod "$baseUrl/sera-edit/provider-status"
  $sensitiveStatusFields = @(
    $providerStatus.PSObject.Properties.Name |
      Where-Object { $_ -in @("api_key", "access_token", "authorization", "secret") }
  )
  if ($sensitiveStatusFields.Count -gt 0) {
    throw "Provider status exposed credential fields: $($sensitiveStatusFields -join ', ')"
  }
  if (![string]$providerStatus.provider -or [string]$providerStatus.transport -notin @("local", "http")) {
    throw "Provider status is incomplete or invalid."
  }

  $created = Invoke-JsonPost "$baseUrl/integrations/musescore-file-sessions" @{
    source_path = $SourcePath
    source_name = Split-Path $SourcePath -Leaf
    host_context = @{
      bridge = "packaged_source_preservation_test"
      selection = @{ is_range = $true; start_measure = 1; end_measure = 1 }
    }
  }
  $sessionId = [string]$created.session.session_id
  $generated = Invoke-JsonPost "$baseUrl/sera-edit/generate-preview" @{
    score_document = $created.score_document
    instruction = "Transpose measure 1 up by a major second while preserving rhythm."
    target_scope = @{ measures = @(1) }
    protected_scope = @{ measures = @(2, 3, 4, 5, 6, 7, 8, 9) }
  }
  if ($generated.status -ne "generated") {
    throw "Generation status: $($generated.status) - $($generated.reason)"
  }
  $previewReport = $generated.preview.validation_report
  if (@($previewReport.warnings).Count -gt 0) {
    Write-Host "Preview warnings: $(@($previewReport.warnings) | ConvertTo-Json -Depth 10 -Compress)"
  }
  if ($previewReport.status -in @("invalid", "unsupported") -or @($previewReport.errors).Count -gt 0) {
    throw "Preview validation failed: $(@($previewReport.errors) -join ' | ')"
  }

  $applied = Invoke-JsonPost "$baseUrl/sera-edit/apply" @{
    score_document = $created.score_document
    patch = $generated.patch
  }
  if (!$applied.committed) {
    throw "Patch was not committed: $($applied.rollback_reason)"
  }

  $exported = Invoke-JsonPost "$baseUrl/integrations/notation-sessions/$sessionId/export" @{
    score_document = $applied.score_document
    expected_revision = 0
  }
  $sourceText = [string](Invoke-WebRequest -UseBasicParsing "$baseUrl/integrations/notation-sessions/$sessionId/artifacts/0").Content
  $revisionText = [string](Invoke-WebRequest -UseBasicParsing "$baseUrl/integrations/notation-sessions/$sessionId/artifacts/1").Content
  [xml]$sourceXml = $sourceText
  [xml]$revisionXml = $revisionText
  $sourceCounts = Get-MusicXmlCounts $sourceXml
  $revisionCounts = Get-MusicXmlCounts $revisionXml
  $sourceValidationErrors = @($created.validation_report.errors)
  $revisionValidationErrors = @($exported.validation_report.errors)
  $validationErrorsUnchanged = ($sourceValidationErrors | ConvertTo-Json -Compress) -ceq ($revisionValidationErrors | ConvertTo-Json -Compress)

  $sourceNonTarget = @($sourceXml.SelectNodes('//measure[@number!="1"]'))
  $revisionNonTarget = @($revisionXml.SelectNodes('//measure[@number!="1"]'))
  $nonTargetEquivalent = $sourceNonTarget.Count -eq $revisionNonTarget.Count
  if ($nonTargetEquivalent) {
    for ($index = 0; $index -lt $sourceNonTarget.Count; $index++) {
      if ($sourceNonTarget[$index].OuterXml -cne $revisionNonTarget[$index].OuterXml) {
        $nonTargetEquivalent = $false
        break
      }
    }
  }
  $countsEqual = ($sourceCounts | ConvertTo-Json -Compress) -ceq ($revisionCounts | ConvertTo-Json -Compress)

  $result = [ordered]@{
    packaged_backend = $baseUrl
    backend_version = [string]$health.version
    provider = [string]$providerStatus.provider
    provider_model = [string]$providerStatus.model
    provider_mode = [string]$providerStatus.mode
    provider_transport = [string]$providerStatus.transport
    provider_available = [bool]$providerStatus.available
    provider_credential_fields_exposed = ($sensitiveStatusFields.Count -gt 0)
    session_id = $sessionId
    export_mode = [string]$exported.export_mode
    changed_event_count = [int]$exported.source_preservation.changed_event_count
    changed_fields = @($exported.source_preservation.changed_fields)
    preview_status = [string]$previewReport.status
    preview_warnings = @($previewReport.warnings)
    source_validation_errors = $sourceValidationErrors.Count
    revision_validation_errors = $revisionValidationErrors.Count
    validation_errors_unchanged = $validationErrorsUnchanged
    source_counts = $sourceCounts
    revision_counts = $revisionCounts
    counts_equal = $countsEqual
    non_target_measure_count = $sourceNonTarget.Count
    non_target_measures_equivalent = $nonTargetEquivalent
    revision_path = [string]$exported.output_path
  }
  $result | ConvertTo-Json -Depth 10

  if (
    $exported.export_mode -ne "source_preserving_patch" -or
    [int]$exported.source_preservation.changed_event_count -ne $ExpectedChangedEvents -or
    !$countsEqual -or
    !$nonTargetEquivalent -or
    !$validationErrorsUnchanged
  ) {
    throw "Packaged semantic source-preservation assertions failed."
  }
}
finally {
  $env:SERA_RUNTIME_DIR = $previousRuntimeDir
  $backendPath = [System.IO.Path]::GetFullPath($BackendExe)
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "SeraBackend.exe" -and [string]$_.ExecutablePath -eq $backendPath } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
