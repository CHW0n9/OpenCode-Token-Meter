# GitHub Upload Instructions for OpenCode Token Meter v1.0.0

This document provides step-by-step instructions for uploading the OpenCode Token Meter release to GitHub.

## ✅ Prerequisites

- GitHub account with repository access
- `Release 1.0.0` folder ready (all 68 files, 2.5 MB)
- This is a **manual upload via GitHub web interface** (no git CLI)

## 📋 Checklist: Files Ready for Upload

Before uploading, verify the Release 1.0.0 directory contains:

### Root Files (8 items)
- ✅ `LICENSE` - GPL-3.0 license file
- ✅ `README.md` - English documentation
- ✅ `README_CN.md` - Chinese documentation
- ✅ `CHANGELOG.md` - Version history
- ✅ `AGENTS.md` - Developer guidelines
- ✅ `.gitignore` - Git ignore rules
- ✅ `build.sh` - Main build script
- ✅ `create_dmg.sh` - DMG creation script

### Build Scripts & Config (4 items)
- ✅ `BUILD_FILES_CHECKLIST.md` - Build file reference
- ✅ `PROJECT_ARCHITECTURE.md` - Architecture documentation
- ✅ `GITHUB_UPLOAD_INSTRUCTIONS.md` - This file

### Source Code (13 items)
- ✅ `App/agent/` - Agent source code (8 Python files + pyproject.toml)
- ✅ `App/menubar/` - Menubar source code (5 Python files + resources)

### Resources (21+ items)
- ✅ `App/menubar/resources/` - All icon files (.png, .icns)
- ✅ `App/menubar/resources/AppIcon.iconset/` - macOS icon source

### Total File Count
- Should be approximately **68 files**
- Total size approximately **2.5 MB**

## 🚀 Upload Steps

### Step 1: Create a New GitHub Repository

1. Go to https://github.com/new
2. Enter repository name: `OpenCode Token Meter` (or your preferred name)
3. Add description: "AI token usage tracker for macOS"
4. Choose **Public** (or Private if preferred)
5. **Do NOT initialize with README** (we have our own)
6. Click **Create repository**

### Step 2: Initialize Git (Local - One Time Setup)

In the Release 1.0.0 folder, initialize git:

```bash
cd /Users/chwong/Desktop/Release\ 1.0.0
git init
git add .
git commit -m "Initial commit: OpenCode Token Meter v1.0.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/OpenCode-Token-Meter.git
git push -u origin main
```

**Replace:** `YOUR_USERNAME` with your actual GitHub username

### Step 3: Alternative - Upload via GitHub Web Interface

If you prefer NOT to use git CLI:

1. Go to your newly created repository on GitHub
2. Click **Add file** → **Upload files**
3. Drag and drop the contents of Release 1.0.0 folder (or select them)
4. Keep the folder structure:
   - Upload `App/` folder as-is
   - Upload all `.md` files to root
   - Upload `build.sh` and `create_dmg.sh` to root
   - Upload `.gitignore` to root
5. Add commit message: `Initial commit: OpenCode Token Meter v1.0.0`
6. Click **Commit changes**

### Step 4: Create a GitHub Release

1. Go to your repository
2. Click **Releases** (or **Create a new release** in the right sidebar)
3. Click **Draft a new release**
4. Fill in the form:
   - **Tag version:** `v1.0.0`
   - **Release title:** `OpenCode Token Meter v1.0.0`
   - **Description:** Copy from CHANGELOG.md or write:

```
OpenCode Token Meter v1.0.0 - Initial Release

## Features
- Real-time AI token usage tracking (Claude, ChatGPT, Gemini, etc.)
- Costs calculation based on provider models
- Token usage analytics and reporting
- Export to CSV/JSON formats
- macOS menubar application with native UI

## System Requirements
- macOS 11.0 or later
- Python 3.7+ (for building from source)

## Installation
- Download the DMG file from releases
- Or build from source: `./build.sh`

## Documentation
See README.md for detailed instructions.
```

5. **Do NOT upload a DMG binary** (you can build it locally with `./build.sh` if needed)
6. Click **Publish release**

### Step 5: Update Repository Settings (Recommended)

1. Go to repository **Settings**
2. Under **Code and automation** → **Pages**:
   - Enable GitHub Pages
   - Choose source: `main` branch, `/root` folder
   - This will auto-generate documentation pages
3. Under **General**, update:
   - Description: "AI token usage tracker for macOS"
   - Topics: `python`, `macos`, `ai`, `token-counting`, `menubar`

## 📝 Summary: What Goes Where

| Item | Location | Status |
|------|----------|--------|
| Source Code | Repository root under `App/` | ✅ Upload as-is |
| Documentation | Repository root | ✅ Upload all .md files |
| Build Scripts | Repository root | ✅ Upload build.sh, create_dmg.sh |
| License | Repository root as `LICENSE` | ✅ Upload |
| .gitignore | Repository root | ✅ Upload |
| Build Artifacts | Do NOT upload | ❌ Excluded |
| User Test Data | Do NOT upload | ❌ Excluded |

## ✨ Post-Upload Checklist

After uploading to GitHub:

- [ ] Repository is visible and public (if intended)
- [ ] All files are present in correct locations
- [ ] README.md displays correctly
- [ ] Build instructions work: `./build.sh` compiles without errors
- [ ] License is properly attributed (GPL-3.0)
- [ ] Release tag v1.0.0 is created
- [ ] GitHub Pages (optional) is configured

## 🔧 Verification: Test Build from GitHub

After uploading, you can verify everything works:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/OpenCode-Token-Meter.git
cd OpenCode-Token-Meter

# Navigate to menubar app
cd App/menubar

# Try to build (requires PyInstaller and dependencies)
python3 -m PyInstaller -y opencode-menubar.spec
```

If this succeeds, the repository is correctly set up for users to build from source.

## ❓ Common Questions

### Q: Should I include the built .app file?
**A:** No. GitHub has size limits and compiled binaries are large. Users can build from source using `./build.sh`.

### Q: What if I want to provide a DMG download?
**A:** Build it locally:
```bash
cd Release\ 1.0.0
./build.sh
./create_dmg.sh
```
Then manually upload the resulting `.dmg` file to the GitHub Release (step 4) as a downloadable asset.

### Q: Can users just download and run the app?
**A:** Only if you provide a pre-built .dmg file in Releases. Otherwise, they must build it locally with `./build.sh`.

### Q: What about security/code signing?
**A:** The .app bundle is not yet code-signed. Users building locally won't have issues. If distributing pre-built apps, consider adding signing via GitHub Actions (future enhancement).

### Q: How do I update the repository after this?
**A:** 
```bash
cd Release\ 1.0.0
git add <modified files>
git commit -m "your message"
git push
```

## 📞 Support

If you encounter issues:

1. Check that all 68 files are present in Release 1.0.0
2. Verify folder structure matches what's described above
3. Ensure .spec file uses relative paths (not absolute)
4. Check Python version: `python3 --version` (requires 3.7+)

For detailed build instructions, see `BUILD_FILES_CHECKLIST.md` and `PROJECT_ARCHITECTURE.md`.

---

**Release Date:** February 1, 2026  
**Version:** 1.0.0  
**Status:** Ready for GitHub Upload
