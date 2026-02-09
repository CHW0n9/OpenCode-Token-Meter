# 窗口无法打开 - 紧急修复指南

## 问题诊断

**症状**: 托盘图标显示正常，但点击"显示主窗口"后窗口不出现

**原因**: `webview.start()` 在新线程中调用失败

## 修复步骤

### 步骤 1: 添加调试日志

编辑 `App/webview_ui/main.py`，找到 `_run_webview` 方法（第85-97行）：

**原代码**:
```python
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
```

**修改为**:
```python
def _run_webview(self):
    """Run webview (in thread)"""
    print("[INFO] _run_webview 线程启动")
    try:
        print("[INFO] 调用 webview.start()...")
        webview.start(
            debug=self.debug,
            http_server=False,
            private_mode=False
        )
        print("[INFO] webview.start() 完成")
    except Exception as e:
        print(f"[ERROR] Webview 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[INFO] 窗口已关闭")
        self.window = None
```

### 步骤 2: 测试并查看日志

```bash
python App/webview_ui/main.py --debug
```

点击"显示主窗口"，观察终端输出：
- 如果看到 `"[INFO] _run_webview 线程启动"` → 线程创建成功
- 如果看到 `"[INFO] 调用 webview.start()..."` → 正在启动 webview
- 如果看到 `"[ERROR] Webview 错误"` → 有具体错误信息

### 步骤 3: 可能的错误和解决方案

#### 错误 1: "NSWindow should only be instantiated on the main thread"
**原因**: macOS 上 webview 必须在主线程创建
**解决**: 改用主线程架构（见方案 B）

#### 错误 2: 窗口闪退，无错误
**原因**: 可能是线程冲突或资源问题
**解决**: 见方案 B

#### 错误 3: 窗口打开后立即关闭
**原因**: webview.start() 返回或报错
**解决**: 检查 index.html 是否存在

### 方案 B: 使用主线程架构（推荐）

如果上述修复无效，改用主线程架构：

**新文件**: `App/webview_ui/main_threaded.py`

```python
"""Main entry - macOS main thread compatible"""
import os
import sys
import webview
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

try:
    from .backend.api import JsApi
except ImportError:
    from backend.api import JsApi


class App:
    def __init__(self, debug=False):
        self.debug = debug
        self.api = None
        self.window = None
        
    def init(self):
        """Initialize API and create window"""
        print("[INFO] Initializing...")
        if self.api is None:
            self.api = JsApi()
        
        web_dir = os.path.join(os.path.dirname(__file__), "web")
        index_path = os.path.join(web_dir, "index.html")
        url = f"file://{os.path.abspath(index_path)}" if os.path.exists(index_path) else "about:blank"
        
        self.window = webview.create_window(
            title="OpenCode Token Meter",
            url=url,
            js_api=self.api,
            width=1200,
            height=800
        )
        print("[INFO] Window created, starting...")
        
        # Start webview (blocks main thread)
        webview.start(debug=self.debug, http_server=False)


def main(debug=False):
    app = App(debug=debug)
    app.init()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    main(debug=args.debug)
```

**测试**:
```bash
python App/webview_ui/main_threaded.py --debug
```

如果窗口能打开，说明问题是线程相关。

### 方案 C: 放弃托盘，先用 Dock 版本

如果托盘和窗口冲突无法解决，暂时使用无托盘版本：

```bash
# 使用之前备份的版本
cp App/webview_ui/main_backup.py App/webview_ui/main.py
python App/webview_ui/main.py --debug
```

这个版本：
- ✅ 窗口能正常显示
- ✅ 有 Dock 图标
- ❌ 没有菜单栏托盘

## 建议

1. **先尝试步骤 1-2**，看具体错误是什么
2. **如果线程错误**，使用方案 B 或 C
3. **如果需要完整功能**，可能需要放弃托盘或使用 PyQt6

## 测试清单

- [ ] 步骤 1: 添加调试日志
- [ ] 步骤 2: 运行并查看错误
- [ ] 步骤 3: 根据错误选择解决方案
- [ ] 验证: 窗口能正常显示
- [ ] 验证: 数据能正常加载

**完成修复后告诉我结果！**
