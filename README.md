<h1 align="center">OpenCode Token Meter</h1>
<p align="center">
  <a href="https://github.com/CHW0n9/OpenCode-Token-Meter/releases">
    <img src="assets/logo.png" alt="Project Logo" width="128">
  </a>
</p>

**OpenCode Token Meter** is a lightweight cross-platform (macOS, Windows) menubar application that tracks model token usage from [OpenCode](https://opencode.ai). It monitors message history, calculates costs for different AI models, and provides detailed usage statistics with an intuitive interface.

**Note**: This project was developed entirely using [OpenCode](https://opencode.ai). This project is not built by the OpenCode team and is not affiliated with them in any way.

---

## Features

- **📊 Real-time Token Tracking** - Monitors incoming and outgoing tokens from AI interactions
- **💰 Cost Calculation** - Automatic cost computation based on model-specific pricing
- **📈 Detailed Analytics** - View token usage by provider, model, and time range
- **⚙️ Customizable Settings** - Set cost thresholds and notification preferences
- **📥 Token Usage Export** - Export usage data for custom date ranges
- **🔄 Automatic Updates** - Embedded background agent continuously monitors your message directory
- **🔐 Privacy-Focused** - All data stored locally in SQLite database
- **⚡ Lightweight** - Minimal resource usage in system tray / menubar
- **💻 Cross-Platform** - Unified support for macOS and Windows

---

## Installation

### Option 1: Pre-built Binaries (Recommended)

#### Windows
1. Download `OpenCodeTokenMeter.exe` from the [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases)
2. Run the executable to start the application.
3. The app will appear in your system tray.

#### macOS
1. Download `OpenCodeTokenMeter-1.0.1.dmg` from the [GitHub Releases](https://github.com/chw0n9/opencode-token-meter/releases)
2. Double-click the `.dmg` file to open it
3. Drag "OpenCode Token Meter.app" to the Applications folder
4. Open Applications folder and double-click "OpenCode Token Meter.app"

**Important: Running Unsigned Apps on macOS**
Since the app is not code-signed, you may see a security warning on first launch. Go to **System Settings → Privacy & Security** and click **"Open Anyway"** for OpenCode Token Meter.

### Option 2: Build from Source

#### Unified Build System
This project uses a **single unified spec file** (`OpenCodeTokenMeter.spec`) with automatic platform detection for building on Windows and macOS.

#### Requirements:
- Python 3.9+
- PyQt6
- PyInstaller

#### Quick Build Steps:

**Windows:**
```powershell
.\build_windows.bat
```
Output: `dist\OpenCodeTokenMeter.exe`

**macOS:**
```bash
./build.sh
```
Output: `dist/OpenCode Token Meter.app`

#### What Gets Built:
- **Windows**: Single unified executable (`.exe`) including the menubar UI and embedded agent.
- **macOS**: Native `.app` bundle including the menubar UI and embedded agent.

#### Key Features of the Build:
- **Embedded Agent**: The background agent now runs as a **background thread** inside the main app. No separate process or executable is required!
- **Platform Detection**: The build system automatically detects your OS and uses the correct icons (`.ico` for Windows, `.icns` for macOS).
- **Single File Distribution**: True single-file distribution (except on macOS where it's a standard app bundle).

---

## Token Data Location

This app scans your OpenCode message directory to calculate token usage. Messages are read from:

- **macOS**: `~/.local/share/opencode/storage/message/`
- **Windows**: `%LOCALAPPDATA%\opencode\storage\message\`

The app stores its configuration and calculated metrics locally at:

- **macOS**: `~/Library/Application Support/OpenCode Token Meter/`
- **Windows**: `%APPDATA%\OpenCode Token Meter\`

---

## Project Architecture

```
OpenCode Token Meter
│
├── App/
│   ├── agent/                    # Background logic (Python)
│   │   ├── agent/db.py          # SQLite database with dedup logic
│   │   ├── agent/scanner.py     # Message directory scanner
│   │   ├── agent/config.py      # Platform-aware configuration
│   │
│   └── menubar/                  # PyQt6 GUI application
│       ├── menubar/app.py       # Main app logic, dialogs, UI
│       ├── menubar/settings.py  # Platform-aware settings management
│       ├── menubar/uds_client.py # Socket client (TCP fallback on Windows)
│       └── menubar/resources/   # App icons (.ico, .icns, .png)
│
├── OpenCodeTokenMeter.spec       # Unified build specification
├── build_windows.bat             # Windows build script
├── build.sh                      # macOS build script
└── AGENTS.md                     # Developer guide
```

### Key Components

**Embedded Agent**
- Runs as a background thread within the main process.
- Scans the OpenCode message directory every few seconds.
- Parses JSON message files and extracts token counts.
- Deduplicates messages to handle OpenCode's session copying.
- Stores data in a local SQLite database (`index.db`).

**Menubar / System Tray App**
- Native UI for macOS (menubar) and Windows (system tray).
- Shows real-time statistics (tokens, requests, costs).
- Comprehensive details window with provider/model breakdown.
- Settings dialog for custom pricing and notification thresholds.
- Data export functionality (CSV/Clipboard).


**Deduplication System**
- Prevents double-counting when OpenCode copies messages between sessions
- Groups messages by: timestamp, role, input, output, reasoning, cache info, provider, model
- Selects canonical record using lexicographically smallest `msg_id`
- All aggregates and exports use deduplicated data

---

## Usage

### Starting the App

1. Launch "OpenCode Token Meter".
2. App icon appears in the macOS menubar (top right) or Windows system tray (bottom right).
3. The embedded agent automatically starts and begins syncing data.

### Interface Display

The application shows up to 6 metrics in a 2×3 grid:

**Row 1:**
- **In** - Total input tokens
- **Req** - Total requests

**Row 2:**
- **Out** - Total output tokens
- **Cost** - Calculated cost in USD

**Row 3 (Optional):**
- **Token%** - Current input token % of threshold
- **Cost%** - Current cost % of threshold

Row 3 only displays if token/cost thresholds are enabled in Settings.

### Main Window

Click the icon to open the main window with:
- Detailed statistics
- Breakdown by provider and model
- All/Provider/Model view tabs
- Date range selector for export

---

## Configuration

### Model Pricing

The app includes default pricing for popular providers:
- **Google**: Gemini models
- **OpenCode Zen**: GLM 4.7
- **Github Copilot**: Claude and GPT models (Charged by premium requests)
- **Other**: Any custom provider/model

You can add custom models or override default pricing in **Settings → Cost Meter**. Models with custom pricing are marked as **(customized)**.

### Database

The SQLite database (`index.db`) is created automatically. It contains:
- `messages` table with token counts and metadata.
- `idx_dedup` index for fast deduplication.
- View tracking and session information.

---

## Troubleshooting

### No Token Data Showing

1. **Verify OpenCode Messages**: Ensure messages exist in the scan directory.
2. **Check Database**: Use `sqlite3` to verify the `index.db` content.
3. **Restart the App**: Quit and relaunch to re-initialize the background agent.

### Windows: App Not Appearing in Tray

- Ensure no other instance is running.
- Check Task Manager for `OpenCodeTokenMeter.exe`.

### macOS: App Blocked by Security

- Go to System Settings → Privacy & Security and allow the app to run.

---

## Development

### Quick Setup

```bash
# Clone and navigate
git clone https://github.com/chw0n9/opencode-token-meter.git
cd opencode-token-meter

# Read developer guide for platform-specific instructions
cat AGENTS.md
```

### Running in Development

```bash
# From the project root
cd App/menubar
python -m menubar
```

### Building for Distribution

**Windows:**
```powershell
.\build_windows.bat
```

**macOS:**
```bash
./build.sh
```

### Code Style

- Python 3.9+
- Follow PEP 8 with Black (88 char line width)
- Use isort for import organization
- Type hints for public APIs
- Parameterized SQL queries only

See [AGENTS.md](AGENTS.md) for complete developer guidelines.

---

## Database Safety

- All SQL queries use parameterized placeholders (`?`) to prevent injection.
- SQLite with WAL mode for safe concurrent access.
- Deduplication query prevents double-counting messages across sessions.
- All data stored locally (no network transmission).

---

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

## Credits

Developed entirely with [OpenCode](https://opencode.ai) - an AI-powered terminal interface for coding.

[OpenCode Repository](https://github.com/anomalyco/opencode)

---

## Screenshots

- **Menubar Display (macOS)**: 2×3 grid with token metrics.
- **Main Window**: Detailed statistics and model breakdown.
- **Settings Dialog**: Model pricing and threshold configuration.

---

## Support & Feedback

- Report bugs: [GitHub Issues](https://github.com/chw0n9/opencode-token-meter/issues)
- Feature requests: [GitHub Discussions](https://github.com/chw0n9/opencode-token-meter/discussions)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

