# -*- mode: python ; coding: utf-8 -*-
"""
Unified PyInstaller spec file for OpenCode Token Meter
Supports both Windows and macOS with platform detection
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Get absolute paths
project_root = os.path.dirname(os.path.abspath(SPEC))
app_dir = os.path.join(project_root, 'App')
menubar_dir = os.path.join(app_dir, 'menubar')
agent_dir = os.path.join(app_dir, 'agent')
resources_dir = os.path.join(menubar_dir, 'resources')

# Add paths to sys.path for module collection
import sys
sys.path.insert(0, menubar_dir)
sys.path.insert(0, agent_dir)

# Collect all agent submodules automatically
agent_submodules = collect_submodules('agent')
menubar_submodules = collect_submodules('menubar')

print(f"Collected {len(agent_submodules)} agent submodules")
print(f"Collected {len(menubar_submodules)} menubar submodules")

# Platform detection
IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'

# Icon file - use absolute paths to ensure PyInstaller can find them during build
if IS_WINDOWS:
    icon_file = os.path.abspath(os.path.join(resources_dir, 'AppIcon.ico'))
    if not os.path.exists(icon_file):
        print(f"WARNING: Windows icon not found at {icon_file}")
        icon_file = None
elif IS_MACOS:
    icon_file = os.path.abspath(os.path.join(resources_dir, 'AppIcon.icns'))
    if not os.path.exists(icon_file):
        print(f"WARNING: macOS icon not found at {icon_file}")
        icon_file = None
else:
    icon_file = None

# Main analysis for menubar app (includes agent as embedded module)
a = Analysis(
    [os.path.join(menubar_dir, 'menubar', '__main__.py')],
    pathex=[menubar_dir, agent_dir],
    binaries=[],
    datas=[
        # Only resources are needed as external data
        (resources_dir, 'resources'),
    ],
    hiddenimports=[
        # Use collected submodules
        *agent_submodules,
        *menubar_submodules,
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # Standard library
        'sqlite3',
        'json',
        'socket',
        'threading',
        'asyncio',
        'datetime',
        'stat',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # PyQt6 unused modules
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        'PyQt6.QtNetwork',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuickWidgets',
        'PyQt6.QtSql',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.Qt3D',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDBus',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtLocation',
        'PyQt6.QtNfc',
        'PyQt6.QtPositioning',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtTextToSpeech',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
        # ICU internationalization (32MB saved)
        'icu',
        'PyQt6.QtCore.icu',
        'PyQt6.Qt6.translations',
        # Qt plugins not needed
        'PyQt6.Qt6.plugins.imageformats',
        'PyQt6.Qt6.plugins.iconengines',
        # Other unused modules
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'PIL',
        'tkinter',
        '_tkinter',
        # Standard library unused modules
        'unittest',
        'pydoc',
        'pydoc_data',
        'email',
        'http',
        'multiprocessing',
        'concurrent',
        'test',
        'distutils',
        'lib2to3',
        'pdb',
        'doctest',
        'curses',
        'idlelib',
        'turtledemo',
        # Qt specific exclusions
        'Qt6.QtPdf',
        'Qt6.QtNetwork',
        'Qt6.QtSvg',
        'Qt6.Qt6.translations',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=2,  # Remove assert and docstrings for smaller size
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific build configurations
if IS_WINDOWS:
    # Windows: Single EXE with embedded agent
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
    name='OpenCodeTokenMeter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols to reduce size
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if icon_file and os.path.exists(icon_file) else None,
)

elif IS_MACOS:
    # macOS: .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='OpenCode Token Meter',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,  # Strip debug symbols to reduce size
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file if icon_file and os.path.exists(icon_file) else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,  # Strip debug symbols to reduce size
        upx=True,
        upx_exclude=[],
        name='OpenCode Token Meter',
    )

    app = BUNDLE(
        coll,
        name='OpenCode Token Meter.app',
        icon=icon_file if icon_file and os.path.exists(icon_file) else None,
        bundle_identifier='com.opencode.tokenmeter',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleDocumentTypes': [],
            'LSUIElement': False,  # Show in Dock
        },
    )
