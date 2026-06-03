#!/usr/bin/env python3
"""
Local Bullet - a localhost-only contest manager.

Run:
    python local_bullet.py

The app stores data in ./data/local_bullet.sqlite3 next to this file.
It binds to 127.0.0.1 only, so it is not exposed to the local Wi-Fi network.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit
import csv
import html
import io
import json
import os
import re
import sqlite3
import threading
import time
import webbrowser
from datetime import datetime


HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("LOCAL_BULLET_PORT", "8000"))
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LOCAL_BULLET_DATA_DIR", APP_DIR / "data"))
DB_PATH = DATA_DIR / "local_bullet.sqlite3"
MAX_BODY_BYTES = 2 * 1024 * 1024
TEAM_NAME_LIMIT = 80
MEMBERS_LIMIT = 2000
TITLE_LIMIT = 120
MAX_TASKS = 80


STYLE = r"""
:root {
  color-scheme: light;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #1b2428;
  background: #f4f6f7;
}
* { box-sizing: border-box; }
body { margin: 0; }
a { color: inherit; }
.top {
  background: #123d35;
  color: white;
  border-bottom: 4px solid #f0b429;
}
.top-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand {
  text-decoration: none;
  color: white;
  font-size: 20px;
  font-weight: 850;
  letter-spacing: 0;
}
.nav {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.nav a, .nav button {
  color: white;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.26);
  border-radius: 6px;
  padding: 8px 10px;
  text-decoration: none;
  font: inherit;
  cursor: pointer;
}
.nav a.active { background: white; color: #123d35; }
.wrap {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 18px 80px;
}
.panel {
  background: white;
  border: 1px solid #d9e1e5;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.panel h1, .panel h2, .panel h3 { margin-top: 0; }
.muted { color: #64747c; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
  align-items: end;
}
.grid.compact { grid-template-columns: repeat(auto-fit, minmax(150px, 220px)); justify-content: start; }
.field { display: grid; gap: 5px; margin-bottom: 12px; }
.field label { font-weight: 750; font-size: 14px; }
.field input, .field textarea, .field select {
  width: 100%;
  min-height: 38px;
  border: 1px solid #bac7cd;
  border-radius: 6px;
  padding: 8px 10px;
  font: inherit;
  background: white;
  color: #1b2428;
}
.field textarea { min-height: 90px; resize: vertical; }
.field input[type="checkbox"] { width: auto; min-height: 0; }
.button-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 12px;
}
form.inline { display: inline; margin: 0; }
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  border: 1px solid #0e6f55;
  background: #0f7b5c;
  color: white;
  border-radius: 6px;
  padding: 8px 11px;
  font: inherit;
  font-weight: 750;
  line-height: 1.15;
  text-decoration: none;
  cursor: pointer;
}
.btn.secondary { background: white; color: #183b33; border-color: #b8c5cb; }
.btn.danger { background: #b3261e; border-color: #8d1d17; }
.btn.warning { background: #9c5b00; border-color: #7c4800; }
.btn.small { min-height: 30px; padding: 5px 8px; font-size: 13px; }
.state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  padding: 5px 9px;
  font-weight: 850;
  background: #eef2f4;
  color: #44535b;
}
.state.running { background: #dff6e9; color: #0b6845; }
.state.ended { background: #fdebea; color: #8a211b; }
.state.scheduled { background: #fff3cd; color: #755400; }
.notice {
  padding: 10px 12px;
  border-radius: 6px;
  background: #e8f6ef;
  border: 1px solid #bce2ce;
  color: #144d35;
  margin-bottom: 14px;
}
.notice.error { background: #fdebea; border-color: #f3b8b3; color: #751d18; }
.table-wrap { overflow: auto; border: 1px solid #d9e1e5; border-radius: 8px; background: white; }
.table { width: 100%; border-collapse: collapse; background: white; }
.table th, .table td {
  padding: 9px 10px;
  border-bottom: 1px solid #e3e9ed;
  text-align: left;
  vertical-align: middle;
}
.table th {
  font-size: 12px;
  text-transform: uppercase;
  color: #5c6b72;
  background: #f0f4f6;
  white-space: nowrap;
}
.table tr:last-child td { border-bottom: 0; }
.table .num { text-align: right; font-variant-numeric: tabular-nums; }
.score { font-size: 22px; font-weight: 900; color: #0f6d52; }
.rank { font-size: 20px; font-weight: 900; color: #123d35; }
.team-meta { color: #64747c; font-size: 13px; margin-top: 3px; }
.cards { display: grid; gap: 10px; }
.team-card {
  border: 1px solid #d9e1e5;
  border-radius: 8px;
  padding: 12px;
  background: white;
}
.team-card form { margin: 0; }
.team-card-title { display: grid; grid-template-columns: 92px minmax(0, 1fr) auto; gap: 10px; align-items: end; }
.score-grid { overflow: auto; border: 1px solid #d9e1e5; border-radius: 8px; background: white; }
.score-grid table { border-collapse: collapse; min-width: max-content; width: 100%; }
.score-grid th, .score-grid td { border: 1px solid #dce4e8; padding: 5px; text-align: center; }
.score-grid th:first-child, .score-grid td:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
  background: white;
  text-align: left;
  min-width: 220px;
}
.score-grid th:first-child { background: #f0f4f6; z-index: 2; }
.cell-btn {
  width: 34px;
  height: 30px;
  border: 1px solid #b9c6cc;
  border-radius: 5px;
  background: #f7f9fa;
  color: #53636c;
  cursor: pointer;
  font: inherit;
  font-weight: 900;
}
.cell-btn.done { background: #16a065; color: white; border-color: #138958; }
.cell-btn.burned { background: #d93025; color: white; border-color: #a82018; }
.tasks {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.sq {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: 1px solid #c9d3d8;
  background: #eef2f4;
  color: #53636c;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-variant-numeric: tabular-nums;
}
.sq.done { background: #16a065; color: white; border-color: #138958; }
.sq.burned { background: #d93025; color: white; border-color: #a82018; }
.ranking-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 14px;
}
.timer {
  font-variant-numeric: tabular-nums;
  font-weight: 900;
  font-size: 28px;
  color: #123d35;
}
.rank-cards { display: none; }
.rank-card {
  background: white;
  border: 1px solid #d9e1e5;
  border-radius: 8px;
  padding: 12px;
}
.rank-card-top {
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr) 74px;
  gap: 10px;
  align-items: start;
}
.rank-card .score { text-align: right; }
.footer-note { margin-top: 18px; color: #64747c; font-size: 13px; }
body.fullscreen {
  background: #071713;
  color: #ecf8f3;
  overflow: hidden;
}
.fs-wrap {
  height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr;
  padding: 24px;
  gap: 18px;
}
.fs-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: center;
}
.fs-title {
  min-width: 0;
  font-size: clamp(30px, 4vw, 64px);
  font-weight: 950;
  line-height: 1.05;
}
.fs-state {
  font-size: clamp(18px, 2vw, 34px);
  color: #f0b429;
  font-weight: 900;
  text-align: right;
}
.fs-timer {
  font-size: clamp(34px, 5vw, 82px);
  font-weight: 950;
  font-variant-numeric: tabular-nums;
  color: white;
}
.fs-board {
  overflow: hidden;
  display: grid;
  align-content: start;
  gap: 8px;
}
.fs-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr) 104px;
  gap: 16px;
  align-items: center;
  min-height: 54px;
  padding: 9px 12px;
  border-radius: 8px;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.10);
}
.fs-row.first {
  background: rgba(240,180,41,.18);
  border-color: rgba(240,180,41,.42);
}
.fs-rank {
  font-size: 30px;
  font-weight: 950;
  color: #f0b429;
  font-variant-numeric: tabular-nums;
}
.fs-team {
  min-width: 0;
  font-size: clamp(20px, 2.2vw, 38px);
  font-weight: 900;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fs-members {
  color: rgba(236,248,243,.72);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fs-score {
  text-align: right;
  font-size: 40px;
  font-weight: 950;
  color: #7ee0ae;
  font-variant-numeric: tabular-nums;
}
.fs-notice {
  color: #ffd777;
  font-size: 18px;
  font-weight: 800;
}
@media (max-width: 760px) {
  .top-inner { align-items: flex-start; flex-direction: column; padding: 11px 10px; }
  .nav { width: 100%; overflow-x: auto; flex-wrap: nowrap; padding-bottom: 2px; }
  .nav a, .nav button { white-space: nowrap; }
  .wrap { padding: 12px 10px 70px; }
  .panel { padding: 12px; }
  .button-row { display: grid; grid-template-columns: 1fr; }
  .button-row .btn { width: 100%; }
  .team-card-title { grid-template-columns: 1fr; }
  .ranking-head { align-items: flex-start; flex-direction: column; }
  .scoreboard-table { display: none; }
  .rank-cards { display: grid; gap: 10px; }
  .score-grid th:first-child, .score-grid td:first-child { min-width: 150px; }
  .fs-wrap { padding: 12px; }
  .fs-head { grid-template-columns: 1fr; }
  .fs-state { text-align: left; }
  .fs-row { grid-template-columns: 48px minmax(0, 1fr) 64px; gap: 8px; min-height: 46px; }
  .fs-rank { font-size: 22px; }
  .fs-score { font-size: 28px; }
}
"""


def now() -> int:
    return int(time.time())


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def clean_text(value: object, limit: int) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()[:limit]


def clean_multiline(value: object, limit: int) -> str:
    value = "" if value is None else str(value)
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)[:limit]


def clamp_int(value: object, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def fmt_seconds(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_dt_input(timestamp: object) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%dT%H:%M")


def fmt_dt_display(timestamp: object) -> str:
    if not timestamp:
        return "-"
    return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M")


def parse_dt_input(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(datetime.strptime(value, "%Y-%m-%dT%H:%M").timestamp())
    except ValueError:
        return None


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS competition (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                title TEXT NOT NULL,
                task_count INTEGER NOT NULL,
                started_at INTEGER,
                ended_at INTEGER,
                freeze_minutes_before_end INTEGER NOT NULL DEFAULT 0,
                unfreeze_minutes_after_end INTEGER NOT NULL DEFAULT -1,
                ranking_unfrozen_at INTEGER,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_number INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL,
                members TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS solves (
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                task_number INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('done', 'burned')),
                marked_at INTEGER NOT NULL,
                PRIMARY KEY (team_id, task_number)
            );
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO competition
                (id, title, task_count, started_at, ended_at, freeze_minutes_before_end,
                 unfreeze_minutes_after_end, ranking_unfrozen_at, updated_at)
            VALUES
                (1, 'Konkurs lokalny', 20, NULL, NULL, 0, -1, NULL, ?)
            """,
            (now(),),
        )


def competition(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute("SELECT * FROM competition WHERE id=1").fetchone()


def state_for(comp: sqlite3.Row) -> str:
    current = now()
    if comp["ended_at"] and current >= comp["ended_at"]:
        return "ended"
    if comp["started_at"] and current >= comp["started_at"]:
        return "running"
    if comp["started_at"]:
        return "scheduled"
    return "not_started"


def display_state(state: str) -> str:
    return {
        "not_started": "nie rozpoczety",
        "scheduled": "zaplanowany",
        "running": "trwa",
        "ended": "zakonczony",
    }.get(state, state)


def duration_minutes(comp: sqlite3.Row) -> str:
    if not comp["started_at"] or not comp["ended_at"] or comp["ended_at"] < comp["started_at"]:
        return ""
    return str(max(0, (int(comp["ended_at"]) - int(comp["started_at"])) // 60))


def timer_label(comp: sqlite3.Row) -> str:
    state = state_for(comp)
    if state == "scheduled":
        return "Start za"
    if state == "running":
        return "Uplynelo"
    if state == "ended":
        return "Czas trwania"
    return "Zegar"


def timer_value(comp: sqlite3.Row) -> int:
    current = now()
    if state_for(comp) == "scheduled":
        return int(comp["started_at"]) - current
    if not comp["started_at"]:
        return 0
    end = min(current, int(comp["ended_at"]) if comp["ended_at"] else current)
    return max(0, end - int(comp["started_at"]))


def freeze_cutoff(comp: sqlite3.Row) -> int | None:
    if not comp["started_at"] or not comp["ended_at"]:
        return None
    minutes = int(comp["freeze_minutes_before_end"] or 0)
    if minutes <= 0:
        return None
    return int(comp["ended_at"]) - minutes * 60


def auto_unfreeze_at(comp: sqlite3.Row) -> int | None:
    if not comp["ended_at"]:
        return None
    minutes = int(comp["unfreeze_minutes_after_end"] or -1)
    if minutes < 0:
        return None
    return int(comp["ended_at"]) + minutes * 60


def ranking_is_frozen(comp: sqlite3.Row) -> bool:
    current = now()
    cutoff = freeze_cutoff(comp)
    if cutoff is None or current < cutoff:
        return False
    if comp["ranking_unfrozen_at"]:
        return False
    unfreeze_at = auto_unfreeze_at(comp)
    if unfreeze_at is not None and current >= unfreeze_at:
        return False
    return True


def ranking_snapshot_at(comp: sqlite3.Row) -> int | None:
    return freeze_cutoff(comp) if ranking_is_frozen(comp) else None


def all_teams(conn: sqlite3.Connection, include_inactive: bool = False) -> list[sqlite3.Row]:
    where = "" if include_inactive else "WHERE active=1"
    return conn.execute(
        f"SELECT * FROM teams {where} ORDER BY team_number, name COLLATE NOCASE"
    ).fetchall()


def next_team_number(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COALESCE(MAX(team_number), 0) + 1 FROM teams").fetchone()[0])


def team_members_display(members: str) -> str:
    parts = [line.strip() for line in (members or "").splitlines() if line.strip()]
    return ", ".join(parts)


def result_rows(conn: sqlite3.Connection, sort: str = "place", cutoff: int | None = None) -> list[dict]:
    comp = competition(conn)
    task_count = int(comp["task_count"])
    team_params: list[object] = []
    team_sql = "SELECT * FROM teams WHERE active=1"
    if cutoff is not None:
        team_sql += " AND created_at<=?"
        team_params.append(cutoff)
    teams = conn.execute(team_sql + " ORDER BY team_number, name COLLATE NOCASE", team_params).fetchall()

    solve_params: list[object] = [task_count]
    solve_sql = "SELECT * FROM solves WHERE task_number<=?"
    if cutoff is not None:
        solve_sql += " AND marked_at<=?"
        solve_params.append(cutoff)
    solves = conn.execute(solve_sql, solve_params).fetchall()

    by_team: dict[int, dict[str, dict[int, int]]] = {
        int(team["id"]): {"done": {}, "burned": {}} for team in teams
    }
    for solve in solves:
        team_id = int(solve["team_id"])
        if team_id not in by_team:
            continue
        status = solve["status"] if solve["status"] in {"done", "burned"} else "done"
        by_team[team_id][status][int(solve["task_number"])] = int(solve["marked_at"])

    rows: list[dict] = []
    for team in teams:
        marks = by_team.get(int(team["id"]), {"done": {}, "burned": {}})
        solved = marks["done"]
        burned = marks["burned"]
        mask = 0
        for task in solved:
            mask |= 1 << (task - 1)
        rows.append(
            {
                "team": team,
                "solved": solved,
                "burned": burned,
                "count": len(solved),
                "mask": mask,
                "last": max(solved.values()) if solved else 0,
            }
        )

    if sort == "number":
        rows.sort(key=lambda row: (int(row["team"]["team_number"]), row["team"]["name"].lower()))
    else:
        rows.sort(
            key=lambda row: (
                -int(row["count"]),
                -int(row["mask"]),
                int(row["last"] or 10**18),
                int(row["team"]["team_number"]),
                row["team"]["name"].lower(),
            )
        )
    return rows


def task_status(row: dict, task: int) -> str:
    if task in row["solved"]:
        return "done"
    if task in row["burned"]:
        return "burned"
    return ""


def task_square(status: str, task: int) -> str:
    return f"<span class='sq {esc(status)}'>{task}</span>"


def set_mark(conn: sqlite3.Connection, team_id: int, task_number: int, action: str) -> None:
    comp = competition(conn)
    task_number = clamp_int(task_number, 1, 1, int(comp["task_count"]))
    if action == "clear":
        conn.execute("DELETE FROM solves WHERE team_id=? AND task_number=?", (team_id, task_number))
        return
    status = "burned" if action == "burned" else "done"
    conn.execute(
        """
        INSERT INTO solves(team_id, task_number, status, marked_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(team_id, task_number)
        DO UPDATE SET status=excluded.status, marked_at=excluded.marked_at
        """,
        (team_id, task_number, status, now()),
    )


def find_team(conn: sqlite3.Connection, lookup: str) -> sqlite3.Row | None:
    lookup = (lookup or "").strip()
    if not lookup:
        return None
    if lookup.isdigit():
        team = conn.execute("SELECT * FROM teams WHERE team_number=? AND active=1", (int(lookup),)).fetchone()
        if team:
            return team
        team = conn.execute("SELECT * FROM teams WHERE id=? AND active=1", (int(lookup),)).fetchone()
        if team:
            return team
    team = conn.execute(
        "SELECT * FROM teams WHERE lower(name)=lower(?) AND active=1 ORDER BY team_number LIMIT 1",
        (lookup,),
    ).fetchone()
    if team:
        return team
    return conn.execute(
        "SELECT * FROM teams WHERE lower(name) LIKE lower(?) AND active=1 ORDER BY team_number LIMIT 1",
        (f"%{lookup}%",),
    ).fetchone()


def layout(title: str, active: str, body: str) -> bytes:
    items = [
        ("admin", "/admin", "Konkurs"),
        ("teams", "/teams", "Druzyny"),
        ("scoring", "/scoring", "Punktowanie"),
        ("ranking", "/ranking", "Ranking"),
        ("fullscreen", "/ranking/fullscreen", "Fullscreen"),
    ]
    nav = "".join(
        f"<a class='{ 'active' if active == key else '' }' href='{href}'>{label}</a>"
        for key, href, label in items
    )
    html_text = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} - Local Bullet</title>
  <style>{STYLE}</style>
</head>
<body>
  <header class="top">
    <div class="top-inner">
      <a class="brand" href="/admin">Local Bullet</a>
      <nav class="nav">{nav}</nav>
    </div>
  </header>
  <main class="wrap">{body}</main>
</body>
</html>"""
    return html_text.encode("utf-8")


def notice(message: str | None, error: bool = False) -> str:
    if not message:
        return ""
    cls = "notice error" if error else "notice"
    return f"<div class='{cls}'>{esc(message)}</div>"


def admin_page(message: str | None = None, error: bool = False) -> bytes:
    with db() as conn:
        comp = competition(conn)
        rows = result_rows(conn)
        team_count = conn.execute("SELECT COUNT(*) FROM teams WHERE active=1").fetchone()[0]
        solve_count = conn.execute("SELECT COUNT(*) FROM solves WHERE status='done'").fetchone()[0]
        state = state_for(comp)
        frozen = ranking_is_frozen(comp)
        frozen_text = (
            f"<p class='muted'>Ranking publiczny jest zamrozony na stan z {esc(fmt_dt_display(ranking_snapshot_at(comp)))}.</p>"
            if frozen
            else ""
        )
        top_rows = rows[:5]
        top_html = "".join(
            f"<tr><td class='rank'>{idx}</td><td>{esc(row['team']['name'])}<div class='team-meta'>nr {row['team']['team_number']}</div></td><td class='score'>{row['count']}</td></tr>"
            for idx, row in enumerate(top_rows, 1)
        ) or "<tr><td colspan='3' class='muted'>Brak druzyn.</td></tr>"
        body = f"""
{notice(message, error)}
<section class="panel">
  <h1>{esc(comp['title'])}</h1>
  <p>
    <span class="state {esc(state)}">{esc(display_state(state))}</span>
    <span class="muted"> {esc(timer_label(comp))}: </span>
    <span class="timer">{esc(fmt_seconds(timer_value(comp)))}</span>
  </p>
  {frozen_text}
  <div class="grid compact">
    <div><strong>{team_count}</strong><div class="muted">aktywnych druzyn</div></div>
    <div><strong>{solve_count}</strong><div class="muted">zaliczonych zadan</div></div>
    <div><strong>{esc(comp['task_count'])}</strong><div class="muted">zadan w konkursie</div></div>
  </div>
  <div class="button-row">
    <form class="inline" method="post" action="/contest/start"><button class="btn">Start teraz</button></form>
    <form class="inline" method="post" action="/contest/end"><button class="btn warning">Zakoncz teraz</button></form>
    <form class="inline" method="post" action="/contest/clear-time"><button class="btn secondary">Wyczysc czas</button></form>
    <form class="inline" method="post" action="/contest/unfreeze"><button class="btn secondary">Odmroz ranking</button></form>
  </div>
</section>

<section class="panel">
  <h2>Ustawienia konkursu</h2>
  <form method="post" action="/settings">
    <div class="grid">
      <div class="field">
        <label>Nazwa konkursu</label>
        <input name="title" maxlength="{TITLE_LIMIT}" value="{esc(comp['title'])}">
      </div>
      <div class="field">
        <label>Liczba zadan</label>
        <input name="task_count" type="number" min="1" max="{MAX_TASKS}" value="{esc(comp['task_count'])}">
      </div>
      <div class="field">
        <label>Start</label>
        <input name="started_at" type="datetime-local" value="{esc(fmt_dt_input(comp['started_at']))}">
      </div>
      <div class="field">
        <label>Czas trwania (min)</label>
        <input name="duration_minutes" type="number" min="0" value="{esc(duration_minutes(comp))}">
      </div>
      <div class="field">
        <label>Koniec</label>
        <input name="ended_at" type="datetime-local" value="{esc(fmt_dt_input(comp['ended_at']))}">
      </div>
      <div class="field">
        <label>Zamroz przed koncem (min)</label>
        <input name="freeze_minutes_before_end" type="number" min="0" value="{esc(comp['freeze_minutes_before_end'])}">
      </div>
      <div class="field">
        <label>Odmroz po koncu (min, -1 = nigdy)</label>
        <input name="unfreeze_minutes_after_end" type="number" min="-1" value="{esc(comp['unfreeze_minutes_after_end'])}">
      </div>
    </div>
    <div class="button-row"><button class="btn">Zapisz ustawienia</button></div>
  </form>
</section>

<section class="panel">
  <h2>Top 5</h2>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>Miejsce</th><th>Druzyna</th><th>Wynik</th></tr></thead>
      <tbody>{top_html}</tbody>
    </table>
  </div>
</section>

<section class="panel">
  <h2>Dane</h2>
  <p class="muted">Eksport JSON zawiera ustawienia, druzyny i punktacje. Import JSON nadpisuje aktualny konkurs.</p>
  <div class="button-row">
    <a class="btn secondary" href="/data/export.json">Pobierz backup JSON</a>
  </div>
  <form method="post" action="/data/import-json">
    <div class="field">
      <label>Wklej backup JSON</label>
      <textarea name="payload" placeholder='{{"competition":...}}'></textarea>
    </div>
    <div class="field">
      <label>Potwierdzenie</label>
      <input name="confirm" placeholder="wpisz IMPORT">
    </div>
    <div class="button-row"><button class="btn warning">Importuj i nadpisz</button></div>
  </form>
  <form method="post" action="/data/wipe-scores">
    <div class="field">
      <label>Usun wszystkie wyniki</label>
      <input name="confirm" placeholder="wpisz WYNIKI">
    </div>
    <button class="btn danger">Wyczysc punktacje</button>
  </form>
</section>
"""
    return layout("Konkurs", "admin", body)


def teams_page(message: str | None = None, error: bool = False) -> bytes:
    with db() as conn:
        teams = all_teams(conn, include_inactive=True)
        next_number = next_team_number(conn)
        cards = []
        for team in teams:
            active_checked = "checked" if int(team["active"]) else ""
            cards.append(
                f"""
<div class="team-card">
  <form method="post" action="/teams/update?id={team['id']}">
    <div class="team-card-title">
      <div class="field"><label>Numer</label><input name="team_number" type="number" min="1" value="{esc(team['team_number'])}"></div>
      <div class="field"><label>Nazwa</label><input name="name" maxlength="{TEAM_NAME_LIMIT}" value="{esc(team['name'])}"></div>
      <label class="field"><span>Aktywna</span><input name="active" type="checkbox" value="1" {active_checked}></label>
    </div>
    <div class="field"><label>Czlonkowie / notatki</label><textarea name="members">{esc(team['members'])}</textarea></div>
    <div class="button-row">
      <button class="btn small">Zapisz</button>
      <button class="btn small danger" formaction="/teams/delete?id={team['id']}" formmethod="post">Usun</button>
    </div>
  </form>
</div>
"""
            )
        cards_html = "\n".join(cards) or "<p class='muted'>Nie ma jeszcze druzyn.</p>"
        body = f"""
{notice(message, error)}
<section class="panel">
  <h1>Druzyny</h1>
  <form method="post" action="/teams/add">
    <div class="grid">
      <div class="field"><label>Numer</label><input name="team_number" type="number" min="1" value="{esc(next_number)}"></div>
      <div class="field"><label>Nazwa</label><input name="name" maxlength="{TEAM_NAME_LIMIT}" placeholder="np. Alfa"></div>
      <div class="field"><label>Czlonkowie / notatki</label><textarea name="members" placeholder="jedna osoba w linii"></textarea></div>
    </div>
    <div class="button-row"><button class="btn">Dodaj druzyne</button></div>
  </form>
</section>

<section class="panel">
  <h2>Szybkie tworzenie</h2>
  <form method="post" action="/teams/bulk-create">
    <div class="grid compact">
      <div class="field"><label>Od numeru</label><input name="start" type="number" min="1" value="{esc(next_number)}"></div>
      <div class="field"><label>Ile druzyn</label><input name="count" type="number" min="1" max="200" value="12"></div>
      <div class="field"><label>Prefix nazwy</label><input name="prefix" value="Druzyna"></div>
    </div>
    <button class="btn secondary">Utworz puste druzyny</button>
  </form>
</section>

<section class="panel">
  <h2>Import CSV / tekst</h2>
  <p class="muted">Format: <code>numer,nazwa,czlonkowie</code> albo samo <code>nazwa</code>. Istniejacy numer zostanie zaktualizowany.</p>
  <form method="post" action="/teams/import-csv">
    <div class="field"><label>Dane</label><textarea name="payload" placeholder="1,Alfa,Ala; Bartek&#10;2,Beta"></textarea></div>
    <button class="btn secondary">Importuj druzyny</button>
  </form>
</section>

<section class="panel">
  <h2>Lista</h2>
  <div class="cards">{cards_html}</div>
</section>
"""
    return layout("Druzyny", "teams", body)


def scoring_page(message: str | None = None, error: bool = False) -> bytes:
    with db() as conn:
        comp = competition(conn)
        rows = result_rows(conn, sort="number")
        options = "".join(
            f"<option value='{row['team']['team_number']}'>{esc(row['team']['team_number'])}. {esc(row['team']['name'])}</option>"
            for row in rows
        )
        task_headers = "".join(f"<th>{task}</th>" for task in range(1, int(comp["task_count"]) + 1))
        body_rows = []
        for row in rows:
            cells = []
            for task in range(1, int(comp["task_count"]) + 1):
                status = task_status(row, task)
                action = "burned" if status == "done" else "clear" if status == "burned" else "done"
                label = "X" if status == "done" else "-" if status == "burned" else "+"
                cells.append(
                    f"""<td><form class="inline" method="post" action="/score/cell">
  <input type="hidden" name="team_id" value="{row['team']['id']}">
  <input type="hidden" name="task_number" value="{task}">
  <input type="hidden" name="action" value="{action}">
  <button class="cell-btn {esc(status)}" title="Klik: puste -> zaliczone -> spalone -> puste">{label}</button>
</form></td>"""
                )
            body_rows.append(
                f"<tr><td><strong>{esc(row['team']['team_number'])}. {esc(row['team']['name'])}</strong><div class='team-meta'>{esc(row['count'])} zaliczonych</div></td>{''.join(cells)}</tr>"
            )
        grid_html = (
            f"""<div class="score-grid"><table><thead><tr><th>Druzyna</th>{task_headers}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"""
            if rows
            else "<p class='muted'>Najpierw dodaj druzyny.</p>"
        )
        body = f"""
{notice(message, error)}
<section class="panel">
  <h1>Punktowanie</h1>
  <form method="post" action="/score/mark">
    <div class="grid compact">
      <div class="field">
        <label>Druzyna</label>
        <input name="team_lookup" list="team-list" placeholder="numer lub nazwa" autocomplete="off">
        <datalist id="team-list">{options}</datalist>
      </div>
      <div class="field"><label>Zadanie</label><input name="task_number" type="number" min="1" max="{esc(comp['task_count'])}" value="1"></div>
      <div class="field">
        <label>Status</label>
        <select name="action">
          <option value="done">zaliczone</option>
          <option value="burned">spalone</option>
          <option value="clear">wyczysc</option>
        </select>
      </div>
    </div>
    <div class="button-row"><button class="btn">Zapisz wynik</button></div>
  </form>
</section>
<section class="panel">
  <h2>Siatka</h2>
  <p class="muted">Klik komorke zmienia status w cyklu: puste, zaliczone, spalone, puste.</p>
  {grid_html}
</section>
"""
    return layout("Punktowanie", "scoring", body)


def ranking_fragment(fullscreen: bool = False) -> str:
    with db() as conn:
        comp = competition(conn)
        cutoff = ranking_snapshot_at(comp)
        rows = result_rows(conn, cutoff=cutoff)
        state = state_for(comp)
        freeze_note = (
            f"<div class='fs-notice'>Ranking zamrozony: {esc(fmt_dt_display(cutoff))}</div>"
            if fullscreen and cutoff
            else f"<div class='notice'>Ranking zamrozony. Pokazuje stan z {esc(fmt_dt_display(cutoff))}.</div>"
            if cutoff
            else ""
        )
        if fullscreen:
            if rows:
                visible_count = 12 if len(rows) > 12 else len(rows)
                row_html = []
                for idx, row in enumerate(rows[:visible_count], 1):
                    members = team_members_display(row["team"]["members"])
                    members_html = f"<div class='fs-members'>{esc(members)}</div>" if members else ""
                    row_html.append(
                        f"""
<div class="fs-row {'first' if idx == 1 else ''}">
  <div class="fs-rank">{idx}</div>
  <div class="fs-team-block"><div class="fs-team">{esc(row['team']['name'])}</div>{members_html}</div>
  <div class="fs-score">{esc(row['count'])}</div>
</div>
"""
                    )
                board = "".join(row_html)
            else:
                board = "<div class='fs-notice'>Brak druzyn.</div>"
            return f"""
<div class="fs-wrap">
  <header class="fs-head">
    <div>
      <div class="fs-title">{esc(comp['title'])}</div>
      {freeze_note}
    </div>
    <div class="fs-state">
      <div>{esc(display_state(state))}</div>
      <div class="fs-timer">{esc(fmt_seconds(timer_value(comp)))}</div>
      <div>{esc(timer_label(comp))}</div>
    </div>
  </header>
  <section class="fs-board">{board}</section>
</div>
"""

        task_count = int(comp["task_count"])
        rows_html = []
        cards_html = []
        for idx, row in enumerate(rows, 1):
            squares = "".join(task_square(task_status(row, task), task) for task in range(1, task_count + 1))
            members = team_members_display(row["team"]["members"])
            members_html = f"<div class='team-meta'>{esc(members)}</div>" if members else ""
            rows_html.append(
                f"<tr><td class='rank'>{idx}</td><td>{esc(row['team']['name'])}{members_html}<div class='team-meta'>nr {esc(row['team']['team_number'])}</div></td><td class='score'>{row['count']}</td><td><div class='tasks'>{squares}</div></td></tr>"
            )
            cards_html.append(
                f"""
<div class="rank-card">
  <div class="rank-card-top">
    <div class="rank">{idx}</div>
    <div><strong>{esc(row['team']['name'])}</strong>{members_html}<div class="team-meta">nr {esc(row['team']['team_number'])}</div></div>
    <div class="score">{row['count']}</div>
  </div>
  <div class="tasks" style="margin-top:10px">{squares}</div>
</div>
"""
            )
        table_body = "".join(rows_html) or "<tr><td colspan='4' class='muted'>Brak druzyn.</td></tr>"
        cards_body = "".join(cards_html) or "<p class='muted'>Brak druzyn.</p>"
        return f"""
<div class="ranking-head">
  <div>
    <h1>{esc(comp['title'])}</h1>
    <div><span class="state {esc(state)}">{esc(display_state(state))}</span></div>
  </div>
  <div><div class="muted">{esc(timer_label(comp))}</div><div class="timer">{esc(fmt_seconds(timer_value(comp)))}</div></div>
</div>
{freeze_note}
<div class="table-wrap scoreboard-table">
  <table class="table">
    <thead><tr><th>Miejsce</th><th>Druzyna</th><th>Wynik</th><th>Zadania</th></tr></thead>
    <tbody>{table_body}</tbody>
  </table>
</div>
<div class="rank-cards">{cards_body}</div>
<div class="footer-note">Ranking odswieza sie automatycznie. Aplikacja dziala lokalnie na tym komputerze.</div>
"""


def ranking_page() -> bytes:
    body = f"""
<section class="panel">
  <div class="button-row" style="margin-top:0;margin-bottom:12px">
    <a class="btn secondary" href="/ranking/fullscreen">Otworz fullscreen</a>
  </div>
  <div id="ranking-root">{ranking_fragment(False)}</div>
</section>
<script>
async function refreshRanking() {{
  try {{
    const response = await fetch('/api/ranking');
    if (!response.ok) return;
    const payload = await response.json();
    document.getElementById('ranking-root').innerHTML = payload.html;
  }} catch (error) {{}}
}}
setInterval(refreshRanking, 2000);
</script>
"""
    return layout("Ranking", "ranking", body)


def fullscreen_page() -> bytes:
    html_text = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ranking fullscreen - Local Bullet</title>
  <style>{STYLE}</style>
</head>
<body class="fullscreen">
  <div id="ranking-root">{ranking_fragment(True)}</div>
  <script>
  async function refreshRanking() {{
    try {{
      const response = await fetch('/api/ranking?fullscreen=1');
      if (!response.ok) return;
      const payload = await response.json();
      document.getElementById('ranking-root').innerHTML = payload.html;
    }} catch (error) {{}}
  }}
  document.addEventListener('keydown', (event) => {{
    if (event.key === 'Escape') window.location.href = '/ranking';
  }});
  setInterval(refreshRanking, 2000);
  </script>
</body>
</html>"""
    return html_text.encode("utf-8")


def export_payload() -> dict:
    with db() as conn:
        comp = dict(competition(conn))
        teams = [dict(row) for row in conn.execute("SELECT * FROM teams ORDER BY team_number").fetchall()]
        solves = [dict(row) for row in conn.execute("SELECT * FROM solves ORDER BY team_id, task_number").fetchall()]
    return {"version": 1, "competition": comp, "teams": teams, "solves": solves}


def import_payload(payload: dict) -> None:
    comp = payload.get("competition") or {}
    teams = payload.get("teams") or []
    solves = payload.get("solves") or []
    with db() as conn:
        conn.execute("DELETE FROM solves")
        conn.execute("DELETE FROM teams")
        conn.execute(
            """
            UPDATE competition
            SET title=?, task_count=?, started_at=?, ended_at=?, freeze_minutes_before_end=?,
                unfreeze_minutes_after_end=?, ranking_unfrozen_at=?, updated_at=?
            WHERE id=1
            """,
            (
                clean_text(comp.get("title") or "Konkurs lokalny", TITLE_LIMIT),
                clamp_int(comp.get("task_count"), 20, 1, MAX_TASKS),
                comp.get("started_at"),
                comp.get("ended_at"),
                clamp_int(comp.get("freeze_minutes_before_end"), 0, 0),
                clamp_int(comp.get("unfreeze_minutes_after_end"), -1, -1),
                comp.get("ranking_unfrozen_at"),
                now(),
            ),
        )
        id_map: dict[int, int] = {}
        used_numbers: set[int] = set()
        for item in teams:
            number = clamp_int(item.get("team_number"), next_team_number(conn), 1)
            while number in used_numbers or conn.execute("SELECT 1 FROM teams WHERE team_number=?", (number,)).fetchone():
                number += 1
            used_numbers.add(number)
            cur = conn.execute(
                """
                INSERT INTO teams(team_number, name, members, active, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    number,
                    clean_text(item.get("name") or f"Druzyna {number}", TEAM_NAME_LIMIT),
                    clean_multiline(item.get("members") or "", MEMBERS_LIMIT),
                    1 if int(item.get("active", 1) or 0) else 0,
                    int(item.get("created_at") or now()),
                    now(),
                ),
            )
            if "id" in item:
                id_map[int(item["id"])] = int(cur.lastrowid)
        task_count = clamp_int(comp.get("task_count"), 20, 1, MAX_TASKS)
        for item in solves:
            old_team_id = int(item.get("team_id") or 0)
            team_id = id_map.get(old_team_id)
            if not team_id:
                continue
            task = clamp_int(item.get("task_number"), 1, 1, task_count)
            status = "burned" if item.get("status") == "burned" else "done"
            conn.execute(
                "INSERT OR REPLACE INTO solves(team_id, task_number, status, marked_at) VALUES(?, ?, ?, ?)",
                (team_id, task, status, int(item.get("marked_at") or now())),
            )


def parse_form(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    try:
        length = int(handler.headers.get("Content-Length", "0") or "0")
    except ValueError:
        length = 0
    if length < 0 or length > MAX_BODY_BYTES:
        raise ValueError("Request body too large")
    raw = handler.rfile.read(length).decode("utf-8", "replace")
    values = parse_qs(raw, keep_blank_values=True)
    return {key: vals[-1] if vals else "" for key, vals in values.items()}


def message_redirect(path: str, message: str, error: bool = False) -> str:
    sep = "&" if "?" in path else "?"
    key = "error" if error else "message"
    return f"{path}{sep}{key}={quote(message)}"


class App(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_bytes(self, status: int, data: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def redirect(self, location: str) -> None:
        data = b""
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        message = query.get("message", [""])[0]
        error_message = query.get("error", [""])[0]
        try:
            if parsed.path == "/":
                self.redirect("/admin")
            elif parsed.path == "/admin":
                self.send_bytes(200, admin_page(message or error_message, bool(error_message)), "text/html; charset=utf-8")
            elif parsed.path == "/teams":
                self.send_bytes(200, teams_page(message or error_message, bool(error_message)), "text/html; charset=utf-8")
            elif parsed.path == "/scoring":
                self.send_bytes(200, scoring_page(message or error_message, bool(error_message)), "text/html; charset=utf-8")
            elif parsed.path == "/ranking":
                self.send_bytes(200, ranking_page(), "text/html; charset=utf-8")
            elif parsed.path == "/ranking/fullscreen":
                self.send_bytes(200, fullscreen_page(), "text/html; charset=utf-8")
            elif parsed.path == "/api/ranking":
                fullscreen = query.get("fullscreen", ["0"])[0] == "1"
                payload = json.dumps({"html": ranking_fragment(fullscreen)}, ensure_ascii=False).encode("utf-8")
                self.send_bytes(200, payload, "application/json; charset=utf-8")
            elif parsed.path == "/data/export.json":
                payload = json.dumps(export_payload(), indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=local-bullet-backup.json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)
            else:
                self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        except Exception as exc:
            self.send_bytes(500, f"Internal error: {exc}".encode("utf-8"), "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        try:
            form = parse_form(self)
            if parsed.path == "/settings":
                self.post_settings(form)
            elif parsed.path == "/contest/start":
                with db() as conn:
                    comp = competition(conn)
                    duration = duration_minutes(comp)
                    started = now()
                    ended = started + int(duration) * 60 if duration else None
                    conn.execute("UPDATE competition SET started_at=?, ended_at=?, ranking_unfrozen_at=NULL, updated_at=? WHERE id=1", (started, ended, now()))
                self.redirect(message_redirect("/admin", "Konkurs uruchomiony."))
            elif parsed.path == "/contest/end":
                with db() as conn:
                    conn.execute("UPDATE competition SET ended_at=?, ranking_unfrozen_at=NULL, updated_at=? WHERE id=1", (now(), now()))
                self.redirect(message_redirect("/admin", "Konkurs zakonczony."))
            elif parsed.path == "/contest/clear-time":
                with db() as conn:
                    conn.execute("UPDATE competition SET started_at=NULL, ended_at=NULL, ranking_unfrozen_at=NULL, updated_at=? WHERE id=1", (now(),))
                self.redirect(message_redirect("/admin", "Czas konkursu wyczyszczony."))
            elif parsed.path == "/contest/unfreeze":
                with db() as conn:
                    conn.execute("UPDATE competition SET ranking_unfrozen_at=?, updated_at=? WHERE id=1", (now(), now()))
                self.redirect(message_redirect("/admin", "Ranking odmrozony."))
            elif parsed.path == "/teams/add":
                self.post_team_add(form)
            elif parsed.path == "/teams/update":
                team_id = clamp_int(parse_qs(parsed.query).get("id", ["0"])[0], 0, 1)
                self.post_team_update(team_id, form)
            elif parsed.path == "/teams/delete":
                team_id = clamp_int(parse_qs(parsed.query).get("id", ["0"])[0], 0, 1)
                with db() as conn:
                    conn.execute("DELETE FROM teams WHERE id=?", (team_id,))
                self.redirect(message_redirect("/teams", "Druzyna usunieta."))
            elif parsed.path == "/teams/bulk-create":
                self.post_bulk_create(form)
            elif parsed.path == "/teams/import-csv":
                self.post_import_csv(form)
            elif parsed.path == "/score/mark":
                self.post_score_mark(form)
            elif parsed.path == "/score/cell":
                self.post_score_cell(form)
            elif parsed.path == "/data/wipe-scores":
                if form.get("confirm") != "WYNIKI":
                    self.redirect(message_redirect("/admin", "Wpisz WYNIKI, aby usunac punktacje.", True))
                    return
                with db() as conn:
                    conn.execute("DELETE FROM solves")
                self.redirect(message_redirect("/admin", "Punktacja wyczyszczona."))
            elif parsed.path == "/data/import-json":
                if form.get("confirm") != "IMPORT":
                    self.redirect(message_redirect("/admin", "Wpisz IMPORT, aby nadpisac dane.", True))
                    return
                payload = json.loads(form.get("payload") or "{}")
                import_payload(payload)
                self.redirect(message_redirect("/admin", "Backup zaimportowany."))
            else:
                self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        except sqlite3.IntegrityError as exc:
            target = "/teams" if parsed.path.startswith("/teams") else "/admin"
            self.redirect(message_redirect(target, f"Blad danych: {exc}", True))
        except Exception as exc:
            target = "/teams" if parsed.path.startswith("/teams") else "/scoring" if parsed.path.startswith("/score") else "/admin"
            self.redirect(message_redirect(target, f"Blad: {exc}", True))

    def post_settings(self, form: dict[str, str]) -> None:
        title = clean_text(form.get("title"), TITLE_LIMIT) or "Konkurs lokalny"
        task_count = clamp_int(form.get("task_count"), 20, 1, MAX_TASKS)
        started_at = parse_dt_input(form.get("started_at", ""))
        ended_at = parse_dt_input(form.get("ended_at", ""))
        duration = form.get("duration_minutes", "").strip()
        if started_at and duration:
            ended_at = started_at + clamp_int(duration, 0, 0) * 60
        freeze = clamp_int(form.get("freeze_minutes_before_end"), 0, 0)
        unfreeze = clamp_int(form.get("unfreeze_minutes_after_end"), -1, -1)
        with db() as conn:
            old_task_count = int(competition(conn)["task_count"])
            conn.execute(
                """
                UPDATE competition
                SET title=?, task_count=?, started_at=?, ended_at=?, freeze_minutes_before_end=?,
                    unfreeze_minutes_after_end=?, ranking_unfrozen_at=NULL, updated_at=?
                WHERE id=1
                """,
                (title, task_count, started_at, ended_at, freeze, unfreeze, now()),
            )
            if task_count < old_task_count:
                conn.execute("DELETE FROM solves WHERE task_number>?", (task_count,))
        self.redirect(message_redirect("/admin", "Ustawienia zapisane."))

    def post_team_add(self, form: dict[str, str]) -> None:
        with db() as conn:
            number = clamp_int(form.get("team_number"), next_team_number(conn), 1)
            name = clean_text(form.get("name"), TEAM_NAME_LIMIT) or f"Druzyna {number}"
            members = clean_multiline(form.get("members"), MEMBERS_LIMIT)
            conn.execute(
                "INSERT INTO teams(team_number, name, members, active, created_at, updated_at) VALUES(?, ?, ?, 1, ?, ?)",
                (number, name, members, now(), now()),
            )
        self.redirect(message_redirect("/teams", "Druzyna dodana."))

    def post_team_update(self, team_id: int, form: dict[str, str]) -> None:
        with db() as conn:
            number = clamp_int(form.get("team_number"), team_id, 1)
            name = clean_text(form.get("name"), TEAM_NAME_LIMIT) or f"Druzyna {number}"
            members = clean_multiline(form.get("members"), MEMBERS_LIMIT)
            active = 1 if form.get("active") == "1" else 0
            conn.execute(
                "UPDATE teams SET team_number=?, name=?, members=?, active=?, updated_at=? WHERE id=?",
                (number, name, members, active, now(), team_id),
            )
        self.redirect(message_redirect("/teams", "Druzyna zapisana."))

    def post_bulk_create(self, form: dict[str, str]) -> None:
        count = clamp_int(form.get("count"), 12, 1, 200)
        start = clamp_int(form.get("start"), 1, 1)
        prefix = clean_text(form.get("prefix"), 40) or "Druzyna"
        created = 0
        with db() as conn:
            number = start
            for _ in range(count):
                while conn.execute("SELECT 1 FROM teams WHERE team_number=?", (number,)).fetchone():
                    number += 1
                conn.execute(
                    "INSERT INTO teams(team_number, name, members, active, created_at, updated_at) VALUES(?, ?, '', 1, ?, ?)",
                    (number, f"{prefix} {number}", now(), now()),
                )
                created += 1
                number += 1
        self.redirect(message_redirect("/teams", f"Utworzono druzyny: {created}."))

    def post_import_csv(self, form: dict[str, str]) -> None:
        payload = form.get("payload") or ""
        imported = 0
        with db() as conn:
            reader = csv.reader(io.StringIO(payload))
            for row in reader:
                row = [cell.strip() for cell in row]
                if not row or not any(row):
                    continue
                if len(row) == 1 or not row[0].isdigit():
                    number = next_team_number(conn)
                    name = clean_text(row[0], TEAM_NAME_LIMIT) or f"Druzyna {number}"
                    members = ""
                else:
                    number = clamp_int(row[0], next_team_number(conn), 1)
                    name = clean_text(row[1] if len(row) > 1 else "", TEAM_NAME_LIMIT) or f"Druzyna {number}"
                    members = clean_multiline(row[2] if len(row) > 2 else "", MEMBERS_LIMIT)
                existing = conn.execute("SELECT id FROM teams WHERE team_number=?", (number,)).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE teams SET name=?, members=?, active=1, updated_at=? WHERE id=?",
                        (name, members, now(), existing["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO teams(team_number, name, members, active, created_at, updated_at) VALUES(?, ?, ?, 1, ?, ?)",
                        (number, name, members, now(), now()),
                    )
                imported += 1
        self.redirect(message_redirect("/teams", f"Zaimportowano wiersze: {imported}."))

    def post_score_mark(self, form: dict[str, str]) -> None:
        with db() as conn:
            team = find_team(conn, form.get("team_lookup", ""))
            if not team:
                self.redirect(message_redirect("/scoring", "Nie znaleziono druzyny.", True))
                return
            task = clamp_int(form.get("task_number"), 1, 1, int(competition(conn)["task_count"]))
            action = form.get("action") if form.get("action") in {"done", "burned", "clear"} else "done"
            set_mark(conn, int(team["id"]), task, action)
        self.redirect(message_redirect("/scoring", "Wynik zapisany."))

    def post_score_cell(self, form: dict[str, str]) -> None:
        with db() as conn:
            team_id = clamp_int(form.get("team_id"), 0, 1)
            task = clamp_int(form.get("task_number"), 1, 1, int(competition(conn)["task_count"]))
            action = form.get("action") if form.get("action") in {"done", "burned", "clear"} else "done"
            set_mark(conn, team_id, task, action)
        self.redirect("/scoring")


def make_server() -> tuple[ThreadingHTTPServer, int]:
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 50):
        try:
            server = ThreadingHTTPServer((HOST, port), App)
            return server, port
        except OSError:
            continue
    raise RuntimeError(f"No free port found from {DEFAULT_PORT} to {DEFAULT_PORT + 49}")


def main() -> None:
    init_db()
    server, port = make_server()
    url = f"http://{HOST}:{port}/admin"
    print("Local Bullet")
    print(f"Data: {DB_PATH}")
    print(f"URL:  {url}")
    print("Stop: Ctrl+C")
    if os.environ.get("LOCAL_BULLET_NO_BROWSER") != "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
