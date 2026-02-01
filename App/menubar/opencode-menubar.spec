# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['menubar/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/*.png', 'resources'),
        ('resources/*.icns', 'resources'),
    ],
    hiddenimports=[
        'PyQt6', 
        'PyQt6.QtCore', 
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'pkgutil',  # Required by PyQt6, don't optimize away
    ],
    hookspath=['.'],  # Use custom hooks from current directory
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused Qt modules to reduce size
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
        # Exclude other unused modules
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
    ],
    noarchive=False,
    optimize=1,  # Use optimize=1 instead of 2 to avoid breaking stdlib modules
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='opencode-menubar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols
    upx=True,  # Use UPX compression
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/AppIcon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,  # Strip symbols from binaries
    upx=True,  # Use UPX compression
    upx_exclude=[],
    name='opencode-menubar',
)

app = BUNDLE(
    coll,
    name='OpenCode Token Meter.app',
    icon='resources/AppIcon.icns',
    bundle_identifier='com.opencode.token.menubar',
    info_plist={
        'CFBundleName': 'OpenCode Token Meter',
        'CFBundleDisplayName': 'OpenCode Token Meter',
        'CFBundleIdentifier': 'com.opencode.token.menubar',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,
    },
)
