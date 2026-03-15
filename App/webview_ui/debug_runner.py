
import sys
import os
import webview
import threading
import time

# Add paths
sys.path.insert(0, os.path.join(os.getcwd(), "..", "menubar"))
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "agent"))

try:
    from backend.api import JsApi
except ImportError:
    # Add webview_ui to path if needed
    sys.path.insert(0, os.getcwd())
    from backend.api import JsApi

def create_window(api):
    web_dir = os.path.join(os.getcwd(), "web")
    index_path = os.path.join(web_dir, "index.html")
    url = f"file://{os.path.abspath(index_path)}?page=details"
    
    window = webview.create_window(
        title="OpenCode Token Meter - Debug Export",
        url=url,
        js_api=api,
        width=1200,
        height=800
    )
    return window

def main():
    api = JsApi()
    window = create_window(api)
    
    # Pass window to API
    if hasattr(api, 'set_window'):
        api.set_window(window)
        print("Window set on API")
    
    webview.start(debug=True)

if __name__ == "__main__":
    main()
