<h1 align="center">OpenCode Token 计量器</h1>
<p align="center">
  <a href="https://github.com/CHW0n9/OpenCode-Token-Meter/releases">
    <img src="assets/logo.png" alt="Project Logo" width="128">
  </a>
</p>

**OpenCode Token 计量器**是一个轻量级的跨平台（macOS、Windows）菜单栏应用程序，可追踪来自 [OpenCode](https://opencode.ai) 的模型 Token 使用情况。它扫描消息历史、计算不同 AI 模型的成本，并提供具有直观界面的详细使用统计。

**注**：本项目完全使用 [OpenCode](https://opencode.ai) 开发。且本项目不是 OpenCode 团队官方开发，且存在隶属关系。

---

## 功能特点

- **📊 实时 Token 追踪** - 监控来自 AI 交互的输入和输出 Token
- **💰 成本计算** - 基于模型特定价格的自动成本计算
- **📈 详细分析** - 按提供商、模型和时间范围查看 Token 使用情况
- **⚙️ 可自定义设置** - 设置成本阈值和通知偏好
- **📥 Token 使用导出** - 导出自定义日期范围的使用数据
- **🔄 自动更新** - 内置后台代理持续监控您的消息目录
- **🔐 隐私保护** - 所有数据存储在本地 SQLite 数据库中
- **⚡ 轻量级** - 菜单栏/系统托盘占用最小资源
- **💻 跨平台** - 统一支持 macOS 和 Windows

---

## 安装

### 方式一：预编译二进制文件（推荐）

#### Windows
1. 从 [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases) 下载 `OpenCodeTokenMeter.exe`
2. 直接运行可执行文件即可启动应用。
3. 应用将出现在您的系统托盘中。

#### macOS
1. 从 [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases) 下载 `OpenCodeTokenMeter-1.0.1.dmg`
2. 双击 `.dmg` 文件打开
3. 将 "OpenCode Token Meter.app" 拖至应用程序文件夹
4. 打开应用程序文件夹，双击 "OpenCode Token Meter.app"

**重要：在 macOS 上运行未签名应用**
由于应用未进行代码签名，您可能会在首次启动时看到安全警告。请前往 **系统设置 → 隐私与安全**，为 OpenCode Token Meter 点击 **"仍要打开"**。

### 方式二：从源代码构建

#### 统一构建系统
本项目使用**单个统一的 spec 文件** (`OpenCodeTokenMeter.spec`)，支持在 Windows 和 macOS 上自动检测平台并进行构建。

#### 要求：
- Python 3.9+
- PyQt6
- PyInstaller

#### 快速构建步骤：

**Windows:**
```powershell
.\build_windows.bat
```
输出：`dist\OpenCodeTokenMeter.exe`

**macOS:**
```bash
./build.sh
```
输出：`dist/OpenCode Token Meter.app`

#### 构建产物：
- **Windows**: 单个统一的可执行文件 (`.exe`)，包含菜单栏 UI 和内置 Agent。
- **macOS**: 原生 `.app` 包，包含菜单栏 UI 和内置 Agent。

#### 构建关键特性：
- **内置 Agent**: 后台代理现在作为主应用内的**后台线程**运行。不再需要单独的 Agent 进程或可执行文件！
- **平台自动检测**: 构建系统会自动检测您的操作系统并使用正确的图标（Windows 使用 `.ico`，macOS 使用 `.icns`）。
- **单文件分发**: 真正的单文件分发（macOS 除外，它使用标准的 .app 包格式）。

---

## Token 数据位置

该应用扫描您的 OpenCode 消息目录来计算 Token 使用情况。消息读取自：

- **macOS**: `~/.local/share/opencode/storage/message/`
- **Windows**: `%LOCALAPPDATA%\opencode\storage\message\`

应用将其配置和计算的指标存储在本地：

- **macOS**: `~/Library/Application Support/OpenCode Token Meter/`
- **Windows**: `%APPDATA%\OpenCode Token Meter\`

---

## 项目架构

```
OpenCode Token 计量器
│
├── App/
│   ├── agent/                    # 后台逻辑 (Python)
│   │   ├── agent/db.py          # SQLite 数据库，包含去重逻辑
│   │   ├── agent/scanner.py     # 消息目录扫描器
│   │   ├── agent/config.py      # 平台感知的配置
│   │
│   └── menubar/                  # PyQt6 GUI 应用
│       ├── menubar/app.py       # 主应用逻辑、对话框、UI
│       ├── menubar/settings.py  # 平台感知的设置管理
│       ├── menubar/uds_client.py # 套接字客户端 (Windows 上回退至 TCP)
│       └── menubar/resources/   # 应用图标 (.ico, .icns, .png)
│
├── OpenCodeTokenMeter.spec       # 统一构建规范
├── build_windows.bat             # Windows 构建脚本
├── build.sh                      # macOS 构建脚本
└── AGENTS.md                     # 开发者指南
```

### 关键组件

**内置 Agent**
- 作为主进程内的后台线程运行。
- 每隔几秒扫描一次 OpenCode 消息目录。
- 解析 JSON 消息文件并提取 Token 计数。
- 去重消息以处理 OpenCode 的会话复制。
- 将数据存储在本地 SQLite 数据库 (`index.db`)。

**菜单栏 / 系统托盘应用**
- 针对 macOS (菜单栏) 和 Windows (系统托盘) 的原生 UI。
- 显示实时统计数据 (Tokens, 请求数, 成本)。
- 具有按提供商/模型分类的综合详细信息窗口。
- 用于自定义定价和通知阈值的设置对话框。
- 数据导出功能 (CSV/剪贴板)。

**去重系统**
- 当 OpenCode 在会话之间复制消息时防止重复计算
- 按以下条件分组消息：时间戳、角色、输入、输出、推理、缓存信息、提供商、模型
- 使用字典顺序最小的 `msg_id` 选择规范记录
- 所有聚合和导出使用去重的数据

---

## 使用方法

### 启动应用

1. 启动 "OpenCode Token Meter"。
2. 应用图标将出现在 macOS 菜单栏（右上方）或 Windows 系统托盘（右下方）。
3. 内置 Agent 将自动启动并开始同步数据。

### 界面显示

应用在 2×3 的网格中显示最多 6 个指标：

**第 1 行：**
- **In** - 总输入 Token
- **Req** - 总请求数

**第 2 行：**
- **Out** - 总输出 Token
- **Cost** - 计算的成本 (美元)

**第 3 行 (可选)：**
- **Token%** - 当前输入 Token 占阈值的百分比
- **Cost%** - 当前成本占阈值的百分比

只有在设置中启用了 Token/成本阈值时，第 3 行才会显示。

### 主窗口

点击图标即可打开主窗口，包含：
- 详细统计数据
- 按提供商和模型分类的细分
- 全部/提供商/模型视图标签
- 用于导出的日期范围选择器

---

## 配置

### 模型定价

应用包含了一些热门提供商的默认定价：
- **Google**: Gemini 系列模型
- **OpenCode Zen**: GLM 4.7
- **Github Copilot**: Claude 和 GPT 系列模型 (按照 premium requests 收费)
- **其他**: 任何自定义提供商/模型

您可以在 **设置 → 成本计量** 中添加自定义模型或覆盖默认定价。自定义定价的模型将被标记为 **(customized)**。

### 数据库

SQLite 数据库 (`index.db`) 将自动创建。它包含：
- `messages` 表，包含 Token 计数和元数据。
- `idx_dedup` 索引，用于快速去重。
- 视图追踪和会话信息。

---

## 故障排除

### 未显示 Token 数据

1. **检查 OpenCode 消息**: 确保扫描目录中存在消息文件。
2. **检查数据库**: 使用 `sqlite3` 验证 `index.db` 的内容。
3. **重启应用**: 退出并重新启动，以重新初始化后台 Agent。

### Windows: 应用未出现在系统托盘

- 确保没有其他实例正在运行。
- 在任务管理器中检查 `OpenCodeTokenMeter.exe`。

### macOS: 应用被安全设置拦截

- 前往系统设置 → 隐私与安全，允许应用运行。

---

## 开发

### 快速设置

```bash
# 克隆并导航
git clone https://github.com/chw0n9/opencode-token-meter.git
cd opencode-token-meter

# 阅读开发者指南以获取平台特定说明
cat AGENTS.md
```

### 开发运行

```bash
# 从项目根目录执行
cd App/menubar
python -m menubar
```

### 为分发构建

**Windows:**
```powershell
.\build_windows.bat
```

**macOS:**
```bash
./build.sh
```

### 代码风格

- Python 3.9+
- 遵循 PEP 8，使用 Black (88 字符行宽)
- 使用 isort 组织导入
- 公开 API 的类型提示
- 仅使用参数化 SQL 查询

更多信息请参见 [AGENTS.md](AGENTS.md)。

---

## 数据库安全

- 所有 SQL 查询都使用参数化占位符 (`?`) 防止注入。
- SQLite 使用 WAL 模式实现安全的并发访问。
- 去重查询防止在不同会话间重复计算消息。
- 所有数据存储在本地 (无网络传输)。

---

## 许可证

本项目在 GNU 通用公共许可证 v3.0 下许可 - 有关详细信息，请参见 [LICENSE](LICENSE) 文件。

---

## 致谢

完全使用 [OpenCode](https://opencode.ai) 开发 - 一个用于编码的 AI 驱动的终端界面。

[OpenCode 仓库](https://github.com/anomalyco/opencode)

---

## 截图

- **菜单栏显示 (macOS)**: 2×3 的 Token 指标网格。
- **主窗口**: 详细统计数据和模型细分。
- **设置对话框**: 模型定价和阈值配置。

---

## 支持与反馈

- 报告错误：[GitHub Issues](https://github.com/chw0n9/opencode-token-meter/issues)
- 功能请求：[GitHub Discussions](https://github.com/chw0n9/opencode-token-meter/discussions)

---

## 更新日志

有关版本历史和更新，请参见 [CHANGELOG.md](CHANGELOG.md)。
