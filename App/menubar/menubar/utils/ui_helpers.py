import os
import sys

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，兼容 PyInstaller --onefile 模式
    在打包后的 exe 中，资源会被解压到 sys._MEIPASS 临时目录
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 创建的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境：当前文件所在目录的上级 (App/menubar)
        # Assuming this file is in App/menubar/menubar/utils/ui_helpers.py
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    
    full_path = os.path.normpath(os.path.join(base_path, relative_path))
    return full_path

def get_icon_path():
    """Get path to app icon file (platform-specific) with PyInstaller support"""
    is_windows = sys.platform == 'win32'
    is_macos = sys.platform == 'darwin'
    
    if is_windows:
        return get_resource_path("resources/AppIcon.ico")
    elif is_macos:
        # For windows, we might want the .icns, for menubar we might want template
        # This function returns the primary App icon
        path = get_resource_path("resources/AppIcon.icns")
        if os.path.exists(path):
            return path
        return get_resource_path("resources/icon_template.png")
    
    return None
