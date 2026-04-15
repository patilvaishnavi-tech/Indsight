#!/usr/bin/env python3
# IndSight News Updater v7 — FIXED
# Uses gemini-2.0-flash (still works until June 2026, no thinking mode issues)
import os, re, json, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime

KEY   = os.environ.get("GEMINI_API_KEY","")
FILE  = "index.html"
MODEL = "gemini-2.0-flash-001"  # stable, no thinking mode, confirmed free
TODAY = datetime.now().strftime("%d %B %Y")

if not KEY: print("❌ GEMINI_API_KEY not set"); exit(1)
print(f"✅ Key:{KEY[:8]}... Model:{MODEL} Date:{TODAY}")

FMT = '{"stories":[{"tag":"EV","headline":"headline text","summary":["s1","s2","s3","s4","s5"],"source":"source name"}]}'

SECTIONS = [
  ("anews",     f"India auto news {TODAY}. 5 stories. ET Auto/Autocar India sources. OEM/EV/ICE topics. JSON:{FMT}",
   {"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("enews",     f"India energy news {TODAY}. 5 stories. Reuters/ET Energy sources. Solar/wind/grid topics. JSON:{FMT}",
   {"Solar":"#854d0e","Wind":"#1e40af","Battery":"#6d28d9","Policy":"#155e75","Grid":"#14532d","Hydrogen":"#6d28d9","EV":"#15803d"}),
  ("policy",    f"India energy policy news {TODAY}. 5 stories. PIB/ET Energy sources. SECI/PLI/FAME topics. JSON:{FMT}",
   {"Policy":"#155e75","Solar":"#854d0e","Battery":"#6d28d9","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Charging":"#854d0e"}),
  ("lead",      f"Auto leadership changes {TODAY}. 5 stories. ET Auto/Business Standard. CEO/MD/Board. JSON:{FMT}",
   {"OEM":"#334155","EV":"#15803d","ICE":"#1d4ed8","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("inv",       f"India auto investment news {TODAY}. 5 stories. ET Auto/Reuters. Plant/EV/JV deals. JSON:{FMT}",
   {"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("liionnews", f"Li-ion battery news {TODAY}. 5 stories. Reuters/ET. CATL/BYD/India PLI. JSON:{FMT}",
   {"Battery":"#6d28d9","Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("tradenews", f"India trade policy news {TODAY}. 5 stories. DGFT/PIB/ET. FTA/anti-dumping/RoDTEP. JSON:{FMT}",
   {"Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Charging":"#854d0e","Commodity":"#9a3412"}),
]

BG = {"#15803d":"#dcfce7","#1d4ed8":"#dbeafe","#334155":"#f1f5f9","#6d28d9":"#ede9fe",
      "#155e75":"#cffafe","#854d0e":"#fef9c3","#9a3412":"#fff7ed","#1e40af":"#dbeafe","#14532d":"#dcfce7"}

def ask(prompt):
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    # No thinkingConfig — not supported on 2.0-flash, causes hangs on 2.5-flash
    body = json.dumps({
        "contents":[{"parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.1,"maxOutputTokens":1500}
    }).encode()
    for attempt in range(2):
        try:
            req = urllib.request.Request(url,data=body,
                  headers={"Content-Type":"application/json"},method="POST")
            with urllib.request.urlopen(req,timeout=30) as r:
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
                print("  ⏳ Rate limit — waiting 30s")
                time.sleep(30)
            else:
                return []
        except Exception as e:
            print(f"  Error: {e}")
            if attempt==0: time.sleep(5)
    return []

def card(s,i,tot,tm):
    tag=s.get("tag","OEM"); col=tm.get(tag,"#334155"); bg=BG.get(col,"#f1f5f9")
    src=s.get("source",""); head=s.get("headline","")
    lines="".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>'
                  for l in s.get("summary",[]))
    q=urllib.parse.quote_plus(head+" "+src+" India 2026")
    link=f'https://news.google.com/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
    return (f'<div class="news-card" style="animation-delay:{i*.08}s">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
            f'<div class="news-card-num">STORY {i+1}/{tot} · {TODAY}</div>'
            f'<div style="font-size:9px;color:#94a3b8;font-weight:600;font-family:Calibri,sans-serif">Source: {src}</div></div>'
            f'<div style="display:inline-flex;background:{bg};color:{col};font-size:10px;font-weight:800;'
            f'letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-bottom:10px;'
            f'font-family:Calibri,sans-serif">{tag}</div>'
            f'<div class="n-headline">{head}</div>'
            f'<div class="n-summary">{lines}</div>'
            f'<div class="n-foot"><span class="n-src">📰 {src}</span>'
            f'<a class="n-link" href="{link}" target="_blank" rel="noopener">Find Original Article ↗</a></div>'
            f'<div class="n-disclaimer">⚠ AI summary — click above to find & verify the original</div></div>')

def inject(html,cid,stories,tm):
    if not stories: return html
    banner=(f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:10px 16px;'
            f'margin-bottom:16px;font-family:Calibri,sans-serif;font-size:13px;color:#14532d;font-weight:600">'
            f'✅ <strong>{len(stories)} stories</strong> · {TODAY} · Click "Find Original Article" to verify</div>')
    cards=banner+'<div class="news-grid">'+"".join(card(s,i,len(stories),tm) for i,s in enumerate(stories))+"</div>"
    start=f'<div id="cont-{cid}">'
    if start not in html: print(f"  ⚠ cont-{cid} not found"); return html
    sp=html.find(start)+len(start); d=1; pos=sp; ep=sp
    while pos<len(html) and d>0:
        no=html.find('<div',pos); nc=html.find('</div>',pos)
        if nc==-1: break
        if no!=-1 and no<nc: d+=1; pos=no+4
        else:
            d-=1
            if d==0: ep=nc
            pos=nc+6
    print(f"  ✅ Injected → cont-{cid}")
    return html[:sp]+cards+html[ep:]

# ── MAIN ──────────────────────────────────────────────
print(f"\n{'='*48}\n  IndSight · {TODAY}\n{'='*48}\n")
print(f"Dir:{os.getcwd()} | Files:{[f for f in os.listdir('.') if f.endswith('.html')]}")

if not os.path.exists(FILE): print(f"❌ {FILE} not found"); exit(1)

html=open(FILE,encoding='utf-8').read()
html=re.sub(r"const TODAY = [^;]+;",f"const TODAY = '{TODAY}';",html)
print(f"✅ Date: {TODAY}\n")

total=0
for cid,prompt,tm in SECTIONS:
    print(f"📰 [{cid}]...")
    s=ask(prompt)
    if s: html=inject(html,cid,s,tm); total+=len(s)
    else: print(f"  ⚠ skipped")
    time.sleep(3)  # 3s gap = well within 60 RPM free limit for 2.0-flash

open(FILE,'w',encoding='utf-8').write(html)
print(f"\n✅ Saved — {total} stories")

os.system(f'git add {FILE}')
rc=os.system(f'git commit -m "News:{TODAY}" && git push origin main')
print("✅ Pushed" if rc==0 else "⚠ Push failed")
print(f"\n{'='*48}\n  Done! {total} stories.\n{'='*48}\n")
