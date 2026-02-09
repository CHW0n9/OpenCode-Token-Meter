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
            on_show=self.show_window,
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
