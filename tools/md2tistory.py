#!/usr/bin/env python3
"""마크다운 원고 → 티스토리 HTML 모드용 순수 HTML.

마크다운 기호(**, #, |, -, >)를 하나도 남기지 않고 HTML 태그로 변환합니다.
아티팩트에서 마크다운을 그대로 복사해 붙이면 티스토리에 '**' 같은 기호가
글자로 찍히므로, 반드시 이 변환을 거쳐야 합니다.

제목 계층
  H1은 본문에 넣지 않습니다. 티스토리 스킨이 글 제목을 h1으로 렌더링하므로
  본문에 h1을 또 쓰면 제목이 두 개가 되어 색인에 불리합니다.
  본문은 h2(대목차) / h3(소목차)만 씁니다.

광고 배치는 docs/10 실측 기준(수동 3개, 깊이 약 8/55/94%)을 자동 적용합니다.

사용법:
    python3 tools/md2tistory.py content/articles/*.md
    python3 tools/md2tistory.py content/articles/x.md -o content/articles/html/
"""

import argparse, html, json, os, re, sys

# ── 광고 코드 템플릿 ────────────────────────────────
def ins(fmt, layout=None):
    lay = f'\n       data-ad-layout="{layout}"' if layout else ""
    return (f'<ins class="adsbygoogle"\n'
            f'       style="display:block"\n'
            f'       data-ad-client="ca-pub-여기에본인퍼블리셔ID"\n'
            f'       data-ad-slot="여기에광고단위ID"\n'
            f'       data-ad-format="{fmt}"{lay}\n'
            f'       data-full-width-responsive="true"></ins>\n'
            f'  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>')

AD = {
 1: ('ad-inline', ins("auto"),
     "결론 박스 뒤 / 목차 앞 (본문 약 8%)\n     근거: 독자가 결론을 읽고 목차로 넘어가며 반드시 지나가고 잠깐 멈추는\n           구간. Active View 조건(면적 50%가 1초 이상)을 채우기 가장 쉽습니다.\n     설정: 반응형 디스플레이 / 지연 로딩 금지"),
 2: ('ad-inline', ins("fluid", "in-article"),
     "본문 중반 (약 50~60%)\n     근거: 실측 상위 블로그 밀도는 본문 1,000~1,300자당 1개.\n     설정: 인아티클 / 지연 로딩 허용"),
 3: ('ad-multiplex', ins("autorelaxed"),
     "글 최하단 (관련 글 뒤)\n     형식: 멀티플렉스. 세션당 PV를 올려 전면광고 노출도 함께 늘립니다.\n     주의: 관련 글 링크 위를 광고로 막지 않았습니다. 그 링크 클릭이\n           Vignette 수익의 출발점입니다."),
}

def ad_block(n):
    cls, code, why = AD[n]
    return (f'<!-- ═══ AD {n} ═══════════════════════════════════════\n'
            f'     위치: {why}\n'
            f'═══════════════════════════════════════════════════ -->\n'
            f'<div class="ad-slot {cls}">\n'
            f'  <span class="ad-label">광고</span>\n  {code}\n</div>\n')

# ── 인라인 마크다운 → HTML ──────────────────────────
def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)', r'<em>\1</em>', t)
    t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', t)
    return t

def slug(t, i):
    return f"s{i}"

# ── 블록 파서 ───────────────────────────────────────
def parse(md):
    """마크다운을 블록 리스트로."""
    lines = md.split("\n")
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        # 헤딩
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m:
            blocks.append(("h", len(m.group(1)), m.group(2).strip())); i += 1; continue
        # 수평선
        if re.match(r'^\s*---+\s*$', ln):
            blocks.append(("hr", None, None)); i += 1; continue
        # 표
        if ln.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i]); i += 1
            blocks.append(("table", None, rows)); continue
        # 인용
        if ln.lstrip().startswith(">"):
            q = []
            while i < len(lines) and (lines[i].lstrip().startswith(">") or
                                      (q and lines[i].strip() and not re.match(r'^[#|\-*\d]', lines[i].lstrip()))):
                q.append(re.sub(r'^\s*>\s?', '', lines[i])); i += 1
            blocks.append(("quote", None, " ".join(x.strip() for x in q if x.strip()))); continue
        # 코드블록
        if ln.lstrip().startswith("```"):
            i += 1; c = []
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                c.append(lines[i]); i += 1
            i += 1
            blocks.append(("code", None, "\n".join(c))); continue
        # 목록
        if re.match(r'^\s*[-*]\s+', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*]\s+', lines[i]):
                items.append(re.sub(r'^\s*[-*]\s+', '', lines[i]).strip()); i += 1
            blocks.append(("ul", None, items)); continue
        if re.match(r'^\s*\d+\.\s+', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]):
                items.append(re.sub(r'^\s*\d+\.\s+', '', lines[i]).strip()); i += 1
            blocks.append(("ol", None, items)); continue
        # 문단
        p = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r'^\s*(#{1,6}\s|[-*]\s|\d+\.\s|\||>|```|---+\s*$)', lines[i]):
            p.append(lines[i].strip()); i += 1
        if p: blocks.append(("p", None, " ".join(p)))
    return blocks

def table_html(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if not all(re.match(r'^:?-+:?$', x) for x in c)]
    if not cells: return ""
    out = ['<div class="tbl-wrap">', "<table>",
           "  <thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells[0]) + "</tr></thead>",
           "  <tbody>"]
    for r in cells[1:]:
        out.append("    <tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out += ["  </tbody>", "</table>", "</div>"]
    return "\n".join(out)

def text_len(b):
    """블록의 순수 글자 수 (광고 깊이 계산용)."""
    k, _, v = b
    if k in ("p", "quote"): return len(re.sub(r'\s', '', v))
    if k in ("ul", "ol"): return sum(len(re.sub(r'\s', '', x)) for x in v)
    if k == "table": return sum(len(re.sub(r'\s', '', r)) for r in v)
    if k == "h": return len(re.sub(r'\s', '', v))
    return 0

# ── 변환 ────────────────────────────────────────────
def convert(md, meta):
    blocks = parse(md)
    title = next((v for k, lv, v in blocks if k == "h" and lv == 1), meta.get("키워드", ""))
    blocks = [b for b in blocks if not (b[0] == "h" and b[1] == 1)]

    # 섹션 구분
    lede_end = 0
    for n, b in enumerate(blocks):
        if b[0] == "h": lede_end = n; break
    lede, rest = blocks[:lede_end], blocks[lede_end:]

    # 기존 '목차' 섹션 제거 (자동 생성으로 대체)
    cleaned, skip = [], False
    for b in rest:
        if b[0] == "h" and re.match(r'^목차', b[2]): skip = True; continue
        if skip and b[0] in ("ol", "ul"): skip = False; continue
        skip = False
        cleaned.append(b)
    rest = cleaned

    # h2 목록으로 목차 생성
    h2s = [(i, b[2]) for i, b in enumerate(rest) if b[0] == "h" and b[1] == 2]
    heads = {}
    for n, (idx, txt) in enumerate(h2s, 1): heads[idx] = slug(txt, n)

    total = sum(text_len(b) for b in rest) or 1

    out = []
    # 결론 박스
    if lede:
        out.append('<div class="lede">')
        for b in lede:
            if b[0] == "p": out.append(f"  <p>{inline(b[2])}</p>")
            elif b[0] == "ul":
                out.append("  <ul>")
                for it in b[2]: out.append(f"    <li>{inline(it)}</li>")
                out.append("  </ul>")
        out.append("</div>\n")

    out.append(ad_block(1))

    # 목차
    if h2s:
        out.append('<nav class="toc">')
        out.append('  <p class="toc-t">목차</p>')
        out.append("  <ol>")
        for n, (idx, txt) in enumerate(h2s, 1):
            clean = re.sub(r'^\d+\.\s*', '', txt)
            out.append(f'    <li><a href="#{heads[idx]}">{inline(clean)}</a></li>')
        out.append("  </ol>")
        out.append("</nav>\n")

    # 본문
    faq, related, disclaimer = [], [], []
    mode, run, ad2_done = None, 0, False
    for i, b in enumerate(rest):
        k, lv, v = b
        run += text_len(b)

        if k == "h":
            t = re.sub(r'^\d+\.\s*', '', v)
            if re.search(r'자주\s*묻는\s*질문', v): mode = "faq";
            elif re.search(r'함께\s*보면', v): mode = "rel"; continue
            else: mode = None
            if mode == "faq":
                out.append(f'<h2 id="{heads.get(i,"faq")}">{inline(t)}</h2>')
                out.append('<div class="faq">')
                continue
            tag = f"h{min(lv,3)}"
            idp = f' id="{heads[i]}"' if i in heads else ""
            out.append(f'<{tag}{idp}>{inline(t)}</{tag}>')
            continue

        if mode == "rel":
            if k == "ul": related = v
            continue

        if mode == "faq":
            if k == "p":
                m = re.match(r'^\*\*(Q\d+\..*?)\*\*\s*(.*)$', v)
                if m:
                    # 질문과 답이 한 문단으로 붙어 오는 경우가 많다.
                    # 답변을 버리지 않도록 둘 다 출력한다.
                    faq.append([m.group(1), m.group(2)])
                    out.append(f'  <p class="faq-q">{inline(m.group(1))}</p>')
                    if m.group(2).strip():
                        out.append(f'  <p class="faq-a">{inline(m.group(2))}</p>')
                elif faq:
                    faq[-1][1] = (faq[-1][1] + " " + v).strip()
                    out.append(f'  <p class="faq-a">{inline(v)}</p>')
                continue

        if k == "p": out.append(f"<p>{inline(v)}</p>")
        elif k == "ul":
            out.append("<ul>")
            for it in v: out.append(f"  <li>{inline(it)}</li>")
            out.append("</ul>")
        elif k == "ol":
            out.append("<ol>")
            for it in v: out.append(f"  <li>{inline(it)}</li>")
            out.append("</ol>")
        elif k == "table": out.append(table_html(v))
        elif k == "code":
            out.append(f'<div class="tip">{inline(v).replace(chr(10), "<br>")}</div>')
        elif k == "quote":
            if i > len(rest) - 4: disclaimer.append(v)
            else: out.append(f'<div class="tip">{inline(v)}</div>')
        elif k == "hr": pass

        # AD2 삽입: 누적 50% 넘고 다음이 h2일 때
        if (not ad2_done and run / total >= 0.5
                and i + 1 < len(rest) and rest[i+1][0] == "h"):
            out.append("")
            out.append(ad_block(2))
            ad2_done = True

    if mode == "faq": out.append("</div>")
    if not ad2_done: out.append(ad_block(2))

    # 관련 글
    if related:
        out.append('\n<div class="related">')
        out.append('  <p class="related-t">함께 보면 좋은 글</p>')
        out.append("  <ul>")
        for it in related:
            t = re.sub(r'^\[|\]$', '', it)
            out.append(f'    <li><a href="/entry/글주소를-여기에">{inline(t)}</a></li>')
        out.append("  </ul>")
        out.append("</div>\n")

    out.append(ad_block(3))

    if disclaimer:
        out.append(f'<p class="disclaimer">{inline(" ".join(disclaimer))}</p>')

    return title, "\n".join(out), faq


CSS = """<style>
/* 본문 폭 확보: 336px보다 좁으면 반응형 광고가 300x250으로 떨어져 eCPM 손해 */
.post-body{font-size:17px;line-height:1.75;color:#222;word-break:keep-all;min-width:0}
.post-body h2{font-size:21px;font-weight:700;margin:44px 0 14px;padding-bottom:8px;
  border-bottom:2px solid #222;letter-spacing:-.01em;scroll-margin-top:20px}
.post-body h3{font-size:18px;font-weight:700;margin:28px 0 10px}
.post-body p{margin:0 0 16px}
.post-body ul,.post-body ol{margin:0 0 18px;padding-left:22px}
.post-body li{margin-bottom:7px}
.post-body code{background:#F2F1EE;padding:1px 5px;border-radius:3px;font-size:15px}

.lede{background:#F7F7F5;border-left:4px solid #C1272D;padding:16px 18px;
  margin:0 0 22px;border-radius:0 4px 4px 0}
.lede p{margin:0 0 10px;font-size:17px}
.lede p:last-child{margin:0}
.lede strong{color:#C1272D}
.lede ul{margin:10px 0 0;padding-left:20px}
.lede li{font-size:15.5px;color:#444}

.toc{border:1px solid #E0DED9;border-radius:4px;padding:16px 18px;margin:0 0 24px;background:#FCFCFB}
.toc-t{font-size:14px;font-weight:700;margin:0 0 10px;color:#555}
.toc ol{margin:0;padding-left:20px}
.toc li{margin-bottom:6px;font-size:15.5px}
.toc a{color:#2F4858;text-decoration:none;border-bottom:1px solid #D6D4CF}

.tbl-wrap{overflow-x:auto;margin:0 0 20px;-webkit-overflow-scrolling:touch}
.post-body table{border-collapse:collapse;width:100%;min-width:340px;font-size:15.5px}
.post-body th,.post-body td{border:1px solid #E0DED9;padding:11px 12px;text-align:left}
.post-body th{background:#F4F3F0;font-weight:700;white-space:nowrap}
.post-body td strong{color:#C1272D}

.tip{background:#F0F4F6;border-left:4px solid #2F4858;padding:14px 16px;
  margin:0 0 20px;border-radius:0 4px 4px 0;font-size:15.5px}
.warn{background:#FBEDED;border-left:4px solid #C1272D;padding:14px 16px;
  margin:0 0 20px;border-radius:0 4px 4px 0;font-size:15.5px}

.faq{border-top:1px solid #E0DED9;margin-top:8px}
.faq-q{font-weight:700;font-size:16.5px;margin:20px 0 8px;color:#1A1A18}
.faq-a{margin:0 0 18px;color:#3A3A38}

.related{border:1px solid #E0DED9;border-radius:4px;padding:18px;margin:0 0 24px;background:#FCFCFB}
.related-t{font-size:15px;font-weight:700;margin:0 0 12px}
.related ul{margin:0;padding-left:20px}
.related li{margin-bottom:9px;font-size:16px}
.related a{color:#2F4858;text-decoration:none;border-bottom:1px solid #C9C7C2}

.disclaimer{margin-top:28px;padding-top:16px;border-top:1px solid #E8E6E1;
  font-size:13.5px;color:#777;line-height:1.7}

/* 광고 슬롯: min-height로 자리를 예약해 레이아웃 이동(CLS)을 막습니다.
   광고가 늦게 로드되며 본문이 밀리면 오클릭이 나고, 오클릭은 무효 트래픽으로
   잡힐 수 있습니다. 상하 28px 여백 = 정책상 20px 이격 기준 충족. */
.ad-slot{margin:28px 0;display:flex;flex-direction:column;align-items:center}
.ad-slot .ad-label{font-size:11px;color:#AAA;letter-spacing:.08em;margin-bottom:6px;align-self:flex-start}
.ad-slot ins{display:block;width:100%}
.ad-inline{min-height:280px}
.ad-multiplex{min-height:400px}

@media(max-width:600px){
  .post-body{font-size:16px}
  .post-body h2{font-size:19px}
  .ad-slot{margin:24px 0}
  .ad-inline{min-height:250px}
  .ad-multiplex{min-height:600px}
}
</style>"""


def head_comment(title, meta):
    return f"""<!--
============================================================
티스토리 HTML 모드에 그대로 붙여넣으세요.

■ 글 제목 (티스토리 제목 칸에 입력)
   {title}

■ 제목 계층
   본문에 h1을 넣지 않았습니다. 티스토리 스킨이 글 제목을 h1으로
   렌더링하므로, 본문에 h1을 또 쓰면 제목이 두 개가 되어 색인에 불리합니다.
   본문은 h2(대목차) / h3(소목차)만 사용합니다.
   목차의 각 항목은 h2의 id와 앵커로 연결돼 있습니다.

■ 마크다운 기호 없음
   ** # | - > 같은 기호를 전부 HTML 태그로 변환했습니다.
   에디터에 붙여넣었을 때 기호가 글자로 찍히지 않습니다.

■ 자동광고 설정 (겹침 방지 - 중요)
   애드센스 → 광고 → 사이트별 → 편집
     앵커 광고        ON     모바일 하단 고정
     전면 광고        ON     링크 클릭 시 Vignette 자동 노출
     페이지 내 광고   OFF    ← 아래 수동 3개와 겹치지 않게 반드시 끄세요

■ 붙여넣기 후 할 일
   1. ca-pub-여기에본인퍼블리셔ID / 여기에광고단위ID 를 실제 값으로 교체
   2. 관련 글의 /entry/글주소를-여기에 를 실제 글 주소로 교체
   3. 대표 이미지 1200px 이상 가로형 지정
   4. 발행 후 서치콘솔 URL 검사 → 색인 요청

■ 절대 넣지 마세요 (계정 영구정지 + 미지급 수익 몰수)
   광고 클릭 유도 문구 / 광고를 가리키는 화살표 /
   버튼 클릭을 광고 노출 트리거로 삼는 스크립트 /
   광고를 콘텐츠나 버튼으로 위장하는 배치

   블로그: {meta.get('블로그','')}
   키워드: {meta.get('키워드','')}
============================================================
-->"""


def faq_schema(faq):
    items = []
    for q, a in faq:
        q = re.sub(r'^Q\d+\.\s*', '', q).strip()
        a = re.sub(r'\*\*(.+?)\*\*', r'\1', a).strip()
        if q and a:
            items.append({"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}})
    if not items: return ""
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items}
    return ('\n<!-- FAQ 구조화 데이터. 본문과 다른 내용을 쓰면 정책 위반입니다.\n'
            '     반드시 본문과 동일하게 유지하세요. -->\n'
            '<script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, indent=1) + '\n</script>')


LEFTOVER = re.compile(r'(\*\*)|(^#{1,6}\s)|(^\s*\|)|(^\s*>\s)|(^\s*[-*]\s)', re.M)

def build(path, outdir):
    raw = open(path, encoding="utf-8").read()
    meta, body = {}, raw
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); meta[k.strip()] = v.strip()
        body = m.group(2)

    title, inner, faq = convert(body.strip(), meta)
    doc = "\n".join([head_comment(title, meta), "", CSS, "",
                     '<div class="post-body">', "", inner, "", "</div>",
                     faq_schema(faq)])

    # 검증: 마크다운 잔여 기호
    check = re.sub(r'<!--.*?-->', '', doc, flags=re.S)
    check = re.sub(r'<script.*?</script>', '', check, flags=re.S)
    check = re.sub(r'<style.*?</style>', '', check, flags=re.S)
    bad = [l for l in check.split("\n") if LEFTOVER.search(l)]

    os.makedirs(outdir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0] + ".html"
    out = os.path.join(outdir, name)
    open(out, "w", encoding="utf-8").write(doc)

    txt = re.sub(r'\s', '', re.sub(r'<[^>]+>', ' ',
          re.sub(r'<!--.*?-->|<script.*?</script>|<style.*?</style>', '', doc, flags=re.S)))
    return {"out": out, "title": title, "chars": len(txt), "faq": len(faq),
            "h2": doc.count("<h2"), "h3": doc.count("<h3"),
            "ads": doc.count('class="ad-slot'), "leftover": bad}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("-o", "--out", default="content/articles/html")
    a = p.parse_args()
    fail = 0
    for f in a.files:
        r = build(f, a.out)
        flag = "OK " if not r["leftover"] else "WARN"
        if r["leftover"]: fail += 1
        print(f"{flag} {os.path.basename(r['out'])}")
        print(f"     {r['title'][:56]}")
        print(f"     {r['chars']}자 h2:{r['h2']} h3:{r['h3']} 광고:{r['ads']} FAQ:{r['faq']}")
        for l in r["leftover"][:3]:
            print(f"     ! 마크다운 잔여: {l.strip()[:70]}")
    print(f"\n{len(a.files)}편 변환, 경고 {fail}편")


if __name__ == "__main__":
    main()
