# OpenCode Token 计量器


**OpenCode Token 计量器**是一个轻量级的 macOS 菜单栏应用程序，可追踪来自 [OpenCode](https://opencode.ai) 的模型 Token 使用情况。它监控消息历史、计算不同 AI 模型的成本，并提供具有直观界面的详细使用统计。

**注**：本项目完全使用 [OpenCode](https://opencode.ai) 开发。且该项目不是 OpenCode 团队官方开发，且不存在隶属关系。

---

## 功能特点

- **📊 实时 Token 追踪** - 监控来自 AI 交互的输入和输出 Token
- **💰 成本计算** - 基于模型特定价格的自动成本计算
- **📈 详细分析** - 按提供商、模型和时间范围查看 Token 使用情况
- **⚙️ 可自定义设置** - 设置成本阈值和通知偏好
- **📥 Token 使用导出** - 导出自定义日期范围的使用数据
- **🔄 自动更新** - 后台代理持续监控您的消息目录
- **🔐 隐私保护** - 所有数据存储在本地 SQLite 数据库中
- **⚡ 轻量级** - 菜单栏占用最小资源

---

## 安装

### 方式一：DMG 安装程序（推荐）

1. 从 [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases) 下载 `OpenCodeTokenMeter-1.0.0.dmg`
2. 双击 `.dmg` 文件打开
3. 将 "OpenCode Token Meter.app" 拖至应用程序文件夹
4. 打开应用程序文件夹，双击 "OpenCode Token Meter.app"

#### 重要：在 macOS 上运行未签名应用

由于应用未进行代码签名，您可能会在首次启动时看到安全警告：

**如果看到"无法打开，因为它来自未识别的开发者"消息：**

1. 打开系统设置 → 隐私与安全
2. 向下滚动找到 "OpenCode Token Meter.app"
3. 点击应用名称旁的 "仍要打开"
4. 重新启动应用

或在终端运行：
```bash
xattr -d com.apple.quarantine "/Applications/OpenCode Token Meter.app"
```

### 方式二：从源代码构建

**要求：**
- Python 3.12+
- PyQt6
- SQLite3

**步骤：**

```bash
# 克隆仓库
git clone https://github.com/chw0n9/opencode-token-meter.git
cd opencode-token-meter

# 构建应用
./build.sh

# DMG 文件将生成在 build/ 目录
```

---

## Token 数据位置

该应用扫描您的 OpenCode 消息目录来计算 Token 使用情况。消息读取自：

```
~/.local/share/opencode/storage/message/
```

每个 OpenCode 会话创建一个类似 `ses_XXXXXXX/` 的子目录，其中包含具有 Token 计数数据的 JSON 消息文件。

应用将其配置和计算的指标存储在本地：

```
~/Library/Application Support/OpenCode Token Meter/index.db
```

---

## 项目架构

```
OpenCode Token 计量器
│
├── App/
│   ├── agent/                    # 后台服务 (Python)
│   │   ├── agent/__main__.py    # 入口点
│   │   ├── agent/db.py          # SQLite 数据库，包含去重逻辑
│   │   ├── agent/scanner.py     # 消息目录扫描器
│   │   ├── agent/uds_server.py  # Unix 域套接字服务器
│   │   ├── agent/config.py      # 配置路径
│   │   └── pyproject.toml
│   │
│   └── menubar/                  # PyQt6 GUI 应用
│       ├── menubar/__main__.py  # 入口点
│       ├── menubar/app.py       # 主应用逻辑、对话框、UI
│       ├── menubar/settings.py  # 设置管理
│       ├── menubar/uds_client.py # 套接字客户端
│       ├── menubar/resources/   # 应用图标和资源
│       ├── setup.py
│       └── pyproject.toml
│
├── build.sh                      # 构建脚本 (PyInstaller)
└── AGENTS.md                     # 开发者指南
```

### 关键组件

**Agent（后台服务）**
- 通过 Unix 域套接字在后台持续运行
- 扫描 `~/.local/share/opencode/storage/message/` 目录
- 解析 JSON 消息文件并提取 Token 计数
- 去重消息（处理 OpenCode 的会话复制）
- 将数据存储在本地 SQLite 数据库

**菜单栏应用（GUI）**
- 在 macOS 菜单栏中显示 Token 使用和成本统计
- 显示输入 Token、请求、输出 Token 和计算的成本
- 具有详细统计细分的主窗口
- 用于成本配置和阈值的设置对话框
- 自定义日期范围导出功能
- 具有加载动画的异步加载

**去重系统**
- 当 OpenCode 在会话之间复制消息时防止重复计算
- 按以下条件分组消息：时间戳、角色、输入、输出、推理、缓存信息、提供商、模型
- 使用字典顺序最小的 `msg_id` 选择规范记录
- 所有聚合和导出使用去重的数据

---

## 使用方法

### 启动应用

1. 从应用程序文件夹启动 "OpenCode Token 计量器"
2. 应用图标出现在 macOS 菜单栏（右上方）
3. Agent 服务自动在后台启动
4. Token 数据每几秒同步一次

### 菜单栏显示

菜单栏显示最多 6 个指标，排列为 2×3 网格：

**第 1 行：**
- **In** - 总输入 Token
- **Req** - 总请求数

**第 2 行：**
- **Out** - 总输出 Token
- **Cost** - 计算的成本（美元）

**第 3 行（可选）：**
- **Token%** - 当前输入 Token 相对于阈值的百分比
- **Cost%** - 当前成本相对于阈值的百分比

只有在设置中启用了 Token/成本阈值时，第 3 行才会显示。

### 主窗口

点击菜单栏图标打开主窗口：
- 详细统计
- 按提供商和模型分类
- 全部/提供商/模型视图标签
- 用于导出的日期范围选择器

### 设置

**成本计量标签：**
- 从预设模型中选择（Google、Anthropic等）
- 或选择"自定义模型"来手动输入提供商/模型名称
- 查看并调整每个模型的定价

**通知标签：**
- 启用/禁用 Token 使用提醒
- 设置 Token 阈值和成本阈值
- 可选：自定义通知频率

### 导出数据

1. 在详细信息对话框中点击"自定义范围"
2. 选择开始和结束日期
3. 查看该时期的统计数据
4. 导出到剪贴板或文件

---

## 配置

### 模型定价

该应用包含流行模型的默认定价：
- **Google**: Gemini 3 models
- **OpenCode Zen**: GLM 4.7
- **Github Copilot**: Claude Sonnet 4.5, GPT 5.2 Codex (按照 premium requests 收费)
- **其他**：任何自定义提供商/模型

您可以在设置 → 成本计量 → "自定义模型"中添加自定义模型

### 数据库

SQLite 数据库自动创建在：
```
~/Library/Application Support/OpenCode Token Meter/index.db
```

其中包含：
- 消息表，包含 Token 计数和元数据
- 用于快速查询的去重索引
- 视图追踪和会话信息

---

## 故障排除

### Agent 未启动

如果 Agent 启动失败：

1. 检查消息目录是否存在：
   ```bash
   ls -la ~/.local/share/opencode/storage/message/
   ```

2. 验证套接字路径是否可写：
   ```bash
   ls -la ~/Library/Application\ Support/OpenCode\ Token\ Meter/
   ```

3. 检查系统日志：
   ```bash
   log stream --predicate 'process == "opencode-agent"'
   ```

### 未显示 Token 数据

1. 确保 OpenCode 消息存在：
   ```bash
   ls ~/.local/share/opencode/storage/message/*/
   ```

2. 检查数据库：
   ```bash
   sqlite3 ~/Library/Application\ Support/OpenCode\ Token\ Meter/index.db "SELECT COUNT(*) FROM messages;"
   ```

3. 重启应用（退出并重新启动）

### 应用崩溃

请报告问题时提供：
- macOS 版本
- 应用版本号
- 重现步骤
- 系统日志

---

## 开发

### 快速设置

```bash
# 克隆并导航
git clone https://github.com/chw0n9/opencode-token-meter.git
cd opencode-token-meter

# 阅读开发者指南
cat AGENTS.md
```

### 开发运行

```bash
# 终端 1：运行 Agent
cd App/agent
python3 -m agent

# 终端 2：运行菜单栏应用
cd App/menubar
python3 -m menubar
```

### 为分发构建

```bash
./build.sh
# DMG 将位于：build/OpenCodeTokenMeter-1.0.0.dmg
```

### 代码风格

- Python 3.12+
- 遵循 PEP 8，使用 Black（88 字符行宽）
- 使用 isort 组织导入
- 公开 API 的类型提示
- 仅使用参数化 SQL 查询

有关完整的开发者指南，请参见 [AGENTS.md](AGENTS.md)。

---

## 数据库安全

- 所有 SQL 查询都使用参数化占位符（`?`）防止注入
- SQLite 使用 WAL 模式实现安全的并发访问
- 去重查询防止消息重复计算
- 所有数据存储在本地（无网络传输）

---

## 许可证

本项目在 GNU 通用公共许可证 v3.0 下许可 - 有关详细信息，请参见 [LICENSE](LICENSE) 文件。

---

## 致谢

完全使用 [OpenCode](https://opencode.ai) 开发 - 一个用于编码的 AI 驱动的终端界面。

[OpenCode 仓库](https://github.com/anomalyco/opencode)

---

## 截图

[截图占位符]

*在此添加截图：*
- 菜单栏显示 Token 指标
- 具有详细统计的主窗口
- 带有模型选择的设置对话框
- 自定义范围导出对话框

---

## 支持与反馈

- 报告错误：[GitHub Issues](https://github.com/chw0n9/opencode-token-meter/issues)
- 功能请求：[GitHub Discussions](https://github.com/chw0n9/opencode-token-meter/discussions)

---

## 更新日志

有关版本历史和更新，请参见 [CHANGELOG.md](CHANGELOG.md)。
