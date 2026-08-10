#!/usr/bin/env python3
"""content/articles/*.md → 폰에서 열어 제목·본문을 복사하는 단일 HTML.

에디터가 마크다운을 해석하지 않으므로 md2text로 순수 텍스트를 만들어
싣는다. 제목과 본문은 넣는 칸이 다르니 복사 버튼도 따로 둔다.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from md2text import convert  # noqa: E402
from md2html import convert as to_html  # noqa: E402

# 발행 우선순위 (docs/16). 파일명 날짜가 아니라 실제 마감 기준.
# 목록에 없는 파일은 뒤로 붙는다 (파일명순).
PRIORITY = [
    "2026-08-11_T1_추석-기차표예매-일정",
    "2026-08-10_T1_다이소상품권-사용법",
    "2026-08-10_T1_현대기아-리콜-확인방법",
    "2026-08-10_T1_쿠팡-정보유출-확인방법",
    "2026-08-06_T1_청약통장-순위확인서",
    "2026-08-04_T1_전세사기-피하는법",
    "2026-08-05_T1_전세자금대출-조건",
    "2026-08-03_T1_광복절-대체공휴일",
    "2026-08-02_T1_에어컨-전기요금-누진세",
    "2026-08-03_T1_쿠팡-고객센터-전화번호",
    "2026-08-02_T1_근로장려금-지급일-신청자격",
    "2026-08-02_T1_실업급여-조건",
    "2026-08-02_T1_퇴직금-계산방법",
    "2026-08-02_T1_전세보증보험-가입방법",
    "2026-08-02_N_전입신고-확정일자",
]

# 발행 마감 — 시의성 원고만. 카드에 그대로 뜬다.
DEADLINE = {
    "2026-08-11_T1_추석-기차표예매-일정": "★ 통계 검증 포맷(설날 기차표 DNA) · 예매 공식발표 뜨면 즉시 업데이트",
    "2026-08-10_T1_다이소상품권-사용법": "잡블로그 첫 글 · 뉴스→키워드 추출 방식",
    "2026-08-10_T1_현대기아-리콜-확인방법": "🔴 이슈파생 · 지금 바로 발행 · G80/K8/아반떼는 8/12~13 재조회 유도",
    "2026-08-10_T1_쿠팡-정보유출-확인방법": "🔴 이슈파생 · 지금 바로 발행 (터진 지 시간 지날수록 값 떨어짐)",
    "2026-08-06_T1_청약통장-순위확인서": "니치 발굴 · 경쟁 중간 검색 3,760/월",
    "2026-08-04_T1_전세사기-피하는법": "★★★ 8월 최고단가 · 이사 성수기",
    "2026-08-05_T1_전세자금대출-조건": "★★★ 부동산+대출 최상위",
    "2026-08-03_T1_광복절-대체공휴일": "8/17 연휴 · 8/12까지 발행",
    "2026-08-02_T1_에어컨-전기요금-누진세": "8월 요금고지 전",
    "2026-08-02_T1_근로장려금-지급일-신청자격": "8월 말 지급일 전",
}


def stem(path):
    return os.path.basename(path).removesuffix(".md")


def sort_key(path):
    try:
        return (0, PRIORITY.index(stem(path)))
    except ValueError:
        return (1, stem(path))


arts = []
for p in sorted(glob.glob(f"{ROOT}/content/articles/*.md"), key=sort_key):
    if os.path.basename(p) == "README.md":
        continue
    raw = open(p, encoding="utf-8").read()
    fm = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    meta = fm.group(1) if fm else ""

    def field(name, default=""):
        m = re.search(rf"^{name}:\s*(.+)$", meta, re.M)
        return m.group(1).strip() if m else default

    title, text = convert(raw)
    _, doc = to_html(raw)
    blog = field("블로그")
    arts.append({
        "title": title,
        "html": doc,        # 붙여넣어 바로 발행하는 본문
        "body": text,       # 본문 보기용 평문
        "blog": (re.match(r"(T1|T2|N)", blog) or [""])[0],
        "kw": field("키워드"),
        "len": "{:,}자 · 목차 {}".format(
            len(re.sub(r"\s", "", text)), doc.count('href="#s')),
        "due": DEADLINE.get(stem(p), ""),
    })

tpl = open(os.path.join(os.path.dirname(__file__), "articles.tpl.html"),
           encoding="utf-8").read()
out = os.path.join(os.path.dirname(__file__), "articles.html")
data = json.dumps(arts, ensure_ascii=False, separators=(",", ":"))
# 본문에 </script>가 들어 있으면 브라우저가 스크립트 블록을 조기 종료한다.
data = data.replace("</script>", "<\\/script>").replace("<!--", "<\\!--")
open(out, "w", encoding="utf-8").write(tpl.replace("/*__ARTS__*/", data))
print("wrote", out, len(arts), "articles")
