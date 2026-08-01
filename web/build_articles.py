#!/usr/bin/env python3
"""content/articles/*.md → 모바일 열람·복사용 단일 HTML."""
import glob, json, os, re, html

ROOT = os.path.join(os.path.dirname(__file__), "..")
arts = []
for p in sorted(glob.glob(f"{ROOT}/content/articles/html/*.html")):
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
    })

tpl = open(os.path.join(os.path.dirname(__file__), "articles.tpl.html"), encoding="utf-8").read()
out = os.path.join(os.path.dirname(__file__), "articles.html")
data = json.dumps(arts, ensure_ascii=False, separators=(",", ":"))
# 기사 HTML에 </script>가 들어 있으면 브라우저가 스크립트 블록을 조기 종료한다.
data = data.replace("</script>", "<\\/script>").replace("<!--", "<\\!--")
open(out, "w", encoding="utf-8").write(tpl.replace("/*__ARTS__*/", data))
print("wrote", out, len(arts), "articles",
      sum(len(a["md"]) for a in arts), "chars")
