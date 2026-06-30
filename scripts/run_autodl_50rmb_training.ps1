param(
    [Parameter(Mandatory = $true)]
    [string]$SshTarget,
    [int]$Port = 22,
    [string]$IdentityFile = "",
    [string]$RepoUrl = "https://github.com/Selancee/Sera.git",
    [string]$RemoteScript = "/root/autodl_train_50rmb.sh",
    [string]$Workdir = "/root/Sera",
    [string]$DataRoot = "/root/autodl-tmp/sera_data",
    [string]$RunRoot = "/root/autodl-tmp/sera_runs",
    [string]$ModelRoot = "/root/autodl-tmp/sera_models",
    [int]$BudgetRmb = 50,
    [double]$GpuRmbPerHour = 1.98,
    [int]$ReservedRmb = 8,
    [int]$MaxRunHours = 20,
    [int]$MaxExamples = 1200,
    [int]$MaxFiles = 1200,
    [int]$Epochs = 6
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$LocalScript = Join-Path $ProjectRoot "training\autodl_train_50rmb.sh"
if (-not (Test-Path -LiteralPath $LocalScript)) {
    throw "Missing local script: $LocalScript"
}
if (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue)) {
    throw "ssh.exe was not found. Install OpenSSH Client or run the script manually in AutoDL."
}
if (-not (Get-Command scp.exe -ErrorAction SilentlyContinue)) {
    throw "scp.exe was not found. Install OpenSSH Client or upload the script manually."
}

$sshArgs = @()
$scpArgs = @()
if ($Port -ne 22) {
    $sshArgs += @("-p", [string]$Port)
    $scpArgs += @("-P", [string]$Port)
}
if (-not [string]::IsNullOrWhiteSpace($IdentityFile)) {
    $sshArgs += @("-i", $IdentityFile)
    $scpArgs += @("-i", $IdentityFile)
}

Write-Host "[Sera] Uploading $LocalScript -> ${SshTarget}:$RemoteScript"
& scp.exe @scpArgs $LocalScript "${SshTarget}:$RemoteScript"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload AutoDL training script."
}

$envAssignments = @(
    "REPO_URL='$RepoUrl'",
    "WORKDIR='$Workdir'",
    "DATA_ROOT='$DataRoot'",
    "RUN_ROOT='$RunRoot'",
    "MODEL_ROOT='$ModelRoot'",
    "BUDGET_RMB='$BudgetRmb'",
    "GPU_RMB_PER_HOUR='$GpuRmbPerHour'",
    "RESERVED_RMB='$ReservedRmb'",
    "MAX_RUN_HOURS='$MaxRunHours'",
    "MAX_EXAMPLES='$MaxExamples'",
    "MAX_FILES='$MaxFiles'",
    "EPOCHS='$Epochs'"
) -join " "
$remoteCommand = "chmod +x $RemoteScript; $envAssignments bash $RemoteScript"

Write-Host "[Sera] Starting AutoDL 50 RMB training run..."
Write-Host "[Sera] Target: $SshTarget"
Write-Host "[Sera] Budget cap: RMB $BudgetRmb, max hours: $MaxRunHours"
& ssh.exe @sshArgs $SshTarget $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Remote training command failed. Check AutoDL output above; partial model files may still be in $ModelRoot."
}

Write-Host ""
Write-Host "[Sera] Remote training command finished."
Write-Host "[Sera] Use scripts\fetch_autodl_model.ps1 with RemoteRunDir from the output to copy the checkpoint into D:\Sera\models."
