[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$ShortcutPath = (Join-Path ([Environment]::GetFolderPath("Desktop")) "Sera.lnk")
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$projectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$target = Join-Path $projectRoot "dist_desktop\release\win-unpacked\Sera.exe"

# A batch-file shortcut creates cmd.exe before Electron can hide any child windows.
# Launch the existing GUI executable directly; do not change the application runtime.
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "Packaged Sera not found: $target. Build the desktop package first, or use run_app.bat from a terminal for source development. The existing shortcut was not changed."
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut([System.IO.Path]::GetFullPath($ShortcutPath))
$shortcut.TargetPath = $target
$shortcut.Arguments = ""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$target,0"
$shortcut.WindowStyle = 1
$shortcut.Description = "Launch the Sera score editing agent"
$shortcut.Save()

Write-Host "Created console-free desktop shortcut: $ShortcutPath"
