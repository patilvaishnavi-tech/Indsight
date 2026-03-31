#!/usr/bin/env python3
"""
IndSight News Updater — Pure Python, no external libraries
Model: gemini-2.0-flash via direct HTTP (works until June 2026)
"""
import os, re, json, time, urllib.request, urllib.error
from datetime import datetime

API_KEY   = os.environ.get("GEMINI_API_KEY", "")
HTML_FILE = "index.html"
MODEL     = "gemini-2.0-flash"
TODAY     = datetime.now().strftime("%d %B %Y")

if not API_KEY:
    print("❌ GEMINI_API_KEY not set"); exit(1)

print(f"✅ Key: {API_KEY[:8]}... | Model: {MODEL} | Date: {TODAY}")

# ── APPROVED SOURCES & STRICT PROMPTS ──────────────────────────
SECTIONS = [
("anews", f"""Auto journalist India {TODAY}. Give 5 UNIQUE real auto news stories.
SOURCES ONLY: ET Auto, Autocar Professional, Autocar India, Mint.
TOPICS: OEM news, vehicle sales, EV adoption (vehicle side only).
NOT: battery manufacturing, energy policy, commodity prices.
Return JSON only: {{"stories":[{{"tag":"EV","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"ET Auto","url":"https://auto.economictimes.com"}}]}}""",
{"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Battery":"#6d28d9","Policy":"#155e75","Charging":"#854d0e","Commodity":"#9a3412"}),

("enews", f"""Energy analyst India {TODAY}. Give 5 UNIQUE real energy news stories.
SOURCES ONLY: Reuters, Financial Times, ET Energy.
TOPICS: solar, wind, hydrogen, battery storage manufacturing, grid.
NOT: vehicle/OEM news, commodity spot prices.
Return JSON only: {{"stories":[{{"tag":"Policy","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"Reuters","url":"https://reuters.com"}}]}}""",
{"Solar":"#854d0e","Wind":"#1e40af","Battery":"#6d28d9","Policy":"#155e75","Grid":"#14532d","Hydrogen":"#6d28d9"}),

("policy", f"""Policy analyst India {TODAY}. Give 5 UNIQUE real govt policy news.
SOURCES ONLY: MNRE, PIB, ET Energy, Mercom India.
TOPICS: SECI tenders, PLI disbursements, PM-KUSUM, FAME III, ALMM, NGHM.
Return JSON only: {{"stories":[{{"tag":"Policy","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"PIB","url":"https://pib.gov.in"}}]}}""",
{"Policy":"#155e75","Solar":"#854d0e","Battery":"#6d28d9"}),

("lead", f"""Business journalist {TODAY}. Give 5 UNIQUE real auto leadership changes.
SOURCES ONLY: ET Auto, Autocar Professional, Business Standard.
TOPICS: CEO/CFO/MD/Board appointments and exits at auto companies.
Return JSON only: {{"stories":[{{"tag":"OEM","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"ET Auto","url":"https://auto.economictimes.com"}}]}}""",
{"OEM":"#334155","EV":"#15803d","ICE":"#1d4ed8"}),

("inv", f"""Investment analyst India {TODAY}. Give 5 UNIQUE real auto investment news.
SOURCES ONLY: ET Auto, Reuters, Business Standard, PIB.
TOPICS: plant expansions, EV charging deals, OEM investments.
Return JSON only: {{"stories":[{{"tag":"EV","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"ET Auto","url":"https://auto.economictimes.com"}}]}}""",
{"EV":"#15803d","ICE":"#1d4ed8","OEM":"#334155","Policy":"#155e75"}),

("liionnews", f"""Battery analyst {TODAY}. Give 5 UNIQUE real Li-ion manufacturing news.
SOURCES ONLY: BloombergNEF, Reuters, Nikkei Asia, ET.
TOPICS: CATL, BYD, LG ES, India PLI batteries, LFP vs NMC trends.
NOT: lithium carbonate spot price.
Return JSON only: {{"stories":[{{"tag":"Battery","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"Reuters","url":"https://reuters.com"}}]}}""",
{"Battery":"#6d28d9","Policy":"#155e75","EV":"#15803d"}),

("tradenews", f"""Trade analyst India {TODAY}. Give 5 UNIQUE real import/export policy news.
SOURCES ONLY: DGFT, PIB, ET, Business Standard.
TOPICS: DGFT notifications, FTA progress, anti-dumping duties, RoDTEP.
Return JSON only: {{"stories":[{{"tag":"Policy","headline":"headline","summary":["line1","line2","line3","line4","line5"],"source":"ET","url":"https://economictimes.com"}}]}}""",
{"Policy":"#155e75","EV":"#15803d","ICE":"#1d4ed8","Commodity":"#9a3412"}),
]

TAG_BG = {"#15803d":"#dcfce7","#1d4ed8":"#dbeafe","#334155":"#f1f5f9",
          "#6d28d9":"#ede9fe","#155e75":"#cffafe","#854d0e":"#fef9c3",
          "#9a3412":"#fff7ed","#1e40af":"#dbeafe","#14532d":"#dcfce7"}

def gemini(prompt):
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    data = json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2000}}).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"```json|```","",text).strip()
            # Extract JSON object
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group()).get("stories",[])
            return json.loads(text).get("stories",[])
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:200]
            print(f"   HTTP {e.code}: {err}")
            if e.code in (429, 503):
                time.sleep(20*(attempt+1))
            else:
                return []
        except Exception as e:
            print(f"   Error: {e}")
            if attempt < 2: time.sleep(10)
    return []

def card(s, i, total, tag_map):
    tag   = s.get("tag","OEM")
    color = tag_map.get(tag, "#334155")
    bg    = TAG_BG.get(color, "#f1f5f9")
    src   = s.get("source","")
    head  = s.get("headline","")
    lines = "".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>' for l in s.get("summary",[]))
    q     = urllib.request.quote(head + " " + src)
    link  = f'https://news.google.com/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
    return (f'<div class="news-card" style="animation-delay:{i*0.08}s">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
            f'<div class="news-card-num">STORY {i+1} OF {total} · {TODAY}</div>'
            f'<div style="font-family:Calibri,sans-serif;font-size:9px;color:#94a3b8;font-weight:600">Source: {src}</div></div>'
            f'<div style="display:inline-flex;background:{bg};color:{color};font-family:Calibri,sans-serif;font-size:10px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-bottom:10px">{tag}</div>'
            f'<div class="n-headline">{head}</div>'
            f'<div class="n-summary">{lines}</div>'
            f'<div class="n-foot"><span class="n-src">📰 {src}</span>'
            f'<a class="n-link" href="{link}" target="_blank" rel="noopener">Search Google News ↗</a></div>'
            f'<div class="n-disclaimer">⚠ AI summary — click Search Google News to verify</div></div>')

def inject(html, cid, stories, tag_map):
    if not stories: return html
    banner = (f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:10px 16px;'
              f'margin-bottom:16px;font-family:Calibri,sans-serif;font-size:13px;color:#14532d;font-weight:600">'
              f'✅ <strong>{len(stories)} stories</strong> · {TODAY} · Approved sources · Click Search Google News to verify</div>')
    cards  = banner + '<div class="news-grid">' + "".join(card(s,i,len(stories),tag_map) for i,s in enumerate(stories)) + "</div>"

    start  = f'<div id="cont-{cid}">'
    if start not in html:
        print(f"   ⚠ Container not found: cont-{cid}"); return html

    sp = html.find(start) + len(start)
    depth=1; pos=sp; ep=sp
    while pos < len(html) and depth > 0:
        no = html.find('<div', pos)
        nc = html.find('</div>', pos)
        if nc == -1: break
        if no != -1 and no < nc: depth+=1; pos=no+4
        else:
            depth-=1
            if depth==0: ep=nc
            pos=nc+6

    print(f"   ✅ Injected {len(stories)} stories → cont-{cid}")
    return html[:sp] + cards + html[ep:]

def main():
    print(f"\n{'═'*50}\n  IndSight · {TODAY}\n{'═'*50}\n")
    if not os.path.exists(HTML_FILE):
        print(f"❌ {HTML_FILE} not found"); return

    html = open(HTML_FILE, encoding="utf-8").read()
    html = re.sub(r"const TODAY = [^;]+;", f"const TODAY = '{TODAY}';", html)
    print(f"✅ Date: {TODAY}\n")

    total = 0
    for cid, prompt, tag_map in SECTIONS:
        print(f"📰 [{cid}] Calling Gemini...")
        stories = gemini(prompt)
        if stories:
            html = inject(html, cid, stories, tag_map)
            total += len(stories)
        else:
            print(f"   ⚠ No stories — skipping")
        time.sleep(4)

    open(HTML_FILE, "w", encoding="utf-8").write(html)
    print(f"\n✅ Saved — {total} stories")

    os.system(f'git add {HTML_FILE}')
    code = os.system(f'git commit -m "News: {TODAY}" && git push origin main')
    print("✅ Pushed!" if code==0 else "⚠ Push failed")
    print(f"\n{'═'*50}\n  Done! {total} stories.\n{'═'*50}\n")

if __name__=="__main__":
    main()
