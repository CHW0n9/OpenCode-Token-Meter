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

# Platform detection
IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

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
        # Menubar resources
        (os.path.join(menubar_dir, 'menubar'), 'menubar'),
        (resources_dir, 'resources'),
        # Agent module (embedded)
        (os.path.join(agent_dir, 'agent'), 'agent'),
    ],
    hiddenimports=[
        # Menubar imports
        'menubar',
        'menubar.app',
        'menubar.settings',
        'menubar.uds_client',
        'menubar.utils.ui_helpers',
        'menubar.windows',
        'menubar.windows.main_stats_window',
        'menubar.windows.details_dialog',
        'menubar.windows.settings_dialog',
        'menubar.windows.custom_range_dialog',
        'menubar.windows.custom_range_stats_dialog',
        'menubar.windows.model_update_dialog',
        # Agent imports (embedded) - all submodules must be listed
        'agent',
        'agent.config',
        'agent.db',
        'agent.scanner',
        'agent.uds_server',
        'agent.exporter',
        'agent.__main__',
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
        strip=False,
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
        strip=False,
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
        strip=False,
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
            'LSUIElement': True,  # Hide from Dock
        },
    )

else:
    # Linux: Single executable
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
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
