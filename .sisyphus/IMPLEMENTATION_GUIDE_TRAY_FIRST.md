# 方案2实现指南：托盘优先架构

## 目标
应用启动时只显示系统托盘图标，点击"显示主窗口"菜单后才创建并显示 webview 窗口。

## 实现步骤

### 步骤1：修改 main.py

将 `App/webview_ui/main.py` 替换为以下内容：

```python
"""Main entry point for OpenCode Token Meter - pywebview version
macOS optimized: Tray-first architecture
"""
import os
import sys
import webview
import argparse

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

# Support both module import and direct execution
try:
    from .backend.api import JsApi
    from .backend.tray import TrayManager
except ImportError:
    from backend.api import JsApi
    from backend.tray import TrayManager


class AppController:
    """Application controller managing tray and window lifecycle"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.window = None
        self.api = None
        self.tray = None
        self.web_dir = os.path.join(os.path.dirname(__file__), "web")
        
    def init_api(self):
        """Initialize API instance"""
        if self.api is None:
            print("[INFO] Initializing API...")
            self.api = JsApi()
            print("[INFO] API initialized")
        return self.api
    
    def create_window(self):
        """Create the main webview window"""
        # Initialize API
        self.init_api()
        
        # Prepare URL
        index_path = os.path.join(self.web_dir, "index.html")
        if os.path.exists(index_path):
            url = f"file://{os.path.abspath(index_path)}"
            print(f"[INFO] Loading URL: {url}")
        else:
            print(f"[ERROR] index.html not found")
            url = "about:blank"
        
        print("[INFO] Creating window...")
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
        
        print("[INFO] Window created successfully")
        return self.window
    
    def show_window(self):
        """Show or create the main window"""
        print("[INFO] Show window requested")
        
        if self.window is None:
            self.create_window()
            # Start webview (this will block until window closes)
            self.start_webview()
        else:
            try:
                self.window.show()
                self.window.restore()
                print("[INFO] Window shown")
            except:
                print("[INFO] Recreating window...")
                self.window = None
                self.show_window()
    
    def start_webview(self):
        """Start webview event loop"""
        print("[INFO] Starting webview...")
        try:
            webview.start(
                debug=self.debug,
                http_server=False,
                private_mode=False
            )
        except Exception as e:
            print(f"[ERROR] Webview error: {e}")
        finally:
            print("[INFO] Webview closed")
            self.window = None
    
    def setup_tray(self):
        """Set up system tray"""
        print("[INFO] Setting up system tray...")
        
        # Initialize API for tray to use
        self.init_api()
        
        # Create tray
        self.tray = TrayManager(api=self.api)
        
        # Override show callback
        def on_show(icon, item):
            print("[Tray] Show window clicked")
            self.show_window()
        self.tray._on_show_window = on_show
        
        print("[INFO] Tray setup complete")
    
    def run(self):
        """Run the application - start with tray only"""
        print("[INFO] Starting OpenCode Token Meter...")
        print("[INFO] Click tray icon → '显示主窗口' to open")
        
        # Setup tray
        self.setup_tray()
        
        # Start tray (blocks on macOS main thread)
        self.tray.run()
    
    def quit(self):
        """Quit application"""
        print("[INFO] Quitting...")
        if self.tray:
            try:
                self.tray.stop()
            except:
                pass
        os._exit(0)


def main(debug=False):
    """Main entry point"""
    app = AppController(debug=debug)
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    main(debug=args.debug)
```

### 步骤2：修改 tray.py（可选）

确保托盘菜单有"显示主窗口"选项：

```python
def get_menu(self):
    """Create tray menu"""
    return Menu(
        MenuItem("显示主窗口", self._on_show_window),
        MenuItem("刷新数据", self._on_refresh),
        Menu.SEPARATOR,
        MenuItem("退出", self._on_quit)
    )
```

## 运行方式

```bash
# 开发模式
python App/webview_ui/main.py --debug

# 正常模式
python App/webview_ui/main.py
```

## 工作流程

1. **启动** → 显示托盘图标（右上角）
2. **点击托盘** → 显示菜单
3. **点击"显示主窗口"** → 创建并显示 webview 窗口
4. **关闭窗口** → 回到托盘状态
5. **点击"退出"** → 完全退出应用

## 注意事项

- macOS 上托盘必须在主线程运行
- webview 窗口打开时会阻塞，直到窗口关闭
- 窗口关闭后变量设为 None，下次点击会重新创建

## 测试步骤

1. 运行应用，确认托盘图标出现
2. 点击托盘图标，确认菜单弹出
3. 点击"显示主窗口"，确认窗口打开
4. 关闭窗口，确认回到托盘状态
5. 再次点击"显示主窗口"，确认窗口重新打开
6. 点击"退出"，确认应用完全退出
