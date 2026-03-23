#!/usr/bin/env python3
"""
IndSight Daily News Updater
───────────────────────────
Run this script once a day (manually or via cron/Task Scheduler).
It calls Claude API, gets today's top 5 news stories for each section,
and writes them directly into your IndSight-FINAL.html file.
Then you commit and push to GitHub — site updates automatically.

SETUP:
  pip install anthropic
  Set your API key: export ANTHROPIC_API_KEY="your-key-here"
  Or paste it directly into ANTHROPIC_API_KEY below.

USAGE:
  python update_news.py

WHAT IT DOES:
  1. Calls Claude for each news section (Auto, Energy, Policy, etc.)
  2. Generates top 5 stories with 5-line summaries
  3. Injects the HTML directly into IndSight-FINAL.html
  4. Saves the updated file
  5. Optionally auto-commits to GitHub (if git is set up)
"""

import anthropic
import json
import re
import os
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────
ANTHROPIC_API_KEY = ""   # ← Paste your Anthropic API key here
                          # OR set env var: ANTHROPIC_API_KEY=xxx
HTML_FILE = "index.html"  # Your IndSight HTML file name
AUTO_GIT_PUSH = False     # Set True to auto-commit + push to GitHub
# ──────────────────────────────────────────────────────────────

client = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
)

TODAY = datetime.now().strftime("%d %B %Y")  # e.g. "21 March 2026"

NEWS_FORMAT = """Return ONLY valid JSON (no markdown fences):
{"stories":[{
  "tag":"TAG",
  "headline":"Sharp headline with company + specific number",
  "summary":[
    "Line 1: What happened — specific event, company, number",
    "Line 2: Why it happened — cause or context",
    "Line 3: Key data point — number, %, GW, units, ₹ or $",
    "Line 4: What it means — impact on sector or India market",
    "Line 5: What to watch — next development or implication"
  ],
  "source":"Publication Name",
  "url":"https://publication-homepage.com"
}]}"""

# Each section: (section_id, prompt, tag_map)
NEWS_SECTIONS = [
    (
        "auto-news",
        f"""You are a senior automotive journalist, India, {TODAY}.
Give the TOP 5 most important news stories in India's automotive sector today —
ICE vehicles, EVs (2W/3W/4W), hydrogen, safety, exports.
Sources: ET Auto, Autocar India, Autocar Professional, Business Standard Auto.
{NEWS_FORMAT}""",
        {"ICE":"ice","EV":"ev","Hydrogen":"h2","2W":"ice","4W":"ice",
         "CV":"ice","Policy":"policy","Safety":"ice","Export":"inv"}
    ),
    (
        "energy-news",
        f"""You are a senior energy analyst, India, {TODAY}.
Give the TOP 5 most important energy sector news — solar, wind, BESS,
hydrogen, grid, oil & gas. Companies: NTPC, Adani Green, Tata Power,
Waaree, Suzlon, ReNew, Greenko.
Sources: Mercom India, ET Energy, PV Magazine India, Bloomberg NEF.
{NEWS_FORMAT}""",
        {"Solar":"solar","Wind":"wind","BESS":"liion","Hydrogen":"h2",
         "Grid":"gen","Gas":"gen","Coal":"gen","Nuclear":"h2"}
    ),
    (
        "policy-news",
        f"""You are an energy policy analyst, India, {TODAY}.
Give the TOP 5 most important govt policy/scheme stories — MNRE, SECI tenders,
PLI disbursements, PM-KUSUM, FAME III, ISTS, ALMM, NGHM.
Sources: MNRE, PIB, ET Energy, Mercom India.
{NEWS_FORMAT}""",
        {"PLI":"policy","FAME":"policy","SECI":"solar","NHGM":"h2",
         "Tender":"policy","Budget":"policy"}
    ),
    (
        "leadership-news",
        f"""You are a business journalist covering automotive CXO moves, {TODAY}.
Give the TOP 5 most important leadership changes in India and global auto —
CEO, CFO, COO, MD, Board appointments and exits.
Sources: ET Auto, Business Standard, Autocar Professional.
{NEWS_FORMAT}""",
        {"Leadership":"lead","CEO":"lead","Board":"lead"}
    ),
    (
        "investments-news",
        f"""You are an automotive investment analyst, India, {TODAY}.
Give the TOP 5 most important investment/capex/M&A/JV/PLI news in auto sector.
Sources: ET Auto, Reuters, Business Standard, PIB.
{NEWS_FORMAT}""",
        {"Capex":"inv","M&A":"inv","JV":"inv","PLI":"policy",
         "EV Infra":"ev","Global":"inv","Battery":"liion"}
    ),
    (
        "liion-news",
        f"""You are a battery technology analyst, {TODAY}.
Give the TOP 5 most important Li-ion cell market stories — CATL, BYD, LG ES,
India PLI (Exide, Amara Raja), cell pricing LFP vs NMC, solid-state progress.
Sources: BloombergNEF, Reuters, Nikkei Asia, ET.
{NEWS_FORMAT}""",
        {"CATL":"liion","BYD":"liion","LG ES":"liion",
         "India PLI":"policy","Cell Price":"liion","Solid State":"liion"}
    ),
    (
        "trade-news",
        f"""You are a trade policy analyst, India, {TODAY}.
Give the TOP 5 most important import/export policy stories — DGFT,
FTA progress (UAE, UK, EU), PLI exports, anti-dumping duties, RoDTEP.
Sources: DGFT, PIB, ET, Business Standard.
{NEWS_FORMAT}""",
        {"Export":"trade","Import":"trade","FTA":"trade",
         "Tariff":"trade","DGFT":"policy","Anti-dumping":"trade"}
    ),
]

TAG_COLORS = {
    "ice":"#1d4ed8","ev":"#15803d","h2":"#6d28d9","lead":"#92400e",
    "inv":"#991b1b","policy":"#155e75","solar":"#854d0e","wind":"#1e40af",
    "liion":"#6d28d9","gen":"#14532d","esg":"#164e63","trade":"#9a3412"
}
TAG_BG = {
    "ice":"#dbeafe","ev":"#dcfce7","h2":"#ede9fe","lead":"#fef3c7",
    "inv":"#fee2e2","policy":"#cffafe","solar":"#fef9c3","wind":"#dbeafe",
    "liion":"#f3e8ff","gen":"#dcfce7","esg":"#cffafe","trade":"#fff7ed"
}

def call_claude(prompt):
    """Call Claude API and return parsed stories list."""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1800,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)["stories"]

def render_story_html(story, index, total, tag_map):
    """Convert a story dict to HTML card."""
    tag_key = tag_map.get(story.get("tag",""), "ice")
    tag_color = TAG_COLORS.get(tag_key, "#1d4ed8")
    tag_bg    = TAG_BG.get(tag_key, "#dbeafe")
    url       = story.get("url","")
    
    summary_lines = "".join(
        f'<div class="n-summary-line"><span class="n-dot">›</span>'
        f'<span>{line}</span></div>'
        for line in story.get("summary", [])
    )
    link_html = (
        f'<a class="n-link" href="{url}" target="_blank" '
        f'rel="noopener noreferrer">Read Original ↗</a>'
        if url.startswith("http")
        else f'<span class="n-link" style="opacity:.5;cursor:default">'
             f'Source: {story.get("source","")}</span>'
    )
    
    return f"""
    <div class="news-card" style="animation-delay:{index*0.08}s">
      <div class="news-card-num">STORY {index+1} OF {total} · {TODAY}</div>
      <div class="ntag" style="background:{tag_bg};color:{tag_color}">
        {story.get("tag","")}
      </div>
      <div class="n-headline">{story.get("headline","")}</div>
      <div class="n-summary">{summary_lines}</div>
      <div class="n-foot">
        <span class="n-src">📰 {story.get("source","")}</span>
        {link_html}
      </div>
    </div>"""

def inject_news_into_html(html, section_id, stories, tag_map):
    """
    Replace the placeholder div content for a given section.
    Looks for:  <div id="cont-{section_id}">...</div>
    and replaces the inner content with generated news cards.
    """
    cards_html = '<div class="news-grid">' + "".join(
        render_story_html(s, i, len(stories), tag_map)
        for i, s in enumerate(stories)
    ) + "</div>"
    
    # Pattern: find div with id="cont-{section_id}" and replace its content
    pattern = rf'(<div id="cont-{re.escape(section_id)}">)(.*?)(</div>)'
    replacement = rf'\g<1>{cards_html}\g<3>'
    updated = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    if updated == html:
        print(f"  ⚠  Could not find container: cont-{section_id}")
    return updated

def update_date_in_html(html):
    """Update the TODAY const in the JS so it shows correct date."""
    return re.sub(
        r"const TODAY = '[^']*';",
        f"const TODAY = '{TODAY}';",
        html
    )

def main():
    print(f"\n╔══════════════════════════════════════╗")
    print(f"║  IndSight News Updater · {TODAY}  ║")
    print(f"╚══════════════════════════════════════╝\n")
    
    if not client.api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not set.")
        print("   Set it in the script or via environment variable.")
        return
    
    # Read HTML file
    if not os.path.exists(HTML_FILE):
        print(f"❌ ERROR: {HTML_FILE} not found in current directory.")
        print(f"   Make sure you run this script in the same folder as your HTML file.")
        return
    
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Update date
    html = update_date_in_html(html)
    print(f"✅ Date updated to {TODAY}\n")
    
    # Generate and inject each news section
    for section_id, prompt, tag_map in NEWS_SECTIONS:
        print(f"📰 Generating: {section_id}...")
        try:
            stories = call_claude(prompt)
            html = inject_news_into_html(html, section_id, stories, tag_map)
            print(f"   ✅ {len(stories)} stories injected into cont-{section_id}")
        except Exception as e:
            print(f"   ⚠  Failed: {e}")
    
    # Save updated HTML
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ Saved: {HTML_FILE}")
    
    # Optional: auto-push to GitHub
    if AUTO_GIT_PUSH:
        print("\n🚀 Pushing to GitHub...")
        os.system(f'git add {HTML_FILE}')
        os.system(f'git commit -m "Daily news update: {TODAY}"')
        os.system('git push origin main')
        print("✅ Pushed! Site will update in ~1 minute.")
    else:
        print("\n📋 NEXT STEPS:")
        print(f"   1. Open GitHub Desktop (or terminal)")
        print(f"   2. Commit the updated {HTML_FILE}")
        print(f"   3. Push to GitHub")
        print(f"   4. Site updates in ~1 minute at your GitHub Pages URL")
    
    print("\n✅ Done! IndSight updated with today's news.\n")

if __name__ == "__main__":
    main()
