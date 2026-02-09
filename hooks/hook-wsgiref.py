# PyInstaller hook for wsgiref stdlib module
# This forces inclusion of the wsgiref package which is needed by pywebview

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

# Get path to wsgiref package in stdlib
stdlib_path = os.path.dirname(os.__file__)
wsgiref_path = os.path.join(stdlib_path, 'wsgiref')

# Collect all wsgiref package files as datas
datas = []
if os.path.isdir(wsgiref_path):
    for filename in os.listdir(wsgiref_path):
        if filename.endswith('.py'):
            src = os.path.join(wsgiref_path, filename)
            datas.append((src, 'wsgiref'))

# Also include all submodules
hiddenimports = collect_submodules('wsgiref')
