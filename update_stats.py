#!/usr/bin/env python3
"""Measure live stats from all Sam repos and regenerate index.html.

Runs weekly via launchd. After running, commit + push to GitHub — GitHub Pages
then redeploys automatically.

Usage:
    python3 update_stats.py                # generate index.html
    python3 update_stats.py --dry-run      # only print stats, don't write
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SAM_ROOT = SCRIPT_DIR.parent.parent      # /Sam/
TOOLS_DIR = SAM_ROOT / "tools"
PLATTFORM_DIR = SAM_ROOT / "plattform"
ORGA_DIR = SAM_ROOT / "orga"

TEMPLATE = SCRIPT_DIR / "template.html"
OUTPUT = SCRIPT_DIR / "index.html"
STATS_JSON = SCRIPT_DIR / "last_stats.json"

# Tool repo names (under /Sam/tools/)
TOOL_REPOS = {
    "immo": "immo",          # real-estate + restaurant
    "fewo": "fewo",          # short-term rental OS
    "buchhaltung": "buchhaltung",  # SMB bookkeeping
    "hausverwalter": "hausverwalter",  # property management (in dev)
}

# Static / manually maintained
QUALITY_GATES = 16
COVERAGE_MIN = 60
SCHEDULED_JOBS_PER_DAY = 7


def count_background_services() -> int:
    """Count launchd plist files relevant to Sascha's setup (sam + user-owned)."""
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    patterns = ["com.sascha*.plist", "com.user*.plist"]
    found = set()
    for p in patterns:
        for hit in agents_dir.glob(p):
            found.add(hit.name)
    return len(found)


def count_skills() -> int:
    """Count all Markdown skill files across the ecosystem.

    Sources:
    - orga/skillsystem/installed/*.md  (skills actively installed)
    - orga/skillsystem/idee/*.md        (curated skill templates)
    - orga/agents/*/skills/*.md         (agent-specific skills)
    """
    count = 0
    skill_sys = ORGA_DIR / "skillsystem"
    for sub in ("installed", "idee"):
        d = skill_sys / sub
        if d.exists():
            count += len([f for f in d.iterdir()
                          if f.is_file() and f.suffix == ".md"])
    agents = ORGA_DIR / "agents"
    if agents.exists():
        for agent in agents.iterdir():
            skills_dir = agent / "skills"
            if skills_dir.is_dir():
                count += sum(1 for _ in skills_dir.rglob("*.md"))
    return count


def count_lines(path: Path, patterns: list) -> int:
    """Sum line counts for files matching any pattern under path (skipping venv/cache)."""
    if not path.exists():
        return 0
    total = 0
    for pattern in patterns:
        for f in path.rglob(pattern):
            parts = set(f.parts)
            if "venv" in parts or "__pycache__" in parts or "node_modules" in parts:
                continue
            try:
                total += sum(1 for _ in f.open("rb"))
            except (OSError, PermissionError):
                continue
    return total


def tool_stats(tool_path: Path) -> dict:
    """Count backend, frontend, tests for a tool repo."""
    backend = count_lines(tool_path / "backend", ["*.py"])
    frontend = count_lines(tool_path / "frontend", ["*.html", "*.js", "*.css"])
    tests = count_lines(tool_path / "tests", ["*.py"])
    total = backend + frontend + tests

    # commits (if git repo)
    commits = 0
    if (tool_path / ".git").exists():
        try:
            commits = int(subprocess.check_output(
                ["git", "-C", str(tool_path), "rev-list", "--count", "HEAD"],
                stderr=subprocess.DEVNULL,
            ).decode().strip())
        except (subprocess.CalledProcessError, ValueError):
            commits = 0
    return {"backend": backend, "frontend": frontend, "tests": tests, "total": total, "commits": commits}


def file_stats(tool_path: Path, relative_file: str) -> dict:
    """Stats for a single file inside a repo: LOC + git commits."""
    f = tool_path / relative_file
    loc = 0
    if f.exists():
        try:
            loc = sum(1 for _ in f.open("rb"))
        except OSError:
            loc = 0

    commits = 0
    if (tool_path / ".git").exists():
        try:
            out = subprocess.check_output(
                ["git", "-C", str(tool_path), "log", "--oneline", "--", relative_file],
                stderr=subprocess.DEVNULL,
            ).decode()
            commits = len([line for line in out.splitlines() if line.strip()])
        except subprocess.CalledProcessError:
            commits = 0
    return {"loc": loc, "commits": commits}


def count_automation() -> dict:
    """Count Python scripts + LOC under /orga (agents, sambrain, platform code).

    Excludes venv/__pycache__/archiv so we measure only live automation code.
    """
    scripts = 0
    loc = 0
    for f in ORGA_DIR.rglob("*.py"):
        parts = set(f.parts)
        if "venv" in parts or "__pycache__" in parts or "archiv" in parts:
            continue
        scripts += 1
        try:
            loc += sum(1 for _ in f.open("rb"))
        except OSError:
            continue
    return {"scripts": scripts, "loc": loc}


def count_linkedin_drafts() -> int:
    """Count total LinkedIn drafts (new + archived)."""
    base = ORGA_DIR / "agents" / "linkedin-agent" / "drafts"
    total = 0
    for sub in ("new", "archived"):
        d = base / sub
        if d.exists():
            total += sum(1 for f in d.iterdir() if f.is_file() and f.suffix == ".md")
    return total


def count_knowledge() -> str:
    """Count entries in Supabase knowledge base. Returns string like '400+' or '0'."""
    # Try the wissen_api helper if it's callable
    wissen_cli = ORGA_DIR / "sambrain" / "wissen_api.py"
    if wissen_cli.exists():
        try:
            out = subprocess.check_output(
                ["python3", str(wissen_cli), "count"],
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).decode().strip()
            n = int(out)
            # Round down to nearest 50 for privacy/roughness
            rounded = (n // 50) * 50
            return f"{rounded}+"
        except Exception:
            pass
    # Fallback: approx
    return "400+"


def humanize(n: int) -> str:
    """28400 -> '28,400'."""
    return f"{n:,}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print stats, don't write files")
    args = parser.parse_args()

    # Collect tool stats
    tools = {name: tool_stats(TOOLS_DIR / repo) for name, repo in TOOL_REPOS.items()}

    # Restaurant planner lives inside the immo repo as gastrocheck.html —
    # measure it separately so it can be shown as its own card.
    gastro = file_stats(TOOLS_DIR / "immo", "frontend/gastrocheck.html")

    # "Real Estate Investment" = immo repo minus the gastro frontend file
    real_estate = {
        "backend": tools["immo"]["backend"],
        "frontend": tools["immo"]["frontend"] - gastro["loc"],
        "tests": tools["immo"]["tests"],
        "total": tools["immo"]["total"] - gastro["loc"],
        "commits": tools["immo"]["commits"] - gastro["commits"],
    }

    # Shared platform LOC
    shared_loc = count_lines(PLATTFORM_DIR, ["*.py"])

    # Aggregate (use original immo totals so we don't double-count)
    frontend = sum(t["frontend"] for t in tools.values())
    backend = sum(t["backend"] for t in tools.values())
    tests = sum(t["tests"] for t in tools.values())
    backend_and_tests = backend + tests
    total_tools = sum(t["total"] for t in tools.values())
    total_all = total_tools + shared_loc

    total_commits = sum(t["commits"] for t in tools.values())

    # Split percentages (of grand total)
    frontend_pct = round(frontend / total_all * 100)
    backend_pct = round(backend_and_tests / total_all * 100)
    shared_pct = round(shared_loc / total_all * 100)

    # 5 distinct products on the page + shared infrastructure (not counted)
    # Real Estate, Restaurant Planner, Freelance Accountant, Airbnb/Booking, Property Mgmt
    tools_live = 5
    tools_status = "4 live, 1 in dev"

    # Agent metrics
    automation = count_automation()
    background_services = count_background_services()
    skills = count_skills()
    knowledge = count_knowledge()

    last_updated = datetime.now().strftime("%B %Y")

    stats = {
        "generated_at": datetime.now().isoformat(),
        "last_updated": last_updated,
        "totals": {
            "loc_all": total_all,
            "loc_tools": total_tools,
            "commits": total_commits,
            "quality_gates": QUALITY_GATES,
            "coverage_min": COVERAGE_MIN,
            "tools_live": tools_live,
            "tools_status": tools_status,
        },
        "split": {
            "frontend_loc": frontend,
            "frontend_pct": frontend_pct,
            "backend_loc": backend_and_tests,
            "backend_pct": backend_pct,
            "shared_loc": shared_loc,
            "shared_pct": shared_pct,
        },
        "tools": tools,
        "agents": {
            "scheduled_jobs_per_day": SCHEDULED_JOBS_PER_DAY,
            "automation_scripts": automation["scripts"],
            "automation_loc": automation["loc"],
            "background_services": background_services,
            "skills": skills,
            "knowledge": knowledge,
        },
    }

    # Build placeholder substitutions
    subs = {
        "TOTAL_LOC": f"~{humanize(total_all)}",
        "TOOLS_COUNT": str(tools_live),
        "TOOLS_STATUS": tools_status,
        "COMMITS_TOTAL": humanize(total_commits),
        "QUALITY_GATES": str(QUALITY_GATES),
        "COVERAGE_MIN": str(COVERAGE_MIN),

        "FRONTEND_LOC": f"~{humanize(frontend)}",
        "FRONTEND_PCT": str(frontend_pct),
        "BACKEND_LOC": f"~{humanize(backend_and_tests)}",
        "BACKEND_PCT": str(backend_pct),
        "SHARED_LOC": f"~{humanize(shared_loc)}",
        "SHARED_PCT": str(shared_pct),

        # Real Estate Investment (immo minus gastro)
        "IMMO_LOC": humanize(real_estate["total"]),
        "IMMO_FRONTEND": humanize(real_estate["frontend"]),
        "IMMO_BACKEND": humanize(real_estate["backend"]),
        "IMMO_TESTS": humanize(real_estate["tests"]),
        "IMMO_COMMITS": str(real_estate["commits"]),

        # Restaurant Business Planner (gastrocheck.html inside immo)
        "GASTRO_LOC": humanize(gastro["loc"]),
        "GASTRO_COMMITS": str(gastro["commits"]),

        "FEWO_LOC": humanize(tools["fewo"]["total"]),
        "FEWO_FRONTEND": humanize(tools["fewo"]["frontend"]),
        "FEWO_BACKEND": humanize(tools["fewo"]["backend"]),
        "FEWO_TESTS": humanize(tools["fewo"]["tests"]),
        "FEWO_COMMITS": str(tools["fewo"]["commits"]),

        "BUCH_LOC": humanize(tools["buchhaltung"]["total"]),
        "BUCH_FRONTEND": humanize(tools["buchhaltung"]["frontend"]),
        "BUCH_BACKEND": humanize(tools["buchhaltung"]["backend"]),
        "BUCH_TESTS": humanize(tools["buchhaltung"]["tests"]),
        "BUCH_COMMITS": str(tools["buchhaltung"]["commits"]),

        "HAUS_LOC": humanize(tools["hausverwalter"]["total"]),
        "HAUS_FRONTEND": humanize(tools["hausverwalter"]["frontend"]),
        "HAUS_BACKEND": humanize(tools["hausverwalter"]["backend"]),
        "HAUS_TESTS": humanize(tools["hausverwalter"]["tests"]),
        "HAUS_COMMITS": str(tools["hausverwalter"]["commits"]),

        "SHARED_LOC": humanize(shared_loc),

        "SCHEDULED_JOBS": str(SCHEDULED_JOBS_PER_DAY),
        "AUTO_LOC": f"~{humanize(automation['loc'])}",
        "AUTO_SCRIPTS": str(automation["scripts"]),
        "BG_SERVICES": str(background_services),
        "SKILLS": str(skills),
        "KNOWLEDGE": knowledge,

        "LAST_UPDATED": last_updated,
    }

    if args.dry_run:
        print(json.dumps(stats, indent=2))
        return

    # Render template
    if not TEMPLATE.exists():
        print(f"ERROR: template not found at {TEMPLATE}", file=sys.stderr)
        sys.exit(1)

    html = TEMPLATE.read_text()
    missing = []
    for key, value in subs.items():
        placeholder = "{{" + key + "}}"
        if placeholder not in html:
            missing.append(key)
        html = html.replace(placeholder, value)

    # Write outputs
    OUTPUT.write_text(html)
    STATS_JSON.write_text(json.dumps(stats, indent=2))
    print(f"wrote {OUTPUT} ({len(html)} bytes)")
    print(f"wrote {STATS_JSON}")
    if missing:
        print(f"WARNING: placeholders not found in template: {missing}")


if __name__ == "__main__":
    main()
