<#
Builds OTEC Reportes.
  .\build.ps1             -> tests + dist\OTEC Reportes.exe (single file) + zip + SHA256
  .\build.ps1 -Installer  -> tests + dist\OTEC Reportes\ (folder) + installer (needs Inno Setup 6)
  .\build.ps1 -SkipTests  -> skip the test suite (not recommended)
#>
param([switch]$Installer, [switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = '.\.venv\Scripts\python.exe'
$version = (Select-String -Path 'src\paths.py' -Pattern "APP_VERSION = '(.+)'").Matches[0].Groups[1].Value

if (-not $SkipTests) {
    Write-Host '== Running tests ==' -ForegroundColor Cyan
    & $python -m pytest -p no:cacheprovider -p no:faulthandler
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed: build aborted.' }
}

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
$env:ONEFILE = if ($Installer) { '0' } else { '1' }
Write-Host "== PyInstaller (ONEFILE=$env:ONEFILE) ==" -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --clean OTECReportes.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

if ($Installer) {
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
              "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) { throw 'Inno Setup 6 is not installed (https://jrsoftware.org/isinfo.php).' }
    & $iscc 'installer\OTECReportes.iss'
    $artifact = Get-ChildItem 'installer\Output\*.exe' | Select-Object -First 1
} else {
    $exe = 'dist\OTEC Reportes.exe'
    $artifact = Get-Item "dist\OTEC Reportes $version.zip" -ErrorAction SilentlyContinue
    Compress-Archive -Path $exe, 'docs\MANUAL_DE_USUARIO.pdf' -DestinationPath "dist\OTEC Reportes $version.zip" -Force
    $artifact = Get-Item "dist\OTEC Reportes $version.zip"
}
$hash = (Get-FileHash $artifact.FullName -Algorithm SHA256).Hash
"$hash  $($artifact.Name)" | Set-Content "$($artifact.FullName).sha256"
Write-Host "== Done: $($artifact.FullName) ($([math]::Round($artifact.Length / 1MB, 1)) MB) ==" -ForegroundColor Green
Write-Host "SHA256 $hash"
