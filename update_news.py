#!/usr/bin/env python3
# IndSight News Updater — Pure Python urllib, no pip install needed
import os, re, json, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime

KEY   = os.environ.get("GEMINI_API_KEY","")
FILE  = "index.html"
MODEL = "gemini-2.0-flash"
TODAY = datetime.now().strftime("%d %B %Y")

if not KEY: print("❌ No API key"); exit(1)
print(f"✅ Key OK | Model: {MODEL} | {TODAY}")

FMT = 'JSON only, no markdown: {"stories":[{"tag":"EV","headline":"...","summary":["s1","s2","s3","s4","s5"],"source":"..."}]}'

SECTIONS = [
  ("anews",   f"India auto news {TODAY}. 5 real stories. Sources: ET Auto, Autocar India, Autocar Professional. Topics: OEM, vehicle sales, EV. {FMT}", {"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("enews",   f"India energy news {TODAY}. 5 real stories. Sources: Reuters, ET Energy, FT. Topics: solar, wind, hydrogen, grid. {FMT}", {"Solar":"#854d0e","Wind":"#1e40af","Battery":"#6d28d9","Policy":"#155e75","Grid":"#14532d","Hydrogen":"#6d28d9","EV":"#15803d"}),
  ("policy",  f"India energy policy news {TODAY}. 5 real stories. Sources: MNRE, PIB, ET Energy. Topics: SECI tenders, PLI, FAME III. {FMT}", {"Policy":"#155e75","Solar":"#854d0e","Battery":"#6d28d9","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Charging":"#854d0e"}),
  ("lead",    f"Auto leadership changes {TODAY}. 5 real stories. Sources: ET Auto, Business Standard. Topics: CEO/MD/Board moves. {FMT}", {"OEM":"#334155","EV":"#15803d","ICE":"#1d4ed8","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("inv",     f"India auto investment news {TODAY}. 5 real stories. Sources: ET Auto, Reuters, PIB. Topics: plant expansions, EV deals. {FMT}", {"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("liionnews", f"Li-ion battery news {TODAY}. 5 real stories. Sources: Reuters, BloombergNEF, ET. Topics: CATL, BYD, India PLI batteries. {FMT}", {"Battery":"#6d28d9","Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Charging":"#854d0e","Commodity":"#9a3412"}),
  ("tradenews", f"India trade policy news {TODAY}. 5 real stories. Sources: DGFT, PIB, ET. Topics: FTA, anti-dumping, RoDTEP. {FMT}", {"Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Charging":"#854d0e","Commodity":"#9a3412"}),
]

BG = {"#15803d":"#dcfce7","#1d4ed8":"#dbeafe","#334155":"#f1f5f9","#6d28d9":"#ede9fe",
      "#155e75":"#cffafe","#854d0e":"#fef9c3","#9a3412":"#fff7ed","#1e40af":"#dbeafe","#14532d":"#dcfce7"}

def ask(prompt):
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    body = json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.2,"maxOutputTokens":1500}}).encode()
    req  = urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"},method="POST")
    for n in range(3):
        try:
            with urllib.request.urlopen(req,timeout=25) as r:
                d = json.loads(r.read())
            t = d["candidates"][0]["content"]["parts"][0]["text"]
            t = re.sub(r"```json|```","",t).strip()
            m = re.search(r'\{.*\}',t,re.DOTALL)
            return json.loads(m.group() if m else t).get("stories",[])
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.read().decode()[:100]}")
            if e.code==429: time.sleep(30)
            else: return []
        except Exception as e:
            print(f"  Err: {e}")
            if n<2: time.sleep(8)
    return []

def card(s,i,tot,tm):
    tag=s.get("tag","OEM"); col=tm.get(tag,"#334155"); bg=BG.get(col,"#f1f5f9")
    src=s.get("source",""); head=s.get("headline","")
    lines="".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>' for l in s.get("summary",[]))
    q=urllib.parse.quote_plus(head+" "+src)
    lnk=f'https://news.google.com/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
    return (f'<div class="news-card" style="animation-delay:{i*.08}s">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
            f'<div class="news-card-num">STORY {i+1}/{tot} · {TODAY}</div>'
            f'<div style="font-size:9px;color:#94a3b8;font-weight:600;font-family:Calibri,sans-serif">Source: {src}</div></div>'
            f'<div style="display:inline-flex;background:{bg};color:{col};font-size:10px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-bottom:10px;font-family:Calibri,sans-serif">{tag}</div>'
            f'<div class="n-headline">{head}</div><div class="n-summary">{lines}</div>'
            f'<div class="n-foot"><span class="n-src">📰 {src}</span>'
            f'<a class="n-link" href="{lnk}" target="_blank" rel="noopener">Search Google News ↗</a></div>'
            f'<div class="n-disclaimer">⚠ AI summary — click Search Google News to verify</div></div>')

def inject(html,cid,stories,tm):
    if not stories: return html
    banner=(f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:10px 16px;'
            f'margin-bottom:16px;font-family:Calibri,sans-serif;font-size:13px;color:#14532d;font-weight:600">'
            f'✅ <strong>{len(stories)} stories</strong> · {TODAY} · Click Search Google News to verify</div>')
    body=banner+'<div class="news-grid">'+"".join(card(s,i,len(stories),tm) for i,s in enumerate(stories))+"</div>"
    tag=f'<div id="cont-{cid}">'; 
    if tag not in html: print(f"  ⚠ Not found: cont-{cid}"); return html
    sp=html.find(tag)+len(tag); d=1; pos=sp; ep=sp
    while pos<len(html) and d>0:
        no=html.find('<div',pos); nc=html.find('</div>',pos)
        if nc==-1: break
        if no!=-1 and no<nc: d+=1; pos=no+4
        else:
            d-=1
            if d==0: ep=nc
            pos=nc+6
    print(f"  ✅ cont-{cid}: {len(stories)} stories")
    return html[:sp]+body+html[ep:]

html = open(FILE,encoding='utf-8').read()
html = re.sub(r"const TODAY = [^;]+;",f"const TODAY = '{TODAY}';",html)
print(f"✅ Date set: {TODAY}\n")

total=0
for cid,prompt,tm in SECTIONS:
    print(f"📰 {cid}...")
    s=ask(prompt)
    if s: html=inject(html,cid,s,tm); total+=len(s)
    else: print(f"  ⚠ skipped")
    time.sleep(4)

open(FILE,'w',encoding='utf-8').write(html)
print(f"\n✅ {total} stories saved")
os.system(f'git add {FILE}')
r=os.system(f'git commit -m "News: {TODAY}" && git push origin main')
print("✅ Pushed" if r==0 else "⚠ Push failed")
