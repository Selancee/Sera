$projectRoot = "D:\Sera"
$target = Join-Path $projectRoot "run_app.bat"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Sera.lnk"

if (-not (Test-Path -LiteralPath $target)) {
    throw "Missing target: $target"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,138"
$shortcut.Description = "Launch the Sera music generation app"
$shortcut.Save()

Write-Host "Created shortcut: $shortcutPath"
