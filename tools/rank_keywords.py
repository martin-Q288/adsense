#!/usr/bin/env python3
"""실측 검색량 기반 키워드 우선순위 산정.

네이버 검색광고 API로 받은 keywords/volume.csv를 점수화합니다.

■ 2026-08-02 공식 수정 (중요)
  초판은 `(1 − 경쟁도)²`로 광고 경쟁도가 낮을수록 점수를 올렸습니다.
  SEO 진입이 쉬울 것이라는 의도였으나 두 가지가 틀렸습니다.

  1. compIdx는 광고 경쟁도이지 SEO 경쟁도가 아닙니다. SERP를 직접 확인해
     보니 실업급여계산기·부동산양도세계산기·청년미래적금 모두 상위가
     정부기관·은행·대형플랫폼·전용도구로 채워져 있고 블로그는 0개였습니다.
  2. 애드센스 RPM은 광고주 입찰이 만듭니다. 광고가 0~2개라는 건 그 트래픽에
     돈을 낼 광고주가 없다는 뜻이고, 곧 RPM이 낮다는 뜻입니다.
     즉 낮은 광고 경쟁도는 기회 신호가 아니라 수익성 경고 신호입니다.

  → 경쟁도·광고수를 RPM 대리지표로 삼아 점수를 올리는 방향으로 바꾸고,
    SEO 진입 가능성은 질의 유형으로 별도 판정합니다.

점수 = log10(월검색량) × 단가티어 × RPM계수 × 질의유형계수

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


# 질의 유형 — 블로그가 상위노출을 가져갈 수 있는 형태인가
TOOL_Q = ["계산기", "조회", "발급", "로그인", "홈페이지", "사이트",
          "바로가기", "신청하기", "앱", "다운로드"]
BRAND_Q = ["은행", "카드", "증권", "보험사", "우체국", "카카오", "토스",
           "신한", "국민", "하나", "우리", "농협", "삼성", "현대", "KB"]
INFO_Q = ["조건", "방법", "사유", "차이", "얼마", "언제", "서류", "자격",
          "기준", "대상", "신청방법", "지급일", "후기", "비교", "추천",
          "안될때", "거절", "탈락", "주의", "실수"]


def query_type(kw):
    """도구형·브랜드형은 블로그가 못 먹는다. 정보형이 블로그 영역."""
    flat = kw.replace(" ", "")
    if any(w in flat for w in TOOL_Q):
        return "도구형", 0.15
    if any(w in flat for w in INFO_Q):
        return "정보형", 1.30
    if any(w in flat for w in BRAND_Q):
        return "브랜드형", 0.30
    return "단일어", 0.55       # "국민연금" 같은 단독 명사 = 공식사이트가 먹음


def rpm_factor(comp, ad_depth):
    """광고 경쟁도와 노출 광고 수를 RPM 대리지표로 사용.

    광고주가 많이 붙는 키워드일수록 페이지 RPM이 높다.
    광고 0~1개는 붙을 광고 인벤토리 자체가 빈약하다는 뜻이다.
    """
    return (0.4 + comp) * (0.5 + min(ad_depth, 10) / 10)


def score(volume, tier, comp, ad_depth, qfactor):
    if volume < 100:
        return 0.0
    return (math.log10(volume) * tier
            * rpm_factor(comp, ad_depth) * qfactor * 100)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--blog", choices=["T1", "T2", "N"])
    p.add_argument("--min-volume", type=int, default=1000)
    p.add_argument("--min-comp", type=float, default=0.0,
                   help="최소 광고 경쟁도 (RPM 하한 역할)")
    p.add_argument("--min-ads", type=int, default=0,
                   help="최소 노출 광고 수. 0~1이면 RPM이 낮습니다")
    p.add_argument("--info-only", action="store_true",
                   help="정보형 질의만 (블로그가 먹을 수 있는 것)")
    p.add_argument("--longtail", action="store_true",
                   help="신규 블로그 진입 구간 프리셋: 검색량 300~3,000 + 광고 5개 이상.\n"
                        "대형 키워드는 법무법인·보험사가 전담 페이지로 방어하지만\n"
                        "이 구간은 그들이 페이지를 만들 유인이 없으면서 광고는 붙습니다.")
    p.add_argument("--max-volume", type=int, default=10**9)
    p.add_argument("-o", "--out")
    a = p.parse_args()
    if a.longtail:
        a.min_volume, a.max_volume, a.min_ads = 300, 3000, 5

    bank = load_bank()
    rows = []
    with open(VOL, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kw = r["keyword"].strip()
            vol = int(r["total"])
            comp = float(r["competition"])
            if vol < a.min_volume or vol > a.max_volume or comp < a.min_comp:
                continue
            if int(r["ad_depth"]) < a.min_ads:
                continue
            if EXCLUDE.search(kw):
                continue
            tier, hint = tier_and_blog(kw, bank)
            blog = assign_blog(kw, hint)
            depth = int(r["ad_depth"])
            qt, qf = query_type(kw)
            rows.append({
                "keyword": kw, "volume": vol,
                "comp": r["comp_label"], "competition": comp,
                "ad_depth": depth, "qtype": qt,
                "tier": tier, "blog": blog,
                "score": round(score(vol, tier, comp, depth, qf), 1),
            })

    if a.info_only:
        rows = [r for r in rows if r["qtype"] == "정보형"]
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
          f"{'유형':>8}{'티어':>5}{'점수':>8}")
    print("-" * 74)
    for r in rows[:a.top]:
        print(f"{r['keyword'][:24]:<26}{r['volume']:>10,}{r['comp']:>6}"
              f"{r['ad_depth']:>5}{r['qtype']:>8}{r['tier']:>5}{r['score']:>8.0f}")
    print("-" * 74)
    print(f"조건 통과 {len(rows):,}개")
    print("\n※ 점수는 수익 잠재력입니다. SEO 진입 가능성은 질의유형으로만")
    print("   근사한 것이므로, 발행 전 실제 검색으로 상위 10개에 블로그가")
    print("   있는지 반드시 확인하세요.")


if __name__ == "__main__":
    main()
