# 方案2完整实现：使用 rumps 替代 pystray

## 1. 安装依赖

```bash
pip install rumps pywebview pystray pillow pyperclip
```

## 2. 创建 rumps 托盘文件

**文件**: `App/webview_ui/backend/tray_rumps.py`

```python
"""System tray for macOS using rumps (compatible with pywebview)"""
import rumps
import os


class TrayManager:
    """Tray manager using rumps for macOS"""
    
    def __init__(self, api=None, on_show=None, on_refresh=None, on_quit=None):
        self.api = api
        self.on_show = on_show
        self.on_refresh = on_refresh
        self.on_quit = on_quit
        self.app = None
        self._running = False
        
        # Get icon path
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.icon_path = os.path.join(base_dir, "web", "assets", "AppIcon.png")
        
    def create_app(self):
        """Create rumps application"""
        # Use text title if icon not found
        if os.path.exists(self.icon_path):
            self.app = rumps.App("OpenCode Token Meter", icon=self.icon_path)
        else:
            self.app = rumps.App("OpenCode Token Meter")
        
        # Create menu items
        show_item = rumps.MenuItem("显示主窗口", callback=self._on_show)
        refresh_item = rumps.MenuItem("刷新数据", callback=self._on_refresh)
        quit_item = rumps.MenuItem("退出", callback=self._on_quit)
        
        self.app.menu = [show_item, refresh_item, None, quit_item]
        return self.app
    
    def _on_show(self, sender):
        """Show window callback"""
        print("[Tray] 显示主窗口")
        if self.on_show:
            self.on_show()
    
    def _on_refresh(self, sender):
        """Refresh callback"""
        print("[Tray] 刷新数据")
        if self.on_refresh:
            self.on_refresh()
        elif self.api:
            try:
                self.api.refresh()
            except:
                pass
    
    def _on_quit(self, sender):
        """Quit callback"""
        print("[Tray] 退出")
        if self.on_quit:
            self.on_quit()
        rumps.quit_application()
    
    def run(self):
        """Start tray"""
        if self._running:
            return
        
        self.create_app()
        self._running = True
        print("[Tray] 启动中...")
        self.app.run()
    
    def stop(self):
        """Stop tray"""
        if self.app and self._running:
            rumps.quit_application()
            self._running = False
```

## 3. 修改主入口文件

**文件**: `App/webview_ui/main.py`

```python
"""Main entry point for OpenCode Token Meter - rumps version"""
import os
import sys
import webview
import argparse
import threading

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

# Support both module import and direct execution
try:
    from .backend.api import JsApi
    from .backend.tray_rumps import TrayManager
except ImportError:
    from backend.api import JsApi
    from backend.tray_rumps import TrayManager


class AppController:
    """Application controller"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.window = None
        self.api = None
        self.tray = None
        self.web_dir = os.path.join(os.path.dirname(__file__), "web")
        
    def init_api(self):
        """Initialize API"""
        if self.api is None:
            print("[INFO] 初始化 API...")
            self.api = JsApi()
            print("[INFO] API 初始化完成")
        return self.api
    
    def create_window(self):
        """Create webview window"""
        self.init_api()
        
        index_path = os.path.join(self.web_dir, "index.html")
        if os.path.exists(index_path):
            url = f"file://{os.path.abspath(index_path)}"
        else:
            print(f"[ERROR] index.html 未找到")
            url = "about:blank"
        
        print("[INFO] 创建窗口...")
        self.window = webview.create_window(
            title="OpenCode Token Meter",
            url=url,
            js_api=self.api,
            width=1200,
            height=800,
            min_size=(800, 600),
            resizable=True,
            fullscreen=False,
            hidden=False
        )
        return self.window
    
    def show_window(self):
        """Show or create window"""
        print("[INFO] 显示窗口")
        
        if self.window is None:
            self.create_window()
            # Start webview in separate thread
            webview_thread = threading.Thread(target=self._run_webview)
            webview_thread.daemon = True
            webview_thread.start()
            print("[INFO] 窗口线程已启动")
        else:
            try:
                self.window.show()
                self.window.restore()
                print("[INFO] 窗口已显示")
            except:
                print("[INFO] 重新创建窗口...")
                self.window = None
                self.show_window()
    
    def _run_webview(self):
        """Run webview (in thread)"""
        try:
            webview.start(
                debug=self.debug,
                http_server=False,
                private_mode=False
            )
        except Exception as e:
            print(f"[ERROR] Webview 错误: {e}")
        finally:
            print("[INFO] 窗口已关闭")
            self.window = None
    
    def refresh_data(self):
        """Refresh data"""
        if self.api:
            try:
                self.api.refresh()
                print("[INFO] 数据已刷新")
            except Exception as e:
                print(f"[ERROR] 刷新失败: {e}")
    
    def quit_app(self):
        """Quit application"""
        print("[INFO] 正在退出...")
        if self.tray:
            try:
                self.tray.stop()
            except:
                pass
        os._exit(0)
    
    def run(self):
        """Run application"""
        print("[INFO] 启动 OpenCode Token Meter...")
        print("[INFO] 点击菜单栏图标 → '显示主窗口'")
        
        # Initialize API
        self.init_api()
        
        # Create tray
        self.tray = TrayManager(
            api=self.api,
            on_show=self.show_window,
            on_refresh=self.refresh_data,
            on_quit=self.quit_app
        )
        
        # Start tray (this runs the main loop)
        self.tray.run()


def main(debug=False):
    """Main entry"""
    app = AppController(debug=debug)
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    
    main(debug=args.debug)
```

## 4. 测试步骤

```bash
# 1. 确保在项目根目录
cd /Users/chwong/Library/CloudStorage/OneDrive-TheHongKongPolytechnicUniversity/OpenCode Projects/20260129 OpenCode Token Meter/OpenCode-Token-Meter-Dev

# 2. 安装 rumps
pip install rumps

# 3. 创建 tray_rumps.py 文件
# (复制上面的代码保存到 App/webview_ui/backend/tray_rumps.py)

# 4. 修改 main.py
# (复制上面的代码替换 App/webview_ui/main.py)

# 5. 运行测试
python App/webview_ui/main.py --debug
```

## 5. 预期行为

1. **启动** → 菜单栏出现图标（右上角）
2. **点击图标** → 弹出菜单
3. **点击"显示主窗口"** → 打开 webview 窗口
4. **关闭窗口** → 回到托盘状态
5. **再次点击"显示主窗口"** → 重新打开窗口
6. **点击"退出"** → 完全退出

## 6. 如果 rumps 也不工作

如果 rumps 也有线程问题，最后的备选方案：

**仅使用 Dock 图标**（无托盘）：
- 应用启动直接显示窗口
- 用户通过 Dock 图标管理应用
- 这是最简单可靠的方案

## 7. 文件清单

需要创建/修改的文件：

```
App/webview_ui/
├── backend/
│   └── tray_rumps.py      # 新建
├── main.py                # 替换
└── ...
```

## 8. 调试

如果还有问题，检查：

```bash
# 测试 rumps 是否能导入
python -c "import rumps; print('rumps OK')"

# 测试托盘模块
python -c "
from App.webview_ui.backend.tray_rumps import TrayManager
t = TrayManager()
t.create_app()
print('Tray created')
"
```
