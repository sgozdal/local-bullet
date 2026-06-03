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
import html
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


STYLE = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#17202a;background:#f5f7f8}*{box-sizing:border-box}body{margin:0}.top{background:#0f4c3a;color:white;border-bottom:4px solid #f1b434}.top-inner{max-width:1180px;margin:auto;padding:16px 20px;display:flex;gap:16px;align-items:center;justify-content:space-between}.brand{display:flex;align-items:center;gap:10px;color:white;text-decoration:none;font-size:20px;font-weight:800}.brand img{width:42px;height:42px;border-radius:6px;object-fit:cover;}.nav{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.nav form{margin:0;display:flex}.top .nav a,.top .nav button{color:white;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:6px;padding:8px 10px;text-decoration:none;font:inherit;cursor:pointer}.wrap{max-width:1180px;margin:0 auto;padding:22px 20px 88px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.panel form>.grid{margin-bottom:18px}form.grid{align-items:end}.button-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:18px}.checkbox-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin-bottom:16px}.team-check-list{display:grid;gap:8px;max-height:58vh;overflow:auto;border:1px solid #dce3e7;border-radius:6px;padding:8px;background:#f8fafb}.check-row{display:flex;gap:9px;align-items:flex-start;padding:7px 8px;border-radius:5px}.check-row:hover{background:#eef3f5}.check-row input{margin-top:3px;flex:0 0 auto}.team-check{align-items:flex-start}.panel{background:white;border:1px solid #dce3e7;border-radius:8px;padding:16px;margin-bottom:16px}.panel h2,.panel h3{margin-top:0}.panel form+h2{margin-top:22px}.section-title{text-align:left}.scoring-quick{display:grid;gap:18px;margin-top:18px}.scoring-quick .button-row{margin:0}.scoring-quick-title{display:block;width:100%;clear:both;margin:0;text-align:left;font-size:1.5em;line-height:1.2;font-weight:700}.scoring-quick-form{margin:0}.muted{color:#66757f}.status-badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:13px;font-weight:800;background:#eef2f4;color:#53636c}.status-badge.registered{background:#dff6e9;color:#0b6845}.status-badge.unregistered{background:#fdebea;color:#8a211b}.help{display:inline-flex;position:relative;align-items:center;justify-content:center;width:18px;height:18px;margin-left:5px;border-radius:999px;border:1px solid #9fb0b9;background:white;color:#42535c;font-size:12px;font-weight:900;text-transform:none;cursor:help}.help::after{content:attr(data-tip);position:absolute;left:0;top:100%;transform:translate(0,4px);white-space:pre-wrap;overflow-wrap:anywhere;display:block;width:min(360px,calc(100vw - 32px));text-align:left;padding:6px 8px;border-radius:4px;border:1px solid #767676;background:#ffffe1;color:#111;font:12px Arial,Helvetica,sans-serif;line-height:1.3;z-index:10;opacity:0;visibility:hidden;pointer-events:none;transition:none;box-shadow:0 2px 5px rgba(0,0,0,.18)}.help:hover::after{opacity:1;visibility:visible}.table .help::after{left:auto;right:0}@media(max-width:720px){.help::after{left:auto;right:0;width:min(320px,calc(100vw - 24px))}}.table form{margin:0}.btn{display:inline-flex;align-items:center;justify-content:center;min-height:38px;line-height:1.2;border:1px solid #0d6b50;background:#0f7b5c;color:white;border-radius:6px;padding:8px 11px;text-decoration:none;font-weight:700;cursor:pointer}.btn.secondary{background:white;color:#16332a;border-color:#b9c6cc}.btn.danger{background:#b3261e;border-color:#8d1d17}.btn.small{min-height:30px;padding:5px 8px;font-size:13px}.field{display:grid;gap:6px;margin-bottom:14px}.grid .field{margin-bottom:0}.field label{font-weight:700}.field input,.field textarea{width:100%;padding:9px 10px;border:1px solid #bdc9cf;border-radius:6px;font:inherit;min-height:38px}.field textarea{min-height:82px;resize:vertical}.members-grid{display:grid;gap:12px;margin-bottom:18px}.member-row{grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.member-row .field{margin-bottom:0}.table{width:100%;border-collapse:collapse;background:white;margin-bottom:16px}.table th,.table td{padding:10px;border-bottom:1px solid #e3e9ed;text-align:left;vertical-align:middle}.table th{font-size:13px;text-transform:uppercase;color:#5b6b73;background:#f0f4f6}.rank{font-size:20px;font-weight:800}.score{font-size:22px;font-weight:900;text-align:center}.team-members{margin-top:3px;margin-bottom:7px;color:#66757f;font-size:13px}.squares{display:flex;gap:4px;flex-wrap:wrap}.sq{width:22px;height:22px;border-radius:4px;border:1px solid #c9d3d8;background:#eef2f4;font-size:11px;display:flex;align-items:center;justify-content:center;color:#53636c}.sq.done{background:#16a065;color:white;border-color:#138958}.score-grid{overflow:auto;margin-bottom:16px}.score-grid table{border-collapse:collapse;background:white}.score-grid th,.score-grid td{border:1px solid #d9e1e5;padding:5px;text-align:center}.score-grid th:first-child,.score-grid td:first-child{text-align:left;position:sticky;left:0;background:white;z-index:1;min-width:160px}.toggle{width:34px;height:30px;border:1px solid #becbd1;border-radius:5px;background:#f4f7f8;cursor:pointer}.toggle.done{background:#16a065;color:white;border-color:#138958}.notice{padding:10px 12px;border-radius:6px;background:#e8f6ef;border:1px solid #bce2ce;color:#144d35;margin-bottom:14px}.error{background:#fdebea;border-color:#f3b8b3;color:#751d18}.timer{font-variant-numeric:tabular-nums;font-weight:800}.code{display:inline-flex;font-weight:900;font-variant-numeric:tabular-nums;letter-spacing:0;border:1px solid #b9c6cc;background:#f0f4f6;border-radius:6px;padding:4px 8px}.state{font-weight:800;padding:4px 8px;border-radius:999px;background:#eef2f4}.state.running{background:#dff6e9;color:#0b6845}.state.ended{background:#fdebea;color:#8a211b}.fullscreen-launch{position:fixed;right:16px;bottom:16px;z-index:30;box-shadow:0 8px 24px rgba(0,0,0,.22)}@media(max-width:720px){.fullscreen-launch{right:10px;bottom:10px;min-height:36px;padding:7px 10px}.panel{margin-bottom:12px}.button-row{margin-top:16px}.panel form>.grid{margin-bottom:16px}.btn{width:auto}.top-inner{align-items:flex-start;flex-direction:column}.table th:nth-child(7),.table td:nth-child(7){display:none}.wrap{padding:14px 10px 74px}.sq{width:19px;height:19px}.score-grid th:first-child,.score-grid td:first-child{min-width:120px}}
"""


STYLE += """
.settings-grid .toggle-field{padding-top:34px}.toggle-field label{display:flex;gap:9px;align-items:flex-start;min-height:38px}.toggle-field input{width:auto;min-height:0;margin:0;padding:0;border:0;flex:0 0 auto}.toggle-field span{line-height:1.25}.toggle-field label>span{display:block;transform:translateY(-11px)}@media(max-width:720px){.settings-grid .toggle-field{padding-top:0}}
"""

STYLE += """
[hidden]{display:none!important}.inline-form{margin:0}.grid-action{align-self:end;padding-bottom:0}.admin-delete-form{margin-top:14px}.help-editor{min-height:360px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}.member-row{display:grid}.fullscreen-frame{position:fixed;inset:0;width:100vw;height:100vh;border:0;background:#081812;z-index:9999}
"""

STYLE += """
.rank-cards{display:none}.rank-card{background:white;border:1px solid #dce3e7;border-radius:8px;padding:12px}.rank-card-top{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:start}.rank-card-place{font-size:22px;font-weight:900;color:#0f4c3a;font-variant-numeric:tabular-nums}.rank-card-team{min-width:0;overflow-wrap:anywhere}.rank-card-score{text-align:right;color:#0f4c3a;font-weight:900;font-variant-numeric:tabular-nums}.rank-card-score span{display:block;font-size:26px;line-height:1}.rank-card-score small{display:block;color:#66757f;font-size:11px;text-transform:uppercase}.rank-card-meta{margin-top:8px;color:#66757f;font-size:13px}.rank-card-tasks{display:flex;gap:4px;overflow-x:auto;padding:10px 0 2px;scrollbar-width:thin}.rank-card-tasks .sq{flex:0 0 auto}.team-print-tools{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px}.settings-grid{grid-template-columns:repeat(auto-fit,minmax(220px,260px));justify-content:start;align-items:start}.settings-grid .field{max-width:260px}.settings-grid .field input{min-width:0}.settings-state-form{align-items:stretch}.settings-form .button-row{margin-top:4px}.responsive-card .actions-cell form{display:block}
@media(max-width:720px){.top-inner{padding:10px 10px 12px;gap:10px}.brand{font-size:17px;max-width:100%;min-width:0}.brand img{width:36px;height:36px}.brand span{min-width:0;overflow-wrap:anywhere}.nav{width:100%;max-width:100%;display:flex;flex-wrap:nowrap;gap:6px;overflow-x:auto;padding-bottom:2px;scrollbar-width:thin}.nav form{flex:0 0 auto}.top .nav a,.top .nav button{white-space:nowrap;min-height:36px;padding:7px 9px}.grid,.settings-grid,.scoring-quick-form{grid-template-columns:1fr!important}.settings-grid{justify-content:stretch}.settings-grid .field{max-width:none}.button-row{display:grid;grid-template-columns:1fr;gap:8px}.button-row .btn,.button-row button,.button-row a{width:100%}.settings-state-form{grid-template-columns:1fr 1fr}.settings-state-form .btn,.settings-form .button-row .btn{width:100%}.scoreboard-table{display:none}.rank-cards{display:grid;gap:10px}.rank-card{padding:11px 10px}.rank-card-top{grid-template-columns:auto minmax(0,1fr) minmax(56px,auto);gap:8px}.rank-card-place{font-size:20px}.rank-card-score span{font-size:24px}.rank-card-tasks{margin-left:-2px;margin-right:-2px}.rank-card-tasks .sq{width:24px;height:24px;font-size:11px}.team-members{font-size:12px}.responsive-card{display:block;background:transparent;border-collapse:separate}.responsive-card thead{display:none}.responsive-card tbody,.responsive-card tr,.responsive-card td{display:block;width:100%}.responsive-card tr{background:white;border:1px solid #dce3e7;border-radius:8px;margin-bottom:10px;overflow:hidden}.responsive-card td{display:grid;grid-template-columns:minmax(96px,34%) minmax(0,1fr);gap:8px;align-items:center;border-bottom:1px solid #edf1f3;padding:9px 10px;overflow-wrap:anywhere}.responsive-card td:last-child{border-bottom:0}.responsive-card td::before{content:attr(data-label);color:#66757f;font-size:12px;font-weight:800;text-transform:uppercase}.responsive-card td.actions-cell{grid-template-columns:1fr}.responsive-card td.actions-cell::before{display:none}.responsive-card td form,.responsive-card td .btn{width:100%}.score-grid{margin-left:-10px;margin-right:-10px;padding:0 10px 6px;-webkit-overflow-scrolling:touch}.score-grid table{min-width:max-content}.score-grid th:first-child,.score-grid td:first-child{min-width:132px;max-width:180px}.toggle{width:36px;height:34px}.scoring-quick .button-row{grid-template-columns:1fr 1fr}.scoring-quick-form .btn{width:100%}.team-check-list{max-height:46vh}.check-row{min-height:42px;padding:9px 8px}.checkbox-grid{grid-template-columns:1fr 1fr}.team-print-tools{display:grid;grid-template-columns:1fr 1fr}.team-print-tools .btn{width:100%}.panel{padding:13px}.panel h1{font-size:1.45em}.panel h2{font-size:1.2em}.member-row{grid-template-columns:1fr}.field{margin-bottom:12px}}
@media(max-width:440px){.settings-state-form,.scoring-quick .button-row,.checkbox-grid,.team-print-tools{grid-template-columns:1fr}.rank-card-top{grid-template-columns:auto minmax(0,1fr)}.rank-card-score{grid-column:1 / -1;text-align:left;display:flex;align-items:baseline;gap:6px}.rank-card-score span{display:inline}.rank-card-score small{display:inline}.responsive-card td{grid-template-columns:1fr;gap:3px}.fullscreen-launch{max-width:calc(100vw - 20px)}}
"""


STYLE += """
@media(max-width:720px){.responsive-card td{display:grid!important}.responsive-card th{display:none!important}}
"""

STYLE += """
@media(max-width:520px){.nav{-webkit-overflow-scrolling:touch}.rank-card-tasks{overscroll-behavior-x:contain}}
@media(min-width:1500px){.wrap{max-width:1400px}.score-grid th:first-child,.score-grid td:first-child{min-width:180px}}
.help:focus::after{opacity:1;visibility:visible}
@media(max-width:720px){.help::after{position:fixed;left:12px;right:12px;top:auto;bottom:12px;width:auto;max-height:min(46vh,280px);overflow:auto;transform:none;z-index:1000}.help:hover::after,.help:focus::after{opacity:1;visibility:visible}}
"""

STYLE += """
.sq.burned{background:#d93025;color:white;border-color:#a82018}.toggle{display:inline-flex;align-items:center;justify-content:center;padding:0}.toggle.burned{background:#d93025;color:white;border-color:#a82018}.mark-icon{width:13px;height:13px;border-radius:999px;display:inline-block;flex:0 0 auto;border:2px solid #111;background:white}.mark-icon.done{background:#16a065;border-color:#16a065}.mark-icon.burned{background:#d93025;border-color:#d93025}.mark-icon.empty{background:white;border-color:#111}.btn .mark-icon{margin-right:7px}.toggle .mark-icon{margin:0}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.scoring-quick-form{grid-template-columns:minmax(220px,1fr) 130px auto;align-items:end}.scoring-actions{display:grid;grid-template-columns:repeat(3,max-content);gap:8px;align-items:end}.scoring-actions .btn{white-space:nowrap}.score-dialog{border:1px solid #ccd6db;border-radius:8px;padding:16px;max-width:min(420px,calc(100vw - 28px));box-shadow:0 18px 42px rgba(0,0,0,.28)}.score-dialog::backdrop{background:rgba(0,0,0,.32)}.score-dialog h2{margin:0 0 12px;font-size:1.15rem;line-height:1.25}.score-dialog-close{display:flex;justify-content:flex-end;margin:0 0 8px}.score-dialog-actions{display:flex;gap:10px;flex-wrap:wrap;margin:0}.score-dialog-actions .btn{white-space:nowrap}
@media(max-width:720px){.scoring-actions{grid-template-columns:1fr}.scoring-actions .btn,.score-dialog-actions .btn{width:100%}.score-dialog-actions{display:grid;grid-template-columns:1fr}.scoring-quick-form{grid-template-columns:1fr!important}}
"""

STYLE += """
.top .nav a.active{background:white;color:#0f4c3a}.local-admin-note{font-size:13px;color:#dce9e0}.team-edit-card{background:white;border:1px solid #dce3e7;border-radius:8px;padding:12px;margin-bottom:10px}.team-edit-title{display:grid;grid-template-columns:100px minmax(0,1fr) auto;gap:10px;align-items:end}.team-edit-title .field{margin-bottom:0}.table-wrap{overflow:auto}.btn.warning{background:#9c5b00;border-color:#7c4800}@media(max-width:720px){.team-edit-title{grid-template-columns:1fr}.team-edit-title .field{margin-bottom:12px}}
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
        "not_started": "nie rozpoczęty",
        "scheduled": "zaplanowany",
        "running": "trwa",
        "ended": "zakończony",
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
        return "Upłynęło"
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


def members_display(members: str) -> str:
    return team_members_display(members)


def team_label(team: sqlite3.Row) -> str:
    return f"{team['name']} ({team['team_number']})"


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
    return f"<span class='sq{task_class(status)}'>{task}</span>"


def task_class(status: str) -> str:
    return f" {status}" if status in {"done", "burned"} else ""


def mark_icon(status: str) -> str:
    icon_class = "done" if status == "done" else "burned" if status == "burned" else "empty"
    return f"""<span class="mark-icon {icon_class}" aria-hidden="true"></span>"""


def site_title() -> str:
    return "Local Bullet"


def logo_src() -> str:
    return "/site-icon"


def logo_img_src() -> str:
    return "/site-icon"


def site_icon_svg() -> bytes:
    return b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
<rect width="96" height="96" rx="14" fill="#0f4c3a"/>
<path d="M18 64h60v10H18z" fill="#f1b434"/>
<path d="M24 24h14v34H24zM42 18h14v40H42zM60 30h12v28H60z" fill="#fff"/>
<circle cx="73" cy="23" r="7" fill="#f1b434"/>
</svg>"""


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


FULLSCREEN_STYLE = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#f7fbf8;background:#081812}*{box-sizing:border-box}body{margin:0}.fs-body{height:100vh;overflow:hidden;background:#081812;color:#f7fbf8}.fs-screen{height:100vh;display:grid;grid-template-rows:auto 1fr;gap:16px;padding:22px}.fs-top{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;border-bottom:3px solid #f1b434;padding-bottom:14px}.fs-title{font-size:38px;line-height:1.05;font-weight:900;min-width:0;overflow-wrap:anywhere}.fs-status{text-align:right;flex:0 0 auto}.fs-registration{flex:1 1 auto;max-width:760px;text-align:center;font-size:22px;line-height:1.2;font-weight:900;color:#fff;background:rgba(15,76,58,.78);border:1px solid rgba(241,180,52,.72);border-radius:8px;padding:9px 14px;box-shadow:0 4px 18px rgba(0,0,0,.18)}.fs-registration span{color:#f7d46b;white-space:nowrap}.fs-freeze{margin-bottom:7px;font-size:17px;font-weight:900;color:#f7d46b}.fs-label{font-size:18px;color:#dce9e0}.fs-clock{font-size:42px;line-height:1;font-weight:900;font-variant-numeric:tabular-nums}.fs-board{min-height:0;display:grid;grid-template-rows:auto 1fr;gap:12px}.fs-pinned{position:relative;z-index:2}.fs-scroll{min-height:0;overflow:hidden}.fs-track{display:grid;gap:10px;padding-bottom:40px}.fs-team{min-width:0;display:grid;grid-template-columns:50px 26ch minmax(0,1fr) 5ch;gap:10px;align-items:center;min-height:76px;padding:10px 12px;border:1px solid #cfd9dd;border-radius:8px;background:#fff;color:#17202a}.fs-team.first{border:2px solid #f1b434;box-shadow:0 6px 22px rgba(0,0,0,.22)}.fs-rank{font-size:30px;font-weight:900;text-align:center;color:#0f4c3a}.fs-name{font-size:20px;line-height:1.1;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.fs-members{margin-top:5px;color:#5d6c74;font-size:14px;line-height:1.2;overflow-wrap:anywhere}.fs-score{text-align:center;font-size:34px;font-weight:900;color:#0f4c3a;font-variant-numeric:tabular-nums}.fs-tasks-wrap{min-width:0;overflow:hidden}.fs-tasks{display:flex;gap:3px;width:max-content;min-width:100%;justify-content:center}.fs-tasks-wrap.fs-tasks-scrollable .fs-tasks{justify-content:start}.fs-task{width:28px;flex:0 0 28px;height:28px;min-width:0;border-radius:5px;border:1px solid #c9d3d8;background:#eef2f4;color:#53636c;font-size:12px;font-weight:800;display:flex;align-items:center;justify-content:center}.fs-task.done{background:#16a065;border-color:#138958;color:#fff}.fs-task.burned{background:#d93025;border-color:#a82018;color:#fff}.fs-empty{display:flex;align-items:center;justify-content:center;min-height:50vh;color:#dce9e0;font-size:24px}.fs-narrow .fs-screen{padding:14px}.fs-narrow .fs-top{align-items:flex-start;flex-direction:column}.fs-narrow .fs-status{text-align:left}.fs-narrow .fs-registration{max-width:100%;text-align:left;font-size:16px;padding:7px 10px}.fs-narrow .fs-registration span{white-space:normal}.fs-narrow .fs-team{grid-template-columns:44px minmax(150px,1fr) 74px;gap:10px}.fs-narrow .fs-tasks-wrap{grid-column:1 / -1}.fs-narrow .fs-title{font-size:30px}.fs-narrow .fs-clock{font-size:34px}
"""


FULLSCREEN_STYLE += """
@media(max-width:760px){.fs-screen{padding:10px;gap:10px}.fs-top{gap:10px;padding-bottom:9px;align-items:flex-start;flex-direction:column}.fs-status{text-align:left}.fs-registration{max-width:100%;text-align:left;font-size:15px;padding:7px 9px}.fs-registration span{white-space:normal}.fs-title{font-size:24px;line-height:1.1}.fs-label{font-size:13px}.fs-freeze{font-size:13px}.fs-clock{font-size:28px}.fs-board{gap:8px}.fs-track{gap:8px;padding-bottom:24px}.fs-team{min-height:0;border-radius:6px;padding:8px 9px;grid-template-columns:38px minmax(0,1fr) 58px;gap:7px}.fs-team.first{position:relative;z-index:3}.fs-rank{font-size:22px}.fs-name{font-size:15px}.fs-members{font-size:11px}.fs-score{font-size:24px}.fs-tasks-wrap{grid-column:1 / -1;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:2px}.fs-task{height:24px;font-size:10px}.fs-scroll{overflow:hidden}}
"""

FULLSCREEN_STYLE += """
@supports (height:100dvh){.fs-body,.fs-screen{height:100dvh}}
@media(min-width:1600px){.fs-screen{padding:30px 40px}.fs-team{grid-template-columns:64px 32ch minmax(0,1fr) 6ch;min-height:88px}.fs-title{font-size:46px}.fs-registration{font-size:26px}.fs-clock{font-size:50px}}
"""

def layout(title: str, active: str, body: str, refresh: bool = False) -> bytes:
    brand_title = site_title()
    nav_items = [
        ("ranking", "/", "Ranking"),
        ("admin", "/admin", "Administrator"),
        ("scoring", "/admin/scoring", "Punktacja"),
        ("teams", "/admin/teams", "Drużyny"),
        ("settings", "/admin/settings", "Ustawienia"),
    ]
    nav = "".join(
        f"<a class='{ 'active' if active == key else '' }' href='{href}'>{label}</a>"
        for key, href, label in nav_items
    )
    refresh_script = """<script>setInterval(()=>fetch('/scoreboard-fragment').then(r=>r.text()).then(html=>{let el=document.getElementById('scoreboard');if(el&&el.innerHTML!==html)el.innerHTML=html}),3000);setInterval(()=>{let t=document.querySelector('[data-start]');if(!t)return;let start=Number(t.dataset.start||0),end=Number(t.dataset.end||0),mode=t.dataset.mode||'waiting',n=Math.floor(Date.now()/1000),v=0;if(mode==='starts'){v=Math.max(0,start-n);if(v===0)location.reload()}else if(mode==='elapsed'){v=Math.max(0,(end&&n>end?end:n)-start);if(end&&n>=end)location.reload()}else if(mode==='ended'){v=Math.max(0,end-start)}let h=String(Math.floor(v/3600)).padStart(2,'0'),m=String(Math.floor(v%3600/60)).padStart(2,'0'),s=String(v%60).padStart(2,'0');t.textContent=`${h}:${m}:${s}`},1000)</script>""" if refresh else ""
    global_script = """<script>(()=>{document.addEventListener('submit',event=>{const submitter=event.submitter;const message=(submitter&&submitter.dataset.confirm)||event.target.dataset.confirm;if(message&&!confirm(message))event.preventDefault()});document.querySelectorAll('img[data-hide-on-error]').forEach(img=>img.addEventListener('error',()=>{img.hidden=true}))})();</script>"""
    icon = esc(logo_src())
    logo = esc(logo_img_src())
    html_text = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{esc(title)}</title><link rel='preload' as='image' href='{logo}'><link rel='icon' href='{icon}'><link rel='apple-touch-icon' href='{icon}'><style>{STYLE}</style></head><body><header class='top'><div class='top-inner'><a class='brand' href='/'><img src='{logo}' alt='' aria-hidden='true' width='42' height='42' loading='eager' decoding='sync' fetchpriority='high' data-hide-on-error><span>{esc(brand_title)}</span></a><nav class='nav'>{nav}</nav></div></header><main class='wrap'>{body}</main>{refresh_script}{global_script}</body></html>"""
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
        body = f"""{notice(message, error)}<div class='grid'><section class='panel'><h2>{esc(comp['title'])}</h2><p>Status: <b>{esc(display_state(state_for(comp)))}</b></p><p>Zadania: <b>{comp['task_count']}</b></p><p>Drużyny: <b>{len(rows)}</b></p></section><section class='panel'><h2>Szybkie akcje</h2><p><a class='btn' href='/admin/scoring'>Oznacz rozwiązane zadania</a></p><p><a class='btn secondary' href='/admin/teams'>Edytuj drużyny</a></p><p><a class='btn secondary' href='/admin/settings'>Ustawienia konkursu</a></p></section></div>"""
    return layout("Administrator", "admin", body)


def settings_page(message: str | None = None, error: bool = False) -> bytes:
    with db() as conn:
        comp = competition(conn)
        body = f"""
{notice(message, error)}
<section class='panel'><h1>Ustawienia konkursu</h1><form method='post' action='/admin/settings' class='settings-form'><div class='grid settings-grid'><div class='field'><label>Tytuł</label><input name='title' maxlength='{TITLE_LIMIT}' value='{esc(comp['title'])}' autocomplete='off' data-1p-ignore='true'></div><div class='field'><label>Liczba zadań</label><input name='task_count' type='number' autocomplete='off' data-1p-ignore='true' min='1' max='{MAX_TASKS}' value='{comp['task_count']}'></div><div class='field'><label>Start konkursu</label><input name='started_at' type='datetime-local' autocomplete='off' data-1p-ignore='true' value='{fmt_dt_input(comp['started_at'])}'></div><div class='field'><label>Koniec konkursu</label><input name='ended_at' type='datetime-local' autocomplete='off' data-1p-ignore='true' value='{fmt_dt_input(comp['ended_at'])}'></div><div class='field'><label>Długość w minutach</label><input name='duration_minutes' type='number' autocomplete='off' data-1p-ignore='true' min='1' value='{duration_minutes(comp)}'></div><div class='field'><label>Zamrożenie rankingu</label><input name='freeze_minutes_before_end' type='number' autocomplete='off' data-1p-ignore='true' min='0' value='{comp['freeze_minutes_before_end']}'></div><div class='field'><label>Odmrożenie rankingu</label><input name='unfreeze_minutes_after_end' type='number' autocomplete='off' data-1p-ignore='true' min='-1' value='{comp['unfreeze_minutes_after_end']}'></div></div><div class='button-row'><button class='btn'>Zapisz</button></div></form></section><section class='panel'><h2>Stan</h2><p>Konkurs: <b>{esc(display_state(state_for(comp)))}</b></p><form method='post' action='/admin/settings/state' class='button-row settings-state-form'><button class='btn' name='action' value='start'>Start teraz</button><button class='btn secondary' name='action' value='end'>Zakończ teraz</button><button class='btn danger' name='action' value='reset'>Wyczyść czas konkursu</button><button class='btn secondary' name='action' value='unfreeze'>Odmroź ranking</button></form></section>
"""
    return layout("Ustawienia", "settings", body)


def teams_page(message: str | None = None, error: bool = False) -> bytes:
    with db() as conn:
        teams = conn.execute("""
            SELECT teams.*, COUNT(CASE WHEN solves.status='done' THEN 1 END) AS solved
            FROM teams LEFT JOIN solves ON solves.team_id=teams.id
            GROUP BY teams.id
            ORDER BY teams.team_number, teams.name COLLATE NOCASE
        """).fetchall()
        rows = []
        for team in teams:
            members = members_display(team["members"])
            members_html = f"<div class='team-members'>{esc(members)}</div>" if members else ""
            rows.append(
                f"<tr><td data-label='Drużyna'><b>{esc(team_label(team))}</b>{members_html}</td>"
                f"<td data-label='Edycja'><a class='btn small secondary' href='/admin/teams/{team['id']}'>Edytuj</a></td>"
                f"<td data-label='Usuwanie'><form method='post' action='/admin/teams/{team['id']}/delete' data-confirm='Usunąć tę drużynę? Tej operacji nie da się cofnąć.'><button class='btn danger small'>Usuń</button></form></td>"
                f"<td data-label='Rozwiązane'>{team['solved']}</td></tr>"
            )
        rows_html = "".join(rows) or "<tr><td colspan='4' class='muted'>Brak drużyn.</td></tr>"
        body = f"""
{notice(message, error)}
<section class='panel'><h1>Drużyny</h1><form method='post' action='/admin/teams' class='grid'><div class='field'><label>Nazwa drużyny</label><input name='name' maxlength='{TEAM_NAME_LIMIT}' placeholder='Opcjonalnie' autocomplete='off' data-1p-ignore='true'></div><div class='grid-action'><button class='btn'>Dodaj drużynę</button></div></form><h2>Automatyczny podział</h2><form method='post' action='/admin/teams/generate' class='grid' data-confirm='Nadpisać obecne drużyny nową listą? To usunie obecne drużyny i rozwiązane zadania.'><div class='field'><label>Docelowa liczba osób</label><input name='people_count' type='number' autocomplete='off' data-1p-ignore='true' min='1' max='5000' required></div><div class='field'><label>Docelowa liczba osób w drużynie</label><input name='team_size' type='number' autocomplete='off' data-1p-ignore='true' min='1' max='20' required></div><div class='grid-action'><button class='btn danger'>Wygeneruj drużyny</button></div></form></section><table class='table responsive-card teams-table'><thead><tr><th>Drużyna</th><th></th><th></th><th>Rozwiązane</th></tr></thead><tbody>{rows_html}</tbody></table>
"""
    return layout("Drużyny", "teams", body)


def team_edit_page(team_id: int, message: str | None = None, error: bool = False) -> bytes:
    with db() as conn:
        team = conn.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
        if not team:
            return layout("Nie znaleziono", "teams", "<div class='panel error'>Nie znaleziono drużyny.</div>")
        body = f"""
{notice(message, error)}
<section class='panel'><h1>Edytuj drużynę</h1><p>Numer drużyny <span class='code'>{esc(team['team_number'])}</span></p><form method='post' action='/admin/teams/{team['id']}'><div class='field'><label>Nazwa</label><input name='name' maxlength='{TEAM_NAME_LIMIT}' value='{esc(team['name'])}' required autocomplete='off' data-1p-ignore='true'></div><div class='field'><label>Członkowie / notatki</label><textarea name='members'>{esc(team['members'])}</textarea></div><div class='button-row'><button class='btn'>Zapisz</button><a class='btn secondary' href='/admin/teams'>Wróć</a></div></form><form method='post' action='/admin/teams/{team['id']}/delete' class='admin-delete-form' data-confirm='Usunąć tę drużynę? Tej operacji nie da się cofnąć.'><button class='btn danger'>Usuń drużynę</button></form></section>
"""
    return layout("Edytuj drużynę", "teams", body)


def score_cell_button(row: dict, task: int, sort_mode: str) -> str:
    team = row["team"]
    status = task_status(row, task)
    labels = {"done": "zrobione", "burned": "spalone", "": "nieoznaczone"}
    title = f"Zadanie {task}: {labels.get(status, 'nieoznaczone')}. Kliknij, aby wybrać akcję."
    aria = f"{team_label(team)}, zadanie {task}: {labels.get(status, 'nieoznaczone')}"
    state = status or "empty"
    return f"""<td><button type="button" class="toggle{task_class(status)}" title="{esc(title)}" data-score-cell data-team-id="{team['id']}" data-team-label="{esc(team_label(team))}" data-task="{task}" data-state="{esc(state)}" data-sort="{esc(sort_mode)}">{mark_icon(status)}<span class="sr-only">{esc(aria)}</span></button></td>"""


def scoring_dialog() -> str:
    script = """<script>(()=>{const dialog=document.getElementById("score-dialog");if(!dialog)return;const form=dialog.querySelector("[data-score-dialog-form]");const title=dialog.querySelector("[data-score-dialog-title]");const primary=dialog.querySelector("[data-dialog-primary]");const secondary=dialog.querySelector("[data-dialog-secondary]");function icon(state){let cls=state==="done"?"done":state==="burned"?"burned":"empty";return '<span class="mark-icon '+cls+'" aria-hidden="true"></span>'}function setButton(btn,action,label){btn.value=action;btn.className=action==="burned"?"btn danger":action==="clear"?"btn secondary":"btn";btn.innerHTML=icon(action==="clear"?"empty":action)+"<span>"+label+"</span>"}document.querySelectorAll("[data-score-cell]").forEach(btn=>{btn.addEventListener("click",()=>{form.elements.team_id.value=btn.dataset.teamId;form.elements.task.value=btn.dataset.task;form.elements.sort.value=btn.dataset.sort||"place";let state=btn.dataset.state||"empty";title.textContent=btn.dataset.teamLabel+", zadanie "+btn.dataset.task;if(state==="done"){setButton(primary,"clear","Odznacz zadanie");setButton(secondary,"burned","Zmień na spalone")}else if(state==="burned"){setButton(primary,"clear","Odznacz zadanie");setButton(secondary,"done","Zmień na zrobione")}else{setButton(primary,"done","Oznacz jako zrobione");setButton(secondary,"burned","Oznacz jako spalone")}if(dialog.showModal)dialog.showModal();else dialog.setAttribute("open","")})});dialog.addEventListener("click",event=>{if(event.target===dialog&&dialog.close)dialog.close()})})();</script>"""
    return """<dialog id="score-dialog" class="score-dialog"><form method="dialog" class="score-dialog-close"><button class="btn secondary small" value="cancel">Zamknij</button></form><h2 data-score-dialog-title>Zadanie</h2><form method="post" action="/admin/scoring/toggle" data-score-dialog-form><input type="hidden" name="team_id"><input type="hidden" name="task"><input type="hidden" name="sort"><div class="score-dialog-actions"><button class="btn" name="action" value="done" data-dialog-primary>""" + mark_icon("done") + """<span>Oznacz jako zrobione</span></button><button class="btn danger" name="action" value="burned" data-dialog-secondary>""" + mark_icon("burned") + """<span>Oznacz jako spalone</span></button></div></form></dialog>""" + script


def scoring_page(message: str | None = None, error: bool = False, sort_mode: str = "place") -> bytes:
    if sort_mode not in {"place", "number"}:
        sort_mode = "place"
    with db() as conn:
        comp = competition(conn)
        rows = result_rows(conn, sort=sort_mode)
        head = "".join(f"<th>{task}</th>" for task in range(1, int(comp["task_count"]) + 1))
        body_rows = []
        for row in rows:
            cells = "".join(score_cell_button(row, task, sort_mode) for task in range(1, int(comp["task_count"]) + 1))
            body_rows.append(f"<tr><td><b>{esc(team_label(row['team']))}</b></td>{cells}</tr>")
        sort_place_class = 'btn small' if sort_mode == 'place' else 'btn small secondary'
        sort_number_class = 'btn small' if sort_mode == 'number' else 'btn small secondary'
        body = f"""
{notice(message, error)}
<section class='panel'><h1>Punktacja</h1><p class='muted'>Kliknij pole, aby wybrać, czy zadanie jest zrobione, spalone albo odznaczone. Spalone zadania są czerwone i nie zmieniają wyniku.</p><div class='scoring-quick'><div class='button-row'><a class='{sort_place_class}' href='/admin/scoring?sort=place'>Sortuj po miejscu</a><a class='{sort_number_class}' href='/admin/scoring?sort=number'>Sortuj po numerze</a></div><h2 class='section-title scoring-quick-title'>Szybkie oznaczanie</h2><form method='post' action='/admin/scoring/mark' class='grid scoring-quick-form'><input type='hidden' name='sort' value='{esc(sort_mode)}'><div class='field'><label>Numer albo nazwa drużyny</label><input name='team_lookup' maxlength='80' autocomplete='off' data-1p-ignore='true' required></div><div class='field'><label>Numer zadania</label><input name='task' type='number' min='1' max='{comp['task_count']}' autocomplete='off' data-1p-ignore='true' required></div><div class='scoring-actions'><button class='btn' name='action' value='done'>{mark_icon("done")}<span>Oznacz jako zrobione</span></button><button class='btn danger' name='action' value='burned'>{mark_icon("burned")}<span>Oznacz jako spalone</span></button><button class='btn secondary' name='action' value='clear'>{mark_icon("empty")}<span>Odznacz</span></button></div></form></div></section><div class='score-grid'><table><thead><tr><th>Drużyna</th>{head}</tr></thead><tbody>{''.join(body_rows) or "<tr><td class='muted'>Brak drużyn.</td></tr>"}</tbody></table></div>{scoring_dialog()}
"""
    return layout("Punktacja", "scoring", body)


def ranking_next_refresh_at(comp: sqlite3.Row) -> int | None:
    current = now()
    freeze_at = freeze_cutoff(comp)
    if freeze_at is not None and current < freeze_at:
        return freeze_at
    if ranking_is_frozen(comp):
        unfreeze_at = auto_unfreeze_at(comp)
        if unfreeze_at is not None and current < unfreeze_at:
            return unfreeze_at
    return None


def ranking_notice(comp: sqlite3.Row) -> str:
    snapshot_at = ranking_snapshot_at(comp)
    if snapshot_at is None:
        return ""
    return f"<div class='notice'>Wyniki są zamrożone. Ranking pokazuje stan z: {esc(fmt_dt_display(snapshot_at))}.</div>"


def scoreboard_fragment(conn: sqlite3.Connection) -> str:
    comp = competition(conn)
    rows = result_rows(conn, cutoff=ranking_snapshot_at(comp))
    task_count = int(comp["task_count"])
    notice_html = ranking_notice(comp)
    if not rows:
        return notice_html + """<div class="panel muted">Brak drużyn.</div>"""
    table = [notice_html, """<table class="table scoreboard-table"><thead><tr><th>#</th><th>Drużyna</th><th>Wynik</th><th>Czas</th></tr></thead><tbody>"""]
    cards = ["""<div class="rank-cards">"""]
    for rank, row in enumerate(rows, 1):
        tasks_html = "".join(task_square(task_status(row, task), task) for task in range(1, task_count + 1))
        members = members_display(row["team"]["members"])
        members_html = f"""<div class="team-members">{esc(members)}</div>""" if members else ""
        count = row["count"]
        time_text = fmt_seconds(row["last"] - comp["started_at"]) if row["last"] and comp["started_at"] else "-"
        name = esc(team_label(row["team"]))
        table.append(f"""<tr><td class="rank" data-label="Miejsce">{rank}</td><td data-label="Drużyna"><b>{name}</b>{members_html}<div class="squares">{tasks_html}</div></td><td class="score" data-label="Wynik">{count}</td><td data-label="Czas">{esc(time_text)}</td></tr>""")
        cards.append(f"""<article class="rank-card"><div class="rank-card-top"><div class="rank-card-place">{rank}</div><div class="rank-card-team"><b>{name}</b>{members_html}</div><div class="rank-card-score"><span>{count}</span><small>zadań</small></div></div><div class="rank-card-meta">Czas: {esc(time_text)}</div><div class="rank-card-tasks">{tasks_html}</div></article>""")
    table.append("</tbody></table>")
    cards.append("</div>")
    return "".join(table) + "".join(cards)


def fullscreen_timer_label(comp: sqlite3.Row) -> str:
    state = state_for(comp)
    if state == "scheduled":
        return "Konkurs zaczyna się za"
    if state == "running" and comp["ended_at"]:
        return "Konkurs kończy się za"
    if state == "running":
        return "Konkurs trwa"
    if state == "ended":
        return "Konkurs zakończony"
    return "Konkurs nie rozpoczęty"


def fullscreen_timer_mode(comp: sqlite3.Row) -> str:
    state = state_for(comp)
    if state == "scheduled":
        return "starts"
    if state == "running" and comp["ended_at"]:
        return "remaining"
    if state == "running":
        return "elapsed"
    if state == "ended":
        return "ended"
    return "waiting"


def fullscreen_timer_value(comp: sqlite3.Row) -> int:
    mode = fullscreen_timer_mode(comp)
    current = now()
    if mode == "starts":
        return max(0, int(comp["started_at"]) - current)
    if mode == "remaining":
        return max(0, int(comp["ended_at"]) - current)
    if mode == "elapsed":
        return max(0, current - int(comp["started_at"]))
    if mode == "ended" and comp["started_at"] and comp["ended_at"]:
        return max(0, int(comp["ended_at"]) - int(comp["started_at"]))
    return 0


def fullscreen_team(row: dict, rank: int, task_count: int, first: bool = False) -> str:
    tasks_html = "".join(f"""<span class="fs-task{task_class(task_status(row, task))}">{task}</span>""" for task in range(1, task_count + 1))
    members = members_display(row["team"]["members"])
    members_html = f"""<div class="fs-members">{esc(members)}</div>""" if members else ""
    first_class = " first" if first else ""
    return f"""<article class="fs-team{first_class}"><div class="fs-rank">{rank}</div><div><div class="fs-name">{esc(team_label(row["team"]))}</div>{members_html}</div><div class="fs-tasks-wrap" data-scroll-key="{row["team"]["id"]}"><div class="fs-tasks">{tasks_html}</div></div><div class="fs-score">{row["count"]}</div></article>"""


def fullscreen_fragment(conn: sqlite3.Connection) -> str:
    comp = competition(conn)
    rows = result_rows(conn, cutoff=ranking_snapshot_at(comp))
    if not rows:
        return "<div class=\"fs-empty\">Brak drużyn.</div>"
    first = fullscreen_team(rows[0], 1, int(comp["task_count"]), True)
    rest = "".join(fullscreen_team(row, rank, int(comp["task_count"])) for rank, row in enumerate(rows[1:], 2))
    return f"""<div class="fs-pinned">{first}</div><div id="fs-team-viewport" class="fs-scroll"><div class="fs-track">{rest}</div></div>"""


def fullscreen_page() -> bytes:
    with db() as conn:
        comp = competition(conn)
        mode = fullscreen_timer_mode(comp)
        refresh_at = ranking_next_refresh_at(comp) or 0
        snapshot_at = ranking_snapshot_at(comp)
        freeze_status = f"""<div class="fs-freeze">Wyniki zamrożone. Stan z: {esc(fmt_dt_display(snapshot_at))}</div>""" if snapshot_at else ""
        board = fullscreen_fragment(conn)
        script = """<script>
const fsState={vertical:{pos:0,phase:"down",hold:0,token:0},hToken:0,h:{}};
function fmtTime(v){v=Math.max(0,Math.floor(v||0));let h=String(Math.floor(v/3600)).padStart(2,"0"),m=String(Math.floor(v%3600/60)).padStart(2,"0"),s=String(v%60).padStart(2,"0");return h+":"+m+":"+s}
function updateFsClock(){let t=document.querySelector("[data-fs-timer]");if(!t)return;let mode=t.dataset.mode,start=Number(t.dataset.start||0),end=Number(t.dataset.end||0),refreshAt=Number(t.dataset.refreshAt||0),n=Math.floor(Date.now()/1000),v=0;if(refreshAt&&n>=refreshAt){location.reload();return;}if(mode==="starts"){v=Math.max(0,start-n);if(v===0)location.reload()}else if(mode==="remaining"){v=Math.max(0,end-n);if(v===0)location.reload()}else if(mode==="elapsed"){v=Math.max(0,n-start)}else if(mode==="ended"){v=Math.max(0,end-start)}t.textContent=fmtTime(v)}
function startVerticalScroll(){let vp=document.getElementById("fs-team-viewport");if(!vp)return;let max=Math.max(0,vp.scrollHeight-vp.clientHeight);fsState.vertical.token++;let token=fsState.vertical.token;if(max<4){fsState.vertical.pos=0;fsState.vertical.phase="down";vp.scrollTop=0;return}let last=performance.now();function frame(ts){if(token!==fsState.vertical.token)return;max=Math.max(0,vp.scrollHeight-vp.clientHeight);let dt=Math.min(.05,(ts-last)/1000);last=ts;let s=fsState.vertical;if(s.phase==="down"){s.pos+=dt*18;if(s.pos>=max){s.pos=max;s.phase="bottom";s.hold=ts}}else if(s.phase==="bottom"){if(ts-s.hold>1200)s.phase="up"}else if(s.phase==="up"){s.pos-=dt*220;if(s.pos<=0){s.pos=0;s.phase="top";s.hold=ts}}else if(s.phase==="top"){if(ts-s.hold>1200)s.phase="down"}vp.scrollTop=Math.max(0,Math.min(max,s.pos));requestAnimationFrame(frame)}requestAnimationFrame(frame)}
function initFs(){document.body.classList.toggle("fs-narrow",innerWidth<900);startVerticalScroll()}
function refreshBoard(){let vp=document.getElementById("fs-team-viewport");if(vp)fsState.vertical.pos=vp.scrollTop;fetch("/fullscreen-fragment").then(r=>r.text()).then(html=>{document.getElementById("fs-board").innerHTML=html;initFs()}).catch(()=>{})}
addEventListener("resize",initFs);updateFsClock();setInterval(updateFsClock,1000);initFs();setInterval(refreshBoard,7000);
</script>"""
        html_text = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(comp["title"])} - pełny ekran</title><link rel="icon" href="{esc(logo_src())}"><style>{FULLSCREEN_STYLE}</style></head><body class="fs-body"><main class="fs-screen"><header class="fs-top"><div class="fs-title">{esc(comp["title"])}</div><div class="fs-status">{freeze_status}<div class="fs-label">{esc(fullscreen_timer_label(comp))}</div><div class="fs-clock" data-fs-timer data-mode="{mode}" data-start="{comp["started_at"] or 0}" data-end="{comp["ended_at"] or 0}" data-refresh-at="{refresh_at}">{fmt_seconds(fullscreen_timer_value(comp))}</div></div></header><section id="fs-board" class="fs-board">{board}</section></main>{script}</body></html>"""
        return html_text.encode("utf-8")


def fullscreen_launch_button() -> str:
    return """<button id="fullscreen-launch" class="btn fullscreen-launch" type="button">Pełny ekran</button><script>(()=>{let button=document.getElementById("fullscreen-launch");if(!button)return;function cleanup(){if(!document.fullscreenElement&&!document.webkitFullscreenElement){document.querySelectorAll("[data-fullscreen-ranking]").forEach(el=>el.remove())}}button.addEventListener("click",async()=>{document.querySelectorAll("[data-fullscreen-ranking]").forEach(el=>el.remove());let frame=document.createElement("iframe");frame.id="fullscreen-frame";frame.className="fullscreen-frame";frame.src="/fullscreen?embedded=1";frame.allow="fullscreen";frame.setAttribute("allowfullscreen","");frame.setAttribute("data-fullscreen-ranking","1");document.body.appendChild(frame);try{if(frame.requestFullscreen){await frame.requestFullscreen()}else if(frame.webkitRequestFullscreen){frame.webkitRequestFullscreen()}else{throw new Error("fullscreen unavailable")}}catch(e){frame.remove();location.href="/fullscreen"}});document.addEventListener("fullscreenchange",cleanup);document.addEventListener("webkitfullscreenchange",cleanup)})();</script>"""


def ranking_page() -> bytes:
    with db() as conn:
        comp = competition(conn)
        state = state_for(comp)
        if state == "scheduled":
            mode = "starts"
        elif state == "running":
            mode = "elapsed"
        elif state == "ended":
            mode = "ended"
        else:
            mode = "waiting"
        scoreboard = scoreboard_fragment(conn)
        body = f"""<section class='panel'><h1>{esc(comp['title'])}</h1><p>Status: <b>{esc(display_state(state))}</b> · {esc(timer_label(comp))}: <span class='timer' data-start='{comp['started_at'] or 0}' data-end='{comp['ended_at'] or 0}' data-mode='{mode}'>{fmt_seconds(timer_value(comp))}</span></p></section><div id='scoreboard'>{scoreboard}</div>{fullscreen_launch_button()}"""
    return layout(comp["title"], "ranking", body, refresh=True)


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
        flash = message or error_message
        is_error = bool(error_message)
        try:
            path = parsed.path
            if path in {"/", "/ranking"}:
                self.send_bytes(200, ranking_page(), "text/html; charset=utf-8")
            elif path == "/scoreboard-fragment":
                with db() as conn:
                    self.send_bytes(200, scoreboard_fragment(conn).encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/fullscreen-fragment":
                with db() as conn:
                    self.send_bytes(200, fullscreen_fragment(conn).encode("utf-8"), "text/html; charset=utf-8")
            elif path in {"/fullscreen", "/ranking/fullscreen"}:
                self.send_bytes(200, fullscreen_page(), "text/html; charset=utf-8")
            elif path == "/site-icon":
                self.send_bytes(200, site_icon_svg(), "image/svg+xml")
            elif path == "/admin":
                self.send_bytes(200, admin_page(flash, is_error), "text/html; charset=utf-8")
            elif path == "/admin/settings":
                self.send_bytes(200, settings_page(flash, is_error), "text/html; charset=utf-8")
            elif path in {"/admin/teams", "/teams"}:
                self.send_bytes(200, teams_page(flash, is_error), "text/html; charset=utf-8")
            elif path.startswith("/admin/teams/"):
                team_id = clamp_int(path.rsplit("/", 1)[-1], 0, 1)
                self.send_bytes(200, team_edit_page(team_id, flash, is_error), "text/html; charset=utf-8")
            elif path in {"/admin/scoring", "/scoring"}:
                sort_mode = query.get("sort", ["place"])[0]
                self.send_bytes(200, scoring_page(flash, is_error, sort_mode), "text/html; charset=utf-8")
            else:
                self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        except Exception as exc:
            self.send_bytes(500, f"Internal error: {exc}".encode("utf-8"), "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        try:
            form = parse_form(self)
            if path in {"/admin/settings", "/settings"}:
                self.post_settings(form)
            elif path == "/admin/settings/state":
                action = form.get("action", "")
                with db() as conn:
                    if action == "start":
                        comp = competition(conn)
                        duration = duration_minutes(comp)
                        started = now()
                        ended = started + int(duration) * 60 if duration else None
                        conn.execute("UPDATE competition SET started_at=?, ended_at=?, ranking_unfrozen_at=NULL, updated_at=? WHERE id=1", (started, ended, now()))
                    elif action == "end":
                        conn.execute("UPDATE competition SET ended_at=?, ranking_unfrozen_at=NULL, updated_at=? WHERE id=1", (now(), now()))
                    elif action == "reset":
                        conn.execute("UPDATE competition SET started_at=NULL, ended_at=NULL, ranking_unfrozen_at=NULL, updated_at=? WHERE id=1", (now(),))
                    elif action == "unfreeze":
                        conn.execute("UPDATE competition SET ranking_unfrozen_at=?, updated_at=? WHERE id=1", (now(), now()))
                self.redirect(message_redirect("/admin/settings", "Stan konkursu zapisany."))
            elif path in {"/admin/teams", "/teams/add"}:
                self.post_team_add(form)
            elif path == "/admin/teams/generate":
                self.post_generate_teams(form)
            elif path.startswith("/admin/teams/") and path.endswith("/delete"):
                team_id = clamp_int(path.split("/")[-2], 0, 1)
                with db() as conn:
                    conn.execute("DELETE FROM teams WHERE id=?", (team_id,))
                self.redirect(message_redirect("/admin/teams", "Drużyna usunięta."))
            elif path.startswith("/admin/teams/"):
                team_id = clamp_int(path.rsplit("/", 1)[-1], 0, 1)
                self.post_team_update(team_id, form)
            elif path in {"/admin/scoring/mark", "/score/mark"}:
                self.post_score_mark(form)
            elif path == "/admin/scoring/toggle":
                self.post_score_toggle(form)
            elif path == "/score/cell":
                self.post_score_cell(form)
            else:
                self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        except sqlite3.IntegrityError as exc:
            target = "/admin/teams" if path.startswith(("/admin/teams", "/teams")) else "/admin/settings" if path.startswith("/admin/settings") else "/admin/scoring"
            self.redirect(message_redirect(target, f"Błąd danych: {exc}", True))
        except Exception as exc:
            target = "/admin/teams" if path.startswith(("/admin/teams", "/teams")) else "/admin/settings" if path.startswith("/admin/settings") else "/admin/scoring"
            self.redirect(message_redirect(target, f"Błąd: {exc}", True))

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
        self.redirect(message_redirect("/admin/settings", "Ustawienia zapisane."))

    def post_team_add(self, form: dict[str, str]) -> None:
        with db() as conn:
            number = next_team_number(conn)
            name = clean_text(form.get("name"), TEAM_NAME_LIMIT) or f"Drużyna {number:02d}"
            conn.execute(
                "INSERT INTO teams(team_number, name, members, active, created_at, updated_at) VALUES(?, ?, '', 1, ?, ?)",
                (number, name, now(), now()),
            )
        self.redirect(message_redirect("/admin/teams", "Drużyna dodana."))

    def post_team_update(self, team_id: int, form: dict[str, str]) -> None:
        with db() as conn:
            team = conn.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
            if not team:
                self.redirect(message_redirect("/admin/teams", "Nie znaleziono drużyny.", True))
                return
            name = clean_text(form.get("name"), TEAM_NAME_LIMIT) or f"Drużyna {int(team['team_number']):02d}"
            members = clean_multiline(form.get("members"), MEMBERS_LIMIT)
            conn.execute(
                "UPDATE teams SET name=?, members=?, active=1, updated_at=? WHERE id=?",
                (name, members, now(), team_id),
            )
        self.redirect(message_redirect(f"/admin/teams/{team_id}", "Drużyna zapisana."))

    def post_generate_teams(self, form: dict[str, str]) -> None:
        people_count = clamp_int(form.get("people_count"), 1, 1, 5000)
        team_size = clamp_int(form.get("team_size"), 1, 1, 20)
        team_count = max(1, (people_count + team_size - 1) // team_size)
        with db() as conn:
            conn.execute("DELETE FROM solves")
            conn.execute("DELETE FROM teams")
            for number in range(1, team_count + 1):
                conn.execute(
                    "INSERT INTO teams(team_number, name, members, active, created_at, updated_at) VALUES(?, ?, '', 1, ?, ?)",
                    (number, f"Drużyna {number:02d}", now(), now()),
                )
        self.redirect(message_redirect("/admin/teams", f"Wygenerowano drużyny: {team_count}."))

    def post_score_mark(self, form: dict[str, str]) -> None:
        sort_mode = form.get("sort") if form.get("sort") in {"place", "number"} else "place"
        with db() as conn:
            team = find_team(conn, form.get("team_lookup", ""))
            if not team:
                self.redirect(message_redirect(f"/admin/scoring?sort={sort_mode}", "Nie znaleziono drużyny.", True))
                return
            task = clamp_int(form.get("task") or form.get("task_number"), 1, 1, int(competition(conn)["task_count"]))
            action = form.get("action") if form.get("action") in {"done", "burned", "clear"} else "done"
            set_mark(conn, int(team["id"]), task, action)
        self.redirect(message_redirect(f"/admin/scoring?sort={sort_mode}", "Wynik zapisany."))

    def post_score_toggle(self, form: dict[str, str]) -> None:
        sort_mode = form.get("sort") if form.get("sort") in {"place", "number"} else "place"
        with db() as conn:
            team_id = clamp_int(form.get("team_id"), 0, 1)
            task = clamp_int(form.get("task") or form.get("task_number"), 1, 1, int(competition(conn)["task_count"]))
            action = form.get("action") if form.get("action") in {"done", "burned", "clear"} else "done"
            set_mark(conn, team_id, task, action)
        self.redirect(f"/admin/scoring?sort={sort_mode}")

    def post_score_cell(self, form: dict[str, str]) -> None:
        with db() as conn:
            team_id = clamp_int(form.get("team_id"), 0, 1)
            task = clamp_int(form.get("task") or form.get("task_number"), 1, 1, int(competition(conn)["task_count"]))
            action = form.get("action") if form.get("action") in {"done", "burned", "clear"} else "done"
            set_mark(conn, team_id, task, action)
        self.redirect("/admin/scoring")

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
