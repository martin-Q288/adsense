#!/usr/bin/env python3
"""콘텐츠 엔진 — 키워드 뱅크 전체를 발행 큐로 자동 변환.

'뭘 쓸지 고르는' 단계를 없앱니다. 뱅크의 모든 시드를 파생 8축으로 전개하고,
시급성·수익성·진입가능성으로 자동 정렬해서 8/1~8/31 날짜별·블로그별
발행 큐를 통째로 뽑습니다. 매일 아침 그날 큐만 보고 쓰면 됩니다.

사용법:
    python3 tools/content_engine.py queue                 # 전체 31일 큐 생성
    python3 tools/content_engine.py today                 # 오늘 쓸 것만
    python3 tools/content_engine.py today --date 2026-08-13
    python3 tools/content_engine.py brief "추석 기차표 예매"  # 글 템플릿 출력
    python3 tools/content_engine.py stats                 # 커버리지 확인
"""

import argparse
import csv
import os
from datetime import date, datetime, timedelta

from issue_radar import AXES, TYPE_PRIORITY, HIGH_CPC

ROOT = os.path.join(os.path.dirname(__file__), "..")
CAL = os.path.join(ROOT, "keywords", "august_calendar.csv")
BANK = os.path.join(ROOT, "keywords", "bank.csv")
OUT = os.path.join(ROOT, "content", "publish_queue.csv")

START, END = date(2026, 8, 1), date(2026, 8, 31)

# 블로그별 하루 발행 슬롯 (docs/11 실측 근거로 4개 → 3개 통합)
#   T1  금융·정책·생활정보  (구 A+B+D 통합)
#   T2  커머스·제품 비교     (구 C)
#   N   네이버 홈판 엔진
SLOTS = {"N": 3, "T1": 10, "T2": 5}

# 키워드 뱅크의 기존 블로그 표기를 통합 구조로 매핑
BLOG_MAP = {"A": "T1", "B": "T1", "D": "T1", "C": "T2", "N": "N"}

# 축별 진입 난이도 가중 — 롱테일일수록 신규 블로그가 먹기 쉬움
AXIS_WEIGHT = {
    "원본": 1.60,
    "오류/문제해결": 1.30, "준비물/서류": 1.25, "연락처/창구": 1.25,
    "자격/조건": 1.15, "계산/금액": 1.10, "시청/접속": 1.10,
    "방법/절차": 1.00, "비교/대안": 0.90,
}


def d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


# 이미 완성형 검색어인 시드는 축 전개를 최소화한다.
# "전세자금대출 거절 사유"를 또 전개하면 "…거절 사유 고객센터" 같은
# 아무도 안 찾는 조합이 나온다.
READY_TAIL = ("방법", "사유", "조건", "계산", "기간", "절차", "신청",
              "발급", "조회", "비교", "기준", "자격", "해지", "전환")


def is_ready(seed):
    return len(seed.split()) >= 3 or seed.endswith(READY_TAIL)


def expand(seed, itype):
    from issue_radar import expand as _ex
    full = [(ax, kw) for ax, kw, _ in _ex(seed, itype)]
    if is_ready(seed):
        # 시드 자체를 최우선으로 쓰고, 축 전개는 소수만 덧붙인다
        return [("원본", seed)] + full[:3]
    return full


def load_all():
    """캘린더 + 뱅크의 모든 시드를 파생 전개해 후보 전체를 만든다."""
    items = []

    with open(CAL, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            pre, prio = d(r["preempt_date"]), int(r["priority"])
            for axis, kw in expand(r["seed_keyword"], r["type"]):
                items.append({
                    "keyword": kw, "seed": r["seed_keyword"], "axis": axis,
                    "source": "calendar", "blog": "", "earliest": pre,
                    "cpc_tier": min(5, prio // 2 + 2), "priority": prio,
                    "event": r["event"], "event_date": r["event_date"],
                })

    with open(BANK, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            tier = int(r["cpc_tier"])
            for axis, kw in expand(r["seed_keyword"], r["type"]):
                items.append({
                    "keyword": kw, "seed": r["seed_keyword"], "axis": axis,
                    "source": "bank", "blog": r["blog"], "earliest": START,
                    "cpc_tier": tier, "priority": tier, "event": "",
                    "event_date": "",
                })

    # 중복 제거 (같은 키워드가 캘린더·뱅크 양쪽에 나오면 캘린더 우선)
    seen, uniq = {}, []
    for it in sorted(items, key=lambda x: x["source"] != "calendar"):
        if it["keyword"] in seen:
            continue
        seen[it["keyword"]] = True
        uniq.append(it)
    return uniq


def score(it, today=START):
    """수익성 × 진입가능성 × 시급성.

    캘린더 항목은 이벤트가 임박할수록 점수가 올라간다(urgency decay).
    상시 고단가 뱅크를 밀어내지 않도록 부스트 상한을 둔다.
    """
    s = it["cpc_tier"] * 10
    s *= AXIS_WEIGHT.get(it["axis"], 1.0)
    if any(w in it["keyword"] for w in HIGH_CPC):
        s *= 1.25
    if it["source"] == "calendar" and it["event_date"]:
        days_left = (d(it["event_date"]) - today).days
        # 임박 0~7일이면 최대 부스트, 멀수록 감쇠
        urgency = max(0.0, min(1.0, (30 - days_left) / 30))
        s *= 1.0 + 0.8 * urgency
        s += it["priority"] * 2
    return s


def assign_blog(it):
    if it["blog"]:
        return BLOG_MAP.get(it["blog"], "T1")
    kw = it["keyword"]
    if any(w in kw for w in ["추천", "비교", "순위", "후기"]):
        return "T2"
    return "T1"


# 이벤트 우선순위 → 그 이벤트에 예약할 글 수.
# 시즌/정책 키워드는 기한이 있어 놓치면 0원이 되므로 점수 경쟁에 맡기지 않고
# 이벤트별로 슬롯을 먼저 예약한 뒤, 남는 자리를 상시 뱅크로 채운다.
EVENT_QUOTA = {10: 12, 9: 9, 8: 7, 7: 5, 6: 4}


def fits(it, blog):
    """이 키워드를 이 블로그에 배치해도 되는가."""
    if blog == "N":                   # 네이버 홈판: 생활밀착 저단가 위주
        return it["cpc_tier"] <= 3
    return it["blog"] == blog


def reserve_events(items, used):
    """1단계: 캘린더 이벤트별로 선점 기간에 슬롯을 예약한다."""
    from collections import defaultdict
    by_event = defaultdict(list)
    for it in items:
        if it["source"] == "calendar":
            by_event[(it["event"], it["event_date"])].append(it)

    reserved = defaultdict(list)      # (date, blog) -> [item]
    # 우선순위 높은 이벤트부터 자리를 잡는다. CSV 순서로 처리하면
    # 뒤쪽의 우선순위 10 이벤트가 앞쪽 이벤트에 밀려 굶는다.
    ordered = sorted(by_event.items(), key=lambda kv: -kv[1][0]["priority"])
    for (event, edate), pool in ordered:
        prio = pool[0]["priority"]
        quota = EVENT_QUOTA.get(prio, 4)
        start = pool[0]["earliest"]
        end = min(END, d(edate)) if edate else END
        span = max(1, (end - start).days + 1)
        # 축을 골고루 섞어 같은 날 같은 패턴이 몰리지 않게
        pool = sorted(pool, key=lambda x: (-AXIS_WEIGHT.get(x["axis"], 1.0),
                                           x["keyword"]))
        placed = 0
        for it in pool:
            if placed >= quota:
                break
            if it["keyword"] in used:
                continue
            # 선점 기간에 고르게 분산하되, 그 날 그 블로그가 차 있으면
            # 빈 날을 찾아 뒤로 밀어준다 (겹친 예약이 버려지지 않도록)
            target = start + timedelta(days=(placed * span) // quota)
            # 주 블로그가 기간 내내 차 있으면 B(이슈 블로그, 슬롯 최다)로 흘린다
            spot = None
            for blog in (it["blog"], "T1"):
                cap = SLOTS.get(blog, 1)
                day = target
                while day <= END:
                    if len(reserved[(day, blog)]) < cap:
                        spot = (day, blog)
                        break
                    day += timedelta(days=1)
                if spot:
                    break
            if not spot:
                continue
            used.add(it["keyword"])
            reserved[spot].append(it)
            placed += 1
    return reserved


def build_queue():
    items = load_all()
    for it in items:
        it["blog"] = assign_blog(it)

    queue, used = [], set()
    reserved = reserve_events(items, used)

    day = START
    while day <= END:
        # 매일 재채점: 이벤트 임박도가 날마다 바뀐다
        for it in items:
            it["score"] = score(it, day)
        cal = sorted((i for i in items if i["source"] == "calendar"),
                     key=lambda x: -x["score"])
        bank = sorted((i for i in items if i["source"] == "bank"),
                      key=lambda x: -x["score"])

        for blog, n in SLOTS.items():
            filled = 0
            # 하루치가 한 축·한 시드로 쏠리지 않게 제한한다
            day_axis, day_seed = {}, set()
            # 슬롯이 큰 블로그일수록 한 축 쏠림이 심해지므로 1/3로 제한
            axis_cap = max(2, round(n / 3))

            # 예약된 이벤트 글을 먼저 깐다
            for it in reserved.get((day, blog), [])[:n]:
                day_seed.add(it["seed"])
                day_axis[it["axis"]] = day_axis.get(it["axis"], 0) + 1
                queue.append({
                    "date": day.isoformat(), "blog": blog,
                    "keyword": it["keyword"], "seed": it["seed"],
                    "axis": it["axis"], "score": round(score(it, day), 1),
                    "source": it["source"], "event": it["event"],
                })
                filled += 1

            def take(pool, upto, relax=False):
                nonlocal filled
                for it in pool:
                    if filled >= upto:
                        return
                    if it["keyword"] in used or it["earliest"] > day:
                        continue
                    if not fits(it, blog):
                        continue
                    if not relax:
                        if it["seed"] in day_seed:
                            continue
                        if day_axis.get(it["axis"], 0) >= axis_cap:
                            continue
                    day_seed.add(it["seed"])
                    day_axis[it["axis"]] = day_axis.get(it["axis"], 0) + 1
                    used.add(it["keyword"])
                    queue.append({
                        "date": day.isoformat(), "blog": blog,
                        "keyword": it["keyword"], "seed": it["seed"],
                        "axis": it["axis"], "score": round(it["score"], 1),
                        "source": it["source"], "event": it["event"],
                    })
                    filled += 1

            take(bank, n)                 # 남는 자리는 상시 고단가 뱅크로
            take(cal, n)                  # 뱅크가 마르면 캘린더 잔여분
            take(bank, n, relax=True)     # 최후 폴백: 다양성 제약 해제
            take(cal, n, relax=True)
        day += timedelta(days=1)
    return queue, items


def cmd_queue(a):
    queue, items = build_queue()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(queue[0]))
        w.writeheader()
        w.writerows(queue)
    print(f"발행 큐 생성: {OUT}")
    print(f"  전개된 키워드 후보 : {len(items):,}개")
    print(f"  8/1~8/31 배정      : {len(queue):,}편")
    print(f"  미배정 잔여        : {len(items)-len(queue):,}개 (9월 이월분)")
    print(f"\n매일 아침: python3 tools/content_engine.py today")


def cmd_today(a):
    target = a.date or date.today().isoformat()
    if not os.path.exists(OUT):
        build_and_save()
    rows = [r for r in csv.DictReader(open(OUT, encoding="utf-8"))
            if r["date"] == target]
    if not rows:
        print(f"{target} 배정 없음. `queue` 먼저 실행하세요.")
        return
    print(f"\n=== {target} 발행 목록 ({len(rows)}편) ===")
    cur = None
    for r in rows:
        if r["blog"] != cur:
            cur = r["blog"]
            print(f"\n[{cur}] {'네이버 홈판' if cur=='N' else ''}")
        ev = f"  ← {r['event']}" if r["event"] else ""
        print(f"  □ {r['keyword']:<38} ({r['axis']}){ev}")
    print(f"\n템플릿: python3 tools/content_engine.py brief \"키워드\"\n")


def build_and_save():
    queue, _ = build_queue()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(queue[0]))
        w.writeheader()
        w.writerows(queue)


def cmd_brief(a):
    kw = a.keyword
    print(f"""
{'='*66}
글 브리프: {kw}
{'='*66}

[발행 전 30초 확인]
  1. 네이버·구글에 "{kw}" 검색
  2. 상위 10개에 블로그 글이 3개 미만인가? → 예면 진행, 아니면 스킵
  3. 이슈성이면: 발생 후 2시간 이내인가?

[구조]  이슈성 800~1,200자 / 정보성 1,500~2,500자

---
# {kw} (2026년 최신)

**결론부터: [핵심 답 한 문장]**

[요약 3줄 — AI 검색 인용을 노리는 구간. 숫자·날짜·조건을 명시]

## 목차

## {kw}란
[정의 + 배경 2~3문단]

## {kw} 방법 (단계별)
1. [단계]
2. [단계]
3. [단계]
   ※ 번호 목록은 AI 요약 인용률이 가장 높음

## 한눈에 보는 표
| 구분 | 내용 | 비고 |
|---|---|---|
|  |  |  |
   ※ 표는 GEO 인용률 최상. 반드시 1개 이상

## 주의할 점
[실수하기 쉬운 지점 3가지 — 체류시간 상승]

## 자주 묻는 질문
**Q1.** / **A1.**
**Q2.** / **A2.**
**Q3.** / **A3.**
   ※ FAQ 스키마 적용

## 함께 보면 좋은 글
- [내부링크 3~5개]
---

[광고 배치]
  첫 문단 직후 · 목차 하단 · H2 2개마다 · 글 하단 멀티플렉스

[체크]
  □ 제목에 키워드 정확히 포함 + "2026"
  □ 대표 이미지 1200px 이상 가로형 (홈판 필수 조건)
  □ 모바일 화면에서 먼저 검수
  □ 쿠팡 링크 있으면 수수료 고지 문구 필수
  □ 발행 후 서치콘솔 URL 검사 → 색인 요청
""")


def cmd_stats(a):
    queue, items = build_queue()
    from collections import Counter
    print(f"\n키워드 후보 총 {len(items):,}개 / 8월 배정 {len(queue):,}편\n")
    print("[블로그별 배정]")
    for b, n in Counter(r["blog"] for r in queue).most_common():
        print(f"  {b}: {n:>4}편  (일 {n/31:.1f})")
    print("\n[축별 분포]")
    for ax, n in Counter(r["axis"] for r in queue).most_common():
        print(f"  {ax:<12} {n:>4}편")
    print("\n[소스별]")
    for s, n in Counter(r["source"] for r in queue).most_common():
        print(f"  {s:<10} {n:>4}편")
    print(f"\n미배정 잔여 {len(items)-len(queue):,}개 → 9월 이월 가능\n")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("queue")
    t = sub.add_parser("today"); t.add_argument("--date")
    b = sub.add_parser("brief"); b.add_argument("keyword")
    sub.add_parser("stats")
    a = p.parse_args()
    {"queue": cmd_queue, "today": cmd_today,
     "brief": cmd_brief, "stats": cmd_stats}[a.cmd](a)


if __name__ == "__main__":
    main()
