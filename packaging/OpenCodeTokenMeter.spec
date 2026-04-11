# -*- mode: python ; coding: utf-8 -*-
"""
Unified PyInstaller spec file for OpenCode Token Meter - pywebview version
Supports both Windows and macOS with platform detection
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Get absolute paths
spec_dir = os.path.dirname(os.path.abspath(SPEC))
project_root = os.path.dirname(spec_dir)
app_dir = os.path.join(project_root, 'App')
webview_ui_dir = os.path.join(app_dir, 'webview_ui')
agent_dir = os.path.join(app_dir, 'agent')
web_dir = os.path.join(webview_ui_dir, 'web')
# Use assets from web directory as the source for resources (icons)
resources_dir = os.path.join(web_dir, 'assets')

# Read version from VERSION file
version_file = os.path.join(project_root, 'VERSION')
try:
    with open(version_file, 'r') as f:
        APP_VERSION = f.read().strip()
except Exception:
    APP_VERSION = '1.1.3'  # Fallback version

# Add paths to sys.path for module collection
sys.path.insert(0, app_dir)
sys.path.insert(0, webview_ui_dir)
sys.path.insert(0, agent_dir)

# Collect all agent submodules automatically
agent_submodules = collect_submodules('agent')

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

# Main analysis for webview_ui app (includes agent as embedded module)
hiddenimports = [
    # Agent submodules
    *agent_submodules,
    # pywebview core modules
    'webview',
    'webview.http',
    # Cross-platform modules used by the app
    'pyperclip',
    # Pillow
    'PIL',
    'PIL.Image',
    # Settings and config
    'backend.settings',
    'backend.api',
    'backend.db_read',
    'backend.bridge',
    'backend.utils',
    'agent.config',
    'agent.db',
    'agent.scanner',
    # Standard library
    'sqlite3',
    'json',
    'socket',
    'threading',
    'asyncio',
    'datetime',
    'stat',
    'copy',
    'tempfile',
    'platform',
    'shutil',
    'pathlib',
    # http modules required by pywebview
    'wsgiref',
    'wsgiref.simple_server',
    'wsgiref.handlers',
]

excludes = [
    # PyQt6 - excluded as we use pywebview now
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'PySide6',
    'PySide2',
    # Unused modules
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'jupyter',
    'notebook',
    'tkinter',
    '_tkinter',
    # Standard library unused modules (keep if in datas)
    'pydoc',
    'pydoc_data',
    'test',
    #'distutils',
    'lib2to3',
    'pdb',
    'doctest',
    'curses',
    'idlelib',
    'turtledemo',
]

if IS_WINDOWS:
    hiddenimports += [
        'webview.platforms.winforms',
        'pystray',
        'pystray._util',
        'pystray._util.win32',
        'win10toast',
    ]
    excludes += ['rumps', 'AppKit', 'Foundation', 'PyObjCTools', 'dbus', 'gi']
elif IS_MACOS:
    hiddenimports += [
        'webview.platforms.cocoa',
        'webview.platforms.darwin',
        'rumps',
        'AppKit',
        'Foundation',
        'PyObjCTools',
    ]
    excludes += ['pystray', 'win10toast', 'dbus', 'gi']
elif IS_LINUX:
    hiddenimports += [
        'webview.platforms.gtk',
        'dbus',
        'dbus.service',
        'dbus.mainloop.glib',
        'gi',
        'gi.repository',
        'gi.repository.GLib',
    ]
    excludes += ['pystray', 'rumps', 'win10toast', 'AppKit', 'Foundation', 'PyObjCTools', 'PIL.ImageTk', 'PIL._imagingtk', 'pkg_resources', 'setuptools']

a = Analysis(
    [os.path.join(webview_ui_dir, '__main__.py')],
    pathex=[app_dir, webview_ui_dir, agent_dir],
    binaries=[],
    datas=[
        # Web frontend files
        (web_dir, 'webview_ui/web'),
        # Resources (icons)
        (resources_dir, 'resources'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[os.path.join(project_root, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
        strip=False,  # Windows build env may not have strip tool
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
            'LSUIElement': True,  # Hide from Dock (menubar-only app)
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': 'macOS',
        },
    )

else:
    # Linux: onedir bundle (tray mode)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='OpenCode Token Meter',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='OpenCode Token Meter',
    )
