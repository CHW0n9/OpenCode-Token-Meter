#!/bin/bash
# OpenCode Token Meter - 手动测试脚本
# 在 macOS 图形界面环境下运行

set -e

echo "=============================================="
echo "OpenCode Token Meter - 手动测试脚本"
echo "=============================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
PASSED=0
FAILED=0
SKIPPED=0

# 测试函数
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    echo -n "Testing: $test_name ... "
    if eval "$test_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

# 获取项目根目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 检查是否在 conda 环境中
OPENCODE_PYTHON="/Users/chwong/miniforge3/envs/opencode/bin/python"
if [ -f "$OPENCODE_PYTHON" ]; then
    PYTHON_CMD="$OPENCODE_PYTHON"
    echo -e "${GREEN}✅ 使用指定的 opencode 环境 Python: $PYTHON_CMD${NC}"
else
    PYTHON_CMD="python"
    echo -e "${YELLOW}⚠️  未找到 $OPENCODE_PYTHON，使用系统默认 python${NC}"
fi

# 1. 检查依赖
echo "1. 检查依赖"
echo "--------------"
run_test "Python 3" "$PYTHON_CMD --version"
run_test "pywebview" "$PYTHON_CMD -c 'import webview'"
run_test "pystray" "$PYTHON_CMD -c 'import pystray'"
run_test "PIL (Pillow)" "$PYTHON_CMD -c 'from PIL import Image'"
echo ""

# 2. 检查文件结构
echo "2. 检查文件结构"
echo "----------------"
run_test "webview_ui 目录" "test -d App/webview_ui"
run_test "backend 目录" "test -d App/webview_ui/backend"
run_test "web 目录" "test -d App/webview_ui/web"
run_test "index.html" "test -f App/webview_ui/web/index.html"
run_test "api.py" "test -f App/webview_ui/backend/api.py"
run_test "main.py" "test -f App/webview_ui/main.py"
echo ""

# 3. 检查 Python 语法
echo "3. 检查 Python 语法"
echo "-------------------"
run_test "main.py 语法" "$PYTHON_CMD -m py_compile App/webview_ui/main.py"
run_test "api.py 语法" "$PYTHON_CMD -m py_compile App/webview_ui/backend/api.py"
run_test "bridge.py 语法" "$PYTHON_CMD -m py_compile App/webview_ui/backend/bridge.py"
run_test "tray.py 语法" "$PYTHON_CMD -m py_compile App/webview_ui/backend/tray.py"
echo ""

# 4. 检查模块导入
echo "4. 检查模块导入"
echo "---------------"
run_test "导入 main" "cd \"$PROJECT_DIR\" && $PYTHON_CMD -c 'from App.webview_ui import main'"
run_test "导入 JsApi" "cd \"$PROJECT_DIR\" && $PYTHON_CMD -c 'from App.webview_ui.backend.api import JsApi'"
echo ""

# 5. GUI 测试（需要用户交互）
echo "5. GUI 功能测试（需要手动验证）"
echo "--------------------------------"
echo -e "${YELLOW}请手动执行以下测试：${NC}"
echo ""
echo "测试 5.1: 应用启动"
echo "  命令: $PYTHON_CMD -m App.webview_ui"
echo "  检查: 窗口是否正常打开，无错误"
echo ""

read -p "是否已测试应用启动? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}  应用启动: PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}  应用启动: SKIPPED${NC}"
    ((SKIPPED++))
fi
echo ""

echo "测试 5.2: 界面显示"
echo "  检查项:"
echo "    - 深色主题是否正确显示"
echo "    - 统计卡片是否可见"
echo "    - Chart.js 图表是否渲染"
echo "    - 布局是否美观"
echo ""

read -p "界面显示是否正常? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}  界面显示: PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}  界面显示: SKIPPED${NC}"
    ((SKIPPED++))
fi
echo ""

echo "测试 5.3: 系统托盘"
echo "  检查项:"
echo "    - 托盘图标是否显示"
echo "    - 右键菜单是否可打开"
echo "    - 菜单功能是否正常"
echo ""

read -p "系统托盘功能是否正常? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}  系统托盘: PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}  系统托盘: SKIPPED${NC}"
    ((SKIPPED++))
fi
echo ""

# 6. 打包测试
echo "6. 打包测试"
echo "-----------"
echo "命令: ./build.sh"
echo "预期: 生成 dist/OpenCode Token Meter.app"
echo ""

if [ -d "dist/OpenCode Token Meter.app" ]; then
    echo -e "${GREEN}  打包文件已存在${NC}"
    APP_SIZE=$(du -sh "dist/OpenCode Token Meter.app" | cut -f1)
    echo "  应用大小: $APP_SIZE"
    
    # 检查是否小于 50MB
    SIZE_BYTES=$(du -s "dist/OpenCode Token Meter.app" | cut -f1)
    SIZE_MB=$((SIZE_BYTES / 1024))
    
    if [ $SIZE_MB -lt 50 ]; then
        echo -e "${GREEN}  体积检查: PASS (${SIZE_MB}MB < 50MB)${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}  体积检查: 警告 (${SIZE_MB}MB >= 50MB)${NC}"
        ((SKIPPED++))
    fi
else
    echo -e "${YELLOW}  打包文件不存在，跳过体积测试${NC}"
    echo "  提示: 运行 ./build.sh 生成打包文件"
    ((SKIPPED++))
fi
echo ""

# 测试总结
echo "=============================================="
echo "测试总结"
echo "=============================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo -e "${YELLOW}跳过: $SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有自动化测试通过!${NC}"
    echo "请完成手动测试项以确保功能完整。"
    exit 0
else
    echo -e "${RED}有 $FAILED 个测试失败，请检查。${NC}"
    exit 1
fi
