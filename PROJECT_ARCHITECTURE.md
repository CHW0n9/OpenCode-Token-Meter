# OpenCode Token Meter - Project Architecture (Updated)

## 项目概述

OpenCode Token Meter 是一个 macOS 菜单栏应用，用于追踪和计算来自 OpenCode 的 AI Token 使用情况。项目采用客户端-服务器架构，分为两个主要组件：
- **Agent**：后台服务，监控消息并存储到 SQLite 数据库
- **Menubar**：PyQt6 GUI 应用，显示统计信息并与 Agent 通信

---

## 目录结构（实际，用于 GitHub）

```
opencode-token-meter/
│
├─ 📄 核心文档
│  ├── LICENSE                  # GPL-3.0 许可证
│  ├── README.md                # 英文文档
│  ├── README_CN.md             # 中文文档
│  ├── CHANGELOG.md             # 版本历史
│  ├── AGENTS.md                # 开发者指南
│  └── .gitignore               # Git 忽略规则
│
├─ 🔨 构建脚本
│  ├── build.sh                 # 主构建脚本（PyInstaller）
│  └── create_dmg.sh            # DMG 创建脚本
│
└─ 📁 App/                      # 应用源代码目录
   │
   ├─ 🔧 agent/                 # 后台服务（Python）
   │  ├── agent/
   │  │  ├── __main__.py        # ← 入口点
   │  │  ├── db.py              # SQLite 数据库 + 去重逻辑
   │  │  ├── scanner.py         # 消息目录扫描器
   │  │  ├── uds_server.py      # Unix Domain Socket 服务器
   │  │  ├── config.py          # 路径和配置常量
   │  │  ├── util.py            # 工具函数
   │  │  ├── exporter.py        # 导出功能
   │  │  ├── cli.py             # CLI 接口
   │  │  └── __init__.py
   │  └── pyproject.toml        # 依赖声明
   │
   └─ 🖥️ menubar/               # GUI 应用（PyQt6）
      ├── menubar/
      │  ├── __main__.py        # ← 入口点
      │  ├── app.py             # 主应用逻辑（2100+ 行）
      │  │  ├── OpenCodeTokenMeter    # 菜单栏应用主类
      │  │  ├── MainStatsWindow       # 详细统计窗口
      │  │  ├── DetailsDialog         # 详细信息对话框
      │  │  ├── SettingsDialog        # 设置对话框
      │  │  ├── CustomRangeDialog     # 日期范围选择
      │  │  └── CustomRangeStatsDialog # 自定义范围统计
      │  ├── settings.py        # 设置管理和成本计算
      │  ├── uds_client.py      # Socket 客户端
      │  └── __init__.py
      │
      ├── resources/            # 应用资源
      │  ├── AppIcon.icns       # macOS 应用图标
      │  ├── icon_template.png  # 菜单栏图标（1x）
      │  ├── icon_template@2x.png # 菜单栏图标（2x）
      │  ├── Icon_*.png         # 各尺寸图标（32, 64, 128, 256, 512, 1024）
      │  ├── icon_512.png       # 512x512 图标
      │  └── AppIcon.iconset/   # macOS iconset 源文件
      │
      ├── opencode-menubar.spec # PyInstaller 构建配置
      ├── pyproject.toml        # 依赖声明
      ├── setup.py              # 安装脚本
      ├── cleanup-bundle.sh     # Qt 框架清理脚本
      └── hook-PyQt6.py         # PyInstaller 的 PyQt6 hook
```

---

## 核心组件详解

### 1. Agent（后台服务）

**位置**: `App/agent/agent/`

**职责**:
- 扫描 `~/.local/share/opencode/storage/message/` 目录
- 解析 JSON 消息文件，提取 Token 计数
- 使用 SQLite 存储数据（去重处理）
- 通过 Unix Domain Socket 提供数据接口

**关键文件**:

| 文件 | 行数 | 功能 |
|------|------|------|
| `__main__.py` | - | Agent 启动入口 |
| `db.py` | 500+ | SQLite 数据库管理和去重逻辑 |
| `scanner.py` | 200+ | 消息目录扫描和 JSON 解析 |
| `uds_server.py` | 150+ | Unix Domain Socket 服务器 |
| `config.py` | 50+ | 常量和路径定义 |
| `util.py` | 100+ | 工具函数 |
| `exporter.py` | 200+ | 数据导出功能 |

**数据库位置**:
```
~/Library/Application Support/OpenCode Token Meter/index.db
```

**消息来源**:
```
~/.local/share/opencode/storage/message/ses_XXXXXXX/
```

**Socket 位置**:
```
~/Library/Application Support/OpenCode Token Meter/agent.sock
```

### 2. Menubar GUI（图形界面）

**位置**: `App/menubar/menubar/`

**职责**:
- 在 macOS 菜单栏显示 Token 统计
- 提供详细分析和导出功能
- 与 Agent 通过 Socket 通信
- 管理用户设置（成本配置）

**关键文件**:

| 文件 | 行数 | 功能 |
|------|------|------|
| `__main__.py` | 50+ | GUI 应用启动 |
| `app.py` | 2100+ | 主应用逻辑和所有对话框 |
| `settings.py` | 400+ | 设置管理和成本计算 |
| `uds_client.py` | 100+ | Socket 客户端和网络通信 |

**子类详解** (`app.py`):

1. **OpenCodeTokenMeter** - 菜单栏应用主类
   - 构建菜单项
   - 管理菜单栏显示
   - 事件处理和窗口管理

2. **MainStatsWindow** - 详细统计窗口
   - 显示完整的 Token 统计表格
   - 支持 All/Provider/Model 视图切换
   - 导出功能

3. **DetailsDialog** - 详细信息对话框
   - 表格显示消息详情
   - 日期范围选择
   - 自定义导出

4. **SettingsDialog** - 设置对话框
   - Cost Meter 标签：模型选择和定价
   - Notification 标签：阈值和提醒配置

5. **CustomRangeDialog** - 日期范围选择
   - 日期选择器
   - 日期验证

6. **CustomRangeStatsDialog** - 自定义范围统计
   - 显示选定日期范围的统计

### 3. 资源文件

**位置**: `App/menubar/resources/`

**包含**:
- 应用图标（`AppIcon.icns`）- 用于 .app bundle
- 菜单栏图标（`icon_template.png`, `icon_template@2x.png`）
- 各尺寸图标（32x32 到 1024x1024）
- macOS iconset 源文件

---

## 技术栈

### 编程语言
- **Python 3.12** - 主要开发语言

### 框架和库
- **PyQt6** - GUI 框架
- **SQLite3** - 数据库
- **Unix Domain Sockets** - 进程间通信

### 构建工具
- **PyInstaller** - Python 应用编译
- **hdiutil** - macOS DMG 创建

### 开发工具
- **Black** - 代码格式化（88 字符行宽）
- **isort** - 导入排序
- **flake8** - 代码检查

---

## 构建流程

### 1. 本地开发运行

**终端 1 - 运行 Agent**:
```bash
cd App/agent
python3 -m agent
```

**终端 2 - 运行 Menubar**:
```bash
cd App/menubar
python3 -m menubar
```

### 2. 生产构建

**一键构建**:
```bash
./build.sh
```

**构建步骤**:
1. PyInstaller 编译 Agent → `opencode-agent` 二进制
2. PyInstaller 根据 `opencode-menubar.spec` 编译 Menubar → `.app` bundle
3. 将 Agent 复制到 `.app/Contents/Resources/bin/opencode-agent`
4. 执行 `cleanup-bundle.sh` 移除不必要的 Qt 模块
5. 执行 `create_dmg.sh` 创建 DMG 安装程序

**输出**:
- `build/OpenCodeTokenMeter-1.0.0.dmg` - 可分发的 DMG
- `App/menubar/dist/OpenCode Token Meter.app` - .app bundle

---

## 数据流

### 用户消息数据路径

```
OpenCode (用户消息)
    ↓
~/.local/share/opencode/storage/message/
    ↓
[Agent 的 scanner.py]
  读取 JSON 文件
  提取 Token 计数
    ↓
[Agent 的 db.py]
  去重处理
  存储到 SQLite
    ↓
~/Library/Application Support/OpenCode Token Meter/index.db
    ↓
[Menubar 的 uds_client.py]
  通过 Unix Socket 查询
    ↓
[Menubar 的 settings.py]
  计算成本（基于模型定价）
    ↓
[Menubar 的 app.py]
  显示在菜单栏和窗口
```

### 去重逻辑

**位置**: `App/agent/agent/db.py` 的 `_get_deduplicated_messages_subquery()`

**原因**: OpenCode 在会话之间复制消息，导致重复计数

**方法**:
1. 按以下字段分组消息:
   - `ts`（时间戳）
   - `role`（发送者角色）
   - `input`（输入内容）
   - `output`（输出内容）
   - `reasoning`（推理信息）
   - `cache_read`（缓存读取）
   - `cache_write`（缓存写入）
   - `provider_id`（提供商）
   - `model_id`（模型）

2. 每组保留 `msg_id` 最小的记录（字典顺序）

3. 所有查询和导出都基于去重后的数据

---

## 配置管理

### Agent 配置
**文件**: `App/agent/agent/config.py`

```python
DB_PATH = ~/Library/Application Support/OpenCode Token Meter/index.db
SOCKET_PATH = ~/Library/Application Support/OpenCode Token Meter/agent.sock
MESSAGE_DIR = ~/.local/share/opencode/storage/message/
```

### Menubar 配置
**文件**: `App/menubar/menubar/settings.py`

包含:
- 模型列表（OpenAI, Anthropic, DeepSeek, Ollama 等）
- 每个模型的 Token 定价
- 用户自定义设置（保存到本地）

---

## 构建配置

### PyInstaller Agent 配置
**文件**: `build.sh`

```bash
PyInstaller --onefile --name opencode-agent App/agent/agent/__main__.py
```

### PyInstaller Menubar 配置
**文件**: `App/menubar/opencode-menubar.spec`

关键配置:
- 入口: `menubar/__main__.py`
- 数据: `resources/` 文件夹（icons）
- 排除: 20+ 不必要的 Qt 模块（减少大小）
- 图标: `AppIcon.icns`
- Bundle ID: `com.opencode.token.menubar`

### DMG 创建
**文件**: `create_dmg.sh`

步骤:
1. 创建 200MB 临时 DMG
2. 挂载为可读写
3. 复制 .app bundle
4. 创建 Applications 符号链接
5. 添加 README.txt
6. 压缩转换为最终 DMG（约 49 MB）

---

## 部署和分发

### GitHub 发布
将整个 `Release 1.0.0` 目录内容上传到 GitHub

**包含文件**:
- ✅ 所有源代码（Python 文件）
- ✅ 配置文件（.spec, .toml）
- ✅ 构建脚本（.sh）
- ✅ 资源文件（icons）
- ✅ 文档（README, LICENSE, CHANGELOG）

**不包含**:
- ❌ `build/` 目录（编译输出）
- ❌ `__pycache__/`（Python 缓存）
- ❌ 用户数据（message/, part/）

### 用户安装

**方式 1: DMG 安装**
1. 下载 DMG 从 GitHub Release
2. 打开 DMG
3. 拖拽 .app 到 Applications 文件夹
4. 首次启动：点击"Open Anyway"（未签名警告）

**方式 2: 从源代码构建**
```bash
git clone https://github.com/.../opencode-token-meter.git
cd opencode-token-meter
./build.sh
# 输出: build/OpenCodeTokenMeter-1.0.0.dmg
```

---

## 性能和优化

### 数据库优化
- WAL 模式用于并发访问
- 去重索引加速聚合查询
- 参数化查询防止 SQL 注入

### UI 优化
- 异步加载防止阻塞
- 成本缓存避免重复计算
- 进度指示器显示长操作

### 构建优化
- PyInstaller 排除 20+ 不必要的 Qt 模块
- 最终 .app bundle ~88 MB
- 压缩 DMG ~49 MB

---

## 开发规范

### 代码风格
- Black: 88 字符行宽
- isort: 导入排序和分组
- flake8: 代码检查
- Type hints: 公开 API 添加类型提示

### SQL 安全
- 只使用参数化查询（`?` 占位符）
- 禁止 f-string 拼接 SQL

### 注释和文档
- 模块级注释说明用途
- 复杂逻辑添加行注释
- 公开函数添加 docstring

---

## 版本控制

### 版本号格式
遵循 Semantic Versioning: `MAJOR.MINOR.PATCH`
- **MAJOR**: 破坏性变更
- **MINOR**: 新功能（向后兼容）
- **PATCH**: Bug 修复

### 当前版本
- 版本: `1.0.0`
- 发布日期: 2025-02-01
- 状态: 生产就绪

### 更新流程
1. 更新版本号
2. 更新 CHANGELOG.md
3. 更新 build.sh 中的版本
4. 运行 ./build.sh 生成新 DMG
5. 在 GitHub 创建新 Release
6. 标签: `v1.0.0`, `v1.1.0` 等

---

## 故障排除

### 常见问题

**Agent 启动失败**
- 检查 `~/.local/share/opencode/storage/message/` 是否存在
- 查看 Socket 文件是否可写
- 检查系统日志: `log stream --predicate 'process == "opencode-agent"'`

**构建失败**
- 验证 Python 3.12+ 已安装
- 验证 AppIcon.icns 存在
- 验证 opencode-menubar.spec 中的路径正确

**数据未显示**
- 确保消息文件存在
- 检查数据库是否创建
- 重启应用

---

## 参考文档

- **用户文档**: `README.md` (English), `README_CN.md` (中文)
- **开发指南**: `AGENTS.md`
- **版本历史**: `CHANGELOG.md`
- **许可证**: `LICENSE` (GPL-3.0)

