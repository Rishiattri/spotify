# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the modern (PyWebView) Spotify-style frontend.

Build:
    pyinstaller app_modern.spec --clean --noconfirm

Output:
    dist\\Spotify\\Spotify.exe        (folder build — recommended)
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

ICON = 'app.ico' if os.path.exists('app.ico') else None

# Ship the UI assets and config next to the exe.
datas = [
    ('ui', 'ui'),
]
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))

# pywebview ships data files (HTML/JS shims) we must bundle.
datas += collect_data_files('webview')

hiddenimports = [
    'pyautogui',
    'pygetwindow',
    'pynput',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'PIL',
    'PIL._tkinter_finder',
    'pystray',
    'pystray._win32',
    'webview',
    'webview.platforms.edgechromium',
    'webview.platforms.winforms',
    'webview.platforms.mshtml',
    'clr_loader',
]
hiddenimports += collect_submodules('webview')

a = Analysis(
    ['app_modern.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pytest', 'pandas', 'scipy', 'IPython', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Spotify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Spotify',
)
