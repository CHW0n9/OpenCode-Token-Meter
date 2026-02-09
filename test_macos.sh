#!/bin/bash
# macOS 测试脚本 - OpenCode Token Meter pywebview 版本
# 在 macOS 图形界面环境下执行

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "   OpenCode Token Meter - macOS 测试脚本"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取项目根目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "📁 项目目录: $PROJECT_DIR"
echo ""

# 检查是否在 conda 环境中
OPENCODE_PYTHON="/Users/chwong/miniforge3/envs/opencode/bin/python"
if [ -f "$OPENCODE_PYTHON" ]; then
    PYTHON_CMD="$OPENCODE_PYTHON"
    echo -e "${GREEN}✅ 使用指定的 opencode 环境 Python: $PYTHON_CMD${NC}"
else
    PYTHON_CMD="python3"
    if [ -z "$CONDA_DEFAULT_ENV" ]; then
        echo -e "${YELLOW}⚠️  未检测到 conda 环境且未找到 $OPENCODE_PYTHON${NC}"
        echo "建议激活 opencode 环境: conda activate opencode"
        echo ""
        read -p "是否继续? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# 1. 安装依赖
echo "${BLUE}1. 检查/安装依赖...${NC}"
echo "---------------------------------------------------------------"
pip install -q pywebview pystray pillow pyperclip 2>/dev/null || {
    echo -e "${YELLOW}⚠️  部分依赖可能已安装${NC}"
}
echo -e "${GREEN}✅ 依赖检查完成${NC}"
echo ""

# 2. 语法检查
echo "${BLUE}2. 执行语法检查...${NC}"
echo "---------------------------------------------------------------"
$PYTHON_CMD -m py_compile App/webview_ui/main.py && echo -e "${GREEN}✅ main.py${NC}"
$PYTHON_CMD -m py_compile App/webview_ui/backend/api.py && echo -e "${GREEN}✅ api.py${NC}"
$PYTHON_CMD -m py_compile App/webview_ui/backend/bridge.py && echo -e "${GREEN}✅ bridge.py${NC}"
$PYTHON_CMD -m py_compile App/webview_ui/backend/tray.py && echo -e "${GREEN}✅ tray.py${NC}"
echo ""

# 3. 导入测试
echo "${BLUE}3. 执行导入测试...${NC}"
echo "---------------------------------------------------------------"
$PYTHON_CMD -c "from App.webview_ui import main; print('✅ 主模块导入成功')"
$PYTHON_CMD -c "from App.webview_ui.backend.api import JsApi; print('✅ API 模块导入成功')"
echo ""

# 4. 启动应用
echo "${BLUE}4. 启动应用...${NC}"
echo "---------------------------------------------------------------"
echo "🚀 正在启动 OpenCode Token Meter..."
echo ""
echo "如果应用正常启动，你将看到:"
echo "  - 主窗口显示"
echo "  - 深色主题界面"
echo "  - 统计卡片和图表"
echo "  - 系统托盘图标"
echo ""
echo "按 Ctrl+C 可以终止应用"
echo ""

# 启动应用（后台运行，这样脚本不会阻塞）
$PYTHON_CMD -m App.webview_ui &
APP_PID=$!

echo "应用 PID: $APP_PID"
echo ""

# 等待几秒检查应用是否正常启动
sleep 3

if ps -p $APP_PID > /dev/null; then
    echo -e "${GREEN}✅ 应用已启动 (PID: $APP_PID)${NC}"
    echo ""
    echo "📝 请手动检查以下项目:"
    echo "  1. 窗口是否正常显示"
    echo "  2. 界面是否为深色主题"
    echo "  3. 统计卡片是否可见"
    echo "  4. 图表是否渲染"
    echo "  5. 系统托盘是否有图标"
    echo ""
    echo "关闭应用后，可以继续执行打包测试"
    echo ""
    
    # 等待应用退出
    wait $APP_PID
    echo -e "${GREEN}✅ 应用已退出${NC}"
else
    echo -e "${RED}❌ 应用启动失败${NC}"
    exit 1
fi

echo ""

# 5. 询问是否打包
read -p "是否执行打包测试? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "${BLUE}5. 执行打包...${NC}"
    echo "---------------------------------------------------------------"
    
    # 清理旧构建
    rm -rf build dist
    
    # 执行打包
    $PYTHON_CMD -m PyInstaller --clean OpenCodeTokenMeter.spec
    
    if [ -d "dist/OpenCode Token Meter.app" ]; then
        echo -e "${GREEN}✅ 打包成功${NC}"
        echo ""
        
        # 检查体积
        APP_SIZE=$(du -sh "dist/OpenCode Token Meter.app" | cut -f1)
        echo "📦 应用大小: $APP_SIZE"
        
        # 检查是否小于 50MB
        SIZE_BYTES=$(du -s "dist/OpenCode Token Meter.app" | cut -f1)
        SIZE_MB=$((SIZE_BYTES / 1024))
        
        if [ $SIZE_MB -lt 50 ]; then
            echo -e "${GREEN}✅ 体积检查通过 ($SIZE_MB MB < 50MB)${NC}"
        else
            echo -e "${YELLOW}⚠️  体积偏大 ($SIZE_MB MB >= 50MB)${NC}"
        fi
        
        echo ""
        read -p "是否运行打包后的应用? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🚀 启动打包后的应用..."
            "./dist/OpenCode Token Meter.app/Contents/MacOS/OpenCode Token Meter"
        fi
    else
        echo -e "${RED}❌ 打包失败${NC}"
        exit 1
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                   测试完成!"
echo "═══════════════════════════════════════════════════════════════"
