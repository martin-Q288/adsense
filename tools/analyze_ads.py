#!/usr/bin/env python3
"""상위노출 블로그의 실제 광고 배치를 계량 분석."""
import re, sys, subprocess, json

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

def fetch(url):
    try:
        r = subprocess.run(["curl","-sSL","--max-time","30","-A",UA,url],
                           capture_output=True, text=True, timeout=40)
        return r.stdout
    except Exception as e:
        return ""

def strip_tags(h):
    h = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", h, flags=re.S|re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))

def analyze(url):
    html = fetch(url)
    if not html or len(html) < 2000:
        return {"url": url, "error": f"fetch failed ({len(html)}B)"}

    out = {"url": url, "bytes": len(html)}

    # 자동광고 / 앵커 / 전면광고
    out["auto_ads"] = bool(re.search(r'adsbygoogle\.js\?client=ca-pub', html))
    out["page_level"] = bool(re.search(r'enable_page_level_ads|overlays|vignette', html, re.I))

    # 명시적 광고 유닛
    ins = re.findall(r'<ins[^>]*class="[^"]*adsbygoogle[^"]*"[^>]*>', html, re.I)
    out["manual_units"] = len(ins)
    fmts, slots = [], []
    for t in ins:
        f = re.search(r'data-ad-format="([^"]+)"', t)
        fmts.append(f.group(1) if f else "fixed")
        s = re.search(r'data-ad-layout="([^"]+)"', t)
        if s: slots.append(s.group(1))
        st = re.search(r'style="([^"]*)"', t)
        if st and ("width" in st.group(1) or "height" in st.group(1)):
            slots.append(st.group(1)[:60])
    out["formats"] = fmts
    out["layouts"] = slots[:8]
    out["full_width_responsive"] = bool(re.search(r'data-full-width-responsive="true"', html))

    # 본문 텍스트 총량
    body = html
    m = re.search(r'(<article[^>]*>.*?</article>)', html, re.S|re.I)
    if m: body = m.group(1)
    else:
        m = re.search(r'(<div[^>]*(?:class|id)="[^"]*(?:entry|post|article|content|tt_article)[^"]*"[^>]*>.*)', html, re.S|re.I)
        if m: body = m.group(1)
    text_total = len(strip_tags(body).replace(" ",""))
    out["body_chars"] = text_total

    # 각 광고 앞에 놓인 본문 글자 수 = 배치 깊이
    positions = []
    for m in re.finditer(r'<ins[^>]*adsbygoogle', body, re.I):
        before = len(strip_tags(body[:m.start()]).replace(" ",""))
        positions.append(before)
    out["ad_depth_chars"] = positions
    if text_total:
        out["ad_depth_pct"] = [round(p/text_total*100) for p in positions]

    # 광고 밀도
    if positions and text_total:
        out["chars_per_ad"] = round(text_total/len(positions))

    # 구조 요소
    out["h2"] = len(re.findall(r'<h2[^>]*>', body, re.I))
    out["tables"] = len(re.findall(r'<table', body, re.I))
    out["faq_schema"] = bool(re.search(r'"@type"\s*:\s*"FAQPage"', html))
    out["toc"] = bool(re.search(r'목차|toc|table-of-contents', body[:8000], re.I))
    out["sticky"] = bool(re.search(r'position\s*:\s*sticky', html, re.I))
    out["lazy"] = bool(re.search(r'data-ad-.*lazy|lazyload.*adsbygoogle|adsbygoogle.*loading="lazy"', html, re.I))
    return out

if __name__ == "__main__":
    for u in sys.argv[1:]:
        r = analyze(u)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        print("-"*70)
