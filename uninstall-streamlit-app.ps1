Add-Type -AssemblyName System.Windows.Forms

# 1. Remove run app launcher
$launcher = Join-Path $PSScriptRoot 'start-streamlit-app.ps1'
if (Test-Path $launcher) {
    Remove-Item $launcher -Force
    Write-Host '[OK] Removed launcher: start-streamlit-app.ps1'
}

# 2. Remove desktop shortcut
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutQuoted = "C:\Users\teong\Desktop\Start Data Quality App.lnk"
if (Test-Path $shortcutQuoted) {
    Remove-Item $shortcutQuoted -Force
    Write-Host '[OK] Removed desktop shortcut.'
}

# 3. Remove Conda environment
$envName = "dataquality"   # Change if your env is named differently

# Try to detect conda root
$possibleCondaPaths = @(
    "$env:USERPROFILE\anaconda3",
    "$env:USERPROFILE\miniconda3",
    "C:\ProgramData\Anaconda3",
    "C:\ProgramData\Miniconda3"
)
$condaRoot = $null
foreach ($path in $possibleCondaPaths) {
    if (Test-Path "$path\Scripts\activate.bat") {
        $condaRoot = $path
        break
    }
}

if ($condaRoot) {
    $activateBat = "$condaRoot\Scripts\activate.bat"
    Write-Host "[STEP] Removing Conda environment: $envName"
    $cmdLine = "/c ""$activateBat"" && conda env remove -n $envName -y"
	Start-Process -FilePath cmd.exe -ArgumentList $cmdLine -Wait
    Write-Host '[OK] Conda environment removed.'
} else {
    Write-Host '[WARN] Could not find Conda installation. Please remove the environment manually if needed.'
}

[System.Windows.Forms.MessageBox]::Show('Uninstallation complete!','Uninstall Success',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
Write-Host 'Uninstallation complete!'
