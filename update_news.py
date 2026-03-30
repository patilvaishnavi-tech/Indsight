#!/usr/bin/env python3
"""
IndSight Daily News Updater — Google Gemini 2.5 Flash-Lite (FREE)
Correct model: gemini-2.5-flash-lite — 1,000 req/day free, March 2026
No external libraries needed — uses Python built-in urllib only
"""
import os, re, json, time, urllib.request, urllib.error
from datetime import datetime

GEMINI_API_KEY = ""
HTML_FILE      = "index.html"
AUTO_GIT_PUSH  = True
TODAY          = datetime.now().strftime("%d %B %Y")
MODEL          = "gemini-2.5-flash-lite"   # ✅ verified free model March 2026

api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY","")
if not api_key:
    print("❌ No GEMINI_API_KEY found."); exit(1)

print(f"✅ Using model: {MODEL}")
print(f"✅ API key found: {api_key[:8]}...")

NEWS_FORMAT = """Return ONLY valid JSON, no markdown:
{"stories":[{"tag":"TAG","headline":"Real headline with company + number","summary":["What happened","Why it happened","Key number","India impact","What to watch"],"source":"Publication","url":"https://publication.com"}]}
Exactly 5 real recent stories. JSON only."""

SECTIONS = [
  ("anews",     f"Auto journalist India {TODAY}. TOP 5 real auto news — EV, ICE, hydrogen. Companies: Maruti, Tata, M&M, Hero, Bajaj, TVS, Ola Electric, Ather. {NEWS_FORMAT}", {"ICE":"#1d4ed8","EV":"#15803d","Hydrogen":"#6d28d9","Policy":"#155e75","Safety":"#1d4ed8","Export":"#991b1b"}),
  ("enews",     f"Energy analyst India {TODAY}. TOP 5 real energy news — solar, wind, BESS, grid. NTPC, Adani Green, Tata Power, Waaree, Suzlon. {NEWS_FORMAT}", {"Solar":"#854d0e","Wind":"#1e40af","BESS":"#6d28d9","Hydrogen":"#6d28d9","Grid":"#14532d"}),
  ("policy",    f"Policy analyst India {TODAY}. TOP 5 real govt policy news — SECI tenders, PLI, PM-KUSUM, FAME III. {NEWS_FORMAT}", {"PLI":"#155e75","FAME":"#155e75","SECI":"#854d0e","Tender":"#155e75","Budget":"#155e75"}),
  ("lead",      f"Business journalist {TODAY}. TOP 5 real auto leadership changes — CEO, CFO, MD, Board. {NEWS_FORMAT}", {"Leadership":"#92400e","CEO":"#92400e","Board":"#92400e"}),
  ("inv",       f"Investment analyst India {TODAY}. TOP 5 real auto investment/M&A/JV/PLI news. {NEWS_FORMAT}", {"Capex":"#991b1b","M&A":"#991b1b","JV":"#991b1b","PLI":"#155e75"}),
  ("liionnews", f"Battery analyst {TODAY}. TOP 5 real Li-ion news — CATL, BYD, LG ES, India PLI, cell pricing. {NEWS_FORMAT}", {"CATL":"#6d28d9","BYD":"#6d28d9","India PLI":"#155e75","Cell Price":"#6d28d9"}),
  ("tradenews", f"Trade analyst India {TODAY}. TOP 5 real import/export news — DGFT, FTA, anti-dumping. {NEWS_FORMAT}", {"Export":"#9a3412","Import":"#9a3412","FTA":"#9a3412","DGFT":"#155e75"}),
]

TAG_BG = {
    "#1d4ed8":"#dbeafe","#15803d":"#dcfce7","#6d28d9":"#ede9fe",
    "#92400e":"#fef3c7","#991b1b":"#fee2e2","#155e75":"#cffafe",
    "#854d0e":"#fef9c3","#1e40af":"#dbeafe","#14532d":"#dcfce7","#9a3412":"#fff7ed"
}

def call_gemini(prompt):
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    body = json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.3}}).encode()
    req  = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read().decode())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"```json|```","", text).strip()
            result = json.loads(text)
            stories = result.get("stories",[])
            print(f"   ✅ Got {len(stories)} stories")
            return stories
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            print(f"   ⚠ HTTP {e.code}: {err[:300]}")
            if e.code == 429:
                wait = 30*(attempt+1)
                print(f"   ⏳ Rate limit — waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 404:
                print(f"   ❌ Model not found — check model name")
                return []
            else:
                if attempt < 2: time.sleep(10)
        except Exception as e:
            print(f"   ⚠ Error attempt {attempt+1}: {e}")
            if attempt < 2: time.sleep(10)
    return []

def render_card(s, i, total, tag_map):
    tag   = s.get("tag","NEWS")
    color = tag_map.get(tag,"#1d4ed8")
    bg    = TAG_BG.get(color,"#dbeafe")
    url   = s.get("url","")
    src   = s.get("source","")
    lines = "".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>' for l in s.get("summary",[]))
    link  = (f'<a class="n-link" href="https://news.google.com/search?q={urllib.parse.quote_plus(s.get("headline","") + " " + s.get("source",""))}&hl=en-IN" target="_blank" rel="noopener">Search on Google News ↗</a>'
             if url.startswith("http")
             else f'<a class="n-link" href="https://www.google.com/search?q={s.get("headline","").replace(" ","+")}" target="_blank">Search ↗</a>')
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
    cards = banner + '<div class="news-grid">' + "".join(render_card(s,i,len(stories),tag_map) for i,s in enumerate(stories)) + "</div>"
    start_tag = f'<div id="cont-{cid}">'
    if start_tag not in html:
        print(f"   ❌ Container not found: cont-{cid}"); return html
    start_pos = html.find(start_tag) + len(start_tag)
    depth=1; pos=start_pos; end_pos=start_pos
    while pos < len(html) and depth > 0:
        no = html.find('<div', pos)
        nc = html.find('</div>', pos)
        if nc == -1: break
        if no != -1 and no < nc: depth+=1; pos=no+4
        else:
            depth-=1
            if depth==0: end_pos=nc
            pos=nc+6
    return html[:start_pos] + cards + html[end_pos:]

def main():
    print(f"\n{'═'*50}\n  IndSight · Gemini 2.5 Flash-Lite · {TODAY}\n{'═'*50}\n")
    if not os.path.exists(HTML_FILE):
        print(f"❌ {HTML_FILE} not found"); return
    with open(HTML_FILE,"r",encoding="utf-8") as f: html = f.read()
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
            print(f"   ⚠ Skipping {cid}")
        time.sleep(5)
    with open(HTML_FILE,"w",encoding="utf-8") as f: f.write(html)
    print(f"\n✅ Saved — {total} stories injected")
    if AUTO_GIT_PUSH:
        print("\n🚀 Pushing to GitHub...")
        os.system(f'git add {HTML_FILE}')
        code = os.system(f'git commit -m "Daily news: {TODAY}" && git push origin main')
        print("✅ Done!" if code==0 else "⚠ Push failed")
    print(f"\n{'═'*50}\n  Complete! {total} stories.\n{'═'*50}\n")

if __name__=="__main__":
    main()
