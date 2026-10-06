param([string]$OutputDirectory = '')

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements.txt first. See README.md.'
}
$releaseVersion = & $pythonPath -c 'from version import VERSION; print(VERSION)'
$releaseDir = if ($OutputDirectory) { [System.IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $PSScriptRoot "release\$releaseVersion" }
& $pythonPath -m unittest -v test_kana.py test_app.py
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
$originalBuildPath = $env:PATH
try {
    # Prevent unrelated native tools from supplying incompatible ICU/UCRT DLLs.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    & $pythonPath -m PyInstaller --noconfirm --clean --onefile --windowed --name KanaStudio --icon icon.ico --version-file version_info.txt --add-data 'assets;assets' --add-data 'LICENSE;.' --add-data 'COPYRIGHT;.' --add-data 'THIRD-PARTY.md;.' --add-data 'licenses;licenses' --distpath $releaseDir app.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
} finally {
    $env:PATH = $originalBuildPath
}
$exePath = Join-Path $releaseDir 'KanaStudio.exe'
$smokePath = if ($OutputDirectory) { Join-Path $releaseDir 'verification' } else { Join-Path $PSScriptRoot 'qa\build-check' }
$process = Start-Process -FilePath $exePath -ArgumentList '--smoke-test', "`"$smokePath`"" -PassThru -WindowStyle Hidden -Wait
if ($process.ExitCode -ne 0) { throw 'Packaged application check failed.' }
Copy-Item -LiteralPath (Join-Path $smokePath 'preview.png') -Destination (Join-Path $releaseDir 'preview.png')
Copy-Item -LiteralPath (Join-Path $smokePath 'preview-light.png') -Destination (Join-Path $releaseDir 'preview-light.png')
& $pythonPath -B package_release.py --output-dir $releaseDir
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
Write-Host "Ready: $exePath"
