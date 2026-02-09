# 功能恢复实施计划

## 当前状态
✅ 托盘图标显示正常（rumps）
⏳ 需要恢复功能

## 实施步骤

### 第一步：验证 API 连通性

**目标**: 确认前端能获取真实数据

**操作**:
1. 运行应用: `python App/webview_ui/main.py --debug`
2. 在打开的窗口中按 `Cmd+Option+I` 打开开发者工具
3. 查看 Console 是否有数据加载
4. 检查 Network 标签看 API 调用

**预期**: 应该能看到今日统计数据

### 第二步：修复数据显示

如果数据没有显示，需要检查:

**后端检查**:
```python
# 测试 API 是否工作
python -c "
import sys
sys.path.insert(0, '.')
from App.webview_ui.backend.api import JsApi
api = JsApi()
result = api.get_stats('today')
print(result)
"
```

**前端检查**:
- 打开开发者工具 Console
- 查看是否有 API 错误
- 检查 dashboard.js 是否正确渲染

### 第三步：添加设置功能

**需要实现**:
1. 设置按钮点击打开设置面板
2. 阈值设置表单
3. 模型定价管理
4. 保存/读取设置

### 第四步：添加数据导出

**需要实现**:
1. 导出按钮
2. CSV 生成功能
3. 文件下载

## 建议

**现在就开始第一步**：运行应用并检查数据是否显示。

如果数据显示正常，说明 Phase 1 已经完成！

如果数据不显示，告诉我具体的错误信息，我们再修复。

**运行命令**:
```bash
python App/webview_ui/main.py --debug
```

然后:
1. 点击"显示主窗口"
2. 打开开发者工具 (Cmd+Option+I)
3. 截图或复制 Console 中的错误信息
