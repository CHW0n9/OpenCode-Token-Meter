# OpenCode Token Meter Database Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现从 `opencode.db` 增量同步消息数据，并保持与旧版文件扫描逻辑并行兼容。

**Architecture:** 在 `Scanner` 类中新增数据库同步方法，通过记录 `max(time_updated)` 实现增量同步，利用 `index.db` 的主键去重特性保障数据一致性。

**Tech Stack:** Python, SQLite (sqlite3), JSON.

---

### Task 1: 配置路径更新

**Files:**
- Modify: `App/agent/agent/config.py`

**Step 1: 新增数据库路径常量**
在 `MSG_ROOT` 之后添加：
```python
# OpenCode primary database path
OPENCODE_DB_PATH = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db")
```

**Step 2: 验证路径**
运行：`python -c "import os; print(os.path.exists(os.path.expanduser('~/.local/share/opencode/opencode.db')))"`
Expected: `True` (如果在开发环境下 OpenCode 已更新)

**Step 3: Commit**
```bash
git add App/agent/agent/config.py
git commit -m "config: add OPENCODE_DB_PATH for database synchronization"
```

---

### Task 2: 数据库层支持 (同步状态管理)

**Files:**
- Modify: `App/agent/agent/db.py`

**Step 1: 初始化同步状态表**
在 `init_db()` 的 `executescript` 中添加：
```sql
CREATE TABLE IF NOT EXISTS sync_state (
  key TEXT PRIMARY KEY,
  val TEXT
);
-- Initialize opencode_db_last_ts if not exists
INSERT OR IGNORE INTO sync_state (key, val) VALUES ('opencode_db_last_ts', '0');
```

**Step 2: 添加 Getter/Setter 函数**
```python
def get_sync_state(key, default='0'):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT val FROM sync_state WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def update_sync_state(key, val):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sync_state (key, val) VALUES (?, ?)", (key, str(val)))
    conn.commit()
    conn.close()
```

**Step 3: 运行语法检查**
Run: `python -m py_compile App/agent/agent/db.py`

**Step 4: Commit**
```bash
git add App/agent/agent/db.py
git commit -m "db: add sync_state table and helpers for DB synchronization"
```

---

### Task 3: 实现数据库同步器 (Syncer)

**Files:**
- Modify: `App/agent/agent/scanner.py`

**Step 1: 导入必要组件**
```python
import sqlite3
from agent.config import OPENCODE_DB_PATH
from agent.db import get_sync_state, update_sync_state
```

**Step 2: 实现 `_sync_from_opencode_db` 方法**
在 `Scanner` 类中添加逻辑：
1. 以只读模式连接 `OPENCODE_DB_PATH`。
2. 读取 `opencode_db_last_ts`。
3. 执行查询并解析 `data` (JSON)。
4. 记录并更新最大的 `time_updated`。

**Step 3: 集成到 `scan_once`**
在 `scan_once()` 函数的末尾（`mark_failed_requests()` 之前）调用 `self._sync_from_opencode_db()`。

**Step 4: Commit**
```bash
git add App/agent/agent/scanner.py
git commit -m "feat: implement database synchronization in Scanner"
```

---

### Task 4: 提高刷新频率

**Files:**
- Modify: `App/agent/agent/config.py`

**Step 1: 修改刷新间隔**
```python
REFRESH_INTERVAL_SECONDS = 30  # Reduced from 300 to 30 for better real-time updates
```

**Step 2: Commit**
```bash
git add App/agent/agent/config.py
git commit -m "config: reduce refresh interval to 30s for real-time tracking"
```
