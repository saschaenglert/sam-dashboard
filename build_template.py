#!/usr/bin/env python3
"""One-off: turn prototype-v10.html into template.html with placeholders."""
import re
from pathlib import Path

V10 = Path("/Users/samgonzales/Library/CloudStorage/Dropbox/Claude/Who is sascha/.superpowers/brainstorm/69143-1776370746/content/prototype-v10.html")
OUT = Path(__file__).parent / "template.html"

html = V10.read_text()

# Replace base64 avatar data URL with image path (matches in tagline header and hero portrait)
html = re.sub(r"url\('data:image/jpeg;base64,[^']+'\)", "url('sam-avatar.jpg')", html)

# Replace hard-coded numbers with placeholders
replacements = {
    # Hero
    "~81,200 lines.<br>4 tools + shared platform.": "{{TOTAL_LOC}} lines.<br>{{TOOLS_COUNT}} tools + shared platform.",
    # Stats
    '<div class="stat-num">4</div><div class="stat-meta">3 live, 1 in dev</div>':
        '<div class="stat-num">{{TOOLS_COUNT}}</div><div class="stat-meta">{{TOOLS_STATUS}}</div>',
    '<div class="stat-num">484</div><div class="stat-meta">and counting</div>':
        '<div class="stat-num">{{COMMITS_TOTAL}}</div><div class="stat-meta">and counting</div>',
    '<div class="stat-num">16</div><div class="stat-meta">pre-commit checks</div>':
        '<div class="stat-num">{{QUALITY_GATES}}</div><div class="stat-meta">pre-commit checks</div>',
    '<div class="stat-num">60%</div><div class="stat-meta">enforced</div>':
        '<div class="stat-num">{{COVERAGE_MIN}}%</div><div class="stat-meta">enforced</div>',

    # Split bar legend
    "Frontend HTML/CSS/JS - ~39,500 LOC (49%)": "Frontend HTML/CSS/JS - {{FRONTEND_LOC}} LOC ({{FRONTEND_PCT}}%)",
    "Backend Python + tests - ~34,400 LOC (42%)": "Backend Python + tests - {{BACKEND_LOC}} LOC ({{BACKEND_PCT}}%)",
    "Shared platform - ~7,400 LOC (9%)": "Shared platform - {{SHARED_LOC}} LOC ({{SHARED_PCT}}%)",

    # Split bar widths
    '<div style="background:var(--green);width:49%;color:var(--navy-deep)">Frontend</div>':
        '<div style="background:var(--green);width:{{FRONTEND_PCT}}%;color:var(--navy-deep)">Frontend</div>',
    '<div style="background:var(--accent);width:42%">Backend + tests</div>':
        '<div style="background:var(--accent);width:{{BACKEND_PCT}}%">Backend + tests</div>',
    '<div style="background:var(--purple);width:9%"></div>':
        '<div style="background:var(--purple);width:{{SHARED_PCT}}%"></div>',

    # Tool 1: Real-estate + restaurant (immo)
    '<span class="tool-loc">22,731 LOC</span>': '<span class="tool-loc">{{IMMO_LOC}} LOC</span>',
    "Property valuation + restaurant go/no-go planning - 243 commits":
        "Property valuation + restaurant go/no-go planning - {{IMMO_COMMITS}} commits",
    '<div class="tool-split-val">20,300</div>': '<div class="tool-split-val">{{IMMO_FRONTEND}}</div>',
    '<div class="tool-split-val">1,016</div>': '<div class="tool-split-val">{{IMMO_BACKEND}}</div>',
    '<div class="tool-split-val">1,415</div>': '<div class="tool-split-val">{{IMMO_TESTS}}</div>',

    # Tool 2: Fewo
    '<span class="tool-loc">20,054 LOC</span>': '<span class="tool-loc">{{FEWO_LOC}} LOC</span>',
    "Operations platform for vacation rentals - 131 commits":
        "Operations platform for vacation rentals - {{FEWO_COMMITS}} commits",
    '<div class="tool-split-val">10,634</div>': '<div class="tool-split-val">{{FEWO_FRONTEND}}</div>',
    '<div class="tool-split-val">8,689</div>': '<div class="tool-split-val">{{FEWO_BACKEND}}</div>',
    '<div class="tool-split-val">731</div>': '<div class="tool-split-val">{{FEWO_TESTS}}</div>',

    # Tool 3: Buchhaltung
    '<span class="tool-loc">13,779 LOC</span>': '<span class="tool-loc">{{BUCH_LOC}} LOC</span>',
    "Bank import, matching, DATEV export - 67 commits":
        "Bank import, matching, DATEV export - {{BUCH_COMMITS}} commits",
    '<div class="tool-split-val">5,217</div>': '<div class="tool-split-val">{{BUCH_BACKEND}}</div>',
    '<div class="tool-split-val">4,551</div>': '<div class="tool-split-val">{{BUCH_TESTS}}</div>',
    '<div class="tool-split-val">4,011</div>': '<div class="tool-split-val">{{BUCH_FRONTEND}}</div>',

    # Tool 4: Hausverwalter
    '<span class="tool-loc">17,318 LOC</span>': '<span class="tool-loc">{{HAUS_LOC}} LOC</span>',
    "Cost allocation, meter readings, tenant mgmt - 43 commits - in dev":
        "Cost allocation, meter readings, tenant mgmt - {{HAUS_COMMITS}} commits - in dev",
    '<div class="tool-split-val">8,057</div>': '<div class="tool-split-val">{{HAUS_BACKEND}}</div>',
    '<div class="tool-split-val">4,718</div>': '<div class="tool-split-val">{{HAUS_TESTS}}</div>',
    '<div class="tool-split-val">4,543</div>': '<div class="tool-split-val">{{HAUS_FRONTEND}}</div>',

    # Tool 5: Shared
    '<span class="tool-loc">7,362 LOC</span>': '<span class="tool-loc">{{SHARED_LOC}} LOC</span>',

    # Agents page
    '<div class="stat-num">7</div><div class="stat-meta">cron + launchd</div>':
        '<div class="stat-num">{{SCHEDULED_JOBS}}</div><div class="stat-meta">cron + launchd</div>',
    '<div class="stat-num">381</div><div class="stat-meta">YouTube</div>':
        '<div class="stat-num">{{TRANSCRIPTS}}</div><div class="stat-meta">YouTube</div>',
    '<div class="stat-num">18</div><div class="stat-meta">LinkedIn pipeline</div>':
        '<div class="stat-num">{{DRAFTS}}</div><div class="stat-meta">LinkedIn pipeline</div>',
    '<div class="stat-num">400+</div><div class="stat-meta">Supabase pgvector</div>':
        '<div class="stat-num">{{KNOWLEDGE}}</div><div class="stat-meta">Supabase pgvector</div>',
    '<div class="stat-num">400+</div><div class="stat-meta">growing daily</div>':
        '<div class="stat-num">{{KNOWLEDGE}}</div><div class="stat-meta">growing daily</div>',

    # Fix section heading inconsistency
    '<div class="section-title">The 5 tools</div>':
        '<div class="section-title">The building blocks</div>',

    # Footer version note - make it dynamic
    "// prototype v10 - tool icons added, numbers live from repos":
        "// last updated: {{LAST_UPDATED}}",
}

for old, new in replacements.items():
    if old in html:
        html = html.replace(old, new)
    else:
        print(f"NOT FOUND: {old[:80]}")

OUT.write_text(html)
print(f"wrote {OUT} ({len(html)} bytes)")
