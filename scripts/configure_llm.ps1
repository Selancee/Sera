param(
  [ValidateSet("openai", "deepseek", "qwen", "openai-compatible", "local_rule")]
  [string]$Provider = "openai",
  [string]$Model = "gpt-5.6-terra",
  [string]$BaseUrl = "",
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $localBase = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE "AppData\Local" }
  $OutputPath = Join-Path $localBase "Sera\llm.env"
}
$target = [System.IO.Path]::GetFullPath($OutputPath)
$targetDir = Split-Path $target -Parent
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

$baseUrls = @{
  openai = "https://api.openai.com/v1"
  deepseek = "https://api.deepseek.com/v1"
  qwen = "https://dashscope.aliyuncs.com/compatible-mode/v1"
  "openai-compatible" = "https://api.openai.com/v1"
  local_rule = ""
}
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = $baseUrls[$Provider]
}
if ($Provider -ne "local_rule") {
  if ($Model -notmatch '^[A-Za-z0-9._-]+$') {
    throw "Model must contain only letters, numbers, dots, underscores, and hyphens."
  }
  $parsedUrl = $null
  if (-not [System.Uri]::TryCreate($BaseUrl, [System.UriKind]::Absolute, [ref]$parsedUrl) -or $parsedUrl.Scheme -notin @("http", "https")) {
    throw "BaseUrl must be an absolute HTTP(S) URL."
  }
  $secureKey = Read-Host "Enter the $Provider API key (input is hidden)" -AsSecureString
  $apiKey = [System.Net.NetworkCredential]::new("", $secureKey).Password
  if ([string]::IsNullOrWhiteSpace($apiKey) -or $apiKey.Contains("`r") -or $apiKey.Contains("`n")) {
    throw "A non-empty single-line API key is required."
  }
} else {
  $Model = "seraedit_rule_v1"
  $apiKey = ""
}
$structuredOutputs = if ($Provider -eq "openai") { "true" } else { "false" }

if (Test-Path -LiteralPath $target) {
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $backup = "$target.backup_$stamp"
  Copy-Item -LiteralPath $target -Destination $backup -Force
  Write-Host "Previous configuration backed up at: $backup"
}

$lines = @(
  "# Sera per-user LLM configuration. Never commit or share this file."
  "SERA_LLM_PROVIDER=$Provider"
  "SERA_LLM_MODEL=$Model"
  "SERA_LLM_BASE_URL=$BaseUrl"
  "SERA_LLM_API_KEY=$apiKey"
  "SERA_LLM_TIMEOUT_SECONDS=90"
  "SERA_LLM_MAX_OUTPUT_TOKENS=4000"
  "SERA_LLM_REASONING_EFFORT=low"
  "SERA_LLM_STORE=false"
  "SERA_LLM_FALLBACK_LOCAL=true"
  "SERA_LLM_STRUCTURED_OUTPUTS=$structuredOutputs"
)
[System.IO.File]::WriteAllText($target, ($lines -join [Environment]::NewLine) + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
$apiKey = $null

Write-Host "Sera LLM configuration written to: $target"
Write-Host "Provider: $Provider"
Write-Host "Model: $Model"
Write-Host "Restart Sera Desktop before testing the provider."
