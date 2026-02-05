from setuptools import setup

APP = ['menubar/__main__.py']
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps'],
    'plist': {
        'CFBundleName': 'OpenCode Token Meter',
        'CFBundleDisplayName': 'OpenCode Token Meter',
        'CFBundleIdentifier': 'com.opencode.token.menubar',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,
    },
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
)
