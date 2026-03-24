#!/usr/bin/env python3
"""
IndSight Daily News Updater — Google Gemini API (FREE)
Fixed: Uses gemini-1.5-flash — verified working, fast, free tier
"""

import os, re, json, time
from datetime import datetime

GEMINI_API_KEY = ""        # leave blank — reads from GitHub Secret automatically
HTML_FILE      = "index.html"
AUTO_GIT_PUSH  = True
TODAY          = datetime.now().strftime("%d %B %Y")

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Run: pip install google-generativeai")
    exit(1)

api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("❌ No GEMINI_API_KEY found. Add it as a GitHub Secret.")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")  # verified working free model

NEWS_FORMAT = """Return ONLY valid JSON, no markdown fences, no explanation:
{"stories":[{"tag":"TAG","headline":"Real headline with company + specific number","summary":["What happened: specific real event","Why it happened: cause or context","Key number: exact reported figure","India impact: effect on market","What to watch: next development"],"source":"Publication Name","url":"https://publication.com"}]}
Exactly 5 real stories from last 30 days. JSON only."""

SECTIONS = [
  ("auto-news",
   f"Senior automotive journalist India {TODAY}. TOP 5 real auto news today — ICE, EV (2W/3W/4W), hydrogen, safety, exports. Companies: Maruti, Tata, M&M, Hero, Bajaj, TVS, Ola Electric, Ather. Sources: ET Auto, Autocar India, Autocar Professional. {NEWS_FORMAT}",
   {"ICE":"#1d4ed8","EV":"#15803d","Hydrogen":"#6d28d9","2W":"#1d4ed8","4W":"#1d4ed8","CV":"#1d4ed8","Policy":"#155e75","Safety":"#1d4ed8","Export":"#991b1b"}),

  ("energy-news",
   f"Senior energy analyst India {TODAY}. TOP 5 real energy news today — solar, wind, BESS, hydrogen, grid, oil & gas. Companies: NTPC, Adani Green, Tata Power, Waaree, Suzlon, ReNew. Sources: Mercom India, ET Energy, PV Magazine India. {NEWS_FORMAT}",
   {"Solar":"#854d0e","Wind":"#1e40af","BESS":"#6d28d9","Hydrogen":"#6d28d9","Grid":"#14532d","Gas":"#14532d","Coal":"#92400e"}),

  ("policy-news",
   f"Energy policy analyst India {TODAY}. TOP 5 real policy news today — SECI tenders, PLI solar/batteries, PM-KUSUM, FAME III, ALMM, NGHM. Sources: MNRE, PIB, ET Energy, Mercom India. {NEWS_FORMAT}",
   {"PLI":"#155e75","FAME":"#155e75","SECI":"#854d0e","NHGM":"#6d28d9","Tender":"#155e75","Budget":"#155e75"}),

  ("leadership-news",
   f"Business journalist automotive CXO moves {TODAY}. TOP 5 real leadership changes — CEO, CFO, COO, MD, Board at India + global auto OEMs and Tier-1 suppliers. Sources: ET Auto, Business Standard, Autocar Professional. {NEWS_FORMAT}",
   {"Leadership":"#92400e","CEO":"#92400e","Board":"#92400e","Appointment":"#92400e","Exit":"#92400e"}),

  ("investments-news",
   f"Auto investment analyst India {TODAY}. TOP 5 real investment/capex/M&A/JV/PLI news — plant expansions, EV charging deals, battery investments. Sources: ET Auto, Reuters, PIB, Bloomberg. {NEWS_FORMAT}",
   {"Capex":"#991b1b","M&A":"#991b1b","JV":"#991b1b","PLI":"#155e75","EV Infra":"#15803d","Global":"#991b1b"}),

  ("liion-news",
   f"Battery technology analyst {TODAY}. TOP 5 real Li-ion news — CATL, BYD, LG ES, Samsung SDI; India PLI (Exide, Amara Raja); cell pricing LFP vs NMC; solid-state progress. Sources: BloombergNEF, Reuters, Nikkei Asia, ET. {NEWS_FORMAT}",
   {"CATL":"#6d28d9","BYD":"#6d28d9","LG ES":"#6d28d9","India PLI":"#155e75","Cell Price":"#6d28d9","Solid State":"#6d28d9"}),

  ("trade-news",
   f"Trade policy analyst India {TODAY}. TOP 5 real import/export policy news — DGFT notifications, FTA progress (UAE, UK, EU), anti-dumping duties, RoDTEP, rupee impact. Sources: DGFT, PIB, ET, Business Standard. {NEWS_FORMAT}",
   {"Export":"#9a3412","Import":"#9a3412","FTA":"#9a3412","Tariff":"#9a3412","DGFT":"#155e75","Anti-dumping":"#9a3412"}),
]

TAG_BG = {
    "#1d4ed8":"#dbeafe","#15803d":"#dcfce7","#6d28d9":"#ede9fe",
    "#92400e":"#fef3c7","#991b1b":"#fee2e2","#155e75":"#cffafe",
    "#854d0e":"#fef9c3","#1e40af":"#dbeafe","#14532d":"#dcfce7","#9a3412":"#fff7ed"
}

def call_gemini(prompt, retries=2):
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            raw = re.sub(r"```json|```", "", response.text.strip()).strip()
            return json.loads(raw).get("stories", [])
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 30 * (attempt + 1)
                print(f"   ⏳ Rate limit — waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"   ❌ Error: {e}")
                if attempt == retries - 1:
                    return []
    return []

def render_card(s, i, total, tag_map):
    tag    = s.get("tag", "")
    color  = tag_map.get(tag, "#1d4ed8")
    bg     = TAG_BG.get(color, "#dbeafe")
    url    = s.get("url", "")
    source = s.get("source", "")
    lines  = "".join(
        f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>'
        for l in s.get("summary", [])
    )
    link = (
        f'<a class="n-link" href="{url}" target="_blank" rel="noopener">Read Original ↗</a>'
        if url.startswith("http")
        else f'<a class="n-link" href="https://www.google.com/search?q={s.get("headline","").replace(" ","+")}" target="_blank" rel="noopener">Search Story ↗</a>'
    )
    return (
        f'<div class="news-card" style="animation-delay:{i*0.08}s">'
        f'<div class="news-card-num">STORY {i+1} OF {total} · {TODAY}</div>'
        f'<div class="ntag" style="background:{bg};color:{color}">{tag}</div>'
        f'<div class="n-headline">{s.get("headline","")}</div>'
        f'<div class="n-summary">{lines}</div>'
        f'<div class="n-foot"><span class="n-src">📰 {source}</span>{link}</div>'
        f'<div class="n-disclaimer">⚠ AI-generated summary — always verify at original source</div>'
        f'</div>'
    )

def inject(html, cid, stories, tag_map):
    if not stories:
        return html
    banner = (
        f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
        f'padding:10px 16px;margin-bottom:16px;font-family:Calibri,sans-serif;'
        f'font-size:13px;color:#14532d;font-weight:600">'
        f'✅ <strong>{len(stories)} stories generated</strong> · {TODAY} · '
        f'Click Read Original to verify each story</div>'
    )
    cards = banner + '<div class="news-grid">' + "".join(
        render_card(s, i, len(stories), tag_map)
        for i, s in enumerate(stories)
    ) + "</div>"

    new_html = re.sub(
        rf'(<div id="cont-{re.escape(cid)}">)(.*?)(</div>)',
        rf'\g<1>{cards}\g<3>',
        html, flags=re.DOTALL
    )
    if new_html == html:
        print(f"   ⚠  Container not found: cont-{cid}")
    return new_html

def main():
    print(f"\n{'═'*52}")
    print(f"  IndSight · Gemini News Updater · {TODAY}")
    print(f"{'═'*52}\n")

    if not os.path.exists(HTML_FILE):
        print(f"❌ {HTML_FILE} not found. Run from the same folder.")
        return

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Update date in JS
    html = re.sub(r"const TODAY = '[^']*';", f"const TODAY = '{TODAY}';", html)
    print(f"✅ Date updated to {TODAY}\n")

    total = 0
    for cid, prompt, tag_map in SECTIONS:
        name = cid.replace("-news","").replace("-"," ").title()
        print(f"📰 [{name}] Calling Gemini...")
        stories = call_gemini(prompt)
        if stories:
            html = inject(html, cid, stories, tag_map)
            total += len(stories)
            print(f"   ✅ {len(stories)} stories injected")
        else:
            print(f"   ⚠  No stories returned — section unchanged")
        time.sleep(2)  # small polite delay between calls

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ Saved {HTML_FILE} — {total} total stories across {len(SECTIONS)} sections")

    if AUTO_GIT_PUSH:
        print("\n🚀 Pushing to GitHub...")
        os.system(f'git add {HTML_FILE}')
        code = os.system(f'git commit -m "Daily news update: {TODAY}" && git push origin main')
        if code == 0:
            print("✅ Pushed! Site updates in ~1 minute.")
        else:
            print("⚠  Git push failed — check git config.")

    print(f"\n{'═'*52}")
    print(f"  Done! {total} stories · {len(SECTIONS)} sections updated")
    print(f"{'═'*52}\n")

if __name__ == "__main__":
    main()
