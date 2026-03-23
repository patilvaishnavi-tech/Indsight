#!/usr/bin/env python3
"""
IndSight Daily News Updater — Powered by Google Gemini API (FREE)
Uses Gemini 2.5 Flash-Lite: 1,000 requests/day free, no credit card.
Get free key at: https://aistudio.google.com
"""

import os, re, json, time
from datetime import datetime

GEMINI_API_KEY = ""        # ← paste key from aistudio.google.com
HTML_FILE      = "index.html"
AUTO_GIT_PUSH  = True
MODEL          = "gemini-2.5-flash-lite"
TODAY          = datetime.now().strftime("%d %B %Y")

try:
    from google import genai
except ImportError:
    print("❌ Run:  pip install google-genai")
    exit(1)

api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("❌ Set GEMINI_API_KEY — get free key at aistudio.google.com")
    exit(1)

client = genai.Client(api_key=api_key)

NEWS_FORMAT = """Return ONLY valid JSON, no markdown fences:
{"stories":[{"tag":"TAG","headline":"sharp headline with company + number","summary":["What happened: specific event + company + data","Why it happened: cause or context","Key number: exact % / GW / units / ₹ / $ figure","India impact: effect on India market or sector","Watch for: next development to track"],"source":"Publication Name","url":"https://publication.com"}]}
Exactly 5 stories. JSON only."""

SECTIONS = [
  ("auto-news", f"Senior automotive journalist India {TODAY}. TOP 5 auto news today — ICE, EV (2W/3W/4W), hydrogen, safety, exports. Companies: Maruti, Tata, M&M, Hero, Bajaj, TVS, Ola Electric, Ather, Hyundai India. Sources: ET Auto, Autocar India, Autocar Professional. {NEWS_FORMAT}", {"ICE":"#1d4ed8","EV":"#15803d","Hydrogen":"#6d28d9","2W":"#1d4ed8","4W":"#1d4ed8","CV":"#1d4ed8","Policy":"#155e75","Safety":"#1d4ed8","Export":"#991b1b"}),
  ("energy-news", f"Senior energy analyst India {TODAY}. TOP 5 energy news today — solar, wind, BESS, hydrogen, grid, oil & gas. Companies: NTPC, Adani Green, Tata Power, Waaree, Suzlon, ReNew, Greenko. Sources: Mercom India, ET Energy, PV Magazine India. {NEWS_FORMAT}", {"Solar":"#854d0e","Wind":"#1e40af","BESS":"#6d28d9","Hydrogen":"#6d28d9","Grid":"#14532d","Gas":"#14532d","Coal":"#92400e"}),
  ("policy-news", f"Energy policy analyst India {TODAY}. TOP 5 govt policy/scheme news — SECI tenders (MW, ₹/unit), PLI solar/batteries, PM-KUSUM, FAME III, ISTS waiver, ALMM, NGHM awards. Sources: MNRE, PIB, ET Energy, Mercom. {NEWS_FORMAT}", {"PLI":"#155e75","FAME":"#155e75","SECI":"#854d0e","NHGM":"#6d28d9","Tender":"#155e75","Budget":"#155e75"}),
  ("leadership-news", f"Business journalist automotive CXO moves {TODAY}. TOP 5 leadership changes India + global auto — CEO, CFO, COO, MD, Board appointments/exits at OEMs + Tier-1 suppliers. Sources: ET Auto, Business Standard, Autocar Professional. {NEWS_FORMAT}", {"Leadership":"#92400e","CEO":"#92400e","Board":"#92400e","Appointment":"#92400e","Exit":"#92400e"}),
  ("investments-news", f"Automotive investment analyst India {TODAY}. TOP 5 investment/capex/M&A/JV/PLI news — India auto plant expansions, global auto M&A affecting India, EV charging infra, battery plant deals. Sources: ET Auto, Reuters, PIB, Bloomberg. {NEWS_FORMAT}", {"Capex":"#991b1b","M&A":"#991b1b","JV":"#991b1b","PLI":"#155e75","EV Infra":"#15803d","Global":"#991b1b"}),
  ("liion-news", f"Battery technology analyst {TODAY}. TOP 5 Li-ion cell market news — CATL, BYD, LG ES, Samsung SDI, Panasonic, SK On; India PLI battery (Exide, Amara Raja, Ola/Bharat Cell); cell pricing LFP vs NMC; solid-state progress; India imports from China. Sources: BloombergNEF, Reuters, Nikkei Asia, ET. {NEWS_FORMAT}", {"CATL":"#6d28d9","BYD":"#6d28d9","LG ES":"#6d28d9","India PLI":"#155e75","Cell Price":"#6d28d9","Solid State":"#6d28d9"}),
  ("trade-news", f"Trade policy analyst India {TODAY}. TOP 5 import/export policy news — DGFT notifications, FTA progress (UAE, UK, EU), PLI exports, anti-dumping duties (auto/solar/Li-ion from China), RoDTEP, rupee impact on trade. Sources: DGFT, PIB, ET, Business Standard. {NEWS_FORMAT}", {"Export":"#9a3412","Import":"#9a3412","FTA":"#9a3412","Tariff":"#9a3412","DGFT":"#155e75","Anti-dumping":"#9a3412"}),
]

TAG_BG = {"#1d4ed8":"#dbeafe","#15803d":"#dcfce7","#6d28d9":"#ede9fe","#92400e":"#fef3c7","#991b1b":"#fee2e2","#155e75":"#cffafe","#854d0e":"#fef9c3","#1e40af":"#dbeafe","#14532d":"#dcfce7","#9a3412":"#fff7ed"}

def call_gemini(prompt, retries=3):
    for attempt in range(retries):
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt)
            raw = re.sub(r"```json|```","",r.text.strip()).strip()
            return json.loads(raw).get("stories", [])
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 60*(attempt+1)
                print(f"   ⏳ Rate limit — waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"   ❌ {e}")
                if attempt == retries-1: return []
    return []

def render_card(s, i, total, tag_map):
    tag = s.get("tag",""); color = tag_map.get(tag,"#1d4ed8"); bg = TAG_BG.get(color,"#dbeafe")
    url = s.get("url",""); source = s.get("source","")
    lines = "".join(f'<div class="n-summary-line"><span class="n-dot">›</span><span>{l}</span></div>' for l in s.get("summary",[]))
    link = f'<a class="n-link" href="{url}" target="_blank" rel="noopener">Read Original ↗</a>' if url.startswith("http") else f'<span class="n-link" style="opacity:.5">Source: {source}</span>'
    return f'<div class="news-card" style="animation-delay:{i*0.08}s"><div class="news-card-num">STORY {i+1} OF {total} · {TODAY}</div><div class="ntag" style="background:{bg};color:{color}">{tag}</div><div class="n-headline">{s.get("headline","")}</div><div class="n-summary">{lines}</div><div class="n-foot"><span class="n-src">📰 {source}</span>{link}</div></div>'

def inject(html, cid, stories, tag_map):
    if not stories: return html
    cards = '<div class="news-grid">'+"".join(render_card(s,i,len(stories),tag_map) for i,s in enumerate(stories))+"</div>"
    new = re.sub(rf'(<div id="cont-{re.escape(cid)}">)(.*?)(</\/div>)', rf'\g<1>{cards}\g<3>', html, flags=re.DOTALL)
    if new == html: print(f"   ⚠  Container not found: cont-{cid}")
    return new

def main():
    print(f"\n{'═'*50}\n  IndSight · Gemini News Updater · {TODAY}\n{'═'*50}\n")
    if not os.path.exists(HTML_FILE):
        print(f"❌ {HTML_FILE} not found. Run from the same folder."); return
    with open(HTML_FILE,"r",encoding="utf-8") as f: html = f.read()
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
            print(f"   ⚠  No stories — skipping section")
        time.sleep(3)
    with open(HTML_FILE,"w",encoding="utf-8") as f: f.write(html)
    print(f"\n✅ Saved {HTML_FILE} — {total} stories across {len(SECTIONS)} sections")
    if AUTO_GIT_PUSH:
        print("\n🚀 Pushing to GitHub...")
        os.system(f'git add {HTML_FILE}')
        code = os.system(f'git commit -m "Daily news update: {TODAY}" && git push origin main')
        print("✅ Pushed! Site updates in ~1 min." if code==0 else "⚠  Git push failed — push manually.")
    print(f"\n{'═'*50}\n  All done! Your IndSight site is updated.\n{'═'*50}\n")

if __name__ == "__main__":
    main()
