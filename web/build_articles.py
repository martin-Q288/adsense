#!/usr/bin/env python3
"""content/articles/*.md → 모바일 열람·복사용 단일 HTML."""
import glob, json, os, re, html

ROOT = os.path.join(os.path.dirname(__file__), "..")

# 발행 우선순위 (docs/16). 파일명 날짜가 아니라 실제 마감 기준.
# 목록에 없는 파일은 뒤로 붙는다 (파일명순).
PRIORITY = [
    "2026-08-03_T1_말복-보양식",
    "2026-08-03_T1_광복절-대체공휴일",
    "2026-08-02_T1_에어컨-전기요금-누진세",
    "2026-08-03_T1_쿠팡-고객센터-전화번호",
    "2026-08-02_T1_근로장려금-지급일-신청자격",
    "2026-08-02_T1_실업급여-조건",
    "2026-08-02_T1_퇴직금-계산방법",
    "2026-08-02_T1_전세보증보험-가입방법",
    "2026-08-02_N_전입신고-확정일자",
]

def sort_key(path):
    base = os.path.basename(path).removesuffix(".html")
    try:
        return (0, PRIORITY.index(base))
    except ValueError:
        return (1, base)

arts = []
for p in sorted((x for x in glob.glob(f"{ROOT}/content/articles/html/*.html")
               if not x.endswith(".mobile.html")), key=sort_key):
    raw = open(p, encoding="utf-8").read()
    head = re.search(r"<!--(.*?)-->", raw, re.S)
    h = head.group(1) if head else ""
    def field(label):
        m = re.search(label + r"\s*[:\n]\s*(.+)", h)
        return m.group(1).strip() if m else ""
    title = ""
    m = re.search(r"글 제목 \(티스토리 제목 칸에 입력\)\n\s*(.+)", h)
    if m: title = m.group(1).strip()
    txt = re.sub(r"<!--.*?-->|<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    txt = re.sub(r"\s", "", re.sub(r"<[^>]+>", " ", txt))
    blog = re.search(r"블로그:\s*(.+)", h)
    arts.append({
        "file": os.path.basename(p),
        "title": title or os.path.basename(p),
        "blog": blog.group(1).strip() if blog else "",
        "kw": (re.search(r"키워드:\s*(.+)", h).group(1).strip()
               if re.search(r"키워드:\s*(.+)", h) else ""),
        "rpm": f"{len(txt)}자",
        "len": f"h2 {raw.count('<h2')} · 광고 {raw.count(chr(34)+'ad-slot')}",
        "md": raw,
        "mob": open(p.replace(".html", ".mobile.html"), encoding="utf-8").read(),
    })

tpl = open(os.path.join(os.path.dirname(__file__), "articles.tpl.html"), encoding="utf-8").read()
out = os.path.join(os.path.dirname(__file__), "articles.html")
data = json.dumps(arts, ensure_ascii=False, separators=(",", ":"))
# 기사 HTML에 </script>가 들어 있으면 브라우저가 스크립트 블록을 조기 종료한다.
data = data.replace("</script>", "<\\/script>").replace("<!--", "<\\!--")
open(out, "w", encoding="utf-8").write(tpl.replace("/*__ARTS__*/", data))
print("wrote", out, len(arts), "articles",
      sum(len(a["md"]) for a in arts), "chars")
