# PyQt → pywebview 迁移规划（草案）

## 项目信息
**请求时间**: 2026-02-06  
**请求者**: 用户  
**目标**: 将 PyQt 应用迁移到 pywebview

## 动机
- PyQt 应用臃肿
- 界面风格老旧
- pywebview 更轻量、现代化

## 项目信息更新

### 项目识别
**项目**: OpenCode Token Meter  
**当前架构**:
- `App/agent/` - 后台 agent（SQLite + 扫描器）
- `App/menubar/` - PyQt6 前端
- `OpenCodeTokenMeter.spec` - PyInstaller 打包配置

### 已确认需求
**界面类型**: ✅ 仪表盘/数据展示（表格 + 统计）  
**系统集成**: 系统托盘图标（确认）、文件系统访问（消息目录）  
**数据流**: Python(agent) → 前端展示  
**打包**: 单文件可执行（PyInstaller）

### 用户决策 ✅

#### 1. 前端技术栈选择
**选择：方案A - 原生 HTML/CSS/JS + Chart.js**

理由：
- 无需 Node.js 构建步骤
- 直接 PyInstaller 打包
- Chart.js 足够支持仪表盘需求
- 符合轻量目标

#### 2. UI 风格
**选择：重新设计 UI**

- 保持核心功能不变
- 重新设计布局和视觉风格
- 现代化仪表盘界面
- 优化表格展示

### 技术选型

| 组件 | 技术 | 用途 |
|------|------|------|
| 窗口框架 | pywebview | 替换 PyQt6 窗口 |
| 系统托盘 | pystray | 托盘图标和菜单 |
| 图表 | Chart.js | Token 使用趋势图 |
| 表格 | 原生 HTML Table + CSS | 统计数据展示 |
| 样式 | Tailwind CSS 或原生 CSS | 现代化 UI |
| 通信 | pywebview.api | Python-JS 桥梁 |

## 探索任务
- [x] 探索现有项目结构（进行中）
- [x] 分析 PyQt 使用情况（进行中）
- [x] 研究 pywebview 最佳实践（进行中）

## 下一步
等待探索结果 + 用户回答上述问题 → 生成详细迁移计划
