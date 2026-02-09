# Menubar 功能分析

**分析时间**: 2026-02-06  
**源文件**: App/menubar/*.py

---

## 1. 架构概览

当前使用 PyQt6 实现的桌面应用，主要组件：
- **OpenCodeTokenMeter**: 主应用类，管理窗口和系统托盘
- **AgentClient**: 与后台 agent 通信的客户端
- **Settings**: 配置管理
- **Windows**: 多个窗口/对话框类

---

## 2. 窗口管理功能

### 2.1 主窗口 (MainStatsWindow)
**用途**: 显示主要统计数据
- 2×3 网格显示：In/Req/Out/Cost/Token%/Cost%
- 刷新按钮
- 查看详情按钮
- 打开设置按钮
- 导出数据按钮

### 2.2 详情对话框 (DetailsDialog)
**用途**: 详细统计数据
- 时间范围选择（今日/7天/本月/自定义）
- Provider 统计标签页
- Model 统计标签页
- All 总览标签页
- 数据表格展示

### 2.3 设置对话框 (SettingsDialog)
**用途**: 应用配置
- Token 阈值设置
- 成本阈值设置
- 模型定价管理
- 通知设置
- 刷新间隔设置

### 2.4 自定义范围对话框 (CustomRangeDialog)
**用途**: 选择自定义时间范围
- 开始日期选择器
- 结束日期选择器
- 确认/取消按钮

### 2.5 自定义范围统计 (CustomRangeStatsDialog)
**用途**: 显示自定义时间范围的统计
- 与 DetailsDialog 类似，但针对自定义范围

### 2.6 模型更新对话框 (ModelUpdateDialog)
**用途**: 版本更新时显示新模型
- 新模型列表
- 更新说明

---

## 3. 系统托盘功能

### 3.1 托盘图标
- 应用启动时创建
- 显示应用图标
- macOS: Menubar 右上角
- Windows: 系统托盘

### 3.2 托盘菜单
- **显示主窗口**: 打开/激活主窗口
- **今日统计**: 显示今日数据摘要
- **刷新**: 强制刷新数据
- **设置**: 打开设置对话框
- **退出**: 退出应用

### 3.3 托盘提示
- 悬停显示今日统计摘要
- Token 使用量
- 成本估算

---

## 4. 数据展示功能

### 4.1 统计卡片 (2×3 网格)
1. **In**: 总输入 Token
2. **Req**: 总请求数
3. **Out**: 总输出 Token
4. **Cost**: 计算成本 (USD)
5. **Token%**: 当前 Token 占阈值百分比（可选）
6. **Cost%**: 当前成本占阈值百分比（可选）

### 4.2 详细表格
- Provider 分组统计
- Model 分组统计
- 列：Provider/Model, Requests, Input, Output, Reasoning, Caching, Cost
- 支持排序

### 4.3 趋势图表
- Token 使用趋势（折线图）
- 成本分布（饼图）

---

## 5. API 接口列表 (Python-JS 通信)

这些是需要暴露给 JavaScript 的方法：

### 5.1 统计数据
| 方法名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `get_stats` | `scope: str` | `dict` | 获取统计数据 (today/7days/month) |
| `get_stats_by_provider` | `scope: str` | `dict` | 按 Provider 分组统计 |
| `get_stats_by_model` | `scope: str` | `dict` | 按 Model 分组统计 |
| `get_stats_range` | `start_ts, end_ts` | `dict` | 自定义时间范围统计 |
| `get_stats_by_model_range` | `start_ts, end_ts` | `dict` | 自定义范围按 Model 统计 |

### 5.2 设置管理
| 方法名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `get_settings` | - | `dict` | 获取所有设置 |
| `save_settings` | `settings: dict` | `bool` | 保存设置 |
| `get_model_price` | `model_id: str` | `dict` | 获取模型定价 |
| `add_model_price` | `model_id, prices` | `bool` | 添加/更新模型定价 |
| `delete_model_price` | `model_id: str` | `bool` | 删除自定义定价 |
| `reset_model_to_default` | `model_id: str` | `bool` | 重置为默认定价 |

### 5.3 数据导出
| 方法名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `export_csv` | `scope: str` | `str` | 导出 CSV 文件路径 |
| `export_csv_range` | `start_ts, end_ts` | `str` | 导出自定义范围 CSV |
| `export_to_clipboard` | `data: str` | `bool` | 复制到剪贴板 |

### 5.4 应用控制
| 方法名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `get_version` | - | `str` | 获取应用版本 |
| `refresh` | - | `bool` | 强制刷新数据 |
| `get_agent_status` | - | `dict` | 获取 Agent 状态 |
| `show_window` | `window_name: str` | - | 显示指定窗口 |
| `close_app` | - | - | 退出应用 |

---

## 6. 设置项清单

### 6.1 版本信息
- `version`: 设置文件版本 (str)

### 6.2 模型定价 (prices)
- `prices.default`: 默认定价 {input, output, caching, request}
- `prices.models`: 用户自定义模型定价 {model_id: {...}}
- `prices.deleted_models`: 用户删除的默认模型列表
- `prices.known_default_models`: 已知的默认模型列表

### 6.3 阈值设置 (thresholds)
- `thresholds.enabled`: 是否启用阈值提醒 (bool)
- `thresholds.daily_tokens`: 每日 Token 阈值 (int)
- `thresholds.daily_cost`: 每日成本阈值 (float)
- `thresholds.monthly_tokens`: 每月 Token 阈值 (int)
- `thresholds.monthly_cost`: 每月成本阈值 (float)
- `thresholds.monthly_reset_day`: 月度重置日 (1-31)

### 6.4 其他设置
- `refresh_interval`: 自动刷新间隔 (秒)
- `notifications_enabled`: 是否启用通知 (bool)

---

## 7. Agent 通信接口

通过 AgentClient (UDS/TCP) 与后台通信：

### 7.1 可用命令
- `status`: 获取 Agent 状态
- `stats`: 获取统计 (scope: today/7days/month)
- `stats_by_provider`: 按 Provider 统计
- `stats_by_model`: 按 Model 统计
- `stats_range`: 自定义时间范围统计
- `stats_by_model_range`: 自定义范围按 Model 统计
- `export_csv`: 导出 CSV
- `export_csv_range`: 导出自定义范围 CSV
- `refresh`: 强制刷新
- `shutdown`: 关闭 Agent

---

## 8. 统计数据结构

### 8.1 基本统计
```python
{
    "input": int,        # 输入 Token
    "output": int,       # 输出 Token
    "reasoning": int,    # 推理 Token
    "cache_read": int,   # 缓存读取
    "cache_write": int,  # 缓存写入
    "requests": int      # 请求数
}
```

### 8.2 Provider 分组
```python
{
    "provider_id": {
        "input": int,
        "output": int,
        ...
    }
}
```

### 8.3 Model 分组
```python
{
    "provider_id": {
        "model_id": {
            "input": int,
            "output": int,
            ...
        }
    }
}
```

---

## 9. 统计信息

### 代码统计
- **app.py**: 约 600+ 行代码
- **settings.py**: 约 585 行代码
- **uds_client.py**: 约 172 行代码

### 功能统计
- **窗口类**: 6 个 (MainStatsWindow, DetailsDialog, SettingsDialog, CustomRangeDialog, CustomRangeStatsDialog, ModelUpdateDialog)
- **Agent API 方法**: 15 个
- **设置项**: 15+ 项
- **Provider**: 4 个 (google, github-copilot, nvidia, opencode)
- **默认模型**: 16 个

---

## 10. 迁移注意事项

### 10.1 需要保留的功能
1. ✅ 系统托盘图标和菜单
2. ✅ 自动刷新机制
3. ✅ Agent 状态检查
4. ✅ 阈值提醒通知
5. ✅ 所有统计数据展示
6. ✅ 设置持久化
7. ✅ 数据导出功能

### 10.2 可以简化的部分
1. PyQt6 信号槽 → pywebview.api
2. QTimer → Python threading.Timer
3. QThread → Python threading
4. 复杂的窗口管理 → 单窗口 + 动态内容切换

### 10.3 需要重新实现
1. 所有对话框 → HTML 模态框
2. 表格展示 → HTML Table + CSS
3. 图表 → Chart.js
4. 系统托盘 → pystray

---

## 11. UI 设计建议

### 11.1 布局
- 左侧/顶部：导航菜单（统计/设置/导出）
- 主区域：动态内容（仪表盘/表格/表单）
- 底部：状态栏（Agent 状态/最后刷新时间）

### 11.2 颜色主题
- 深色主题（开发者工具风格）
- 主色：蓝色系
- 成功：绿色
- 警告：橙色
- 错误：红色

### 11.3 组件
- 卡片式统计展示
- 响应式表格
- 模态对话框
- Toast 通知

---

*生成时间: 2026-02-06*  
*用于: PyQt6 → pywebview 迁移规划*
