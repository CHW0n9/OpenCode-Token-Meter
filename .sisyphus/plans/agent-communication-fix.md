# Agent通信和窗口管理修复计划

## TL;DR
修复三个核心问题：
1. **Agent启动失败** - 路径配置不正确，导致无法连接
2. **窗口背景不一致** - CSS需要全局统一
3. **菜单无法重新打开窗口** - 窗口关闭检测机制缺失

---

## 问题分析

### 问题1: Agent无法启动连接
**根本原因**：
- `main_tray.py` 的 sys.path 配置顺序错误
- 当前：先 `menubar` 后 `agent`，导致导入agent.config失败
- 启动路径计算不正确

**正确路径**：
```
项目根目录/
├── App/
│   ├── agent/agent/config.py         ← agent config
│   ├── menubar/menubar/uds_client.py  ← 导入agent.config
│   └── webview_ui/main_tray.py     ← 也需要导入agent.config
```

从 `webview_ui` 导入 `agent` 的正确方式：
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
# 这里的路径是：webview_ui/../agent = App/agent
```

**通信机制**：
- Windows: TCP (127.0.0.1:50899)
- macOS: Unix Domain Socket (`~/Library/Application Support/OpenCode Token Meter/agent.sock`)

### 问题2: 窗口边框颜色
**根本原因**：
- macOS的webview窗口边框是系统控制的
- 当前CSS `bg-black-950` 是深灰色，不是纯黑

**解决方案**：
- HTML头部使用 `!important` 强制纯黑
- CSS全局覆盖背景色为 `#000000`
- 滚动条和边框也统一黑色系

### 问题3: 窗口关闭检测失败
**根本原因**：
- `main_tray.py` 只在启动时检查webview是否运行
- 窗口关闭后，PID还在（进程变成了僵尸状态）
- 没有定期检查窗口状态

**解决方案**：
- 定期检查进程状态 `os.kill(pid, 0)`
- 如果进程不存在，清除PID文件
- 每次点击菜单时先检查窗口是否还活着

---

## 修复计划

### Phase 1: 修复Agent启动和通信

#### 任务1：修正 sys.path 配置
**文件**: `App/webview_ui/main_tray.py`

**当前错误**：
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
```

**修改为**：
```python
# 必须先添加 agent，因为它被 menubar 依赖
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
```

**验证方式**：
```python
import agent.config
from agent.config import BASE_DIR, SOCKET_PATH, USE_TCP
```

#### 任务2：修正 agent 启动路径计算
**文件**: `App/webview_ui/main_tray.py`

**当前错误**：
```python
agent_paths = [
    os.path.join(os.path.dirname(__file__), "..", "agent"),  # webview_ui/../agent WRONG
]
```

**修改为**：
```python
# webview_ui 在 App/webview_ui/
# 需要到达 App/agent → ../agent
app_dir = os.path.dirname(os.path.dirname(__file__))  # App/
agent_paths = [
    os.path.join(app_dir, "agent"),  # App/agent CORRECT
    os.path.expanduser("~/Desktop/OpenCode Token Meter/App/agent"),
]
```

#### 任务3：增加Agent启动调试输出
**文件**: `App/webview_ui/main_tray.py`

**在 `_ensure_agent_running()` 中添加**：
```python
def _ensure_agent_running(self):
    print(f"[DEBUG] BASE_DIR={BASE_DIR}")
    print(f"[DEBUG] SOCKET_PATH={SOCKET_PATH}")
    print(f"[DEBUG] USE_TCP={USE_TCP}")
    
    # 检查socket文件存在（仅macOS）
    if not USE_TCP:
        print(f"[DEBUG] Socket file exists: {os.path.exists(SOCKET_PATH)}")
    
    # 然后是现有的启动逻辑...
```

**验证命令**：
```bash
python App/webview_ui/main_tray.py --debug
# 应该看到：DEBUG: agent路径 exists: True
# 然后是: Agent started successfully
```

---

### Phase 2: 统一窗口颜色主题

#### 任务4：HTML全局黑色背景
**文件**: `App/webview_ui/web/index.html`

**在 `<head>` 中添加**：
```html
<style>
    /* 强制全局纯黑 - 最高优先级 */
    html, body {
        background-color: #000000 !important;
        background: #000000 !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 100% !important;
        width: 100% !important;
    }
    
    /* 确保容器也是黑色 */
    #app, .app-container, main {
        background-color: #000000 !important;
        background: #000000 !important;
    }
</style>
```

#### 任务5：CSS全局颜色覆盖
**文件**: `App/webview_ui/web/css/styles.css`

**替换开头为**：
```css
html, body {
    background-color: #000000 !important;
    background: #000000 !important;
    margin: 0 !important;
    padding: 0 !important;
}

body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #ffffff;
    overflow-x: hidden;
}

/* 所有背景容器改为纯黑 */
.bg-black-800, .bg-black-900, .bg-black-700 {
    background-color: #0d0d0d !important;
    border: 1px solid #222222 !important;
}

/* 滚动条黑色 */
::-webkit-scrollbar {
    background: #000000;
}

::-webkit-scrollbar-track {
    background: #000000;
}

::-webkit-scrollbar-thumb {
    background: #222222;
    border-radius: 4px;
}
```

---

### Phase 3: 修复窗口关闭检测

#### 任务6：定期窗口状态检查
**文件**: `App/webview_ui/webview_runner.py`

**在进程退出时自动清理PID文件**：
```python
import atexit

def cleanup_pid_file():
    try:
        pid_file = os.path.join(BASE_DIR, "webview.pid")
        if os.path.exists(pid_file):
            os.remove(pid_file)
            print("[INFO] Cleaned up pid file on exit")
    except:
        pass

def main(debug=False, initial_page='dashboard'):
    atexit.register(cleanup_pid_file)
    # ... 现有代码
```

#### 任务7：改进窗口存活检测
**文件**: `App/webview_ui/main_tray.py`

**修改 `_is_webview_running()` 方法**：
```python
def _is_webview_running(self):
    """检查webview进程是否还在运行"""
    pid = self._get_webview_pid()
    if pid is None:
        return False
    try:
        # 检查进程是否存在且不是僵尸
        import signal
        os.kill(pid, 0)  # 不发送信号，只检查存在性
        return True
    except OSError as e:
        # 进程不存在，清理PID文件
        print(f"[DEBUG] Webview process {pid} not found: {e}")
        self._clear_webview_pid()
        return False
```

**在 `start_webview_subprocess()` 开始时检查进程状态**：
```python
def start_webview_subprocess(self, page='dashboard'):
    # 先检查已有进程是否还活着
    if self._get_webview_pid() is not None:
        try:
            os.kill(self._get_webview_pid(), 0)
            print(f"[DEBUG] Existing webview process is still alive")
            # 进程还活着，用nav文件导航
            self._write_nav_file(page)
            return
        except OSError:
            # 进程不存在，清理PID文件
            print("[DEBUG] Stale PID file, cleaning up")
            self._clear_webview_pid()
    # ... 继续启动新进程
```

---

## 成功标准

### 1. Agent通信 ✓
- ✅ `python App/webview_ui/main_tray.py --debug` 启动时看到 "Agent started successfully"
- ✅ webview窗口能加载真实的统计数据（不是mock数据）
- ✅ 点击菜单"Show Details" / "Settings" 窗口切换页面

### 2. 窗口颜色一致 ✓
- ✅ 窗口打开后背景纯黑 `#000000`
- ✅ scrollbars也是黑色
- ✅ 边框是深灰色（macOS系统限制）

### 3. 窗口关闭检测 ✓
- ✅ 关闭窗口后，点击菜单能重新打开
- ✅ PID文件在进程退出时被清理
- ✅ 不会出现多个窗口同时存在

---

## 测试步骤

```bash
# 1. 先测试agent能否独立启动
cd App/agent
python -m agent

# 按 Ctrl+C 停止agent，然后测试tray启动

# 2. 测试tray版本
cd App/webview_ui
python main_tray.py --debug

# 观察日志：
# - [INFO] Starting agent from: /path/to/App/agent
# - [INFO] Agent started successfully
# - 打开窗口后，尝试关闭窗口
# - 再次点击菜单，窗口能重新打开
```

---

## 文件清单

修改的文件：
1. `App/webview_ui/main_tray.py`
   - 修复sys.path顺序
   - 修复agent启动路径
   - 改进窗口状态检测
   - 增加调试输出

2. `App/webview_ui/web/index.html`
   - 添加强制黑色背景style

3. `App/webview_ui/web/css/styles.css`
   - 全局黑色主题
   - 边框和滚动条统一颜色

4. `App/webview_ui/webview_runner.py`
   - 添加exit时cleanup逻辑

---

## 执行

使用 `/start-work` 执行此计划。执行者将按以下步骤进行：

1. 读取并修改 `main_tray.py` 的 sys.path 和启动逻辑
2. 修改 `index.html` 添加style标签
3. 重写 `styles.css` 的开头部分
4. 修改 `webview_runner.py` 添加cleanup
5. 运行测试验证agent启动和窗口管理
