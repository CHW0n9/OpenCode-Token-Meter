#!/bin/bash
# 紧急修复脚本 - 让窗口能显示

echo "════════════════════════════════════════════════════════════"
echo "  OpenCode Token Meter - 窗口修复脚本"
echo "════════════════════════════════════════════════════════════"
echo ""

# 方案1：使用无托盘版本（保证可用）
echo "[方案1] 使用无托盘版本..."
cp App/webview_ui/main_backup.py App/webview_ui/main.py
echo "✅ 已切换到无托盘版本"
echo ""
echo "现在可以运行:"
echo "  /Users/chwong/miniforge3/envs/opencode/bin/python App/webview_ui/main.py --debug"
echo ""
echo "这将:"
echo "  ✅ 立即显示窗口"
echo "  ✅ 正常加载数据"
echo "  ✅ 可以继续开发功能"
echo "  ❌ 但没有系统托盘（有Dock图标）"
echo ""
echo "════════════════════════════════════════════════════════════"
