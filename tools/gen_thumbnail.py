#!/usr/bin/env python3
"""글 썸네일 자동 생성기.

마크다운 원고의 프런트매터(키워드, 제목)를 읽어 클릭을 유도하는
카드형 썸네일 PNG를 만듭니다. HTML/CSS로 그린 뒤 Playwright로
스크린샷을 떠서 저장하는 방식이라 폰트·레이아웃을 자유롭게 조정할
수 있습니다.

사용법:
    python3 tools/gen_thumbnail.py content/articles/2026-08-02_T1_실업급여-조건.md
    python3 tools/gen_thumbnail.py content/articles/*.md   # 여러 개 한 번에

출력: content/articles/thumbnails/<원고파일명>.png (800x800, 2배 해상도)

프런트매터에 아래 필드를 넣으면 자동 분리 대신 직접 지정할 수 있습니다.
    썸네일_배지: 조건부터 신청까지
    썸네일_제목1: 실업급여
    썸네일_제목2: 조건 확인
    썸네일_CTA: 지금 바로 확인하기
"""

import argparse
import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR = os.path.join(ROOT, "content", "articles", "thumbnails")

RED = "#ff2323"
RED_DARK = "#d81212"

FONT_CSS = """
@font-face {
  font-family: 'Pretendard';
  src: url('FONT_BLACK') format('opentype');
  font-weight: 900;
}
@font-face {
  font-family: 'Pretendard';
  src: url('FONT_BOLD') format('opentype');
  font-weight: 700;
}
"""

TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
FONT_FACES
* { margin:0; padding:0; box-sizing:border-box; }
body {
  width:800px; height:800px;
  background: radial-gradient(circle at 30% 20%, #fff5f5 0%, #f1f1f1 70%);
  font-family: 'Pretendard', sans-serif;
  display:flex; align-items:center; justify-content:center;
}
.card {
  position:relative;
  width:700px; height:700px;
  background:#ffffff;
  border-radius:40px;
  border:5px dashed RED_COLOR;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  gap:34px;
  padding:50px;
  box-shadow: 0 18px 50px rgba(216,18,18,0.18);
}
.tab {
  position:absolute; top:-26px; left:44px;
  width:52px; height:52px;
  background:RED_COLOR;
  border-radius:50%;
  border:6px solid #ffffff;
  display:flex; align-items:center; justify-content:center;
}
.tab::after {
  content:'';
  width:16px; height:16px;
  background:#ffffff;
  border-radius:50%;
}
.badge {
  background:RED_COLOR;
  color:#fff;
  font-weight:700;
  font-size:30px;
  padding:14px 36px;
  border-radius:999px;
  letter-spacing:-0.5px;
  box-shadow: 0 8px 20px rgba(216,18,18,0.35);
}
.headline {
  text-align:center;
  font-weight:900;
  font-size:HEADSIZEpx;
  line-height:1.18;
  letter-spacing:-1.5px;
  color:#111111;
}
.headline .accent { color:RED_COLOR; }
.cta {
  background:RED_COLOR;
  color:#fff;
  font-weight:700;
  font-size:34px;
  letter-spacing:-0.5px;
  padding:22px 48px;
  border-radius:20px;
  display:flex; align-items:center; gap:10px;
  box-shadow: 0 10px 26px rgba(216,18,18,0.4);
}
.cta .arrow { font-weight:900; }
</style></head>
<body>
  <div class="card">
    <div class="tab"></div>
    <div class="badge">BADGE</div>
    <div class="headline">LINE1<br><span class="accent">LINE2</span></div>
    <div class="cta">CTA<span class="arrow">›</span></div>
  </div>
</body></html>
"""


def read_frontmatter(path):
    text = open(path, encoding="utf-8").read()
    fm = {}
    lines = text.split("\n")
    for line in lines[:20]:
        m = re.match(r"^([^:]+):\s*(.+)$", line)
        if m and not line.startswith("#"):
            fm[m.group(1).strip()] = m.group(2).strip()
    h1 = ""
    for line in lines:
        if line.startswith("# "):
            h1 = line[2:].strip()
            break
    return fm, h1


def split_keyword(kw):
    """주 키워드를 두 줄로 나눕니다."""
    words = kw.split()
    if len(words) >= 2:
        mid = (len(words) + 1) // 2
        return " ".join(words[:mid]), " ".join(words[mid:])
    w = kw.replace(" ", "")
    if len(w) <= 4:
        return w, ""
    cut = (len(w) + 1) // 2
    return w[:cut], w[cut:]


def derive_badge(h1):
    if "—" in h1:
        sub = h1.split("—", 1)[1].strip()
    else:
        sub = h1
    sub = re.sub(r"\d{4}년?", "", sub).strip(" -,")
    limit = 13
    if len(sub) > limit:
        cut = sub[:limit]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        sub = cut + "…"
    return sub or "2026년 최신 기준"


def build_html(fm, h1, font_black, font_bold):
    primary_kw = fm.get("키워드", h1).split(",")[0].strip()

    badge = fm.get("썸네일_배지") or derive_badge(h1)
    if "썸네일_제목1" in fm and "썸네일_제목2" in fm:
        line1, line2 = fm["썸네일_제목1"], fm["썸네일_제목2"]
    else:
        line1, line2 = split_keyword(primary_kw)
    cta = fm.get("썸네일_CTA") or f"{primary_kw.replace(' ', '')[:10]} 확인하기"

    maxlen = max(len(line1), len(line2))
    headsize = 108 if maxlen <= 5 else (92 if maxlen <= 7 else 74)

    html = TEMPLATE
    html = html.replace(
        "FONT_FACES",
        FONT_CSS.replace("FONT_BLACK", f"file://{font_black}")
                .replace("FONT_BOLD", f"file://{font_bold}"),
    )
    html = html.replace("RED_COLOR", RED).replace("HEADSIZE", str(headsize))
    html = html.replace("BADGE", badge)
    html = html.replace("LINE1", line1)
    html = html.replace("LINE2", line2 or "&nbsp;")
    html = html.replace("CTA", cta)
    return html


def render(html, out_path, page):
    page.set_content(html, wait_until="load")
    page.wait_for_timeout(120)
    page.locator(".card").screenshot(path=out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", help="원고 .md 경로 (glob 가능)")
    p.add_argument("--font-dir", default=os.environ.get(
        "THUMB_FONT_DIR", os.path.join(ROOT, "assets", "fonts")))
    a = p.parse_args()

    font_black = os.path.join(a.font_dir, "Pretendard-Black.otf")
    font_bold = os.path.join(a.font_dir, "Pretendard-Bold.otf")
    if not os.path.exists(font_black):
        sys.exit(f"폰트 없음: {font_black}")

    files = []
    for f in a.files:
        files.extend(sorted(glob.glob(f)) or [f])

    os.makedirs(OUT_DIR, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 800, "height": 800},
                                 device_scale_factor=2)
        for path in files:
            fm, h1 = read_frontmatter(path)
            html = build_html(fm, h1, font_black, font_bold)
            base = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(OUT_DIR, base + ".png")
            render(html, out_path, page)
            print(f"OK  {out_path}")
        browser.close()


if __name__ == "__main__":
    main()
