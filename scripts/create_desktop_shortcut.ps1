$projectRoot = "D:\Sera"
$target = Join-Path $projectRoot "run_app.bat"
$packagedIcon = Join-Path $projectRoot "dist_desktop\release\win-unpacked\Sera.exe"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Sera.lnk"

if (-not (Test-Path -LiteralPath $target)) {
    throw "Missing target: $target"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = if (Test-Path -LiteralPath $packagedIcon) { $packagedIcon } else { "$env:SystemRoot\System32\SHELL32.dll,138" }
$shortcut.Description = "Launch the Sera score editing agent"
$shortcut.Save()

Write-Host "Created shortcut: $shortcutPath"
