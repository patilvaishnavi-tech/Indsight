#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# IndSight Data Pipeline v8 — server-side fetch → JSON
# ─────────────────────────────────────────────────────────────────────────────
# WHAT CHANGED vs v7:
#   * No longer rewrites index.html. It writes JSON data files that the browser
#     fetches with a cache-busting query string. This is the only reliable way
#     to keep the site fresh (CORS proxies in the browser were failing silently).
#   * News: Google News RSS (primary, real URLs + published dates, no key) with
#     strict per-section source allow-lists + dedup. Gemini (optional) only
#     enriches summaries — it never invents headlines/URLs/dates.
#   * Markets: USD/INR (open.er-api.com), Nifty Auto + Nifty Energy (Yahoo),
#     metals Cu/Al/Ni/Zn/Pb-as-needed + lithium proxy (Yahoo futures) — all
#     server-side (no CORS). On failure for any single item we keep the LAST
#     GOOD value from the previous JSON and flag it stale (never blank, never
#     silently-frozen — the timestamp tells the truth).
#   * Charts: each commodity/FX series is APPENDED to a rolling history file so
#     the x-axis automatically extends to the latest trading date. No hardcoded
#     start/end dates anywhere.
#
# OUTPUT (all under ./data/):
#   data/news.json          — { generated_at, sections:{ anews:[...], ... } }
#   data/markets.json       — { generated_at, fx:{...}, nifty_auto:{...}, nifty_energy:{...} }
#   data/commodities.json   — { generated_at, metals:{ copper:{...}, ... } }
#   data/history.json       — rolling per-series price history for charts
#   data/version.txt        — unix timestamp used by the browser for ?v= cache-busting
#
# ENV:
#   GEMINI_API_KEY  (optional) — if absent, RSS summaries are used as-is.
# ─────────────────────────────────────────────────────────────────────────────

import os, re, json, time, html, hashlib, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

IST       = timezone(timedelta(hours=5, minutes=30))
NOW       = datetime.now(IST)
NOW_UNIX  = int(time.time())
TODAY_STR = NOW.strftime("%d %b %Y")
TODAY_LONG= NOW.strftime("%d %B %Y")
DATA_DIR  = "data"
GEMINI_KEY= os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-2.0-flash-001"

UA = {"User-Agent": "Mozilla/5.0 (compatible; IndSightBot/1.0; +https://github.com)"}

os.makedirs(DATA_DIR, exist_ok=True)

def log(msg): print(msg, flush=True)

def http_get(url, timeout=20, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(2 + i * 2)
    raise last

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    log(f"  ✅ wrote {path}")

# ─────────────────────────────────────────────────────────────────────────────
# 1) NEWS — Google News RSS, strict source allow-list, dedup
# ─────────────────────────────────────────────────────────────────────────────
# Each section: approved domains (substring match on the article's real source)
# + a search query. Google News RSS returns title, link (real article URL),
# pubDate, and <source>. We filter by domain, dedup by normalised headline.

NEWS_SECTIONS = {
    "anews": {
        "label": "Auto News",
        "domains": ["auto.economictimes.indiatimes.com", "autocarpro.in",
                    "autocarindia.com", "livemint.com"],
        "names":   ["ET Auto", "Autocar Professional", "Autocar India", "Mint"],
        "query":   "India automobile OEM EV sales launch",
    },
    "lead": {
        "label": "Leadership",
        "domains": ["auto.economictimes.indiatimes.com", "autocarpro.in",
                    "autocarindia.com", "livemint.com"],
        "names":   ["ET Auto", "Autocar Professional", "Autocar India", "Mint"],
        "query":   "India auto CEO MD appointment resignation leadership",
    },
    "inv": {
        "label": "Investments",
        "domains": ["auto.economictimes.indiatimes.com", "autocarpro.in",
                    "autocarindia.com", "livemint.com"],
        "names":   ["ET Auto", "Autocar Professional", "Autocar India", "Mint"],
        "query":   "India auto investment plant capex EV factory JV",
    },
    "enews": {
        "label": "Energy / Generation News",
        "domains": ["reuters.com", "ft.com", "energy.economictimes.indiatimes.com"],
        "names":   ["Reuters", "Financial Times", "ET Energy"],
        "query":   "India energy solar wind inverter generation grid renewable",
    },
    "sustain": {
        "label": "Sustainability & ESG",
        "domains": ["reuters.com", "ft.com", "energy.economictimes.indiatimes.com"],
        "names":   ["Reuters", "Financial Times", "ET Energy"],
        "query":   "India sustainability ESG net zero carbon green decarbonisation",
    },
    "policy": {
        "label": "Energy Policy",
        "domains": ["reuters.com", "ft.com", "energy.economictimes.indiatimes.com"],
        "names":   ["Reuters", "Financial Times", "ET Energy"],
        "query":   "India energy policy SECI PLI FAME renewable scheme",
    },
    "liionnews": {
        "label": "Li-ion Battery",
        "domains": ["reuters.com", "ft.com", "energy.economictimes.indiatimes.com",
                    "auto.economictimes.indiatimes.com"],
        "names":   ["Reuters", "Financial Times", "ET Energy", "ET Auto"],
        "query":   "lithium ion battery cell India CATL BYD PLI gigafactory",
    },
    "tradenews": {
        "label": "Trade News",
        "domains": ["reuters.com", "ft.com", "energy.economictimes.indiatimes.com",
                    "auto.economictimes.indiatimes.com", "livemint.com"],
        "names":   ["Reuters", "Financial Times", "ET Energy", "ET Auto", "Mint"],
        "query":   "India trade FTA anti-dumping import export auto duty",
    },
}

MAX_STORIES = 5

def norm_headline(h):
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())[:80]

def domain_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""

def clean_text(t):
    return html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()

def rss_items(query):
    q = urllib.parse.quote(f"{query} when:14d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    xml = http_get(url)
    root = ET.fromstring(xml)
    out = []
    for it in root.iter("item"):
        title = clean_text(it.findtext("title", ""))
        link  = (it.findtext("link", "") or "").strip()
        pub   = (it.findtext("pubDate", "") or "").strip()
        src_el= it.find("source")
        src   = clean_text(src_el.text) if src_el is not None else ""
        src_url = src_el.get("url", "") if src_el is not None else ""
        # Google News wraps the real source domain in <source url=...>
        out.append({"title": title, "link": link, "pub": pub,
                    "source": src, "source_url": src_url})
    return out

def fmt_pubdate(pub):
    # RSS pubDate -> "12 Jun 2026"
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(pub, fmt).strftime("%d %b %Y")
        except Exception:
            continue
    return pub[:16] if pub else ""

def gemini_summary(headline, source):
    """Optional: 2–3 crisp bullet points. Never used to invent facts —
    only to phrase what the headline already states. Returns [] on any failure."""
    if not GEMINI_KEY:
        return []
    prompt = (f'Summarise this Indian {source} news headline into 2 short factual '
              f'bullet points (max 14 words each), no speculation, no new numbers. '
              f'Return JSON only: {{"points":["...","..."]}}. Headline: "{headline}"')
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}")
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.2, "maxOutputTokens": 200}}).encode()
    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        txt = d["candidates"][0]["content"]["parts"][0]["text"]
        txt = re.sub(r"```json|```", "", txt).strip()
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        pts = json.loads(m.group() if m else txt).get("points", [])
        return [clean_text(p) for p in pts if p][:3]
    except Exception as e:
        log(f"    (gemini enrich skipped: {str(e)[:60]})")
        return []

def build_news_section(key, cfg, prev_section):
    log(f"📰 [{key}] {cfg['label']} …")
    try:
        items = rss_items(cfg["query"])
    except Exception as e:
        log(f"  ⚠ RSS failed ({str(e)[:80]}) — keeping previous data, flagged stale")
        # Keep last good, mark stale
        for s in prev_section:
            s["stale"] = True
        return prev_section

    seen, stories = set(), []
    for it in items:
        dom = domain_of(it["source_url"]) or domain_of(it["link"])
        if not any(d in dom or d in it["source"].lower().replace(" ", "")
                   for d in cfg["domains"]):
            # also allow match on the human source name
            if not any(n.lower() in it["source"].lower() for n in cfg["names"]):
                continue
        nh = norm_headline(it["title"])
        if not nh or nh in seen:
            continue
        seen.add(nh)
        summary = gemini_summary(it["title"], it["source"]) if GEMINI_KEY else []
        if not summary:
            summary = [it["title"]]  # honest fallback: headline as the single line
        stories.append({
            "headline": it["title"],
            "summary":  summary,
            "source":   it["source"] or "Google News",
            "url":      it["link"],
            "published": fmt_pubdate(it["pub"]),
            "stale":    False,
        })
        if len(stories) >= MAX_STORIES:
            break

    if not stories:
        log("  ⚠ no fresh approved-source stories found")
        return []   # browser shows "No new updates available"
    log(f"  ✅ {len(stories)} fresh stories")
    return stories

def run_news():
    prev = load_json(os.path.join(DATA_DIR, "news.json"), {}).get("sections", {})
    sections = {}
    for key, cfg in NEWS_SECTIONS.items():
        sections[key] = build_news_section(key, cfg, prev.get(key, []))
        time.sleep(1)
    return {"generated_at": NOW.isoformat(), "generated_str": TODAY_STR, "sections": sections}

# ─────────────────────────────────────────────────────────────────────────────
# 2) MARKETS — FX + Nifty Auto + Nifty Energy (server-side, no CORS)
# ─────────────────────────────────────────────────────────────────────────────
def yahoo_quote(symbol):
    """Return {price, prev, change_pct, time_str} or None."""
    sym = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
    d = json.loads(http_get(url))
    meta = d["chart"]["result"][0]["meta"]
    price = meta.get("regularMarketPrice")
    prev  = meta.get("chartPreviousClose") or meta.get("previousClose")
    if price is None:
        return None
    chg = ((price - prev) / prev * 100) if prev else 0.0
    ts  = meta.get("regularMarketTime")
    tstr = datetime.fromtimestamp(ts, IST).strftime("%d %b %Y") if ts else TODAY_STR
    return {"price": round(price, 2), "prev": round(prev, 2) if prev else None,
            "change_pct": round(chg, 2), "as_of": tstr}

def run_markets(prev):
    out = {"generated_at": NOW.isoformat(), "generated_str": TODAY_STR}

    # ── FX: USD/INR (consistent single source across the whole site) ──
    log("💱 FX USD/INR (open.er-api.com) …")
    try:
        d = json.loads(http_get("https://open.er-api.com/v6/latest/USD"))
        if d.get("result") != "success":
            raise ValueError("api result not success")
        inr = d["rates"]["INR"]
        cny = d["rates"].get("CNY")
        prev_fx = prev.get("fx", {})
        out["fx"] = {
            "usdinr": round(inr, 4),
            "prev":   prev_fx.get("usdinr", round(inr, 4)),
            "cnyinr": round(inr / cny, 4) if cny else None,
            "source": "open.er-api.com",
            "as_of":  (d.get("time_last_update_utc") or TODAY_STR)[:16],
            "stale":  False,
        }
        log(f"  ✅ USD/INR = {inr}")
    except Exception as e:
        log(f"  ⚠ FX failed ({str(e)[:60]}) — keeping last good, stale")
        out["fx"] = {**prev.get("fx", {"usdinr": None, "source": "open.er-api.com"}),
                     "stale": True}

    # ── Nifty Auto & Nifty Energy (Yahoo) ──
    for label, symbols, field in [
        ("nifty_auto",   ["^CNXAUTO", "CNXAUTO.NS"],          "Nifty Auto"),
        ("nifty_energy", ["^CNXENERGY", "CNXENERGY.NS", "^NSEI"], "Nifty Energy"),
    ]:
        log(f"📈 {field} (Yahoo) …")
        got = None
        for s in symbols:
            try:
                q = yahoo_quote(s)
                if q:
                    got = q
                    break
            except Exception as e:
                log(f"    {s} failed: {str(e)[:50]}")
        if got:
            out[label] = {**got, "source": "NSE via Yahoo Finance (EOD)", "stale": False}
            log(f"  ✅ {field} = {got['price']} ({got['change_pct']:+}%)")
        else:
            log(f"  ⚠ {field} failed — keeping last good, stale")
            out[label] = {**prev.get(label, {"price": None}),
                          "source": "NSE via Yahoo Finance (EOD)", "stale": True}
    return out

# ─────────────────────────────────────────────────────────────────────────────
# 3) COMMODITIES — metals + lithium proxy (Yahoo futures), USD/tonne
# ─────────────────────────────────────────────────────────────────────────────
# Yahoo continuous-future symbols (USD/lb or USD/tonne depending on contract).
# We normalise everything to USD/tonne for display. Where a clean LME feed isn't
# freely available server-side, we use the most reliable free proxy and label it.
METALS = {
    "copper":    {"symbol": "HG=F",  "to_tonne": 2204.62, "unit": "$/t", "name": "Copper",    "src": "COMEX (HG=F) via Yahoo"},
    "aluminium": {"symbol": "ALI=F", "to_tonne": 1.0,     "unit": "$/t", "name": "Aluminium", "src": "COMEX Aluminium (ALI=F) via Yahoo"},
    "zinc":      {"symbol": "ZN=F",  "to_tonne": 1.0,     "unit": "$/t", "name": "Zinc",      "src": "Yahoo (ZN=F)"},
    "nickel":    {"symbol": None,    "to_tonne": 1.0,     "unit": "$/t", "name": "Nickel",    "src": "LME (manual/last good)"},
    "steel":     {"symbol": "HRC=F", "to_tonne": 1.0,     "unit": "$/t", "name": "Steel HRC", "src": "COMEX HRC (HRC=F) via Yahoo"},
    "lithium":   {"symbol": None,    "to_tonne": 1.0,     "unit": "$/t", "name": "Lithium",   "src": "SMM/Fastmarkets (est., last good)"},
}

def run_commodities(prev):
    out = {"generated_at": NOW.isoformat(), "generated_str": TODAY_STR, "metals": {}}
    prev_metals = prev.get("metals", {})
    for key, cfg in METALS.items():
        log(f"🔩 {cfg['name']} …")
        pm = prev_metals.get(key, {})
        if not cfg["symbol"]:
            # No reliable free server-side feed → carry last good, flag stale.
            out["metals"][key] = {**pm, "name": cfg["name"], "unit": cfg["unit"],
                                  "source": cfg["src"], "stale": True} if pm else {
                "name": cfg["name"], "unit": cfg["unit"], "source": cfg["src"],
                "today": None, "prev": None, "change_pct": None, "stale": True}
            log(f"  ⚠ no free feed — carry last good ({pm.get('today')})")
            continue
        try:
            q = yahoo_quote(cfg["symbol"])
            if not q:
                raise ValueError("empty quote")
            today = round(q["price"] * cfg["to_tonne"])
            prevp = round(q["prev"] * cfg["to_tonne"]) if q["prev"] else pm.get("today")
            chg   = round(((today - prevp) / prevp * 100), 2) if prevp else None
            out["metals"][key] = {
                "name": cfg["name"], "unit": cfg["unit"], "source": cfg["src"],
                "today": today, "prev": prevp, "change_pct": chg,
                "as_of": q["as_of"], "stale": False,
            }
            log(f"  ✅ {cfg['name']} = ${today}/t ({chg:+}%)" if chg is not None
                else f"  ✅ {cfg['name']} = ${today}/t")
        except Exception as e:
            log(f"  ⚠ {cfg['name']} failed ({str(e)[:50]}) — last good, stale")
            out["metals"][key] = {**pm, "name": cfg["name"], "unit": cfg["unit"],
                                  "source": cfg["src"], "stale": True} if pm else {
                "name": cfg["name"], "unit": cfg["unit"], "source": cfg["src"],
                "today": None, "prev": None, "change_pct": None, "stale": True}
    return out

# ─────────────────────────────────────────────────────────────────────────────
# 4) HISTORY — append today's point so charts auto-extend (no hardcoded dates)
# ─────────────────────────────────────────────────────────────────────────────
def run_history(markets, commodities):
    hist = load_json(os.path.join(DATA_DIR, "history.json"),
                     {"series": {}})
    series = hist.setdefault("series", {})
    label = NOW.strftime("%d %b")

    def append(name, value):
        if value is None:
            return
        s = series.setdefault(name, {"labels": [], "prices": []})
        # replace if same-day re-run, else append; cap to last 60 points
        if s["labels"] and s["labels"][-1] == label:
            s["prices"][-1] = value
        else:
            s["labels"].append(label)
            s["prices"].append(value)
        s["labels"] = s["labels"][-60:]
        s["prices"] = s["prices"][-60:]

    for k, m in commodities.get("metals", {}).items():
        append(k, m.get("today"))
    fx = markets.get("fx", {})
    append("usdinr", fx.get("usdinr"))
    append("cnyinr", fx.get("cnyinr"))

    hist["generated_at"] = NOW.isoformat()
    return hist

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    log(f"\n{'='*52}\n  IndSight pipeline · {TODAY_LONG}\n{'='*52}")
    log(f"  cwd={os.getcwd()}  gemini={'on' if GEMINI_KEY else 'off'}\n")

    prev_markets     = load_json(os.path.join(DATA_DIR, "markets.json"), {})
    prev_commodities = load_json(os.path.join(DATA_DIR, "commodities.json"), {})

    news        = run_news()
    markets     = run_markets(prev_markets)
    commodities = run_commodities(prev_commodities)
    history     = run_history(markets, commodities)

    save_json(os.path.join(DATA_DIR, "news.json"), news)
    save_json(os.path.join(DATA_DIR, "markets.json"), markets)
    save_json(os.path.join(DATA_DIR, "commodities.json"), commodities)
    save_json(os.path.join(DATA_DIR, "history.json"), history)
    with open(os.path.join(DATA_DIR, "version.txt"), "w") as f:
        f.write(str(NOW_UNIX))
    log(f"  ✅ wrote {DATA_DIR}/version.txt ({NOW_UNIX})")

    total = sum(len(v) for v in news["sections"].values())
    log(f"\n{'='*52}\n  Done · {total} news stories · markets+commodities updated\n{'='*52}\n")

if __name__ == "__main__":
    main()
