#!/usr/bin/env python3
# IndSight News Updater v5 — Pure Python, zero dependencies
# Uses gemini-2.5-flash (free tier, confirmed working April 2026)
import os, re, json, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime

KEY   = os.environ.get("GEMINI_API_KEY","")
FILE  = "index.html"
MODEL = "gemini-2.5-flash-preview-04-17"   # confirmed free April 2026
TODAY = datetime.now().strftime("%d %B %Y")

if not KEY: print("❌ GEMINI_API_KEY not set"); exit(1)
print(f"✅ Key: {KEY[:8]}... | {MODEL} | {TODAY}")

FMT = '{"stories":[{"tag":"EV","headline":"real headline","summary":["s1","s2","s3","s4","s5"],"source":"publication"}]}'

SECTIONS = [
  ("anews",     f"5 real India auto news stories as of {TODAY}. ET Auto/Autocar India sources. OEM, EV, sales topics. Return only JSON: {FMT}",
   {"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("enews",     f"5 real India energy news stories as of {TODAY}. Reuters/ET Energy sources. Solar, wind, grid topics. Return only JSON: {FMT}",
   {"Solar":"#854d0e","Wind":"#1e40af","Battery":"#6d28d9","Policy":"#155e75","Grid":"#14532d","Hydrogen":"#6d28d9","EV":"#15803d"}),
  ("policy",    f"5 real India energy policy news stories as of {TODAY}. MNRE/PIB/ET Energy sources. SECI tenders, PLI, FAME III. Return only JSON: {FMT}",
   {"Policy":"#155e75","Solar":"#854d0e","Battery":"#6d28d9","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Charging":"#854d0e"}),
  ("lead",      f"5 real auto leadership changes as of {TODAY}. ET Auto/Business Standard sources. CEO/MD/Board moves. Return only JSON: {FMT}",
   {"OEM":"#334155","EV":"#15803d","ICE":"#1d4ed8","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("inv",       f"5 real India auto investment news stories as of {TODAY}. ET Auto/Reuters sources. Plant expansions, EV deals. Return only JSON: {FMT}",
   {"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("liionnews", f"5 real Li-ion battery news stories as of {TODAY}. Reuters/BloombergNEF/ET sources. CATL, BYD, India PLI. Return only JSON: {FMT}",
   {"Battery":"#6d28d9","Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("tradenews", f"5 real India trade policy news stories as of {TODAY}. DGFT/PIB/ET sources. FTA, anti-dumping, RoDTEP. Return only JSON: {FMT}",
   {"Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Charging":"#854d0e","Commodity":"#9a3412"}),
]

BG = {"#15803d":"#dcfce7","#1d4ed8":"#dbeafe","#334155":"#f1f5f9","#6d28d9":"#ede9fe",
      "#155e75":"#cffafe","#854d0e":"#fef9c3","#9a3412":"#fff7ed","#1e40af":"#dbeafe","#14532d":"#dcfce7"}

def ask(prompt):
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    body = json.dumps({
        "contents":[{"parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.1,"maxOutputTokens":2000}
    }).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"},method="POST")
            with urllib.request.urlopen(req,timeout=45) as r:
                d = json.loads(r.read())
            txt = d["candidates"][0]["content"]["parts"][0]["text"]
            txt = re.sub(r"```json|```","",txt).strip()
            m = re.search(r'\{.*\}',txt,re.DOTALL)
            result = json.loads(m.group() if m else txt)
            stories = result.get("stories",[])
            print(f"  ✅ {len(stories)} stories")
            return stories
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:200]
            print(f"  HTTP {e.code}: {err}")
            if e.code == 429:
                print(f"  Rate limit — waiting 45s...")
                time.sleep(45)
            elif e.code == 503:
                print(f"  Service unavailable — waiting 20s...")
                time.sleep(20)
            else:
                print(f"  Fatal HTTP error — skipping")
                return []
        except Exception as e:
            print(f"  Error attempt {attempt+1}: {e}")
            if attempt < 2: time.sleep(10)
    return []

def make_card(s,i,tot,tm):
    tag  = s.get("tag","OEM")
    col  = tm.get(tag,"#334155")
    bg   = BG.get(col,"#f1f5f9")
    src  = s.get("source","")
    head = s.get("headline","")
    lines= "".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>' for l in s.get("summary",[]))
    q    = urllib.parse.quote_plus(head+" "+src)
    link = f'https://news.google.com/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
    return (f'<div class="news-card" style="animation-delay:{i*.08}s">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
            f'<div class="news-card-num">STORY {i+1}/{tot} · {TODAY}</div>'
            f'<div style="font-size:9px;color:#94a3b8;font-weight:600;font-family:Calibri,sans-serif">Source: {src}</div></div>'
            f'<div style="display:inline-flex;background:{bg};color:{col};font-size:10px;font-weight:800;'
            f'letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-bottom:10px;font-family:Calibri,sans-serif">{tag}</div>'
            f'<div class="n-headline">{head}</div>'
            f'<div class="n-summary">{lines}</div>'
            f'<div class="n-foot"><span class="n-src">📰 {src}</span>'
            f'<a class="n-link" href="{link}" target="_blank" rel="noopener">Search Google News ↗</a></div>'
            f'<div class="n-disclaimer">⚠ AI summary — click Search Google News to verify</div></div>')

def inject(html,cid,stories,tm):
    if not stories: return html
    banner = (f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
              f'padding:10px 16px;margin-bottom:16px;font-family:Calibri,sans-serif;'
              f'font-size:13px;color:#14532d;font-weight:600">'
              f'✅ <strong>{len(stories)} stories</strong> · {TODAY} · Click "Search Google News" to verify</div>')
    cards = banner+'<div class="news-grid">'+"".join(make_card(s,i,len(stories),tm) for i,s in enumerate(stories))+"</div>"
    start = f'<div id="cont-{cid}">'
    if start not in html:
        print(f"  ⚠ Container not found: cont-{cid}"); return html
    sp = html.find(start)+len(start)
    d=1; pos=sp; ep=sp
    while pos<len(html) and d>0:
        no=html.find('<div',pos); nc=html.find('</div>',pos)
        if nc==-1: break
        if no!=-1 and no<nc: d+=1; pos=no+4
        else:
            d-=1
            if d==0: ep=nc
            pos=nc+6
    print(f"  ✅ Injected into cont-{cid}")
    return html[:sp]+cards+html[ep:]

# ── MAIN ────────────────────────────────────────────────
print(f"\n{'='*50}\n  IndSight News Update · {TODAY}\n{'='*50}\n")

if not os.path.exists(FILE):
    print(f"❌ {FILE} not found in {os.getcwd()}"); exit(1)

html = open(FILE,encoding='utf-8').read()
# Update TODAY constant in JS
html = re.sub(r"const TODAY = [^;]+;",f"const TODAY = '{TODAY}';",html)
print(f"✅ Date set: {TODAY}\n")

total = 0
for cid, prompt, tm in SECTIONS:
    print(f"📰 [{cid}]...")
    stories = ask(prompt)
    if stories:
        html = inject(html,cid,stories,tm)
        total += len(stories)
    else:
        print(f"  ⚠ No stories — section unchanged")
    time.sleep(5)   # polite delay between calls

open(FILE,'w',encoding='utf-8').write(html)
print(f"\n✅ Saved {FILE} — {total} stories total")

print("\n🚀 Pushing to GitHub...")
os.system(f'git add {FILE}')
rc = os.system(f'git commit -m "News: {TODAY}" && git push origin main')
print("✅ Pushed!" if rc==0 else "⚠ Git push failed")
print(f"\n{'='*50}\n  Done! {total} stories.\n{'='*50}\n")
