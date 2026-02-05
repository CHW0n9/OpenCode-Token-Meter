# Build 文件依赖清单

## build.sh 使用的文件

当用户运行 `./build.sh` 时，以下文件会被使用：

### 必需的源代码文件

#### Agent (后台服务)
- `App/agent/agent/__main__.py` - Agent 入口点
- `App/agent/agent/db.py` - SQLite 数据库逻辑和去重
- `App/agent/agent/scanner.py` - 消息目录扫描器
- `App/agent/agent/uds_server.py` - Unix Domain Socket 服务器
- `App/agent/agent/config.py` - 配置和路径常量
- `App/agent/agent/util.py` - 工具函数
- `App/agent/agent/__init__.py` - 包初始化

#### Menubar GUI (图形界面)
- `App/menubar/menubar/__main__.py` - GUI 入口点
- `App/menubar/menubar/app.py` - 主应用逻辑（2100+ 行）
  - OpenCodeTokenMeter 类：菜单栏应用
  - MainStatsWindow 类：详细统计窗口
  - DetailsDialog 类：详细信息对话框
  - SettingsDialog 类：设置对话框
  - CustomRangeDialog 类：日期范围选择
  - CustomRangeStatsDialog 类：自定义范围统计
- `App/menubar/menubar/settings.py` - 设置管理和成本计算
- `App/menubar/menubar/uds_client.py` - Socket 客户端
- `App/menubar/menubar/__init__.py` - 包初始化

### 必需的配置文件

- `App/agent/pyproject.toml` - Agent 依赖声明
- `App/menubar/pyproject.toml` - Menubar 依赖声明
- `App/menubar/opencode-menubar.spec` - PyInstaller 构建配置

### 必需的资源文件

- `App/menubar/resources/AppIcon.icns` - macOS 应用图标
- `App/menubar/resources/icon_template.png` - 菜单栏图标 (1x)
- `App/menubar/resources/icon_template@2x.png` - 菜单栏图标 (2x)
- `App/menubar/resources/Icon_*.png` - 各尺寸图标

### 必需的脚本

- `build.sh` - 主构建脚本
  - 使用 PyInstaller 编译 Agent
  - 使用 PyInstaller 编译 Menubar（根据 .spec 文件）
  - 将 Agent 复制到 Menubar .app bundle
  - 调用 cleanup-bundle.sh 清理 Qt 框架
  - 调用 create_dmg.sh 创建 DMG

- `create_dmg.sh` - DMG 安装程序创建脚本
  - 创建临时 DMG
  - 复制 .app 到 DMG
  - 创建 Applications 符号链接
  - 转换为压缩 DMG

- `App/menubar/cleanup-bundle.sh` - 可选的 Qt 框架清理
  - 移除不必要的 Qt 模块以减少大小

### 必需的文档

- `LICENSE` - GPL-3.0 许可证
- `README.md` - 英文文档
- `README_CN.md` - 中文文档
- `CHANGELOG.md` - 版本历史
- `AGENTS.md` - 开发者指南
- `.gitignore` - Git 忽略规则

---

## 构建流程

```
build.sh
├── 验证 Agent 目录位置
├── 验证 Menubar 目录位置
├── 使用 PyInstaller 编译 Agent
│   └── App/agent/agent/__main__.py → opencode-agent 二进制
├── 使用 PyInstaller 编译 Menubar
│   ├── 读取 App/menubar/opencode-menubar.spec
│   ├── 编译 App/menubar/menubar/__main__.py
│   ├── 包含资源文件（resources/）
│   └── 生成 .app bundle
├── 将 Agent 二进制复制到 .app/Contents/Resources/bin/
├── 调用 cleanup-bundle.sh 清理框架
└── 调用 create_dmg.sh 创建 DMG
    ├── hdiutil create - 创建 DMG
    ├── cp App bundle 到 DMG
    ├── hdiutil convert - 压缩 DMG
    └── 生成 OpenCodeTokenMeter-1.0.0.dmg
```

---

## 不包含在 Release 中的文件

以下文件和目录不应上传到 GitHub（已由 .gitignore 排除）：

- `build/` - 编译输出目录
- `App/menubar/dist/` - PyInstaller 输出
- `App/menubar/build/` - PyInstaller 中间文件
- `App/agent/build/` - PyInstaller 中间文件
- `__pycache__/` 目录
- `.DS_Store` - macOS 系统文件
- `message/` - 用户测试数据
- `part/` - 用户测试数据
- `archieve/` - 旧版本
- `logo design/` - 设计源文件

---

## 文件大小统计

| 项目 | 大小 |
|------|------|
| 完整源代码 | ~2.4 MB |
| Python 源文件 | ~16 个 |
| 资源文件 | ~21 个 |
| 编译后的 .app | ~88 MB |
| 最终 DMG | ~49 MB |

---

## 用户如何构建

用户从 GitHub 克隆代码后：

```bash
cd opencode-token-meter
./build.sh
```

构建会自动：
1. 安装依赖（PyInstaller, PyQt6）
2. 编译 Agent 和 Menubar
3. 创建 .app 
4. 打包成 DMG

最终输出：
- `build/OpenCodeTokenMeter-1.0.0.dmg` - 可分发的安装程序

---

## GitHub 上传清单

这个 Release 1.0.0 文件夹中的所有文件都应该上传到 GitHub：

- ✅ 所有 .py 源文件
- ✅ 所有 .toml 配置文件  
- ✅ opencode-menubar.spec
- ✅ 所有 .sh 脚本
- ✅ 所有资源文件（icons, images）
- ✅ 所有文档（README, LICENSE, CHANGELOG, etc.）
- ✅ .gitignore 配置

```
Release 1.0.0/
├── README.md               ✅
├── README_CN.md            ✅
├── CHANGELOG.md            ✅
├── LICENSE                 ✅
├── AGENTS.md               ✅
├── .gitignore              ✅
├── build.sh                ✅
├── create_dmg.sh           ✅
└── App/
    ├── agent/
    │   ├── agent/
    │   │   ├── __main__.py ✅
    │   │   ├── db.py       ✅
    │   │   ├── scanner.py  ✅
    │   │   ├── uds_server.py ✅
    │   │   ├── config.py   ✅
    │   │   ├── util.py     ✅
    │   │   └── __init__.py ✅
    │   └── pyproject.toml  ✅
    └── menubar/
        ├── menubar/
        │   ├── __main__.py ✅
        │   ├── app.py      ✅
        │   ├── settings.py ✅
        │   ├── uds_client.py ✅
        │   └── __init__.py ✅
        ├── resources/
        │   ├── AppIcon.icns ✅
        │   ├── icon_template.png ✅
        │   ├── icon_template@2x.png ✅
        │   ├── Icon_*.png  ✅
        │   └── AppIcon.iconset/ ✅
        ├── opencode-menubar.spec ✅
        ├── pyproject.toml  ✅
        ├── setup.py        ✅
        ├── cleanup-bundle.sh ✅
        └── hook-PyQt6.py   ✅
```

