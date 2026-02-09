# 功能恢复实施计划 - Phase 1: 核心数据功能

## 当前状态
✅ 基础框架完成
✅ API 桥接层完成
✅ 托盘功能完成
⚠️ 窗口显示问题（已提供解决方案）
⏳ 需要恢复：统计数据对接

## Phase 1 目标：统计仪表盘数据显示

### 步骤 1：确保窗口能显示
**操作**（选择其一）：
- 方案 A：使用无托盘版本
  ```bash
  cp App/webview_ui/main_backup.py App/webview_ui/main.py
  python App/webview_ui/main.py --debug
  ```
- 方案 B：修复托盘版本（需手动修改代码，见 WINDOW_FIX_GUIDE.md）

### 步骤 2：验证 API 数据获取

**测试命令**：
```python
import sys
sys.path.insert(0, '.')
from App.webview_ui.backend.api import JsApi

api = JsApi()
result = api.get_stats('today')
print(result)
```

**预期输出**：
```python
{
    'success': True,
    'data': {
        'input': 125000,
        'output': 45000,
        'requests': 142,
        'cost': 1.25
    }
}
```

### 步骤 3：前端数据对接

**检查文件**：`App/webview_ui/web/js/api.js`
- 确保 `getStats()` 方法正确调用 `window.pywebview.api.get_stats()`
- 检查是否有 mock 数据拦截

**检查文件**：`App/webview_ui/web/js/dashboard.js`
- 确保 `loadStats()` 正确调用 API
- 确保 `renderCards()` 正确显示数据

**需要修改的关键点**：
1. 在 `index.html` 确保正确引入所有 JS 文件
2. 确保 `pywebviewready` 事件触发后再加载数据
3. 确保统计卡片的 DOM ID 与 JS 匹配

### 步骤 4：测试数据加载

**操作**：
1. 打开应用窗口
2. 按 `Cmd+Option+I` 打开开发者工具
3. 查看 Console 是否有 API 调用日志
4. 查看 Network 标签是否有数据返回

**成功标志**：
- 统计卡片显示真实数据（不是 mock 数据）
- Console 无红色错误
- 自动刷新正常工作（30秒间隔）

### 步骤 5：添加手动刷新

**操作**：
1. 在托盘菜单添加"刷新数据"
2. 在窗口界面添加刷新按钮
3. 确保刷新时更新所有统计数据

## 实施清单

- [ ] 步骤 1：窗口能正常显示
- [ ] 步骤 2：API 能获取真实数据
- [ ] 步骤 3：前端正确显示数据
- [ ] 步骤 4：自动刷新正常工作
- [ ] 步骤 5：手动刷新功能可用

## 下一步

完成 Phase 1 后，进入 Phase 2：
- 设置面板（阈值、模型定价）
- 数据导出功能
- Provider/Model 视图切换

## 开始实施

**立即执行**：
```bash
# 使用可用版本
cp App/webview_ui/main_backup.py App/webview_ui/main.py

# 运行测试
python App/webview_ui/main.py --debug
```

**然后告诉我**：
1. 窗口是否正常显示？
2. 统计卡片显示的是真实数据还是 mock 数据？
3. Console 有什么错误信息？
