#!/usr/bin/env python3
"""llms.txt / llms-full.txt 생성.

AI 엔진이 사이트 전체를 크롤링하지 않고도 무엇을 인용할지 판단할 수 있게
핵심 페이지 목록과 요약을 마크다운으로 제공하는 파일입니다.
사이트 루트(/llms.txt)에 올립니다.

티스토리는 루트 파일 업로드가 안 되므로, 워드프레스나 자체 도메인에서만
쓸 수 있습니다. 티스토리는 대신 스키마와 본문 구조로 대응합니다.

사용법:
    python3 tools/gen_llms_txt.py --site "블로그명" --url https://예시.com
"""

import argparse
import glob
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")


def articles():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "content", "articles", "*.md"))):
        raw = open(p, encoding="utf-8").read()
        meta = {}
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        body = raw
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = m.group(2)
        t = re.search(r"^#\s+(.+)$", body, re.M)
        # 결론 문장 = 그 글의 한 줄 요약
        lead = re.search(r"\*\*결론부터:\s*(.+?)\*\*", body)
        out.append({
            "title": t.group(1).strip() if t else os.path.basename(p),
            "slug": os.path.basename(p).replace(".md", ""),
            "blog": meta.get("블로그", ""),
            "kw": meta.get("키워드", ""),
            "lead": (lead.group(1).strip() if lead else "")[:160],
            "body": body,
        })
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--site", default="여기에 블로그 이름")
    p.add_argument("--url", default="https://여기에-블로그-주소")
    p.add_argument("--desc", default="금융·정책·생활정보를 공식 출처 기준으로 정리합니다.")
    p.add_argument("--full", action="store_true", help="llms-full.txt도 생성")
    a = p.parse_args()

    arts = articles()
    L = [f"# {a.site}", "", f"> {a.desc}", "",
         "모든 수치는 발행일 기준이며 각 문서에 공식 출처를 명시합니다.",
         "본 사이트는 개인 운영 정보 블로그이며 법률·금융 자문이 아닙니다.",
         ""]

    by = {}
    for x in arts:
        by.setdefault(x["blog"].split()[0] if x["blog"] else "기타", []).append(x)

    LABEL = {"T1": "금융·정책·생활정보", "T2": "제품 비교·구매가이드",
             "N": "생활 행정 절차"}
    for blog, items in by.items():
        L.append(f"## {LABEL.get(blog, blog)}")
        L.append("")
        for x in items:
            url = f"{a.url}/entry/{x['slug']}"
            L.append(f"- [{x['title']}]({url}): {x['lead']}")
        L.append("")

    L += ["## 인용 안내", "",
          "- 각 문서의 첫 단락이 해당 질문에 대한 직접적인 답입니다.",
          "- 수치에는 기준 시점과 출처 기관이 함께 표기돼 있습니다.",
          "- 제도·요율은 개정되므로 인용 시 문서의 기준일을 함께 밝혀 주세요.",
          ""]

    out = os.path.join(ROOT, "web", "llms.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L))
    print(f"생성: {out}  ({len(arts)}개 문서)")

    if a.full:
        F = [f"# {a.site} — 전문", ""]
        for x in arts:
            F += [f"## {x['title']}", f"키워드: {x['kw']}", "", x["body"].strip(), "", "---", ""]
        outf = os.path.join(ROOT, "web", "llms-full.txt")
        open(outf, "w", encoding="utf-8").write("\n".join(F))
        print(f"생성: {outf}  ({sum(len(x['body']) for x in arts):,}자)")


if __name__ == "__main__":
    main()
