#!/usr/bin/env python3
"""content/articles/*.md → 모바일 열람·복사용 단일 HTML."""
import glob, json, os, re, html

ROOT = os.path.join(os.path.dirname(__file__), "..")
arts = []
for p in sorted(glob.glob(f"{ROOT}/content/articles/*.md")):
    raw = open(p, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    meta, body = ({}, raw)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2).strip()
    title = re.search(r"^#\s+(.+)$", body, re.M)
    arts.append({
        "file": os.path.basename(p),
        "title": title.group(1) if title else os.path.basename(p),
        "blog": meta.get("블로그", ""),
        "kw": meta.get("키워드", ""),
        "rpm": meta.get("예상 RPM", ""),
        "len": meta.get("분량", ""),
        "md": body,
    })

tpl = open(os.path.join(os.path.dirname(__file__), "articles.tpl.html"), encoding="utf-8").read()
out = os.path.join(os.path.dirname(__file__), "articles.html")
open(out, "w", encoding="utf-8").write(
    tpl.replace("/*__ARTS__*/", json.dumps(arts, ensure_ascii=False, separators=(",", ":"))))
print("wrote", out, len(arts), "articles",
      sum(len(a["md"]) for a in arts), "chars")
