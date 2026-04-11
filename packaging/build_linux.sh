#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
DIST_DIR="$ROOT_DIR/dist"
PACKAGING_DIR="$ROOT_DIR/packaging/linux"
SPEC_FILE="$ROOT_DIR/packaging/OpenCodeTokenMeter.spec"
TAILWIND_DIR="$ROOT_DIR/App/webview_ui/web"
APP_NAME="OpenCode Token Meter"
PKG_NAME="opencode-token-meter"
BIN_NAME="opencode-token-meter"
VERSION_FILE="$ROOT_DIR/VERSION"
VERSION="1.1.3"
TAILWIND_INPUT="$ROOT_DIR/App/webview_ui/web/css/tailwind.input.css"
TAILWIND_OUTPUT="$ROOT_DIR/App/webview_ui/web/css/tailwind.css"
TAILWIND_CONFIG="$ROOT_DIR/App/webview_ui/web/tailwind.config.js"

if [ -f "$VERSION_FILE" ]; then
  VERSION="$(tr -d '\n' < "$VERSION_FILE")"
fi

case "$(uname -m)" in
  x86_64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  armv7l) ARCH="armhf" ;;
  *) ARCH="$(uname -m)" ;;
esac

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   OpenCode Token Meter Build Script    ${NC}"
echo -e "${BLUE}========================================${NC}"

# Prefer venv Python, fallback to system python3
if [ -f "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  PYTHON="$(command -v python3 || true)"
fi

if [ -z "$PYTHON" ]; then
  echo "Error: python3 not found. Install python3 or create .venv first."
  exit 1
fi

echo -e " - Python: ${GREEN}$PYTHON${NC}"
echo -e " - Version: ${GREEN}$VERSION${NC}"

TEMP_LOG=""
TEMP_DEB_LOG=""
cleanup() {
  if [ -n "$TEMP_LOG" ]; then
    rm -f "$TEMP_LOG" 2>/dev/null || true
  fi
  if [ -n "$TEMP_DEB_LOG" ]; then
    rm -f "$TEMP_DEB_LOG" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Install dependencies
echo -e "\n${BLUE}[1/5] Checking dependencies...${NC}"
"$PYTHON" -m pip install --quiet --upgrade pyinstaller pywebview pillow pyperclip 2>/dev/null || true
echo -e " - Dependencies OK"

# Compile Tailwind CSS
echo -e "\n${BLUE}[2/5] Building frontend CSS...${NC}"
if [ -f "$TAILWIND_INPUT" ] && [ -f "$TAILWIND_CONFIG" ]; then
  if command -v npx >/dev/null 2>&1; then
    (
      cd "$TAILWIND_DIR"
      npx tailwindcss@3.4.17 -c "tailwind.config.js" -i "css/tailwind.input.css" -o "css/tailwind.css" --minify
    ) >/dev/null
    echo -e " - Tailwind CSS compiled"
  elif [ -f "$TAILWIND_OUTPUT" ]; then
    echo -e " - npx not found, using existing tailwind.css"
  else
    echo -e "${RED}Error: npx not found and $TAILWIND_OUTPUT is missing${NC}"
    exit 1
  fi
else
  echo -e " - Tailwind sources not present, skipping"
fi

# Clean previous builds
echo -e "\n${BLUE}[3/5] Cleaning previous builds...${NC}"
rm -rf "$BUILD_DIR" "$DIST_DIR"
echo -e " - Cleaned"

# Build using unified spec file
echo -e "\n${BLUE}[4/5] Building application...${NC}"

TEMP_LOG=$(mktemp)
"$PYTHON" -m PyInstaller --clean --noconfirm --log-level=ERROR "$SPEC_FILE" > "$TEMP_LOG" 2>&1 &
PID=$!

# Spinner
SPIN_CHARS='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
i=0
while kill -0 "$PID" 2>/dev/null; do
  i=$(( (i + 1) % ${#SPIN_CHARS} ))
  printf "\r - Building... ${YELLOW}${SPIN_CHARS:$i:1}${NC} "
  sleep 0.1
done

wait "$PID"
BUILD_EXIT=$?
printf "\r"

if [ "$BUILD_EXIT" -ne 0 ]; then
  echo -e " - ${YELLOW}Build log:${NC}"
  grep "INFO:" "$TEMP_LOG" | head -20 || true
  exit 1
fi

grep "^[0-9]* INFO:" "$TEMP_LOG" | head -4 || true

APP_DIR="$DIST_DIR/$APP_NAME"
APP_EXE="$APP_DIR/$APP_NAME"
if [ ! -d "$APP_DIR" ] || [ ! -f "$APP_EXE" ]; then
  echo "ERROR: Build output not found: $APP_DIR"
  exit 1
fi

APP_SIZE=$(du -sh "$APP_DIR" | cut -f1 | xargs)

prune_linux_bundle() {
  local bundle_root="$1"
  local internal_dir="$bundle_root/_internal"
  if [ ! -d "$internal_dir" ]; then
    return 0
  fi

  rm -rf \
    "$internal_dir/share/icons" \
    "$internal_dir/share/themes"
}

prune_linux_bundle "$APP_DIR"
APP_SIZE=$(du -sh "$APP_DIR" | cut -f1 | xargs)
echo -e " - App: ${GREEN}${APP_SIZE}${NC}"

report_top_sizes() {
  local target_dir="$1"
  local title="$2"
  if [ ! -e "$target_dir" ]; then
    return 0
  fi

  echo -e "\n${BLUE}${title}${NC}"
  "$PYTHON" - "$target_dir" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])

def human(size: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    value = float(size)
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024.0
        unit += 1
    return f"{value:.1f}{units[unit]}"

def tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob('*'):
        if child.is_file():
            total += child.stat().st_size
    return total

if root.is_file():
    print(f"  {human(root.stat().st_size)}\t{root.name}")
    raise SystemExit(0)

dirs = []
files = []
for child in root.iterdir():
    if child.is_dir():
        dirs.append((tree_size(child), child.name))
    else:
        files.append((child.stat().st_size, child.name))

if dirs:
    print('  Directories:')
    for size, name in sorted(dirs, reverse=True)[:10]:
        print(f"    {human(size)}\t{name}")

if files:
    print('  Files:')
    for size, name in sorted(files, reverse=True)[:10]:
        print(f"    {human(size)}\t{name}")
PY
}

report_bundle_contents() {
  local build_root="$1"
  if [ ! -d "$build_root" ]; then
    return 0
  fi

  echo -e "\n${BLUE}Bundle diagnostics${NC}"
  "$PYTHON" - "$build_root" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

def human(size: int) -> str:
    units = ['B', 'KB', 'MB', 'GB']
    value = float(size)
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024.0
        unit += 1
    return f"{value:.1f}{units[unit]}"

def iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            yield from iter_strings(item)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from iter_strings(key)
            yield from iter_strings(value)

toc_file = next(root.glob('*/*.toc'), None)
warn_file = next(root.glob('*warn-*.txt'), None)

if warn_file and warn_file.exists():
    print(f"  warn file: {warn_file.relative_to(root)}")
    warnings = warn_file.read_text(errors='ignore').splitlines()
    suspicious_warns = [line for line in warnings if any(k in line.lower() for k in (
        'not found', 'missing', 'failed', 'cannot', 'warning'
    ))]
    for line in suspicious_warns[:20]:
        print(f"    {line}")

if toc_file and toc_file.exists():
    print(f"  toc file: {toc_file.relative_to(root)}")
    try:
        data = ast.literal_eval(toc_file.read_text(errors='ignore'))
    except Exception as exc:
        print(f"    failed to parse toc: {exc}")
        raise SystemExit(0)

    strings = set(iter_strings(data))
    patterns = [
        'win10toast', 'AppKit', 'Foundation', 'PyObjCTools',
        'rumps', 'pystray', 'webview.platforms.winforms',
        'webview.platforms.cocoa', 'webview.platforms.darwin',
        'dbus', 'gi.repository', 'gi/', 'webkit', 'gtk',
    ]
    suspicious = [item for item in sorted(strings) if any(p.lower() in item.lower() for p in patterns)]

    if suspicious:
        print('  suspicious entries:')
        for item in suspicious[:80]:
            print(f"    {item}")
    else:
        print('  suspicious entries: none matched the current filters')

    if strings:
        existing = []
        for item in strings:
            path = Path(item)
            if path.is_file():
                try:
                    existing.append((path.stat().st_size, item))
                except OSError:
                    pass
        if existing:
            print('  largest packed files:')
            for size, item in sorted(existing, reverse=True)[:20]:
                print(f"    {human(size)}\t{item}")
PY
}

# Build a .deb package when dpkg-deb is available
DEB_PATH=""
if command -v dpkg-deb >/dev/null 2>&1; then
  echo -e "\n${BLUE}[5/5] Creating Debian package...${NC}"

  TEMP_DEB_LOG=$(mktemp)
  STAGING_DIR="$BUILD_DIR/debroot"
  DEBIAN_DIR="$STAGING_DIR/DEBIAN"
  OPT_DIR="$STAGING_DIR/opt/$PKG_NAME"

  rm -rf "$STAGING_DIR"
  install -d "$DEBIAN_DIR" \
    "$OPT_DIR" \
    "$STAGING_DIR/usr/bin" \
    "$STAGING_DIR/usr/share/applications" \
    "$STAGING_DIR/usr/share/icons/hicolor/256x256/apps"

  cp -a "$APP_DIR/." "$OPT_DIR/"
  install -m 755 "$PACKAGING_DIR/opencode-token-meter.wrapper" "$STAGING_DIR/usr/bin/$BIN_NAME"
  install -m 644 "$PACKAGING_DIR/opencode-token-meter.desktop" "$STAGING_DIR/usr/share/applications/$BIN_NAME.desktop"
  install -m 644 "$ROOT_DIR/App/webview_ui/web/assets/AppIcon.png" "$STAGING_DIR/usr/share/icons/hicolor/256x256/apps/$BIN_NAME.png"
  install -m 755 "$PACKAGING_DIR/postinst" "$DEBIAN_DIR/postinst"
  install -m 755 "$PACKAGING_DIR/prerm" "$DEBIAN_DIR/prerm"
  install -m 755 "$PACKAGING_DIR/postrm" "$DEBIAN_DIR/postrm"

  cat > "$DEBIAN_DIR/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: OpenCode Token Meter <noreply@localhost>
Depends: libgtk-3-0, libwebkit2gtk-4.0-37 | libwebkit2gtk-4.1-0, libayatana-appindicator3-1 | libappindicator3-1, libdbus-1-3, libglib2.0-0, libx11-6, libnotify4
Homepage: https://github.com/chw0n9/opencode-token-meter
Description: Track OpenCode token usage from the system tray
 A desktop token meter for OpenCode with tray integration and a web dashboard.
EOF

chmod 755 "$DEBIAN_DIR"/postinst "$DEBIAN_DIR"/prerm "$DEBIAN_DIR"/postrm

DEB_PATH="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
if command -v fakeroot >/dev/null 2>&1; then
  fakeroot dpkg-deb --build "$STAGING_DIR" "$DEB_PATH" > "$TEMP_DEB_LOG" 2>&1
else
  dpkg-deb --build "$STAGING_DIR" "$DEB_PATH" > "$TEMP_DEB_LOG" 2>&1
fi

  DEB_SIZE=$(du -h "$DEB_PATH" | cut -f1 | xargs)
  echo -e " - Deb: ${GREEN}${DEB_SIZE}${NC}"
else
  echo -e "\n${BLUE}[5/5] Skipping Debian package (dpkg-deb not found)${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}           Build Complete!              ${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e " App:  ${GREEN}${APP_SIZE}${NC} → dist/$APP_NAME/"
if [ -n "$DEB_PATH" ]; then
  echo -e " Deb:  ${GREEN}${DEB_SIZE}${NC} → $(basename "$DEB_PATH")"
fi
echo -e " Run:  ${GREEN}./dist/$APP_NAME/$APP_NAME${NC}"
exit 0
