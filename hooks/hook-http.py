# PyInstaller hook for http stdlib module
# This forces inclusion of the http package which is needed by pywebview

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

# Get path to http package in stdlib
stdlib_path = os.path.dirname(os.__file__)
http_path = os.path.join(stdlib_path, 'http')

# Collect all http package files as datas
datas = []
if os.path.isdir(http_path):
    for filename in os.listdir(http_path):
        if filename.endswith('.py'):
            src = os.path.join(http_path, filename)
            datas.append((src, 'http'))

# Also include all submodules
hiddenimports = collect_submodules('http')
