"""
Luqi AI — Dashboard Module
===========================
Personal dashboard with widget system, knowledge base, and habit tracker.
Uses SQLite for persistence.  All functions are async-compatible wrappers
around synchronous sqlite3 calls.

Typical usage::
    from dashboard import init_db, get_widgets, save_widget
    init_db()
    widgets = get_widgets("user-123")
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get("LUQI_DASHBOARD_DB", "/mnt/agents/output/project/backend/dashboard.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Widget definitions — 17 types
# ---------------------------------------------------------------------------

_WIDGET_TYPES: dict[str, dict[str, Any]] = {
    "clock": {
        "name": "Clock",
        "category": "utility",
        "icon": "🕐",
        "default_config": {"format": "12h", "show_seconds": True, "timezone": "local"},
        "render_html": lambda cfg: f"""
<div class="widget-clock p-4 bg-white rounded-xl shadow-sm border border-gray-100 text-center">
  <div class="text-3xl font-mono font-bold text-gray-800" id="clock-{cfg.get('_id', 'x')}">--:--:--</div>
  <div class="text-xs text-gray-500 mt-1">{cfg.get('timezone', 'local').upper()}</div>
</div>
<script>
(function(){{
  function tick(){{
    const now = new Date();
    const el = document.getElementById('clock-{cfg.get('_id', 'x')}');
    if (!el) return;
    {'const opts = {hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true};' if cfg.get('format') == '12h' else 'const opts = {hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false};'}
    el.textContent = now.toLocaleTimeString('en-US', opts);
  }}
  tick(); setInterval(tick, 1000);
}})();
</script>""",
    },
    "weather": {
        "name": "Weather",
        "category": "info",
        "icon": "🌤",
        "default_config": {"location": "New York", "unit": "celsius"},
        "render_html": lambda cfg: f"""
<div class="widget-weather p-4 bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl shadow-sm text-white">
  <div class="flex items-center justify-between">
    <div>
      <div class="text-3xl font-bold">72°F</div>
      <div class="text-sm opacity-90">{cfg.get('location', 'New York')}</div>
    </div>
    <div class="text-4xl">🌤</div>
  </div>
  <div class="mt-3 flex gap-4 text-xs opacity-80">
    <span>💧 45%</span><span>💨 12mph</span><span>👁 10mi</span>
  </div>
</div>""",
    },
    "stocks": {
        "name": "Stocks",
        "category": "finance",
        "icon": "📈",
        "default_config": {"symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"]},
        "render_html": lambda cfg: """
<div class="widget-stocks p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">📈 Market</h3>
  <div class="space-y-2">
    <div class="flex justify-between text-sm"><span class="font-medium">AAPL</span><span class="text-green-600">$182.45 ▲</span></div>
    <div class="flex justify-between text-sm"><span class="font-medium">GOOGL</span><span class="text-green-600">$141.20 ▲</span></div>
    <div class="flex justify-between text-sm"><span class="font-medium">MSFT</span><span class="text-red-600">$378.90 ▼</span></div>
    <div class="flex justify-between text-sm"><span class="font-medium">TSLA</span><span class="text-green-600">$248.15 ▲</span></div>
  </div>
</div>""",
    },
    "news": {
        "name": "News Feed",
        "category": "info",
        "icon": "📰",
        "default_config": {"category": "tech", "count": 5},
        "render_html": lambda cfg: """
<div class="widget-news p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">📰 Latest News</h3>
  <div class="space-y-3">
    <a href="#" class="block text-sm hover:text-blue-600 transition"><span class="text-xs text-gray-400">2h ago</span> AI breakthrough in protein folding research</a>
    <a href="#" class="block text-sm hover:text-blue-600 transition"><span class="text-xs text-gray-400">4h ago</span> New framework simplifies web development</a>
    <a href="#" class="block text-sm hover:text-blue-600 transition"><span class="text-xs text-gray-400">6h ago</span> Quantum computing milestone achieved</a>
  </div>
</div>""",
    },
    "tasks": {
        "name": "Task List",
        "category": "productivity",
        "icon": "✅",
        "default_config": {"show_completed": True},
        "render_html": lambda cfg: """
<div class="widget-tasks p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">✅ Tasks</h3>
  <div class="space-y-2">
    <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" checked class="rounded"> <span class="line-through text-gray-400">Review PRs</span></label>
    <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" class="rounded"> <span>Update documentation</span></label>
    <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" class="rounded"> <span>Deploy staging</span></label>
    <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" class="rounded"> <span>Team standup</span></label>
  </div>
</div>""",
    },
    "calendar": {
        "name": "Calendar",
        "category": "productivity",
        "icon": "📅",
        "default_config": {"view": "month", "highlight_today": True},
        "render_html": lambda cfg: """
<div class="widget-calendar p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">📅 """ + datetime.now().strftime("%B %Y") + """</h3>
  <div class="grid grid-cols-7 gap-1 text-center text-xs">
    <div class="text-gray-400">S</div><div class="text-gray-400">M</div><div class="text-gray-400">T</div><div class="text-gray-400">W</div><div class="text-gray-400">T</div><div class="text-gray-400">F</div><div class="text-gray-400">S</div>
    <div class="py-1"></div><div class="py-1"></div><div class="py-1"></div><div class="py-1"></div><div class="py-1"></div><div class="py-1">1</div><div class="py-1">2</div>
    <div class="py-1">3</div><div class="py-1">4</div><div class="py-1">5</div><div class="py-1">6</div><div class="py-1">7</div><div class="py-1">8</div><div class="py-1">9</div>
    <div class="py-1">10</div><div class="py-1">11</div><div class="py-1">12</div><div class="py-1 bg-blue-500 text-white rounded-full">13</div><div class="py-1">14</div><div class="py-1">15</div><div class="py-1">16</div>
  </div>
</div>""",
    },
    "notes": {
        "name": "Quick Notes",
        "category": "productivity",
        "icon": "📝",
        "default_config": {"autosave": True},
        "render_html": lambda cfg: """
<div class="widget-notes p-4 bg-yellow-50 rounded-xl shadow-sm border border-yellow-200">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">📝 Quick Notes</h3>
  <textarea class="w-full h-32 bg-transparent text-sm resize-none outline-none" placeholder="Type your notes here..."></textarea>
</div>""",
    },
    "bookmarks": {
        "name": "Bookmarks",
        "category": "utility",
        "icon": "🔖",
        "default_config": {"links": [{"title": "GitHub", "url": "https://github.com"}, {"title": "Docs", "url": "#"}]},
        "render_html": lambda cfg: """
<div class="widget-bookmarks p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">🔖 Bookmarks</h3>
  <div class="space-y-2">
    <a href="https://github.com" target="_blank" class="flex items-center gap-2 text-sm hover:text-blue-600 transition">🔖 GitHub</a>
    <a href="#" class="flex items-center gap-2 text-sm hover:text-blue-600 transition">🔖 Documentation</a>
    <a href="#" class="flex items-center gap-2 text-sm hover:text-blue-600 transition">🔖 Analytics</a>
  </div>
</div>""",
    },
    "calculator": {
        "name": "Calculator",
        "category": "utility",
        "icon": "🧮",
        "default_config": {"mode": "standard"},
        "render_html": lambda cfg: """
<div class="widget-calculator p-4 bg-gray-800 rounded-xl shadow-sm text-white">
  <div class="bg-gray-900 rounded-lg p-3 text-right text-xl font-mono mb-3" id="calc-display">0</div>
  <div class="grid grid-cols-4 gap-2">
    <button onclick="calcClear()" class="p-2 rounded bg-red-500 hover:bg-red-600 text-sm">C</button>
    <button onclick="calcOp('/')" class="p-2 rounded bg-gray-600 hover:bg-gray-500 text-sm">÷</button>
    <button onclick="calcOp('*')" class="p-2 rounded bg-gray-600 hover:bg-gray-500 text-sm">×</button>
    <button onclick="calcBack()" class="p-2 rounded bg-gray-600 hover:bg-gray-500 text-sm">⌫</button>
    <button onclick="calcNum('7')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">7</button>
    <button onclick="calcNum('8')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">8</button>
    <button onclick="calcNum('9')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">9</button>
    <button onclick="calcOp('-')" class="p-2 rounded bg-gray-600 hover:bg-gray-500 text-sm">−</button>
    <button onclick="calcNum('4')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">4</button>
    <button onclick="calcNum('5')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">5</button>
    <button onclick="calcNum('6')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">6</button>
    <button onclick="calcOp('+')" class="p-2 rounded bg-gray-600 hover:bg-gray-500 text-sm">+</button>
    <button onclick="calcNum('1')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">1</button>
    <button onclick="calcNum('2')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">2</button>
    <button onclick="calcNum('3')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">3</button>
    <button onclick="calcEquals()" class="p-2 rounded bg-blue-500 hover:bg-blue-600 text-sm row-span-2">=</button>
    <button onclick="calcNum('0')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm col-span-2">0</button>
    <button onclick="calcNum('.')" class="p-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">.</button>
  </div>
</div>
<script>
let calcExpr = '';
function calcUpdate() { document.getElementById('calc-display').textContent = calcExpr || '0'; }
function calcNum(n) { calcExpr += n; calcUpdate(); }
function calcOp(op) { if (calcExpr) calcExpr += ' ' + op + ' '; calcUpdate(); }
function calcClear() { calcExpr = ''; calcUpdate(); }
function calcBack() { calcExpr = calcExpr.trim().slice(0, -1); calcUpdate(); }
function calcEquals() { try { calcExpr = String(eval(calcExpr) || 0); } catch { calcExpr = 'Error'; } calcUpdate(); }
</script>""",
    },
    "translator": {
        "name": "Quick Translate",
        "category": "utility",
        "icon": "🌐",
        "default_config": {"source": "en", "target": "es"},
        "render_html": lambda cfg: """
<div class="widget-translator p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">🌐 Translate</h3>
  <textarea class="w-full h-20 border rounded-lg p-2 text-sm mb-2" placeholder="Enter text..."></textarea>
  <div class="flex justify-between items-center">
    <span class="text-xs text-gray-500">EN → ES</span>
    <button class="px-3 py-1 bg-blue-500 text-white rounded-lg text-xs hover:bg-blue-600">Translate</button>
  </div>
</div>""",
    },
    "timer": {
        "name": "Timer",
        "category": "productivity",
        "icon": "⏱",
        "default_config": {"default_minutes": 25},
        "render_html": lambda cfg: """
<div class="widget-timer p-4 bg-white rounded-xl shadow-sm border border-gray-100 text-center">
  <h3 class="text-sm font-semibold text-gray-700 mb-2">⏱ Timer</h3>
  <div class="text-4xl font-mono font-bold text-gray-800 mb-3" id="timer-display">25:00</div>
  <div class="flex gap-2 justify-center">
    <button onclick="startTimer()" class="px-3 py-1 bg-green-500 text-white rounded text-xs">Start</button>
    <button onclick="pauseTimer()" class="px-3 py-1 bg-yellow-500 text-white rounded text-xs">Pause</button>
    <button onclick="resetTimer()" class="px-3 py-1 bg-red-500 text-white rounded text-xs">Reset</button>
  </div>
</div>
<script>
let timerSec = 1500, timerInterval = null;
function fmtTimer() { const m = Math.floor(timerSec/60), s = timerSec%60; document.getElementById('timer-display').textContent = String(m).padStart(2,'0')+':'+String(s).padStart(2,'0'); }
function startTimer() { if (timerInterval) return; timerInterval = setInterval(() => { if (timerSec > 0) { timerSec--; fmtTimer(); } else { clearInterval(timerInterval); timerInterval = null; alert('Timer done!'); } }, 1000); }
function pauseTimer() { clearInterval(timerInterval); timerInterval = null; }
function resetTimer() { pauseTimer(); timerSec = 1500; fmtTimer(); }
</script>""",
    },
    "pomodoro": {
        "name": "Pomodoro",
        "category": "productivity",
        "icon": "🍅",
        "default_config": {"work_minutes": 25, "break_minutes": 5},
        "render_html": lambda cfg: """
<div class="widget-pomodoro p-4 bg-red-50 rounded-xl shadow-sm border border-red-100 text-center">
  <h3 class="text-sm font-semibold text-red-700 mb-2">🍅 Pomodoro</h3>
  <div class="text-4xl font-mono font-bold text-red-600 mb-3" id="pomo-display">25:00</div>
  <div class="flex gap-2 justify-center">
    <button onclick="startPomo()" class="px-3 py-1 bg-red-500 text-white rounded text-xs">Start</button>
    <button onclick="resetPomo()" class="px-3 py-1 bg-gray-500 text-white rounded text-xs">Reset</button>
  </div>
  <div class="mt-2 text-xs text-red-400" id="pomo-status">Ready to focus</div>
</div>
<script>
let pomoSec = 1500, pomoInterval = null, pomoMode = 'work';
function fmtPomo() { const m = Math.floor(pomoSec/60), s = pomoSec%60; document.getElementById('pomo-display').textContent = String(m).padStart(2,'0')+':'+String(s).padStart(2,'0'); }
function startPomo() { if (pomoInterval) return; document.getElementById('pomo-status').textContent = pomoMode === 'work' ? 'Focusing...' : 'On break...'; pomoInterval = setInterval(() => { if (pomoSec > 0) { pomoSec--; fmtPomo(); } else { clearInterval(pomoInterval); pomoInterval = null; pomoMode = pomoMode === 'work' ? 'break' : 'work'; pomoSec = (pomoMode === 'work' ? 25 : 5) * 60; fmtPomo(); document.getElementById('pomo-status').textContent = pomoMode === 'work' ? 'Break over! Ready to focus' : 'Work session done! Take a break'; } }, 1000); }
function resetPomo() { clearInterval(pomoInterval); pomoInterval = null; pomoMode = 'work'; pomoSec = 1500; fmtPomo(); document.getElementById('pomo-status').textContent = 'Ready to focus'; }
</script>""",
    },
    "system-monitor": {
        "name": "System Monitor",
        "category": "dev",
        "icon": "💻",
        "default_config": {"show_cpu": True, "show_memory": True, "show_disk": True},
        "render_html": lambda cfg: """
<div class="widget-system p-4 bg-gray-900 rounded-xl shadow-sm text-white">
  <h3 class="text-sm font-semibold mb-3">💻 System</h3>
  <div class="space-y-3">
    <div><div class="flex justify-between text-xs mb-1"><span>CPU</span><span>45%</span></div><div class="h-2 bg-gray-700 rounded-full"><div class="h-2 bg-green-500 rounded-full" style="width:45%"></div></div></div>
    <div><div class="flex justify-between text-xs mb-1"><span>Memory</span><span>62%</span></div><div class="h-2 bg-gray-700 rounded-full"><div class="h-2 bg-yellow-500 rounded-full" style="width:62%"></div></div></div>
    <div><div class="flex justify-between text-xs mb-1"><span>Disk</span><span>78%</span></div><div class="h-2 bg-gray-700 rounded-full"><div class="h-2 bg-red-500 rounded-full" style="width:78%"></div></div></div>
  </div>
</div>""",
    },
    "api-status": {
        "name": "API Status",
        "category": "dev",
        "icon": "🔌",
        "default_config": {"endpoints": [{"name": "Main API", "url": "/api/health"}, {"name": "Auth", "url": "/auth/health"}]},
        "render_html": lambda cfg: """
<div class="widget-api p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">🔌 API Status</h3>
  <div class="space-y-2">
    <div class="flex justify-between items-center text-sm"><span>Main API</span><span class="text-green-600 text-xs">● Online</span></div>
    <div class="flex justify-between items-center text-sm"><span>Auth Service</span><span class="text-green-600 text-xs">● Online</span></div>
    <div class="flex justify-between items-center text-sm"><span>Database</span><span class="text-green-600 text-xs">● Online</span></div>
    <div class="flex justify-between items-center text-sm"><span>Cache</span><span class="text-yellow-600 text-xs">● Degraded</span></div>
  </div>
</div>""",
    },
    "usage-stats": {
        "name": "Usage Stats",
        "category": "analytics",
        "icon": "📊",
        "default_config": {"period": "week"},
        "render_html": lambda cfg: """
<div class="widget-usage p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">📊 Usage</h3>
  <div class="flex items-end gap-2 h-24 mb-2">
    <div class="flex-1 bg-blue-200 rounded-t" style="height:40%"></div>
    <div class="flex-1 bg-blue-300 rounded-t" style="height:65%"></div>
    <div class="flex-1 bg-blue-400 rounded-t" style="height:50%"></div>
    <div class="flex-1 bg-blue-500 rounded-t" style="height:80%"></div>
    <div class="flex-1 bg-blue-600 rounded-t" style="height:60%"></div>
    <div class="flex-1 bg-blue-700 rounded-t" style="height:90%"></div>
    <div class="flex-1 bg-blue-800 rounded-t" style="height:75%"></div>
  </div>
  <div class="flex justify-between text-xs text-gray-400">
    <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
  </div>
</div>""",
    },
    "recent-chats": {
        "name": "Recent Chats",
        "category": "communication",
        "icon": "💬",
        "default_config": {"count": 5},
        "render_html": lambda cfg: """
<div class="widget-chats p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">💬 Recent Chats</h3>
  <div class="space-y-3">
    <div class="flex items-center gap-3"><div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-xs">A</div><div class="flex-1 min-w-0"><div class="text-sm font-medium">Alice</div><div class="text-xs text-gray-500 truncate">Can you review the latest changes?</div></div></div>
    <div class="flex items-center gap-3"><div class="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-xs">B</div><div class="flex-1 min-w-0"><div class="text-sm font-medium">Bob</div><div class="text-xs text-gray-500 truncate">Meeting at 3pm</div></div></div>
    <div class="flex items-center gap-3"><div class="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center text-xs">C</div><div class="flex-1 min-w-0"><div class="text-sm font-medium">Carol</div><div class="text-xs text-gray-500 truncate">Thanks for the help!</div></div></div>
  </div>
</div>""",
    },
    "shortcuts": {
        "name": "Keyboard Shortcuts",
        "category": "utility",
        "icon": "⌨️",
        "default_config": {},
        "render_html": lambda cfg: """
<div class="widget-shortcuts p-4 bg-white rounded-xl shadow-sm border border-gray-100">
  <h3 class="text-sm font-semibold text-gray-700 mb-3">⌨️ Shortcuts</h3>
  <div class="space-y-2 text-sm">
    <div class="flex justify-between"><span class="text-gray-600">Search</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Ctrl+K</kbd></div>
    <div class="flex justify-between"><span class="text-gray-600">New Note</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Ctrl+N</kbd></div>
    <div class="flex justify-between"><span class="text-gray-600">Settings</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Ctrl+,</kbd></div>
    <div class="flex justify-between"><span class="text-gray-600">Help</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Ctrl+/</kbd></div>
  </div>
</div>""",
    },
}


# ---------------------------------------------------------------------------
# 2. Database schema
# ---------------------------------------------------------------------------

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS widgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    widget_type TEXT NOT NULL,
    title       TEXT,
    config      TEXT DEFAULT '{}',
    position    TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT DEFAULT '',
    tags        TEXT DEFAULT '[]',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    frequency     TEXT DEFAULT 'daily',
    streak        INTEGER DEFAULT 0,
    last_tracked  TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id    INTEGER NOT NULL,
    tracked_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    note        TEXT,
    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_widgets_user ON widgets(user_id);
CREATE INDEX IF NOT EXISTS idx_kb_user ON knowledge_base(user_id);
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
"""

_db_initialized = False


def init_db() -> None:
    """Create all tables and indexes if they do not exist yet."""
    global _db_initialized
    if _db_initialized:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_INIT_SQL)
    conn.commit()
    conn.close()
    _db_initialized = True


def _conn() -> sqlite3.Connection:
    """Return a connection with row factory set."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# 3. Widget CRUD
# ---------------------------------------------------------------------------

def get_widgets(user_id: str) -> list[dict[str, Any]]:
    """Fetch all widgets for a user, ordered by creation time."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM widgets WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
        return [_row_to_widget(r) for r in rows]


def save_widget(user_id: str, widget: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a widget.

    If ``widget`` contains ``id``, the existing row is updated.
    Returns the persisted widget dict.
    """
    init_db()
    wid = widget.get("id")
    wtype = widget.get("widget_type", "clock")
    title = widget.get("title", _WIDGET_TYPES.get(wtype, {}).get("name", wtype))
    config = json.dumps(widget.get("config", {}))
    position = json.dumps(widget.get("position", {}))

    with _conn() as conn:
        if wid:
            conn.execute(
                """UPDATE widgets SET widget_type = ?, title = ?, config = ?, position = ?
                   WHERE id = ? AND user_id = ?""",
                (wtype, title, config, position, wid, user_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM widgets WHERE id = ?", (wid,)
            ).fetchone()
        else:
            cur = conn.execute(
                "INSERT INTO widgets (user_id, widget_type, title, config, position) VALUES (?, ?, ?, ?, ?)",
                (user_id, wtype, title, config, position),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM widgets WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return _row_to_widget(row)


def remove_widget(user_id: str, widget_id: int) -> None:
    """Delete a widget by ID, ensuring it belongs to the given user."""
    with _conn() as conn:
        conn.execute("DELETE FROM widgets WHERE id = ? AND user_id = ?", (widget_id, user_id))
        conn.commit()


def get_default_widgets() -> list[dict[str, Any]]:
    """Return a pre-configured default set of widgets for new users."""
    defaults = [
        {"widget_type": "clock", "title": "Clock", "config": {"format": "12h", "show_seconds": True}, "position": {"x": 0, "y": 0, "w": 2, "h": 2}},
        {"widget_type": "tasks", "title": "My Tasks", "config": {"show_completed": True}, "position": {"x": 2, "y": 0, "w": 2, "h": 3}},
        {"widget_type": "weather", "title": "Weather", "config": {"location": "New York", "unit": "celsius"}, "position": {"x": 4, "y": 0, "w": 2, "h": 2}},
        {"widget_type": "notes", "title": "Quick Notes", "config": {"autosave": True}, "position": {"x": 0, "y": 2, "w": 2, "h": 3}},
        {"widget_type": "pomodoro", "title": "Focus Timer", "config": {"work_minutes": 25, "break_minutes": 5}, "position": {"x": 2, "y": 3, "w": 2, "h": 3}},
        {"widget_type": "calendar", "title": "Calendar", "config": {"view": "month"}, "position": {"x": 4, "y": 2, "w": 2, "h": 3}},
        {"widget_type": "usage-stats", "title": "Weekly Usage", "config": {"period": "week"}, "position": {"x": 0, "y": 5, "w": 3, "h": 3}},
        {"widget_type": "system-monitor", "title": "System", "config": {"show_cpu": True, "show_memory": True}, "position": {"x": 3, "y": 5, "w": 3, "h": 3}},
    ]
    return defaults


def render_widget_html(widget_type: str, config: dict[str, Any]) -> str:
    """Render the HTML for a widget given its type and configuration."""
    wdef = _WIDGET_TYPES.get(widget_type)
    if not wdef:
        return f"<div class=\"p-4 text-red-500\">Unknown widget: {widget_type}</div>"
    merged = {**wdef["default_config"], **config}
    merged["_id"] = str(hash(widget_type + str(merged)) % 10000)
    return wdef["render_html"](merged)


# ---------------------------------------------------------------------------
# 4. Knowledge Base CRUD
# ---------------------------------------------------------------------------

def get_kb_pages(user_id: str) -> list[dict[str, Any]]:
    """Fetch all knowledge base pages for a user, newest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge_base WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [_row_to_kb(r) for r in rows]


def save_kb_page(user_id: str, page: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a knowledge base page."""
    pid = page.get("id")
    title = page.get("title", "Untitled")
    content = page.get("content", "")
    tags = json.dumps(page.get("tags", []))
    now = datetime.now().isoformat()

    with _conn() as conn:
        if pid:
            conn.execute(
                "UPDATE knowledge_base SET title = ?, content = ?, tags = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (title, content, tags, now, pid, user_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM knowledge_base WHERE id = ?", (pid,)).fetchone()
        else:
            cur = conn.execute(
                "INSERT INTO knowledge_base (user_id, title, content, tags, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, title, content, tags, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM knowledge_base WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_kb(row)


def search_kb(user_id: str, query: str) -> list[dict[str, Any]]:
    """Full-text-ish search across title, content, and tags."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge_base WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)",
            (user_id, f"%{query}%", f"%{query}%"),
        ).fetchall()
        results = [_row_to_kb(r) for r in rows]
        tag_matches = conn.execute(
            "SELECT * FROM knowledge_base WHERE user_id = ?", (user_id,)
        ).fetchall()
        for r in tag_matches:
            tags = json.loads(r["tags"])
            if any(query.lower() in t.lower() for t in tags):
                kb = _row_to_kb(r)
                if kb["id"] not in {x["id"] for x in results}:
                    results.append(kb)
        results.sort(key=lambda x: x["updated_at"], reverse=True)
        return results


# ---------------------------------------------------------------------------
# 5. Habit Tracker CRUD
# ---------------------------------------------------------------------------

def get_habits(user_id: str) -> list[dict[str, Any]]:
    """Fetch all habits for a user."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
        return [_row_to_habit(r) for r in rows]


def save_habit(user_id: str, habit: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a habit."""
    hid = habit.get("id")
    name = habit.get("name", "New Habit")
    description = habit.get("description", "")
    frequency = habit.get("frequency", "daily")

    with _conn() as conn:
        if hid:
            conn.execute(
                "UPDATE habits SET name = ?, description = ?, frequency = ? WHERE id = ? AND user_id = ?",
                (name, description, frequency, hid, user_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM habits WHERE id = ?", (hid,)).fetchone()
        else:
            cur = conn.execute(
                "INSERT INTO habits (user_id, name, description, frequency) VALUES (?, ?, ?, ?)",
                (user_id, name, description, frequency),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM habits WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_habit(row)


def track_habit(user_id: str, habit_id: int) -> dict[str, Any]:
    """Record a habit completion for today and update streak.

    Returns the updated habit dict.
    """
    today = datetime.now().date()
    now = datetime.now().isoformat()

    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id)
        ).fetchone()
        if not row:
            raise ValueError(f"Habit {habit_id} not found for user {user_id}")

        last = row["last_tracked"]
        streak = row["streak"] or 0

        if last:
            last_date = datetime.fromisoformat(last).date()
            if last_date == today:
                pass
            elif (today - last_date).days == 1:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        conn.execute(
            "UPDATE habits SET streak = ?, last_tracked = ? WHERE id = ?",
            (streak, now, habit_id),
        )
        conn.execute(
            "INSERT INTO habit_logs (habit_id, tracked_at, note) VALUES (?, ?, ?)",
            (habit_id, now, "Tracked via dashboard"),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
        return _row_to_habit(row)


# ---------------------------------------------------------------------------
# 6. Daily Summary
# ---------------------------------------------------------------------------

def get_daily_summary(user_id: str) -> dict[str, Any]:
    """Aggregate today's info: habits, widget count, KB count, recent activity."""
    today = datetime.now().date()
    today_start = datetime(today.year, today.month, today.day).isoformat()

    with _conn() as conn:
        habits = conn.execute(
            "SELECT * FROM habits WHERE user_id = ?", (user_id,)
        ).fetchall()
        habit_count = len(habits)
        habits_tracked_today = sum(
            1 for h in habits
            if h["last_tracked"] and datetime.fromisoformat(h["last_tracked"]).date() == today
        )
        longest_streak = max((h["streak"] or 0 for h in habits), default=0)

        widget_count = conn.execute(
            "SELECT COUNT(*) as c FROM widgets WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]

        kb_count = conn.execute(
            "SELECT COUNT(*) as c FROM knowledge_base WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]

        recent_kb = conn.execute(
            "SELECT title, updated_at FROM knowledge_base WHERE user_id = ? ORDER BY updated_at DESC LIMIT 3",
            (user_id,),
        ).fetchall()

    return {
        "date": today.isoformat(),
        "habits": {
            "total": habit_count,
            "tracked_today": habits_tracked_today,
            "longest_streak": longest_streak,
        },
        "widgets": {"total": widget_count},
        "knowledge_base": {
            "total_pages": kb_count,
            "recently_updated": [{"title": r["title"], "updated_at": r["updated_at"]} for r in recent_kb],
        },
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# 7. Row converters
# ---------------------------------------------------------------------------

def _row_to_widget(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "widget_type": row["widget_type"],
        "title": row["title"],
        "config": json.loads(row["config"] or "{}"),
        "position": json.loads(row["position"] or "{}"),
        "created_at": row["created_at"],
    }


def _row_to_kb(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "content": row["content"],
        "tags": json.loads(row["tags"] or "[]"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_habit(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "description": row["description"],
        "frequency": row["frequency"],
        "streak": row["streak"],
        "last_tracked": row["last_tracked"],
        "created_at": row["created_at"],
    }
