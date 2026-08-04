#!/usr/bin/env python3
"""발행 파이프라인 — 오늘 날짜만 있으면 끝까지 돈다.

주차에 묶이지 않는다. 언제 실행하든 그 시점 기준으로 뭘 쓸지 뽑고,
원고 틀을 만들고, 텍스트·썸네일·아티팩트까지 한 번에 낸다.

  python3 tools/pipeline.py today            오늘 뭘 쓸지 (등급·마감 순)
  python3 tools/pipeline.py new "전세대출 조건 2026" --blog T1
                                             검색의도 체크리스트가 박힌 원고 틀 생성
  python3 tools/pipeline.py build            전체 산출물 재생성 (텍스트·썸네일·아티팩트)
  python3 tools/pipeline.py status           원고별 발행 준비 상태
"""
import argparse
import datetime as dt
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import keywords_2026 as KW  # noqa: E402

ARTICLES = os.path.join(ROOT, "content/articles")
TIER = {3: "고단가 3,000원↑", 2: "고단가 1,500~3,000원", 1: "트래픽형 500~1,500원"}


def slug(s):
    return re.sub(r"[^\w가-힣]+", "-", s).strip("-")


def existing():
    return {os.path.basename(p) for p in glob.glob(f"{ARTICLES}/*.md")}


def cmd_today(args):
    today = dt.date.today()
    m = today.month
    print(f"\n  {today:%Y-%m-%d} 기준 · {m}월 발행 후보\n")
    print(f"  {'키워드':28s} {'등급':6s} {'구분':6s} 메모")
    print("  " + "-" * 82)
    for k, t, season, memo in KW.pick(m, limit=args.limit):
        mark = "★" * t
        kind = "시즌" if season else "상시"
        print(f"  {k:28s} {mark:6s} {kind:6s} {memo}")
    print(f"""
  등급  ★★★ {TIER[3]}   ★★ {TIER[2]}   ★ {TIER[1]}
  시즌  타이밍이 전부. 지나면 값이 없다
  상시  계절을 안 탄다. 블로그 고정 수익 기반

  황금 키워드 판정 (자료 6단계)
    · 월간검색량 {KW.VOLUME_MIN:,}~{KW.VOLUME_MAX:,}
    · {KW.TARGET_AGE}
    · 키워드에 행동이 붙어야 광고가 붙는다 — {' / '.join(KW.ACTIONS[:6])}

  다음: python3 tools/pipeline.py new "키워드" --blog T1
""")


SCAFFOLD = """---
발행일: {date}
블로그: {blog}
유형: {kind}
등급: {stars}
키워드: {kw}
검색의도: (한 줄로. 무엇을 결정하러 왔는가)
누가: (직업·상황까지. "사람들"은 답이 아님)
직전상황: (검색 직전에 무슨 일이 있었나)
앙꼬: (달력·공식사이트·AI요약이 못 주는 것. 없으면 이 주제는 접는다)
내부링크: (묶을 기존 원고 2편)
분량: 약 2,000자
썸네일_배지: {kw}
썸네일_제목1: {kw}
썸네일_제목2:
썸네일_CTA: 확인하기
---

# {kw} (제목 공식: 메인 + 서브 + 연관검색어 + 총정리)

(첫 문장에 결론. 그다음 문장이 독자의 상황을 짚는다 — docs/17)

· 요약 1
· 요약 2
· 요약 3

## (소제목 1 — 독자가 품고 온 감정을 먼저 받는다)

## (소제목 2 — 숫자와 출처를 이 섹션 안에)

## (소제목 3 — 표 1개 이상, 단위 명시)

## 자주 묻는 질문

**질문 1?**
(첫 문장에서 답이 끝나야 한다)

---

**함께 보면 좋은 글**
- (기존 원고 1)
- (기존 원고 2)
- (기존 원고 3)

> 이 글은 {date}에 정리했습니다. (YMYL이면 공식 출처와 상담 창구를 명시)

<!-- 발행 전 점검 (docs/14 · docs/17)
  [ ] 검색 의도 5칸을 다 채웠는가. 앙꼬가 비면 주제를 바꾼다
  [ ] 제목에 연관검색어를 넣었는가 (구글·네이버에서 직접 확인)
  [ ] 전문용어를 쓴 자리마다 쉬운 말 풀이가 붙었는가
  [ ] 분량용 섹션은 없는가. 500자로 끝날 건 500자로
  [ ] 표에 가격·시간·횟수가 있는가
  [ ] 함께 보면 좋은 글 3줄을 실제 링크로 걸었는가
-->
"""


def cmd_new(args):
    kw = args.keyword
    today = dt.date.today()
    tier, season, memo = 2, False, ""
    for k, t, s, mm in KW.CALENDAR.get(today.month, []):
        if k == kw:
            tier, season, memo = t, s, mm
            break
    else:
        for k, t, mm in KW.EVERGREEN:
            if k == kw:
                tier, season, memo = t, False, mm
                break

    name = f"{today:%Y-%m-%d}_{args.blog}_{slug(kw)}.md"
    path = os.path.join(ARTICLES, name)
    if os.path.exists(path):
        sys.exit(f"이미 있습니다: {name}")
    open(path, "w", encoding="utf-8").write(SCAFFOLD.format(
        date=f"{today:%Y-%m-%d}", blog=args.blog, kw=kw,
        kind=("시즌형 — 타이밍이 전부" if season else "상시형 — 고정 수익 기반"),
        stars="★" * tier + f" ({TIER[tier]})"))
    print(f"만들었습니다: content/articles/{name}")
    if memo:
        print(f"  자료 메모: {memo}")
    print("\n  프런트매터의 검색의도·누가·직전상황·앙꼬 네 칸을 먼저 채우세요.")
    print("  앙꼬가 안 채워지면 그 글은 쓰지 않는 게 맞습니다 (docs/17).")


def run(*cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr)
    return r.returncode == 0


def cmd_build(args):
    mds = sorted(p for p in glob.glob(f"{ARTICLES}/*.md")
                 if os.path.basename(p) != "README.md")
    print(f"원고 {len(mds)}편\n")

    print("[1/3] 텍스트 변환")
    run(sys.executable, "tools/md2text.py", *mds)
    readme = os.path.join(ARTICLES, "text/README.txt")
    if os.path.exists(readme):
        os.remove(readme)

    # gen_thumbnail.py 가 출력 경로를 스스로 정한다 (content/articles/thumbnails).
    # 이미 있는 것은 건너뛴다 — 브라우저를 띄우는 작업이라 느리다.
    print("\n[2/3] 썸네일")
    thumbs = os.path.join(ARTICLES, "thumbnails")
    todo = [p for p in mds if not os.path.exists(
        os.path.join(thumbs, os.path.basename(p)[:-3] + ".png"))]
    if todo:
        run(sys.executable, "tools/gen_thumbnail.py", *todo)
    print(f"  새로 만든 것 {len(todo)}개")

    print("\n[3/3] 아티팩트")
    run(sys.executable, "web/build_articles.py")
    print("\n끝났습니다. web/articles.html 을 Artifact 로 배포하세요.")


# 재가동 램프 — 15개월 휴면이라 크롤러 방문 주기가 길다(docs/16).
# 개수 상한은 다음이 공개한 적이 없다. 아래는 "휴면 뒤 급변을 만들지 않는다"는
# 원칙에서 나온 값이지 공식 기준이 아니다 (docs/19).
RAMP = [(1, 7, 1), (8, 14, 2), (15, 999, 3)]   # (시작일, 끝일, 하루 편수)
SLOTS = ["09:00", "13:00", "19:00"]            # 최소 3시간 간격

# 고단가 카테고리는 신고 대상이 되기 쉽다(자료: 티스토리 저품질 매뉴얼).
# 연속 발행하지 않고 생활정보를 사이에 끼운다.
HIGH_CPC = ["전세", "대출", "보험", "부동산", "월세", "청약", "DSR", "주담대",
            "퇴직", "실업급여", "장려금", "세액", "임플란트", "병원", "의료"]


def is_high_cpc(title):
    return any(w in title for w in HIGH_CPC)


def cmd_plan(args):
    start = dt.date.today()
    rows = []
    for p in sorted(glob.glob(f"{ARTICLES}/*.md")):
        if os.path.basename(p) == "README.md":
            continue
        raw = open(p, encoding="utf-8").read()
        fm = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
        meta = fm.group(1) if fm else ""
        m = re.search(r"^#\s+(.+)$", raw, re.M)
        title = m.group(1).strip() if m else os.path.basename(p)
        due = "시의성" in meta or "시즌" in meta
        rows.append({"t": title, "high": is_high_cpc(title), "due": due,
                     "f": os.path.basename(p)})

    # 마감 있는 것 먼저. 그다음 고단가와 생활정보를 번갈아 낸다.
    urgent = [r for r in rows if r["due"]]
    rest = [r for r in rows if not r["due"]]
    high = [r for r in rest if r["high"]]
    life = [r for r in rest if not r["high"]]
    queue = list(urgent)
    while high or life:
        if life and (not high or (queue and queue[-1]["high"])):
            queue.append(life.pop(0))
        elif high:
            queue.append(high.pop(0))

    print(f"\n  발행 계획 · {start:%Y-%m-%d} 시작 · 원고 {len(queue)}편\n")
    day, i, warned = 0, 0, False
    while i < len(queue):
        day += 1
        cap = next(c for a, b, c in RAMP if a <= day <= b)
        d = start + dt.timedelta(days=day - 1)
        todays = queue[i:i + cap]
        i += cap
        print(f"  {d:%m/%d}({'월화수목금토일'[d.weekday()]})  "
              f"하루 {cap}편")
        prev_high = None
        for k, r in enumerate(todays):
            flag = "고단가" if r["high"] else "생활"
            bad = " ← 고단가 연속" if (prev_high and r["high"]) else ""
            if bad:
                warned = True
            print(f"      {SLOTS[k]}  [{flag:4s}] {r['t'][:44]}{bad}")
            prev_high = r["high"]
        print()

    print(f"""  램프  1~7일차 하루 1편 · 8~14일차 2편 · 15일차부터 3편
  간격  {' / '.join(SLOTS)} — 최소 3시간
  교차  고단가(대출·보험·부동산) 뒤에는 생활정보를 끼운다

  주의  이 숫자는 다음이 공개한 기준이 아니다. 15개월 휴면 뒤
        급변을 만들지 않기 위한 값이다 (docs/19)
""")
    if warned:
        print("  고단가가 연속으로 붙은 날이 있다. 원고를 더 채워 사이를 벌리는 게 좋다.\n")


def cmd_status(args):
    print(f"\n  {'원고':36s} {'글자':>7s} {'의도':4s} {'앙꼬':4s} {'링크':4s}")
    print("  " + "-" * 66)
    for p in sorted(glob.glob(f"{ARTICLES}/*.md")):
        if os.path.basename(p) == "README.md":
            continue
        raw = open(p, encoding="utf-8").read()
        fm = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
        meta = fm.group(1) if fm else ""

        def filled(field):
            m = re.search(rf"^{field}:\s*(.+)$", meta, re.M)
            v = m.group(1).strip() if m else ""
            return "○" if v and not v.startswith("(") else "×"

        body = raw[fm.end():] if fm else raw
        n = len(re.sub(r"\s", "", re.sub(r"<!--.*?-->", "", body, flags=re.S)))
        base = os.path.basename(p)[:36]
        print(f"  {base:36s} {n:>7,} {filled('검색의도'):^4s} "
              f"{filled('앙꼬'):^4s} {filled('내부링크'):^4s}")
    print("\n  × 가 있으면 발행 전에 채우세요 (docs/17)\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("today", help="오늘 기준 발행 후보")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(func=cmd_today)

    p = sub.add_parser("new", help="원고 틀 생성")
    p.add_argument("keyword")
    p.add_argument("--blog", default="T1", choices=["T1", "T2", "N"])
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("plan", help="발행 일정 (램프·간격·카테고리 교차)")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("build", help="전체 산출물 재생성")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("status", help="발행 준비 상태")
    p.set_defaults(func=cmd_status)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
