#!/usr/bin/env python3
"""
IndSight Daily News Updater — Google Gemini (FREE)
FULLY FIXED: correct IDs, correct regex, correct library
"""
import os, re, json, time
from datetime import datetime

GEMINI_API_KEY = ""
HTML_FILE      = "index.html"
AUTO_GIT_PUSH  = True
TODAY          = datetime.now().strftime("%d %B %Y")

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Run: pip install google-generativeai"); exit(1)

api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY","")
if not api_key:
    print("❌ No GEMINI_API_KEY found."); exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

NEWS_FORMAT = """Return ONLY valid JSON, no markdown:
{"stories":[{"tag":"TAG","headline":"Real headline with company + number","summary":["What happened","Why it happened","Key number","India impact","What to watch"],"source":"Publication","url":"https://publication.com"}]}
Exactly 5 real recent stories. JSON only."""

# EXACT container IDs from the HTML file
SECTIONS = [
  ("anews",      f"Auto journalist India {TODAY}. TOP 5 real auto news — EV, ICE, hydrogen. Companies: Maruti, Tata, M&M, Hero, Bajaj, TVS, Ola Electric, Ather. {NEWS_FORMAT}", {"ICE":"#1d4ed8","EV":"#15803d","Hydrogen":"#6d28d9","Policy":"#155e75","Safety":"#1d4ed8","Export":"#991b1b"}),
  ("enews",      f"Energy analyst India {TODAY}. TOP 5 real energy news — solar, wind, BESS, grid. Companies: NTPC, Adani Green, Tata Power, Waaree, Suzlon. {NEWS_FORMAT}", {"Solar":"#854d0e","Wind":"#1e40af","BESS":"#6d28d9","Hydrogen":"#6d28d9","Grid":"#14532d"}),
  ("policy",     f"Policy analyst India {TODAY}. TOP 5 real govt policy news — SECI tenders, PLI, PM-KUSUM, FAME III, ALMM. {NEWS_FORMAT}", {"PLI":"#155e75","FAME":"#155e75","SECI":"#854d0e","Tender":"#155e75","Budget":"#155e75"}),
  ("lead",       f"Business journalist {TODAY}. TOP 5 real auto leadership changes — CEO, CFO, MD, Board. {NEWS_FORMAT}", {"Leadership":"#92400e","CEO":"#92400e","Board":"#92400e"}),
  ("inv",        f"Investment analyst India {TODAY}. TOP 5 real auto investment/M&A/JV/PLI news. {NEWS_FORMAT}", {"Capex":"#991b1b","M&A":"#991b1b","JV":"#991b1b","PLI":"#155e75"}),
  ("liionnews",  f"Battery analyst {TODAY}. TOP 5 real Li-ion news — CATL, BYD, LG ES, India PLI, cell pricing. {NEWS_FORMAT}", {"CATL":"#6d28d9","BYD":"#6d28d9","India PLI":"#155e75","Cell Price":"#6d28d9"}),
  ("tradenews",  f"Trade analyst India {TODAY}. TOP 5 real import/export policy news — DGFT, FTA, anti-dumping, RoDTEP. {NEWS_FORMAT}", {"Export":"#9a3412","Import":"#9a3412","FTA":"#9a3412","DGFT":"#155e75"}),
]

TAG_BG = {
    "#1d4ed8":"#dbeafe","#15803d":"#dcfce7","#6d28d9":"#ede9fe",
    "#92400e":"#fef3c7","#991b1b":"#fee2e2","#155e75":"#cffafe",
    "#854d0e":"#fef9c3","#1e40af":"#dbeafe","#14532d":"#dcfce7","#9a3412":"#fff7ed"
}

def call_gemini(prompt):
    for attempt in range(3):
        try:
            r = model.generate_content(prompt)
            raw = re.sub(r"```json|```","",r.text.strip()).strip()
            return json.loads(raw).get("stories",[])
        except Exception as e:
            print(f"   ⚠ Attempt {attempt+1} failed: {e}")
            time.sleep(20)
    return []

def render_card(s, i, total, tag_map):
    tag   = s.get("tag","NEWS")
    color = tag_map.get(tag,"#1d4ed8")
    bg    = TAG_BG.get(color,"#dbeafe")
    url   = s.get("url","")
    src   = s.get("source","")
    lines = "".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>' for l in s.get("summary",[]))
    link  = f'<a class="n-link" href="{url}" target="_blank" rel="noopener">Read Original ↗</a>' if url.startswith("http") else f'<a class="n-link" href="https://www.google.com/search?q={s.get("headline","").replace(" ","+")}" target="_blank">Search ↗</a>'
    return (f'<div class="news-card" style="animation-delay:{i*0.08}s">'
            f'<div class="news-card-num">STORY {i+1} OF {total} · {TODAY}</div>'
            f'<div class="ntag" style="background:{bg};color:{color}">{tag}</div>'
            f'<div class="n-headline">{s.get("headline","")}</div>'
            f'<div class="n-summary">{lines}</div>'
            f'<div class="n-foot"><span class="n-src">📰 {src}</span>{link}</div>'
            f'<div class="n-disclaimer">⚠ AI summary — verify at original source</div>'
            f'</div>')

def inject(html, cid, stories, tag_map):
    if not stories: return html
    banner = (f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
              f'padding:10px 16px;margin-bottom:16px;font-family:Calibri,sans-serif;'
              f'font-size:13px;color:#14532d;font-weight:600">'
              f'✅ <strong>{len(stories)} stories</strong> · {TODAY}</div>')
    cards  = banner + '<div class="news-grid">' + "".join(render_card(s,i,len(stories),tag_map) for i,s in enumerate(stories)) + "</div>"

    # Replace everything INSIDE the container div
    # Uses a split approach — more reliable than regex for nested HTML
    start_tag = f'<div id="cont-{cid}">'
    if start_tag not in html:
        print(f"   ❌ Container not found: cont-{cid}")
        return html

    # Find the start position
    start_pos = html.find(start_tag) + len(start_tag)
    # Find the matching closing </div> by counting nesting
    depth = 1
    pos   = start_pos
    while pos < len(html) and depth > 0:
        next_open  = html.find('<div', pos)
        next_close = html.find('</div>', pos)
        if next_close == -1: break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                end_pos = next_close
            pos = next_close + 6

    new_html = html[:start_pos] + cards + html[end_pos:]
    print(f"   ✅ Injected {len(stories)} stories into cont-{cid}")
    return new_html

def main():
    print(f"\n{'═'*50}\n  IndSight · {TODAY}\n{'═'*50}\n")

    if not os.path.exists(HTML_FILE):
        print(f"❌ {HTML_FILE} not found"); return

    with open(HTML_FILE,"r",encoding="utf-8") as f:
        html = f.read()

    # Update TODAY const in JS
    html = re.sub(r"const TODAY = [^;]+;", f"const TODAY = '{TODAY}';", html)
    print(f"✅ Date updated to {TODAY}\n")

    total = 0
    for cid, prompt, tag_map in SECTIONS:
        print(f"📰 [{cid}] Calling Gemini...")
        stories = call_gemini(prompt)
        if stories:
            html = inject(html, cid, stories, tag_map)
            total += len(stories)
        else:
            print(f"   ⚠ No stories returned")
        time.sleep(3)

    with open(HTML_FILE,"w",encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ Saved — {total} stories injected")

    if AUTO_GIT_PUSH:
        print("\n🚀 Pushing to GitHub...")
        os.system(f'git add {HTML_FILE}')
        code = os.system(f'git commit -m "Daily news: {TODAY}" && git push origin main')
        print("✅ Site updated!" if code==0 else "⚠ Push failed")

    print(f"\n{'═'*50}\n  Done! {total} stories.\n{'═'*50}\n")

if __name__=="__main__":
    main()
