<h1 align="center">OpenCode Token 计量器</h1>
<p align="center">
  <a href="https://github.com/CHW0n9/OpenCode-Token-Meter/releases">
    <img src="assets/logo.png" alt="Project Logo" width="128">
  </a>
</p>

**OpenCode Token 计量器** 是一个轻量级的 macOS/Windows 菜单栏应用，使用 Python 和 pywebview 构建，用于监控 [OpenCode](https://opencode.ai) 的 Token 使用量、成本和分析数据。

![Dashboard Screenshot](assets/Screenshot_dashboard.png)

**注**：本项目完全使用 [OpenCode](https://opencode.ai) 开发。本项目不是 OpenCode 团队官方开发，且不存在任何隶属关系。

---

## 🚀 功能特点

- **📊 实时 Token 追踪** - 通过扫描本地消息文件和新的 `opencode.db` 实时监控 AI 交互产生的 Token 使用情况。
- **💰 成本计算** - 基于特定模型的定价（Anthropic, Google, GitHub Copilot, NVIDIA 等）自动计算成本。
- **📈 详细数据分析** - 按供应商、模型和时间范围查看 Token 使用情况，配有高对比度的图表展示 (Chart.js)。
- **⚙️ 可自定义设置** - 设置成本阈值，管理自定义模型定价，并配置通知偏好。
- **📥 数据导出** - 支持将自定义日期范围的使用数据导出为 CSV 或复制到剪贴板。
- **🔄 现代架构** - 后台代理和统计工作进程作为嵌入式线程在单个进程内运行。
- **🔐 隐私保护** - 所有数据存储在本地 SQLite 数据库中，并配有强大的去重逻辑。
- **💻 跨平台支持** - 为 macOS（菜单栏）和 Windows（系统托盘）提供原生体验。

---

## 📦 安装方法

### 选项 1：预构建二进制文件（推荐）

#### Windows
1. 从 [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases) 下载 `OpenCodeTokenMeter-1.1.1.exe`。
2. 运行可执行文件即可启动应用。应用将出现在系统托盘中。

#### macOS
1. 从 [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases) 下载 `OpenCodeTokenMeter-1.1.1.dmg`。
2. 将 "OpenCode Token Meter.app" 拖入您的应用程序 (Applications) 文件夹。
3. **安全说明**：由于应用未签名，首次启动时您可能需要在 **系统设置 → 隐私与安全** 中点击 **“仍要打开”**。

---

### 选项 2：从源代码构建

#### 依赖要求
- Python 3.9+
- 推荐使用：Conda 环境 `opencode`。

```bash
# Windows
pip install pyinstaller pywebview pystray pillow pyperclip win10toast

# macOS
pip install pyinstaller pywebview rumps pillow pyperclip pyobjc-framework-Cocoa
```

#### 构建命令
本项目使用 **单一统一的 spec 文件** (`OpenCodeTokenMeter.spec`)，支持自动平台检测。

**Windows:**
```powershell
.\build_windows.bat
```
输出：`dist\OpenCodeTokenMeter.exe`

**macOS:**
```bash
./build.sh
```
输出：`dist/OpenCode Token Meter.app` 和 `.dmg`

---

## 🏗️ 项目架构

### 目录结构
```
opencode-token-meter/
├── 📄 根目录文档
│   ├── LICENSE                  # GPL-3.0 许可证
│   ├── README.md                # 英文文档
│   ├── README_CN.md             # 中文文档
│   ├── CHANGELOG.md             # 版本历史
│   └── AGENTS.md                # 开发者指南
├── 🔨 构建系统
│   ├── OpenCodeTokenMeter.spec   # 统一的 PyInstaller 配置
│   ├── build.sh                 # macOS 构建脚本
│   └── build_windows.bat        # Windows 构建脚本
└── 📁 App/                      # 源代码
    ├── agent/                   # 消息追踪与数据库逻辑 (Agent, Stats Worker)
    └── webview_ui/              # 基于 Web 的前端 (pywebview)
        ├── backend/             # Python-JS API 桥接与设置管理
        └── web/                 # HTML/CSS/JS (Tailwind, Chart.js, Lato 字体)
```

### 数据流
1. **扫描器 (Scanner)**：定期检查 `~/.local/share/opencode/storage/message/` (旧版) 和 `opencode.db` (新版) 中的 AI 消息。
2. **数据库 (Database)**：解析 JSON 数据并将去重后的记录存储在本地 SQLite 数据库 (`index.db`) 中。
3. **桥接器 (Bridge)**：`JsApi` 桥接器从 `index.db` 获取数据并提供给 Webview UI。
4. **用户界面 (UI)**：使用响应式界面和加粗的 **Lato (900)** 字体显示统计数据和图表。

---

## ⚙️ 配置说明

- **数据库位置**：
  - macOS: `~/Library/Application Support/OpenCode Token Meter/index.db`
  - Windows: `%APPDATA%\OpenCode Token Meter\index.db`
- **模型定价**：在 **设置 → 成本计量** 中覆盖默认定价。支持输入、输出、缓存和单次请求定价。

---

## 🤝 参与贡献

请参阅 [AGENTS.md](AGENTS.md) 获取完整的开发者指南，包括：
- 运行开发模式 (`python App/webview_ui/main_tray.py --debug`)。
- SQL 安全性（始终使用参数化查询）。
- 发布前的手动验证清单。

---

## 📜 许可证

本项目采用 GNU General Public License v3.0 许可 - 详情请参阅 [LICENSE](LICENSE) 文件。

---

## 致谢

- 完全使用 [OpenCode](https://opencode.ai) 开发 - 一个用于编程的 AI 驱动终端界面。
- 本项目使用了 [Lato](https://fonts.google.com/specimen/Lato) 字体，由 Łukasz Dziedzic 设计，采用 SIL Open Font License 许可。
