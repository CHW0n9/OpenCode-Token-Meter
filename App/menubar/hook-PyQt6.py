"""
Custom PyInstaller hook for PyQt6 to exclude unnecessary modules.
This hook takes precedence over the default PyQt6 hook.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

# Only include the modules we actually use
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

# Explicitly exclude all modules we don't need
excludedimports = [
    'PyQt6.QtNetwork',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngine',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebChannel',
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
]

# Don't collect data files for excluded modules
datas = []
