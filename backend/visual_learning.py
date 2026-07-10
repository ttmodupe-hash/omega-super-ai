"""
Luqi AI v24.5.0 — Visual Learning Engine
==========================================
Interactive diagrams, flowcharts, and visual learning aids.

Features:
  - Interactive flowchart generation
  - Animated process diagrams
  - Concept mind maps
  - Comparison tables with visual indicators
  - Interactive quizzes with visual feedback
  - Progress tracking visualization
  - Browser-based (works on mobile)

Part of Luqi AI v24.5.0 by Limitless Telecoms — Empowering Africa
"""

from __future__ import annotations

import html
import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger: logging.Logger = logging.getLogger("luqi.visual_learning")

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DiagramType(str, Enum):
    """Supported diagram categories."""

    FLOWCHART = "flowchart"
    MINDMAP = "mindmap"
    PROCESS = "process"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    HIERARCHY = "hierarchy"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class InteractiveDiagram:
    """Lightweight descriptor for an interactive diagram."""

    diagram_type: DiagramType
    title: str
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared CSS / JS scaffolding
# ---------------------------------------------------------------------------

_CSS_BASE: str = """
:root {
  --bg: #1a1a2e;
  --bg-card: #16213e;
  --bg-hover: #0f3460;
  --accent-blue: #4a9eff;
  --accent-green: #2ecc71;
  --accent-orange: #f39c12;
  --accent-red: #e74c3c;
  --accent-purple: #9b59b6;
  --accent-cyan: #00d2ff;
  --text: #e0e0e0;
  --text-dim: #a0a0b0;
  --border: #2a2a4a;
  --radius: 12px;
  --shadow: 0 8px 32px rgba(0,0,0,0.35);
  --transition: 0.3s ease;
}
*, *::before, *::after { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  overflow-x: hidden;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
}
h1, h2, h3 {
  margin: 0 0 16px 0;
  font-weight: 700;
  letter-spacing: -0.02em;
}
h1 { font-size: clamp(1.5rem, 4vw, 2.2rem); }
h2 { font-size: clamp(1.2rem, 3vw, 1.7rem); color: var(--accent-blue); }
h3 { font-size: 1.1rem; color: var(--accent-cyan); }
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
  transition: transform var(--transition), box-shadow var(--transition);
}
.card:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.45); }
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 10px 20px; border: none; border-radius: 8px;
  background: var(--accent-blue); color: #fff; font-size: 0.95rem;
  font-weight: 600; cursor: pointer; transition: filter var(--transition), transform var(--transition);
}
.btn:hover { filter: brightness(1.15); transform: scale(1.03); }
.btn:focus-visible { outline: 3px solid var(--accent-cyan); outline-offset: 2px; }
.btn-secondary { background: var(--bg-hover); border: 1px solid var(--border); }
.btn-success { background: var(--accent-green); }
.btn-danger  { background: var(--accent-red); }
.btn-warning { background: var(--accent-orange); }
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
@media (max-width: 640px) {
  .container { padding: 12px 8px; }
  .card { padding: 14px; }
}
""".strip()

_JS_UTILS: str = """
function $(s){ return document.querySelector(s); }
function $$(s){ return document.querySelectorAll(s); }
function on(el, ev, fn){ el.addEventListener(ev, fn); }
function ce(tag, cls, text){
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function animateCSS(el, keyframes, opts){
  return el.animate(keyframes, Object.assign({duration:400, easing:'ease'}, opts));
}
""".strip()


def _html_boilerplate(title: str, body: str, extra_css: str = "", extra_js: str = "") -> str:
    """Wrap *body* in a self-contained HTML document with the Luqi dark theme."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — Luqi AI Visual Learning</title>
<style>
{_CSS_BASE}
{extra_css}
</style>
</head>
<body>
<div class="container" role="main" aria-label="{html.escape(title)}">
{body}
</div>
<script>
{_JS_UTILS}
{extra_js}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Singleton implementation
# ---------------------------------------------------------------------------


class _MetaVLE(type):
    """Metaclass enforcing the singleton contract for ``VisualLearningEngine``."""

    _instance: VisualLearningEngine | None = None

    def __call__(cls, *args: Any, **kw: Any) -> VisualLearningEngine:  # type: ignore[override]
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kw)
        return cls._instance


@dataclass
class _QuizState:
    """Internal mutable state for quiz rendering."""

    current: int = 0
    score: int = 0
    answers: list[int] = field(default_factory=list)


class VisualLearningEngine(metaclass=_MetaVLE):
    """
    Visual Learning Engine for Luqi AI.

    Generates interactive, self-contained HTML/CSS/JS learning aids with
    no external dependencies.  All methods return an HTML string that can
    be served directly or embedded in a larger page.
    """

    # ------------------------------------------------------------------ #
    # Flowchart
    # ------------------------------------------------------------------ #
    def create_flowchart(
        self,
        title: str,
        steps: list[dict[str, Any]],
        decisions: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Build an interactive flowchart.

        Parameters
        ----------
        title : str
            Chart heading.
        steps : list[dict]
            Each dict has ``text`` and optionally ``shape`` (``'start'``,
            ``'process'``, ``'decision'``, ``'end'``).
        decisions : list[dict] | None
            Decision nodes with ``text``, ``yes_branch``, ``no_branch``.

        Returns
        -------
        str
            Self-contained HTML page.
        """
        decisions = decisions or []
        uid = "f" + uuid.uuid4().hex[:8]
        nodes_html: list[str] = []
        shapes = {"start": "oval", "end": "oval", "decision": "diamond", "process": "rect"}

        all_nodes = steps + decisions
        for i, node in enumerate(all_nodes):
            nid = f"{uid}-n{i}"
            text = html.escape(str(node.get("text", f"Step {i + 1}")))
            shape = shapes.get(node.get("shape", "process"), "rect")
            extra_cls = " decision" if shape == "diamond" else ""
            detail = html.escape(str(node.get("detail", "")))
            detail_attr = f' data-detail="{detail}"' if detail else ""
            nodes_html.append(
                f'<div class="fc-node fc-{shape}{extra_cls}" '
                f'id="{nid}" tabindex="0" role="button" aria-label="Flowchart step: {text}"{detail_attr}>'
                f'<span class="fc-label">{text}</span></div>'
            )

        arrows_html: list[str] = []
        for i in range(len(all_nodes) - 1):
            arrows_html.append(
                f'<div class="fc-arrow" data-from="{uid}-n{i}" data-to="{uid}-n{i + 1}">'
                f'<span class="fc-arrowhead">&#9660;</span></div>'
            )
        for d in decisions:
            src = all_nodes.index(d) if d in all_nodes else -1
            if src < 0:
                continue
            for label, target in [("Yes", d.get("yes_branch")), ("No", d.get("no_branch"))]:
                if target is not None and 0 <= int(target) < len(all_nodes):
                    arrows_html.append(
                        f'<div class="fc-arrow fc-labelled" data-from="{uid}-n{src}" '
                        f'data-to="{uid}-n{int(target)}">'
                        f'<span class="fc-edge-label">{label}</span>'
                        f'<span class="fc-arrowhead">&#9660;</span></div>'
                    )

        css = """
.fc-wrap { display:flex; flex-direction:column; align-items:center; gap:18px; padding:20px 0; }
.fc-node { position:relative; padding:16px 28px; background:var(--bg-hover); border:2px solid var(--accent-blue);
  border-radius:var(--radius); cursor:pointer; min-width:160px; text-align:center;
  transition:transform var(--transition), box-shadow var(--transition); font-weight:600; }
.fc-node:hover, .fc-node:focus { transform:scale(1.05); box-shadow:0 0 20px rgba(74,158,255,0.35); outline:none; }
.fc-oval { border-radius:50px; background:linear-gradient(135deg, var(--accent-green), #27ae60); border-color:#27ae60; }
.fc-diamond { transform:rotate(45deg); width:140px; height:140px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg, var(--accent-orange), #e67e22); border-color:#e67e22; }
.fc-diamond .fc-label { transform:rotate(-45deg); font-size:0.85rem; }
.fc-rect { background:linear-gradient(135deg, var(--accent-blue), #2980b9); }
.fc-arrow { position:relative; height:28px; width:2px; background:var(--text-dim); margin:-6px 0; }
.fc-arrowhead { position:absolute; bottom:-6px; left:50%; transform:translateX(-50%); color:var(--text-dim); font-size:10px; }
.fc-labelled .fc-edge-label { position:absolute; left:12px; top:-10px; font-size:0.75rem; color:var(--accent-cyan); font-weight:700; }
.fc-detail-panel { margin-top:16px; padding:14px; background:var(--bg); border:1px solid var(--border); border-radius:8px; color:var(--accent-cyan); display:none; }
.fc-detail-panel.active { display:block; animation:fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity:0; transform:translateY(-6px); } to { opacity:1; transform:translateY(0); } }
@media (max-width:640px) { .fc-node { min-width:120px; padding:12px 18px; font-size:0.9rem; } }
""".strip()

        js = f"""
document.querySelectorAll('.fc-node').forEach(function(node) {{
  node.addEventListener('click', function() {{
    document.querySelectorAll('.fc-node').forEach(function(n){{ n.style.boxShadow=''; }});
    this.style.boxShadow='0 0 24px rgba(74,158,255,0.6)';
    var panel = document.getElementById('{uid}-detail');
    var detail = this.getAttribute('data-detail');
    if (panel && detail) {{ panel.textContent = detail; panel.classList.add('active'); }}
  }});
}});
""".strip()

        body = f"""
<h1>{html.escape(title)}</h1>
<div class="card">
  <div class="fc-wrap" id="{uid}">
    {''.join(nodes_html)}
    {''.join(arrows_html)}
  </div>
  <div class="fc-detail-panel" id="{uid}-detail" role="region" aria-live="polite">Click a node for details</div>
</div>
"""
        return _html_boilerplate(title, body, css, js)

    # ------------------------------------------------------------------ #
    # Mind map
    # ------------------------------------------------------------------ #
    def create_mindmap(self, topic: str, subtopics: list[dict[str, Any]]) -> str:
        """
        Build a radial mind map with expandable branches.

        Parameters
        ----------
        topic : str
            Central concept.
        subtopics : list[dict]
            Each dict has ``name`` and optionally ``children`` (list).

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "m" + uuid.uuid4().hex[:8]
        topic_safe = html.escape(topic)
        cats = ["blue", "green", "orange", "red", "purple", "cyan"]

        def _branch(st: dict[str, Any], idx: int, parent_id: str) -> str:
            name = html.escape(str(st.get("name", "Untitled")))
            cat = cats[idx % len(cats)]
            kids = st.get("children", [])
            bid = f"{uid}-b{idx}"
            kids_html = ""
            if kids:
                lis = ""
                for ci, child in enumerate(kids):
                    cname = html.escape(str(child if isinstance(child, str) else child.get("name", "?")))
                    lis += f'<li class="mm-leaf mm-{cat}">{cname}</li>'
                kids_html = f'<ul class="mm-children" id="{bid}-kids">{lis}</ul>'
            has_kids = " expandable" if kids else ""
            return (
                f'<li class="mm-branch{has_kids}" id="{bid}" data-parent="{parent_id}">'
                f'<span class="mm-node mm-{cat}" tabindex="0" role="button" '
                f'aria-expanded="false">{name}</span>{kids_html}</li>'
            )

        branches_html = "".join(_branch(st, i, f"{uid}-root") for i, st in enumerate(subtopics))

        css = """
.mm-wrap { position:relative; min-height:500px; padding:20px; }
.mm-root { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  background:linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  padding:18px 30px; border-radius:50px; font-weight:800; font-size:1.15rem;
  box-shadow:0 0 30px rgba(74,158,255,0.4); cursor:pointer; z-index:2; }
.mm-tree { list-style:none; padding:0; margin:0; position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); }
.mm-branch { margin:10px 0; }
.mm-node { display:inline-block; padding:8px 16px; border-radius:20px; font-weight:600; cursor:pointer;
  transition:transform var(--transition), box-shadow var(--transition); border:2px solid transparent; }
.mm-node:hover, .mm-node:focus { transform:scale(1.08); outline:none; }
.mm-blue { background:rgba(74,158,255,0.15); border-color:var(--accent-blue); color:var(--accent-blue); }
.mm-green { background:rgba(46,204,113,0.15); border-color:var(--accent-green); color:var(--accent-green); }
.mm-orange { background:rgba(243,156,18,0.15); border-color:var(--accent-orange); color:var(--accent-orange); }
.mm-red { background:rgba(231,76,60,0.15); border-color:var(--accent-red); color:var(--accent-red); }
.mm-purple { background:rgba(155,89,182,0.15); border-color:var(--accent-purple); color:var(--accent-purple); }
.mm-cyan { background:rgba(0,210,255,0.15); border-color:var(--accent-cyan); color:var(--accent-cyan); }
.mm-children { list-style:none; padding-left:24px; margin:6px 0; display:none; border-left:2px solid var(--border); }
.mm-children.visible { display:block; animation:slideDown 0.3s ease; }
@keyframes slideDown { from { opacity:0; max-height:0; } to { opacity:1; max-height:400px; } }
.mm-leaf { padding:4px 10px; margin:3px 0; border-radius:8px; font-size:0.9rem; background:var(--bg-card); }
.mm-line { position:absolute; background:var(--border); z-index:0; }
""".strip()

        js = f"""
(function() {{
  var root = document.getElementById('{uid}-root');
  var tree = document.getElementById('{uid}-tree');
  var branches = tree.querySelectorAll('.mm-branch');
  var angleStep = (2 * Math.PI) / Math.max(branches.length, 1);
  var radius = Math.min(window.innerWidth * 0.35, 220);
  branches.forEach(function(b, i) {{
    var angle = i * angleStep - Math.PI / 2;
    var x = Math.cos(angle) * radius;
    var y = Math.sin(angle) * radius;
    b.style.position = 'absolute';
    b.style.left = 'calc(50% + ' + x + 'px)';
    b.style.top = 'calc(50% + ' + y + 'px)';
    b.style.transform = 'translate(-50%, -50%)';
  }});
  tree.querySelectorAll('.mm-node').forEach(function(node) {{
    node.addEventListener('click', function() {{
      var kids = this.parentElement.querySelector('.mm-children');
      if (kids) {{
        var open = kids.classList.toggle('visible');
        this.setAttribute('aria-expanded', open ? 'true' : 'false');
      }}
    }});
  }});
}})();
""".strip()

        body = f"""
<h1>{topic_safe} — Mind Map</h1>
<div class="card mm-wrap" id="{uid}">
  <div class="mm-root" id="{uid}-root" tabindex="0">{topic_safe}</div>
  <ul class="mm-tree" id="{uid}-tree">{branches_html}</ul>
</div>
"""
        return _html_boilerplate(f"Mind Map: {topic}", body, css, js)

    # ------------------------------------------------------------------ #
    # Process diagram
    # ------------------------------------------------------------------ #
    def create_process_diagram(self, title: str, stages: list[dict[str, Any]]) -> str:
        """
        Build a horizontal process flow with animated progression.

        Parameters
        ----------
        title : str
            Diagram heading.
        stages : list[dict]
            Each dict has ``name``, ``description``, and optionally ``status``
            (``'pending'``, ``'active'``, ``'completed'``).

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "p" + uuid.uuid4().hex[:8]
        cards: list[str] = []
        for i, stage in enumerate(stages):
            name = html.escape(str(stage.get("name", f"Stage {i + 1}")))
            desc = html.escape(str(stage.get("description", "")))
            status = stage.get("status", "pending")
            sc = {"completed": "pd-done", "active": "pd-active", "pending": "pd-pending"}.get(status, "pd-pending")
            dot = {"completed": "&#10003;", "active": "&#9654;", "pending": "&#9679;"}.get(status, "&#9679;")
            detail = html.escape(str(stage.get("detail", desc)))
            cards.append(
                f'<div class="pd-stage {sc}" id="{uid}-s{i}" tabindex="0" role="button" '
                f'aria-label="Stage {i + 1}: {name}, status {status}" data-detail="{detail}">'
                f'<div class="pd-dot">{dot}</div>'
                f'<div class="pd-name">{name}</div>'
                f'<div class="pd-desc">{desc}</div></div>'
            )
            if i < len(stages) - 1:
                cards.append(f'<div class="pd-connector"></div>')

        css = """
.pd-flow { display:flex; align-items:center; gap:0; overflow-x:auto; padding:24px 8px; }
.pd-stage { flex:0 0 160px; text-align:center; padding:18px 12px; background:var(--bg-card);
  border:2px solid var(--border); border-radius:var(--radius); cursor:pointer;
  transition:transform var(--transition), border-color var(--transition); position:relative; }
.pd-stage:hover, .pd-stage:focus { transform:translateY(-4px); outline:none; }
.pd-dot { width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  margin:0 auto 10px; font-size:1.1rem; font-weight:800; background:var(--bg); border:2px solid var(--text-dim); color:var(--text-dim); }
.pd-done { border-color:var(--accent-green); }
.pd-done .pd-dot { background:var(--accent-green); color:#fff; border-color:var(--accent-green); }
.pd-active { border-color:var(--accent-blue); animation:pulse 2s infinite; }
.pd-active .pd-dot { background:var(--accent-blue); color:#fff; border-color:var(--accent-blue); }
.pd-pending { opacity:0.65; }
@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(74,158,255,0.4);} 50%{box-shadow:0 0 0 10px rgba(74,158,255,0);} }
.pd-connector { flex:0 0 40px; height:3px; background:linear-gradient(90deg, var(--accent-green), var(--accent-blue)); border-radius:2px; position:relative; }
.pd-connector::after { content:'>'; position:absolute; right:-4px; top:50%; transform:translateY(-50%);
  color:var(--accent-blue); font-weight:800; }
.pd-detail { margin-top:14px; padding:14px; background:var(--bg); border:1px solid var(--border); border-radius:8px; display:none; color:var(--accent-cyan); }
.pd-detail.active { display:block; animation:fadeIn 0.3s ease; }
.pd-name { font-weight:700; margin-bottom:4px; }
.pd-desc { font-size:0.85rem; color:var(--text-dim); }
@media (max-width:640px) { .pd-flow { flex-direction:column; gap:8px; } .pd-connector { display:none; } }
""".strip()

        js = f"""
document.querySelectorAll('.pd-stage').forEach(function(s) {{
  s.addEventListener('click', function() {{
    document.querySelectorAll('.pd-stage').forEach(function(x){{ x.style.boxShadow=''; }});
    this.style.boxShadow='0 0 20px rgba(74,158,255,0.5)';
    var d = document.getElementById('{uid}-detail');
    var detail = this.getAttribute('data-detail');
    if (d && detail) {{ d.textContent = detail; d.classList.add('active'); }}
  }});
}});
""".strip()

        body = f"""
<h1>{html.escape(title)}</h1>
<div class="card">
  <div class="pd-flow" id="{uid}">{''.join(cards)}</div>
  <div class="pd-detail" id="{uid}-detail" role="region" aria-live="polite">Click a stage for details</div>
</div>
"""
        return _html_boilerplate(title, body, css, js)

    # ------------------------------------------------------------------ #
    # Comparison table
    # ------------------------------------------------------------------ #
    def create_comparison_table(
        self,
        title: str,
        items: list[dict[str, Any]],
        criteria: list[str],
    ) -> str:
        """
        Build a side-by-side comparison with visual indicators.

        Parameters
        ----------
        title : str
            Table heading.
        items : list[dict]
            Each dict maps criterion -> value.  Special values:
            ``True``/``False`` render as checkmark / cross.
            ``int``/``float`` render as progress bars.
        criteria : list[str]
            Row labels (leftmost column).

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "c" + uuid.uuid4().hex[:8]
        header_cols = "<th class=\"cmp-crit\">Criterion</th>"
        item_names: list[str] = []
        for it in items:
            name = html.escape(str(it.get("_name", it.get("name", "Item"))))
            item_names.append(name)
            header_cols += f'<th class="cmp-item">{name}</th>'

        rows: list[str] = []
        for crit in criteria:
            crit_safe = html.escape(crit)
            row = f'<td class="cmp-crit">{crit_safe}</td>'
            for it in items:
                val = it.get(crit)
                cell = self._render_comparison_cell(val)
                row += f"<td>{cell}</td>"
            rows.append(f"<tr>{row}</tr>")

        css = """
.cmp-table { width:100%; border-collapse:collapse; margin-top:12px; }
.cmp-table th, .cmp-table td { padding:14px 16px; text-align:center; border-bottom:1px solid var(--border); }
.cmp-table th { background:var(--bg-hover); color:var(--accent-blue); font-weight:700; position:sticky; top:0; }
.cmp-crit { text-align:left; font-weight:600; color:var(--accent-cyan); }
.cmp-check { color:var(--accent-green); font-size:1.3rem; }
.cmp-cross { color:var(--accent-red); font-size:1.3rem; }
.cmp-bar-wrap { background:var(--bg); border-radius:6px; height:18px; overflow:hidden; }
.cmp-bar-fill { height:100%; border-radius:6px; background:linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); transition:width 1s ease; }
.cmp-bar-label { font-size:0.75rem; color:var(--text-dim); margin-top:2px; }
.cmp-table tr:hover td { background:rgba(74,158,255,0.06); }
@media (max-width:640px) { .cmp-table th, .cmp-table td { padding:10px 8px; font-size:0.85rem; } }
""".strip()

        js = """
document.querySelectorAll('.cmp-bar-fill').forEach(function(bar){
  var w = bar.getAttribute('data-width');
  if (w) { bar.style.width='0%'; setTimeout(function(){ bar.style.width=w+'%'; }, 100); }
});
""".strip()

        body = f"""
<h1>{html.escape(title)}</h1>
<div class="card" style="overflow-x:auto;">
  <table class="cmp-table" id="{uid}" role="table" aria-label="Comparison table">
    <thead><tr>{header_cols}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
"""
        return _html_boilerplate(title, body, css, js)

    @staticmethod
    def _render_comparison_cell(val: Any) -> str:
        """Render a single comparison cell value."""
        if val is True:
            return '<span class="cmp-check" aria-label="Yes">&#10003;</span>'
        if val is False:
            return '<span class="cmp-cross" aria-label="No">&#10007;</span>'
        if isinstance(val, (int, float)) and 0 <= val <= 100:
            return (
                f'<div class="cmp-bar-wrap">'
                f'<div class="cmp-bar-fill" data-width="{val}"></div></div>'
                f'<div class="cmp-bar-label">{val}%</div>'
            )
        return html.escape(str(val))

    # ------------------------------------------------------------------ #
    # Timeline
    # ------------------------------------------------------------------ #
    def create_timeline(self, title: str, events: list[dict[str, Any]]) -> str:
        """
        Build a horizontal timeline with event markers.

        Parameters
        ----------
        title : str
            Timeline heading.
        events : list[dict]
            Each dict has ``date``, ``title``, and ``description``.

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "t" + uuid.uuid4().hex[:8]
        items_html: list[str] = []
        for i, ev in enumerate(events):
            date = html.escape(str(ev.get("date", "")))
            etitle = html.escape(str(ev.get("title", "Event")))
            desc = html.escape(str(ev.get("description", "")))
            side = "tl-left" if i % 2 == 0 else "tl-right"
            items_html.append(
                f'<div class="tl-event {side}" tabindex="0" role="button" '
                f'aria-label="Event on {date}: {etitle}">'
                f'<div class="tl-dot"></div>'
                f'<div class="tl-content">'
                f'<div class="tl-date">{date}</div>'
                f'<h3 class="tl-title">{etitle}</h3>'
                f'<p class="tl-desc">{desc}</p></div></div>'
            )

        css = """
.tl-track { position:relative; padding:30px 0; }
.tl-track::before { content:''; position:absolute; left:50%; top:0; bottom:0; width:3px;
  background:linear-gradient(180deg, var(--accent-blue), var(--accent-purple)); transform:translateX(-50%); }
.tl-event { position:relative; width:46%; margin-bottom:24px; cursor:pointer;
  transition:transform var(--transition); }
.tl-event:hover, .tl-event:focus { transform:translateY(-3px); outline:none; }
.tl-left { margin-right:auto; padding-right:30px; text-align:right; }
.tl-right { margin-left:auto; padding-left:30px; text-align:left; }
.tl-dot { position:absolute; width:18px; height:18px; border-radius:50%; background:var(--accent-blue);
  border:3px solid var(--bg); top:6px; z-index:1; box-shadow:0 0 10px rgba(74,158,255,0.5); }
.tl-left .tl-dot { right:-9px; }
.tl-right .tl-dot { left:-9px; }
.tl-content { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:16px; }
.tl-date { font-size:0.8rem; color:var(--accent-cyan); font-weight:700; margin-bottom:4px; }
.tl-title { margin:0 0 6px 0; font-size:1rem; }
.tl-desc { margin:0; font-size:0.9rem; color:var(--text-dim); }
@media (max-width:640px) {
  .tl-track::before { left:20px; }
  .tl-event { width:calc(100% - 50px); margin-left:40px !important; padding-left:20px !important; padding-right:0 !important; text-align:left !important; }
  .tl-left .tl-dot, .tl-right .tl-dot { left:-29px !important; right:auto !important; }
}
""".strip()

        body = f"""
<h1>{html.escape(title)}</h1>
<div class="card"><div class="tl-track" id="{uid}">{''.join(items_html)}</div></div>
"""
        return _html_boilerplate(title, body, css, "")

    # ------------------------------------------------------------------ #
    # Hierarchy
    # ------------------------------------------------------------------ #
    def create_hierarchy(self, title: str, structure: dict[str, Any]) -> str:
        """
        Build an expandable organisational / technical hierarchy chart.

        Parameters
        ----------
        title : str
            Chart heading.
        structure : dict
            Nested dict with ``name`` and ``children`` (list of dicts).

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "h" + uuid.uuid4().hex[:8]

        def _node(nd: dict[str, Any], depth: int = 0) -> str:
            name = html.escape(str(nd.get("name", "Node")))
            role = html.escape(str(nd.get("role", "")))
            kids = nd.get("children", [])
            role_span = f'<span class="hc-role">{role}</span>' if role else ""
            nid = f"{uid}-d{depth}-{uuid.uuid4().hex[:4]}"
            chevron = '<span class="hc-chev">&#9662;</span>' if kids else ""
            kid_html = ""
            if kids:
                kid_list = "".join(_node(child, depth + 1) for child in kids)
                kid_html = f'<ul class="hc-kids" id="{nid}-kids">{kid_list}</ul>'
            expandable = " hc-expand" if kids else ""
            return (
                f'<li class="hc-node{expandable}">'
                f'<div class="hc-box" tabindex="0" role="button" aria-expanded="true" '
                f'data-target="{nid}-kids">{chevron}<span class="hc-name">{name}</span>{role_span}</div>'
                f'{kid_html}</li>'
            )

        tree_html = _node(structure)

        css = """
.hc-tree { list-style:none; padding:0; margin:0; }
.hc-node { margin:4px 0; }
.hc-box { display:inline-flex; align-items:center; gap:10px; padding:10px 18px; background:var(--bg-card);
  border:1px solid var(--border); border-radius:var(--radius); cursor:pointer;
  transition:background var(--transition), transform var(--transition); min-width:180px; }
.hc-box:hover, .hc-box:focus { background:var(--bg-hover); transform:translateX(4px); outline:none; }
.hc-name { font-weight:700; }
.hc-role { font-size:0.8rem; color:var(--text-dim); background:var(--bg); padding:2px 8px; border-radius:4px; }
.hc-chev { color:var(--accent-blue); font-size:0.8rem; transition:transform var(--transition); }
.hc-collapsed .hc-chev { transform:rotate(-90deg); }
.hc-kids { list-style:none; padding-left:32px; margin:4px 0; border-left:2px solid var(--border); }
.hc-kids.collapsed { display:none; }
.hc-root > .hc-box { background:linear-gradient(90deg, var(--accent-blue), var(--accent-purple)); color:#fff; border:none; }
.hc-root > .hc-box .hc-role { background:rgba(255,255,255,0.2); color:#fff; }
@media (max-width:640px) { .hc-box { min-width:auto; padding:8px 12px; font-size:0.9rem; } }
""".strip()

        js = """
document.querySelectorAll('.hc-expand .hc-box').forEach(function(box){
  box.addEventListener('click', function(){
    var targetId = this.getAttribute('data-target');
    var target = document.getElementById(targetId);
    if (target) {
      var collapsed = target.classList.toggle('collapsed');
      this.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      this.parentElement.classList.toggle('hc-collapsed', collapsed);
    }
  });
});
""".strip()

        body = f"""
<h1>{html.escape(title)}</h1>
<div class="card">
  <ul class="hc-tree hc-root" id="{uid}">{tree_html}</ul>
</div>
"""
        return _html_boilerplate(title, body, css, js)

    # ------------------------------------------------------------------ #
    # Interactive quiz
    # ------------------------------------------------------------------ #
    def create_interactive_quiz(self, questions: list[dict[str, Any]]) -> str:
        """
        Build a multiple-choice quiz with visual feedback.

        Parameters
        ----------
        questions : list[dict]
            Each dict has ``question``, ``options`` (list), ``answer``
            (0-based index), and optionally ``explanation``.

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "q" + uuid.uuid4().hex[:8]
        state = _QuizState()
        total = len(questions)

        slides: list[str] = []
        for qi, q in enumerate(questions):
            qtext = html.escape(str(q.get("question", "Question")))
            opts = q.get("options", [])
            explanation = html.escape(str(q.get("explanation", "")))
            opt_html = ""
            for oi, opt in enumerate(opts):
                opt_safe = html.escape(str(opt))
                opt_html += (
                    f'<button class="qz-opt" data-q="{qi}" data-opt="{oi}" '
                    f'aria-label="Option {oi + 1}: {opt_safe}">{opt_safe}</button>'
                )
            slides.append(
                f'<div class="qz-slide" id="{uid}-slide{qi}" style="display:none;" '
                f'data-answer="{q.get("answer", 0)}" data-explanation="{explanation}">'
                f'<h3>Question {qi + 1} of {total}</h3>'
                f'<p class="qz-q">{qtext}</p>'
                f'<div class="qz-opts">{opt_html}</div>'
                f'<div class="qz-feedback" id="{uid}-fb{qi}" role="status" aria-live="polite"></div>'
                f'</div>'
            )

        css = """
.qz-progress { height:8px; background:var(--bg); border-radius:4px; margin-bottom:20px; overflow:hidden; }
.qz-progress-bar { height:100%; width:0%; background:linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); border-radius:4px; transition:width 0.4s ease; }
.qz-slide { animation:fadeIn 0.4s ease; }
.qz-q { font-size:1.1rem; font-weight:600; margin-bottom:16px; }
.qz-opts { display:flex; flex-direction:column; gap:10px; }
.qz-opt { text-align:left; padding:12px 16px; background:var(--bg-card); border:2px solid var(--border);
  border-radius:8px; cursor:pointer; color:var(--text); font-size:1rem;
  transition:background var(--transition), border-color var(--transition); }
.qz-opt:hover, .qz-opt:focus { background:var(--bg-hover); border-color:var(--accent-blue); outline:none; }
.qz-opt.correct { border-color:var(--accent-green); background:rgba(46,204,113,0.15); }
.qz-opt.wrong { border-color:var(--accent-red); background:rgba(231,76,60,0.15); }
.qz-opt.disabled { pointer-events:none; opacity:0.7; }
.qz-feedback { margin-top:14px; padding:12px; border-radius:8px; font-weight:600; display:none; }
.qz-feedback.show { display:block; }
.qz-feedback.correct-fb { background:rgba(46,204,113,0.15); color:var(--accent-green); }
.qz-feedback.wrong-fb { background:rgba(231,76,60,0.15); color:var(--accent-red); }
.qz-nav { display:flex; justify-content:space-between; margin-top:20px; }
.qz-result { text-align:center; padding:30px; }
.qz-score { font-size:3rem; font-weight:800; background:linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.qz-badge { display:inline-block; padding:8px 20px; border-radius:20px; font-weight:700; margin-top:12px; }
.qz-badge.gold { background:rgba(243,156,18,0.2); color:var(--accent-orange); }
.qz-badge.silver { background:rgba(192,192,192,0.15); color:#c0c0c0; }
.qz-badge.bronze { background:rgba(205,127,50,0.15); color:#cd7f32; }
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
""".strip()

        js = f"""
(function() {{
  var total = {total};
  var current = 0;
  var score = 0;
  var slides = document.querySelectorAll('.qz-slide');
  var bar = document.getElementById('{uid}-bar');
  var container = document.getElementById('{uid}');

  function show(i) {{
    slides.forEach(function(s){{ s.style.display='none'; }});
    if (slides[i]) slides[i].style.display='block';
    if (bar) bar.style.width = Math.round(((i)/total)*100) + '%';
  }}
  show(0);

  document.querySelectorAll('.qz-opt').forEach(function(btn){{
    btn.addEventListener('click', function(){{
      if (this.classList.contains('disabled')) return;
      var slide = this.closest('.qz-slide');
      var qIdx = parseInt(this.getAttribute('data-q'));
      var chosen = parseInt(this.getAttribute('data-opt'));
      var correct = parseInt(slide.getAttribute('data-answer'));
      var explanation = slide.getAttribute('data-explanation');
      var fb = document.getElementById('{uid}-fb' + qIdx);
      var allOpts = slide.querySelectorAll('.qz-opt');

      allOpts.forEach(function(o){{ o.classList.add('disabled'); }});
      if (chosen === correct) {{
        score++;
        this.classList.add('correct');
        if (fb) {{ fb.textContent = 'Correct! ' + explanation; fb.className='qz-feedback correct-fb show'; }}
      }} else {{
        this.classList.add('wrong');
        allOpts[correct].classList.add('correct');
        if (fb) {{ fb.textContent = 'Incorrect. ' + explanation; fb.className='qz-feedback wrong-fb show'; }}
      }}

      setTimeout(function(){{
        current++;
        if (current >= total) {{
          showResult();
        }} else {{
          show(current);
        }}
      }}, 2200);
    }});
  }});

  function showResult(){{
    var pct = Math.round((score/total)*100);
    var badgeClass = pct >= 80 ? 'gold' : (pct >= 50 ? 'silver' : 'bronze');
    var badgeText = pct >= 80 ? 'Outstanding!' : (pct >= 50 ? 'Good Job!' : 'Keep Learning!');
    container.innerHTML = '<div class="qz-result">'+
      '<h2>Quiz Complete!</h2>'+
      '<div class="qz-score">'+pct+'%</div>'+
      '<div class="qz-badge '+badgeClass+'">'+badgeText+'</div>'+
      '<p style="margin-top:12px;color:var(--text-dim);">You scored '+score+' out of '+total+'</p>'+
      '<button class="btn" onclick="location.reload()" style="margin-top:16px;">Retry</button>'+
      '</div>';
  }}
}})();
""".strip()

        body = f"""
<h1>Interactive Quiz</h1>
<div class="card" id="{uid}">
  <div class="qz-progress"><div class="qz-progress-bar" id="{uid}-bar"></div></div>
  {''.join(slides)}
</div>
"""
        return _html_boilerplate("Interactive Quiz", body, css, js)

    # ------------------------------------------------------------------ #
    # Progress visualisation
    # ------------------------------------------------------------------ #
    def create_progress_visual(self, progress_data: dict[str, Any]) -> str:
        """
        Build circular progress indicators, skill tree, and badges.

        Parameters
        ----------
        progress_data : dict
            May contain ``skills`` (list of dicts with ``name``, ``level``
            0-100), ``overall`` (0-100), and ``badges`` (list of str).

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "g" + uuid.uuid4().hex[:8]
        overall = int(progress_data.get("overall", 0))
        skills = progress_data.get("skills", [])
        badges = progress_data.get("badges", [])
        radius = 52
        circ = 2 * 3.1416 * radius
        offset = circ - (overall / 100) * circ

        skill_html = ""
        for i, sk in enumerate(skills):
            name = html.escape(str(sk.get("name", "Skill")))
            level = int(sk.get("level", 0))
            soff = circ - (level / 100) * circ
            cat = ["blue", "green", "orange", "purple", "cyan"][i % 5]
            skill_html += f"""
<div class="pv-skill">
  <svg class="pv-ring" viewBox="0 0 120 120" aria-label="{name} {level}%">
    <circle class="pv-track" cx="60" cy="60" r="{radius}"/>
    <circle class="pv-fill pv-{cat}" cx="60" cy="60" r="{radius}"
      stroke-dasharray="{circ}" stroke-dashoffset="{soff}"/>
    <text x="60" y="58" text-anchor="middle" class="pv-pct">{level}%</text>
    <text x="60" y="75" text-anchor="middle" class="pv-label">{name}</text>
  </svg>
</div>"""

        badge_html = ""
        for b in badges:
            bsafe = html.escape(str(b))
            badge_html += f'<span class="pv-badge">{bsafe}</span>'

        css = """
.pv-overall { display:flex; justify-content:center; margin-bottom:30px; }
.pv-ring { width:160px; height:160px; }
.pv-ring circle { fill:none; stroke-width:8; }
.pv-track { stroke:var(--border); }
.pv-fill { stroke-linecap:round; transition:stroke-dashoffset 1.5s ease; }
.pv-blue { stroke:var(--accent-blue); }
.pv-green { stroke:var(--accent-green); }
.pv-orange { stroke:var(--accent-orange); }
.pv-purple { stroke:var(--accent-purple); }
.pv-cyan { stroke:var(--accent-cyan); }
.pv-pct { fill:var(--text) !important; font-size:1.6rem; font-weight:800; }
.pv-label { fill:var(--text-dim) !important; font-size:0.65rem; }
.pv-skills { display:flex; flex-wrap:wrap; gap:20px; justify-content:center; margin-bottom:24px; }
.pv-skill svg { width:100px; height:100px; }
.pv-skill .pv-pct { font-size:1.1rem; }
.pv-skill .pv-label { font-size:0.55rem; }
.pv-badges { display:flex; flex-wrap:wrap; gap:10px; justify-content:center; }
.pv-badge { padding:6px 14px; background:var(--bg-hover); border:1px solid var(--border); border-radius:20px;
  font-size:0.85rem; font-weight:600; color:var(--accent-cyan); }
@media (max-width:640px) { .pv-ring { width:120px; height:120px; } .pv-skill svg { width:80px; height:80px; } }
""".strip()

        body = f"""
<h1>Progress Dashboard</h1>
<div class="card">
  <h2 style="text-align:center;">Overall Progress</h2>
  <div class="pv-overall">
    <svg class="pv-ring" viewBox="0 0 120 120" aria-label="Overall progress {overall}%">
      <circle class="pv-track" cx="60" cy="60" r="{radius}"/>
      <circle class="pv-fill pv-blue" cx="60" cy="60" r="{radius}"
        stroke-dasharray="{circ}" stroke-dashoffset="{offset}"/>
      <text x="60" y="58" text-anchor="middle" class="pv-pct">{overall}%</text>
      <text x="60" y="75" text-anchor="middle" class="pv-label">Overall</text>
    </svg>
  </div>
  <h3 style="text-align:center;">Skills</h3>
  <div class="pv-skills">{skill_html}</div>
  <h3 style="text-align:center;">Badges</h3>
  <div class="pv-badges">{badge_html}</div>
</div>
"""
        return _html_boilerplate("Progress Dashboard", body, css, "")

    # ------------------------------------------------------------------ #
    # Security framework diagram
    # ------------------------------------------------------------------ #
    def create_security_framework_diagram(self, framework: dict[str, Any]) -> str:
        """
        Build a NIST / ISO 27001 security framework visualisation.

        Parameters
        ----------
        framework : dict
            Has ``name``, ``domains`` (list of dicts with ``name``,
            ``controls``, ``maturity`` 0-5).

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "s" + uuid.uuid4().hex[:8]
        fname = html.escape(str(framework.get("name", "Security Framework")))
        domains = framework.get("domains", [])
        domain_html = ""
        for i, d in enumerate(domains):
            dname = html.escape(str(d.get("name", "Domain")))
            maturity = int(d.get("maturity", 0))
            controls = d.get("controls", [])
            mat_color = ["", "#e74c3c", "#e67e22", "#f39c12", "#2ecc71", "#4a9eff"][maturity] if 0 <= maturity <= 5 else "#4a9eff"
            ctrl_html = ""
            for ci, c in enumerate(controls):
                cname = html.escape(str(c if isinstance(c, str) else c.get("name", "Control")))
                cstatus = "Implemented" if isinstance(c, str) else c.get("status", "Planned")
                ccolor = "sf-impl" if cstatus == "Implemented" else "sf-planned"
                ctrl_html += f'<li class="sf-ctrl {ccolor}">{cname}</li>'
            domain_html += f"""
<div class="sf-domain" tabindex="0" role="region" aria-label="Domain: {dname}, maturity level {maturity}">
  <div class="sf-header">
    <span class="sf-dname">{dname}</span>
    <span class="sf-mat" style="background:{mat_color}">Maturity: {maturity}/5</span>
  </div>
  <div class="sf-mbar"><div class="sf-mfill" style="width:{maturity*20}%"></div></div>
  <ul class="sf-ctrls">{ctrl_html}</ul>
</div>"""

        css = """
.sf-framework { display:flex; flex-direction:column; gap:18px; }
.sf-domain { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:18px;
  transition:transform var(--transition); }
.sf-domain:hover, .sf-domain:focus { transform:translateY(-2px); outline:none; }
.sf-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px; }
.sf-dname { font-weight:700; font-size:1.05rem; }
.sf-mat { padding:4px 12px; border-radius:12px; font-size:0.8rem; font-weight:700; color:#fff; }
.sf-mbar { height:8px; background:var(--bg); border-radius:4px; overflow:hidden; margin-bottom:12px; }
.sf-mfill { height:100%; background:linear-gradient(90deg, var(--accent-red), var(--accent-orange), var(--accent-green)); border-radius:4px; transition:width 1s ease; }
.sf-ctrls { list-style:none; padding:0; margin:0; display:flex; flex-wrap:wrap; gap:8px; }
.sf-ctrl { padding:6px 12px; border-radius:6px; font-size:0.85rem; font-weight:600; }
.sf-impl { background:rgba(46,204,113,0.15); color:var(--accent-green); border:1px solid var(--accent-green); }
.sf-planned { background:rgba(243,156,18,0.1); color:var(--accent-orange); border:1px solid var(--accent-orange); }
""".strip()

        body = f"""
<h1>{fname}</h1>
<div class="card">
  <div class="sf-framework" id="{uid}">{domain_html}</div>
</div>
"""
        return _html_boilerplate(f"Security Framework: {fname}", body, css, "")

    # ------------------------------------------------------------------ #
    # OSI model diagram
    # ------------------------------------------------------------------ #
    def create_osi_model_diagram(self) -> str:
        """
        Build an interactive OSI 7-layer model.

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "o" + uuid.uuid4().hex[:8]
        layers = [
            {
                "num": 7,
                "name": "Application",
                "desc": "HTTP, FTP, SMTP, DNS, SSH, Telnet",
                "detail": "Provides network services directly to end-user applications. Handles high-level protocols for resource sharing and remote file access.",
                "color": "#4a9eff",
            },
            {
                "num": 6,
                "name": "Presentation",
                "desc": "SSL/TLS, JPEG, MPEG, ASCII, EBCDIC",
                "detail": "Translates data between application and network formats. Handles encryption, compression, and character encoding.",
                "color": "#9b59b6",
            },
            {
                "num": 5,
                "name": "Session",
                "desc": "NetBIOS, RPC, PPTP, SOCKS",
                "detail": "Manages sessions between applications. Handles authentication, authorization, and session checkpointing.",
                "color": "#00d2ff",
            },
            {
                "num": 4,
                "name": "Transport",
                "desc": "TCP, UDP, SCTP, DCCP",
                "detail": "Provides reliable end-to-end data delivery. TCP offers connection-oriented reliable transfer; UDP offers connectionless fast delivery.",
                "color": "#2ecc71",
            },
            {
                "num": 3,
                "name": "Network",
                "desc": "IP, ICMP, OSPF, BGP, ARP",
                "detail": "Handles logical addressing and routing. Determines the best path for data across multiple networks.",
                "color": "#f39c12",
            },
            {
                "num": 2,
                "name": "Data Link",
                "desc": "Ethernet, Wi-Fi (802.11), PPP, ARP",
                "detail": "Manages MAC addressing and frame delivery on the same network. Divided into LLC and MAC sublayers.",
                "color": "#e67e22",
            },
            {
                "num": 1,
                "name": "Physical",
                "desc": "USB, Ethernet cables, Fibre, Radio",
                "detail": "Transmits raw bit stream over physical medium. Defines electrical, mechanical, and procedural specifications.",
                "color": "#e74c3c",
            },
        ]

        layer_html = ""
        for layer in layers:
            layer_html += (
                f'<div class="osi-layer" tabindex="0" role="button" '
                f'aria-label="Layer {layer["num"]}: {layer["name"]}" '
                f'style="--lcolor:{layer["color"]}" data-num="{layer["num"]}" '
                f'data-name="{html.escape(layer["name"])}" '
                f'data-desc="{html.escape(layer["desc"])}" '
                f'data-detail="{html.escape(layer["detail"])}">'
                f'<span class="osi-num">{layer["num"]}</span>'
                f'<span class="osi-lname">{html.escape(layer["name"])}</span>'
                f'<span class="osi-protos">{html.escape(layer["desc"])}</span></div>'
            )

        css = """
.osi-stack { display:flex; flex-direction:column-reverse; gap:6px; }
.osi-layer { display:flex; align-items:center; gap:16px; padding:14px 20px; background:var(--bg-card);
  border-left:5px solid var(--lcolor); border-radius:0 var(--radius) var(--radius) 0;
  cursor:pointer; transition:transform var(--transition), background var(--transition); }
.osi-layer:hover, .osi-layer:focus { transform:translateX(8px); background:var(--bg-hover); outline:none; }
.osi-num { width:36px; height:36px; border-radius:50%; background:var(--lcolor); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1rem; flex-shrink:0; }
.osi-lname { font-weight:700; font-size:1.05rem; min-width:130px; }
.osi-protos { font-size:0.85rem; color:var(--text-dim); margin-left:auto; text-align:right; }
.osi-detail { margin-top:16px; padding:18px; background:var(--bg); border:1px solid var(--border);
  border-radius:var(--radius); display:none; animation:fadeIn 0.3s ease; }
.osi-detail.active { display:block; }
.osi-detail h3 { color:var(--accent-cyan); margin-top:0; }
@media (max-width:640px) { .osi-protos { display:none; } }
""".strip()

        js = f"""
document.querySelectorAll('.osi-layer').forEach(function(layer){{
  layer.addEventListener('click', function(){{
    document.querySelectorAll('.osi-layer').forEach(function(l){{ l.style.background=''; l.style.borderLeftWidth='5px'; }});
    this.style.background='var(--bg-hover)';
    this.style.borderLeftWidth='8px';
    var panel = document.getElementById('{uid}-detail');
    if (panel) {{
      panel.innerHTML = '<h3>Layer ' + this.getAttribute('data-num') + ' — ' + this.getAttribute('data-name') + '</h3>' +
        '<p><strong>Protocols:</strong> ' + this.getAttribute('data-desc') + '</p>' +
        '<p>' + this.getAttribute('data-detail') + '</p>';
      panel.classList.add('active');
    }}
  }});
}});
""".strip()

        body = f"""
<h1>OSI 7-Layer Model</h1>
<div class="card">
  <div class="osi-stack" id="{uid}">{layer_html}</div>
  <div class="osi-detail" id="{uid}-detail" role="region" aria-live="polite">
    <p style="color:var(--text-dim);">Click a layer to explore its protocols and functions.</p>
  </div>
</div>
"""
        return _html_boilerplate("OSI 7-Layer Model", body, css, js)

    # ------------------------------------------------------------------ #
    # TCP 3-way handshake
    # ------------------------------------------------------------------ #
    def create_tcp_handshake_animation(self) -> str:
        """
        Build an animated TCP 3-way handshake diagram.

        Returns
        -------
        str
            Self-contained HTML page.
        """
        uid = "tcp" + uuid.uuid4().hex[:8]
        steps = [
            {
                "seq": 1,
                "from": "Client",
                "to": "Server",
                "label": "SYN",
                "detail": "Client sends SYN (synchronize) packet with initial sequence number (ISN) to initiate connection.",
                "state": "SYN_SENT",
            },
            {
                "seq": 2,
                "from": "Server",
                "to": "Client",
                "label": "SYN-ACK",
                "detail": "Server responds with SYN-ACK: acknowledges client's SYN (ACK = ISN+1) and sends its own ISN.",
                "state": "SYN_RECEIVED",
            },
            {
                "seq": 3,
                "from": "Client",
                "to": "Server",
                "label": "ACK",
                "detail": "Client acknowledges server's SYN (ACK = Server ISN+1). Connection is now ESTABLISHED.",
                "state": "ESTABLISHED",
            },
        ]

        steps_html = ""
        for step in steps:
            direction = "tc-right" if step["from"] == "Client" else "tc-left"
            steps_html += (
                f'<div class="tc-step {direction}" id="{uid}-s{step["seq"]}" tabindex="0" role="button" '
                f'aria-label="Step {step["seq"]}: {step["label"]} from {step["from"]} to {step["to"]}">'
                f'<div class="tc-packet">'
                f'<span class="tc-flag">{html.escape(step["label"])}</span>'
                f'<span class="tc-arrow">&#10132;</span>'
                f'<span class="tc-target">{html.escape(step["to"])}</span></div>'
                f'<p class="tc-detail">{html.escape(step["detail"])}</p></div>'
            )

        css = """
.tc-actors { display:flex; justify-content:space-between; align-items:center; padding:20px 40px; margin-bottom:10px; }
.tc-actor { text-align:center; }
.tc-icon { width:56px; height:56px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:1.4rem; margin:0 auto 8px; font-weight:800; }
.tc-client .tc-icon { background:linear-gradient(135deg, var(--accent-blue), var(--accent-cyan)); }
.tc-server .tc-icon { background:linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); }
.tc-label { font-weight:700; font-size:1rem; }
.tc-steps { position:relative; padding:10px 0; }
.tc-step { margin:16px 0; padding:16px 20px; background:var(--bg-card); border:2px solid var(--border);
  border-radius:var(--radius); cursor:pointer; transition:transform var(--transition), border-color var(--transition);
  opacity:0; animation:tcFadeIn 0.5s ease forwards; }
.tc-step:nth-child(1) { animation-delay:0.5s; }
.tc-step:nth-child(2) { animation-delay:1.8s; }
.tc-step:nth-child(3) { animation-delay:3.1s; }
.tc-step:hover, .tc-step:focus { transform:translateY(-3px); border-color:var(--accent-blue); outline:none; }
.tc-right { border-left:4px solid var(--accent-blue); }
.tc-left { border-right:4px solid var(--accent-purple); }
.tc-packet { display:flex; align-items:center; gap:12px; font-weight:700; margin-bottom:8px; }
.tc-flag { padding:4px 14px; border-radius:6px; background:var(--accent-orange); color:#fff; font-size:0.9rem; }
.tc-arrow { font-size:1.2rem; color:var(--accent-cyan); }
.tc-target { color:var(--text-dim); font-size:0.9rem; }
.tc-detail { margin:0; font-size:0.9rem; color:var(--text-dim); }
.tc-state-panel { margin-top:18px; padding:16px; background:var(--bg); border:1px solid var(--border);
  border-radius:8px; text-align:center; }
.tc-state { display:inline-block; padding:6px 16px; border-radius:20px; font-weight:700;
  background:rgba(74,158,255,0.15); color:var(--accent-blue); margin:4px; }
.tc-seq-num { display:inline-block; padding:4px 10px; border-radius:4px; background:var(--bg-card);
  font-family:monospace; font-size:0.85rem; color:var(--accent-cyan); margin:2px; }
@keyframes tcFadeIn { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
@media (max-width:640px) { .tc-actors { padding:14px 10px; } .tc-icon { width:44px; height:44px; font-size:1.1rem; } }
""".strip()

        js = f"""
document.querySelectorAll('.tc-step').forEach(function(step){{
  step.addEventListener('click', function(){{
    document.querySelectorAll('.tc-step').forEach(function(s){{ s.style.boxShadow=''; }});
    this.style.boxShadow='0 0 20px rgba(74,158,255,0.4)';
  }});
}});
// Auto-show state progression
setTimeout(function(){{
  var panel = document.getElementById('{uid}-states');
  if (panel) panel.innerHTML =
    '<span class="tc-state">Client: SYN_SENT</span><span class="tc-state">Server: LISTEN</span>';
}}, 500);
setTimeout(function(){{
  var panel = document.getElementById('{uid}-states');
  if (panel) panel.innerHTML =
    '<span class="tc-state">Client: SYN_SENT</span><span class="tc-state">Server: SYN_RECEIVED</span>';
}}, 1800);
setTimeout(function(){{
  var panel = document.getElementById('{uid}-states');
  if (panel) panel.innerHTML =
    '<span class="tc-state" style="background:rgba(46,204,113,0.2);color:var(--accent-green);">Client: ESTABLISHED</span>' +
    '<span class="tc-state" style="background:rgba(46,204,113,0.2);color:var(--accent-green);">Server: ESTABLISHED</span>';
}}, 3100);
""".strip()

        body = f"""
<h1>TCP 3-Way Handshake</h1>
<div class="card">
  <div class="tc-actors">
    <div class="tc-actor tc-client">
      <div class="tc-icon">C</div>
      <div class="tc-label">Client</div>
    </div>
    <div style="flex:1; text-align:center; color:var(--text-dim); font-size:0.85rem;">Network</div>
    <div class="tc-actor tc-server">
      <div class="tc-icon">S</div>
      <div class="tc-label">Server</div>
    </div>
  </div>
  <div class="tc-steps" id="{uid}">
    {steps_html}
  </div>
  <div class="tc-state-panel" id="{uid}-states" role="status" aria-live="polite">
    <span style="color:var(--text-dim);">Waiting for handshake to begin...</span>
  </div>
</div>
"""
        return _html_boilerplate("TCP 3-Way Handshake", body, css, js)

    # ------------------------------------------------------------------ #
    # FastAPI endpoint registration
    # ------------------------------------------------------------------ #
    def register_endpoints(self, app_or_router: Any) -> None:
        """
        Register all visual-learning endpoints on a FastAPI app or APIRouter.

        Parameters
        ----------
        app_or_router :
            A ``FastAPI`` application instance or ``APIRouter``.

        Raises
        ------
        TypeError
            If *app_or_router* lacks the expected ``post``/``get`` methods.
        """
        if not (hasattr(app_or_router, "post") and hasattr(app_or_router, "get")):
            raise TypeError("app_or_router must expose .post() and .get() methods")

        from pydantic import BaseModel

        class FlowchartPayload(BaseModel):
            title: str
            steps: list[dict[str, Any]]
            decisions: list[dict[str, Any]] | None = None

        class MindmapPayload(BaseModel):
            topic: str
            subtopics: list[dict[str, Any]]

        class ProcessPayload(BaseModel):
            title: str
            stages: list[dict[str, Any]]

        class ComparisonPayload(BaseModel):
            title: str
            items: list[dict[str, Any]]
            criteria: list[str]

        class TimelinePayload(BaseModel):
            title: str
            events: list[dict[str, Any]]

        class QuizPayload(BaseModel):
            questions: list[dict[str, Any]]

        class SecurityPayload(BaseModel):
            framework: dict[str, Any]

        # Register routes ------------------------------------------------

        @app_or_router.post("/api/visual/flowchart", tags=["visual-learning"], summary="Generate interactive flowchart")
        def _flowchart(payload: FlowchartPayload) -> dict[str, str]:
            html_content = self.create_flowchart(payload.title, payload.steps, payload.decisions)
            return {"html": html_content}

        @app_or_router.post("/api/visual/mindmap", tags=["visual-learning"], summary="Generate mind map")
        def _mindmap(payload: MindmapPayload) -> dict[str, str]:
            html_content = self.create_mindmap(payload.topic, payload.subtopics)
            return {"html": html_content}

        @app_or_router.post("/api/visual/process", tags=["visual-learning"], summary="Generate process diagram")
        def _process(payload: ProcessPayload) -> dict[str, str]:
            html_content = self.create_process_diagram(payload.title, payload.stages)
            return {"html": html_content}

        @app_or_router.post("/api/visual/comparison", tags=["visual-learning"], summary="Generate comparison table")
        def _comparison(payload: ComparisonPayload) -> dict[str, str]:
            html_content = self.create_comparison_table(payload.title, payload.items, payload.criteria)
            return {"html": html_content}

        @app_or_router.post("/api/visual/timeline", tags=["visual-learning"], summary="Generate timeline")
        def _timeline(payload: TimelinePayload) -> dict[str, str]:
            html_content = self.create_timeline(payload.title, payload.events)
            return {"html": html_content}

        @app_or_router.post("/api/visual/quiz", tags=["visual-learning"], summary="Generate interactive quiz")
        def _quiz(payload: QuizPayload) -> dict[str, str]:
            html_content = self.create_interactive_quiz(payload.questions)
            return {"html": html_content}

        @app_or_router.post(
            "/api/visual/security-framework",
            tags=["visual-learning"],
            summary="Generate security framework diagram",
        )
        def _security_framework(payload: SecurityPayload) -> dict[str, str]:
            html_content = self.create_security_framework_diagram(payload.framework)
            return {"html": html_content}

        @app_or_router.get("/api/visual/osi-model", tags=["visual-learning"], summary="Interactive OSI model")
        def _osi_model() -> dict[str, str]:
            html_content = self.create_osi_model_diagram()
            return {"html": html_content}

        @app_or_router.get("/api/visual/tcp-handshake", tags=["visual-learning"], summary="TCP handshake animation")
        def _tcp_handshake() -> dict[str, str]:
            html_content = self.create_tcp_handshake_animation()
            return {"html": html_content}

        logger.info("Visual Learning Engine endpoints registered (%s)", type(app_or_router).__name__)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def generate_diagram(
    diagram_type: DiagramType,
    title: str,
    data: dict[str, Any],
) -> str:
    """
    Convenience dispatcher for one-off diagram generation.

    Parameters
    ----------
    diagram_type : DiagramType
        Which diagram to create.
    title : str
        Diagram heading.
    data : dict
        Type-specific payload forwarded to the engine method.

    Returns
    -------
    str
        Self-contained HTML string.
    """
    engine = VisualLearningEngine()
    match diagram_type:
        case DiagramType.FLOWCHART:
            return engine.create_flowchart(
                title, data.get("steps", []), data.get("decisions")
            )
        case DiagramType.MINDMAP:
            return engine.create_mindmap(title, data.get("subtopics", []))
        case DiagramType.PROCESS:
            return engine.create_process_diagram(title, data.get("stages", []))
        case DiagramType.COMPARISON:
            return engine.create_comparison_table(
                title, data.get("items", []), data.get("criteria", [])
            )
        case DiagramType.TIMELINE:
            return engine.create_timeline(title, data.get("events", []))
        case DiagramType.HIERARCHY:
            return engine.create_hierarchy(title, data.get("structure", {}))
        case _:
            raise ValueError(f"Unsupported diagram type: {diagram_type}")


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

_engine_instance: VisualLearningEngine | None = None


def get_engine() -> VisualLearningEngine:
    """Return the global ``VisualLearningEngine`` singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VisualLearningEngine()
    return _engine_instance
