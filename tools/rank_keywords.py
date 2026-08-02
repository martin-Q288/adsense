#!/usr/bin/env python3
"""실측 검색량 기반 키워드 우선순위 산정.

네이버 검색광고 API로 받은 keywords/volume.csv를 점수화합니다.
기존 8축 기계 전개와 달리 여기 있는 키워드는 전부 네이버가 반환한
'실제로 검색되는' 질의입니다.

점수 = log10(월검색량) × 단가티어 × (1 − 경쟁도)²

사용법:
    python3 tools/rank_keywords.py                    # 상위 40개
    python3 tools/rank_keywords.py --top 100 --blog T1
    python3 tools/rank_keywords.py -o keywords/ranked.csv
"""

import argparse
import csv
import math
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
VOL = os.path.join(ROOT, "keywords", "volume.csv")
BANK = os.path.join(ROOT, "keywords", "bank.csv")

# 단가 추정 신호어 → 티어. 뱅크 시드와 매칭 안 될 때 사용
TIER_SIGNALS = [
    (5, ["개인회생", "파산", "회생", "상속", "증여", "합의금", "변호사",
         "임플란트", "전세자금", "주택담보", "신용대출", "대환", "채무",
         "전세사기", "보증보험", "양도세", "양도소득"]),
    (4, ["대출", "보험", "세금", "세액", "환급", "지원금", "장려금",
         "적금", "연금", "펀드", "ETF", "청약", "이자", "수수료",
         "치료", "비용", "견적", "렌탈"]),
    (3, ["신청", "자격", "조건", "계산기", "발급", "조회", "요금",
         "추천", "비교", "후기"]),
]

# 제외: 브랜드·종목·시황 등 정보성 블로그로 다루기 부적합하거나
# 뉴스·증권사이트에 밀리는 것들
EXCLUDE = re.compile(
    r"(증시|지수|나스닥|다우|코스피|코스닥|S&P|환율|주가|"
    r"KODEX|TIGER|ACE|삼성전자|하나카드|KT|SKT|LG유플|네이버페이|"
    r"토스|카카오뱅크|헤이딜러|알닷|판판대로|경리나라)")


def load_bank():
    rows = []
    with open(BANK, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            s = r["seed_keyword"].strip()
            if s:
                rows.append((s.replace(" ", ""), int(r["cpc_tier"]),
                             r["blog"].strip()))
    # 긴 시드부터 매칭 (더 구체적인 것 우선)
    return sorted(rows, key=lambda x: -len(x[0]))


def tier_and_blog(kw, bank):
    flat = kw.replace(" ", "")
    for seed, tier, blog in bank:
        if seed in flat or flat in seed:
            return tier, blog
    for tier, words in TIER_SIGNALS:
        if any(w in kw for w in words):
            return tier, ""
    return 2, ""


def assign_blog(kw, blog_hint):
    if blog_hint:
        return {"A": "T1", "B": "T1", "D": "T1", "C": "T2"}.get(blog_hint, "T1")
    if any(w in kw for w in ["추천", "비교", "순위", "후기", "가격", "렌탈"]):
        return "T2"
    return "T1"


def score(volume, tier, comp):
    if volume < 100:
        return 0.0
    return math.log10(volume) * tier * ((1 - comp) ** 2) * 100


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--blog", choices=["T1", "T2", "N"])
    p.add_argument("--min-volume", type=int, default=1000)
    p.add_argument("--max-comp", type=float, default=1.0)
    p.add_argument("-o", "--out")
    a = p.parse_args()

    bank = load_bank()
    rows = []
    with open(VOL, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kw = r["keyword"].strip()
            vol = int(r["total"])
            comp = float(r["competition"])
            if vol < a.min_volume or comp > a.max_comp:
                continue
            if EXCLUDE.search(kw):
                continue
            tier, hint = tier_and_blog(kw, bank)
            blog = assign_blog(kw, hint)
            rows.append({
                "keyword": kw, "volume": vol,
                "comp": r["comp_label"], "competition": comp,
                "ad_depth": int(r["ad_depth"]),
                "tier": tier, "blog": blog,
                "score": round(score(vol, tier, comp), 1),
            })

    rows.sort(key=lambda x: -x["score"])
    if a.blog:
        rows = [r for r in rows if r["blog"] == a.blog]

    if a.out:
        out = a.out if os.path.isabs(a.out) else os.path.join(ROOT, a.out)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"저장: {out} ({len(rows)}개)\n")

    print(f"{'키워드':<26}{'월검색량':>10}{'경쟁':>6}{'광고':>5}"
          f"{'티어':>5}{'블로그':>7}{'점수':>8}")
    print("-" * 70)
    for r in rows[:a.top]:
        print(f"{r['keyword'][:24]:<26}{r['volume']:>10,}{r['comp']:>6}"
              f"{r['ad_depth']:>5}{r['tier']:>5}{r['blog']:>7}{r['score']:>8.0f}")
    print("-" * 70)
    print(f"조건 통과 {len(rows):,}개 / 전체 검토 대상")


if __name__ == "__main__":
    main()
