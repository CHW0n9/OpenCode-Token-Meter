# macOS 解决方案：使用 rumps 替代 pystray

## 问题根源

**pystray + pywebview 在 macOS 上冲突**：
- pystray 需要主线程运行 NSStatusBar
- pywebview 的 webview.start() 阻塞主线程
- macOS 不允许两者同时占用主线程

## 解决方案：使用 rumps

`rumps` 是专门为 macOS 设计的菜单栏应用库，与 pywebview 兼容更好。

### 安装

```bash
pip install rumps
```

### 替代 tray.py 实现

创建 `App/webview_ui/backend/tray_rumps.py`：

```python
"""System tray for macOS using rumps (compatible with pywebview)"""
import rumps
import threading


class TrayManagerRumps:
    """Tray manager using rumps for macOS compatibility"""
    
    def __init__(self, window=None, api=None, on_show=None, on_quit=None):
        self.window = window
        self.api = api
        self.on_show = on_show
        self.on_quit = on_quit
        self.app = None
        
    def create_app(self):
        """Create rumps application"""
        self.app = rumps.App("OpenCode Token Meter", 
                             icon="App/webview_ui/web/assets/AppIcon.png")
        
        # Create menu
        self.app.menu = [
            rumps.MenuItem("显示主窗口", callback=self._on_show),
            rumps.MenuItem("刷新数据", callback=self._on_refresh),
            None,  # Separator
            rumps.MenuItem("退出", callback=self._on_quit)
        ]
        
        return self.app
    
    def _on_show(self, sender):
        """Show window callback"""
        print("[Tray] Show window clicked")
        if self.on_show:
            self.on_show()
        elif self.window:
            try:
                self.window.show()
                self.window.restore()
            except:
                pass
    
    def _on_refresh(self, sender):
        """Refresh callback"""
        print("[Tray] Refresh clicked")
        if self.api:
            try:
                self.api.refresh()
            except:
                pass
    
    def _on_quit(self, sender):
        """Quit callback"""
        print("[Tray] Quit clicked")
        if self.on_quit:
            self.on_quit()
        rumps.quit_application()
    
    def run(self):
        """Start tray (non-blocking with timer)"""
        self.create_app()
        # Run without blocking
        self.app.run()
    
    def stop(self):
        """Stop tray"""
        if self.app:
            rumps.quit_application()
```

### 修改 main.py 使用 rumps

```python
"""Main entry point - macOS compatible with rumps"""
import os
import sys
import webview
import argparse
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

try:
    from .backend.api import JsApi
    from .backend.tray_rumps import TrayManagerRumps
except ImportError:
    from backend.api import JsApi
    from backend.tray_rumps import TrayManagerRumps


class AppController:
    def __init__(self, debug=False):
        self.debug = debug
        self.window = None
        self.api = None
        self.tray = None
        self.web_dir = os.path.join(os.path.dirname(__file__), "web")
        
    def init_api(self):
        if self.api is None:
            print("[INFO] Initializing API...")
            self.api = JsApi()
            print("[INFO] API initialized")
        return self.api
    
    def create_window(self):
        self.init_api()
        index_path = os.path.join(self.web_dir, "index.html")
        url = f"file://{os.path.abspath(index_path)}" if os.path.exists(index_path) else "about:blank"
        
        print("[INFO] Creating window...")
        self.window = webview.create_window(
            title="OpenCode Token Meter",
            url=url,
            js_api=self.api,
            width=1200,
            height=800,
            min_size=(800, 600)
        )
        return self.window
    
    def show_window(self):
        if self.window is None:
            self.create_window()
            # Start webview in separate thread
            threading.Thread(target=self._run_webview).start()
        else:
            try:
                self.window.show()
                self.window.restore()
            except:
                self.window = None
                self.show_window()
    
    def _run_webview(self):
        webview.start(debug=self.debug, http_server=False)
        self.window = None
    
    def run(self):
        print("[INFO] Starting...")
        self.init_api()
        
        # Create tray with callbacks
        self.tray = TrayManagerRumps(
            api=self.api,
            on_show=self.show_window
        )
        
        # Start tray (this blocks on macOS)
        self.tray.run()


def main(debug=False):
    AppController(debug=debug).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    main(debug=args.debug)
```

## 备选方案

如果 rumps 也不工作，可以考虑：

### 方案 B：仅使用 Dock（无托盘）

```python
# 不使用托盘，只在 Dock 显示
# 用户通过 Dock 图标右键菜单操作
```

### 方案 C：分离进程

```python
# 托盘一个进程，webview 另一个进程
# 通过 socket/queue 通信
```

## 推荐

1. **先尝试 rumps** - macOS 原生支持最好
2. **如果不行** - 放弃托盘，只用 Dock 图标
3. **最后选择** - 使用 PyQt6 的托盘（但这样就回到了原点）

## 当前可用方案

如果不改代码，**当前可用的是无托盘版本**：

```bash
# 修改 main.py 禁用托盘（之前测试过可行）
# 第79-82行注释掉托盘代码

# 运行
python App/webview_ui/main.py --debug
```

这会让应用：
- ✅ 正常显示窗口
- ✅ 有 Dock 图标
- ❌ 没有菜单栏托盘图标

对于大多数用户来说，Dock 图标已经足够。
