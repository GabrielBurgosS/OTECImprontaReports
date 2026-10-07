# -*- mode: python ; coding: utf-8 -*-
# Build with:  .\build.ps1   (or: pyinstaller OTECReportes.spec)
# ONEFILE=1 (default) -> dist/OTEC Reportes.exe ; ONEFILE=0 -> dist/OTEC Reportes/ (for the installer)
import os
from PyInstaller.utils.hooks import collect_submodules

ONEFILE = os.environ.get('ONEFILE', '1') == '1'
NAME = 'OTEC Reportes'

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/plantillas/*.xlsx', 'assets/plantillas'),
        ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=collect_submodules('keyring.backends') + ['win32timezone'],
    excludes=['pytest', 'PIL', 'IPython', 'matplotlib', 'notebook', 'xlwings'],
    noarchive=False,
)
# Selenium ships selenium-manager for Linux and macOS too; only the Windows one is needed
a.datas = [d for d in a.datas if not any(part in d[0].replace(os.sep, '/') for part in
                                          ('webdriver/common/linux/', 'webdriver/common/macos/'))]
pyz = PYZ(a.pure)

exe_options = dict(
    name=NAME,
    icon='assets/icon.ico',
    version='installer/version_info.txt',
    console=False,
    upx=False,  # UPX-packed executables trigger more antivirus false positives
    disable_windowed_traceback=False,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **exe_options)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)
