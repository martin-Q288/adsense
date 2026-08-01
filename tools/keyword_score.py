#!/usr/bin/env python3
"""키워드 우선순위 스코어링.

CSV 컬럼: keyword,monthly_volume,cpc,competition,niche
  monthly_volume : 월 검색량 (네이버 검색광고 키워드도구)
  cpc            : 예상 클릭당 단가(원) (구글 키워드플래너)
  competition    : 0.0 ~ 1.0 (낮을수록 유리)
  niche          : 블로그 배정용 태그

점수 = log(검색량) × CPC가중 × (1 - 경쟁도)^2
경쟁도에 제곱 가중을 준 이유: 신규 블로그는 경쟁 키워드에서 사실상 0위입니다.
검색량이 커도 못 먹으면 의미가 없어서 경쟁도를 가장 강하게 반영합니다.

사용법:
    python3 tools/keyword_score.py keywords/seed.csv
    python3 tools/keyword_score.py keywords/seed.csv --top 30 --niche 금융
"""

import argparse
import csv
import math
import sys


def score(volume, cpc, competition):
    if volume <= 0:
        return 0.0
    vol_w = math.log10(volume + 1)
    cpc_w = math.log10(cpc + 1) if cpc > 0 else 0.1
    comp_w = max(0.0, 1.0 - competition) ** 2
    return vol_w * cpc_w * comp_w * 100


def load(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            try:
                rows.append({
                    "keyword": r["keyword"].strip(),
                    "volume": int(float(r["monthly_volume"])),
                    "cpc": float(r["cpc"]),
                    "competition": float(r["competition"]),
                    "niche": r.get("niche", "").strip(),
                })
            except (KeyError, ValueError) as e:
                print(f"  [skip] line {i}: {e}", file=sys.stderr)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_path")
    p.add_argument("--top", type=int, default=50)
    p.add_argument("--niche", help="특정 니치만 필터")
    a = p.parse_args()

    rows = load(a.csv_path)
    if a.niche:
        rows = [r for r in rows if a.niche in r["niche"]]
    if not rows:
        print("데이터 없음.")
        return

    for r in rows:
        r["score"] = score(r["volume"], r["cpc"], r["competition"])
        # 글 1편이 상위노출됐을 때의 월 기대수익 (CTR 20%, RPM≈CPC×0.3 가정)
        r["potential"] = r["volume"] * 0.20 * (r["cpc"] * 0.3) / 1000 * 1000
    rows.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n{'순위':<5}{'키워드':<30}{'월검색량':>10}{'CPC':>8}"
          f"{'경쟁도':>8}{'점수':>8}{'월기대수익':>12}")
    print("-" * 82)
    for i, r in enumerate(rows[: a.top], 1):
        print(f"{i:<5}{r['keyword'][:28]:<30}{r['volume']:>10,}"
              f"{r['cpc']:>8,.0f}{r['competition']:>8.2f}"
              f"{r['score']:>8.1f}{r['potential']:>11,.0f}원")
    print("-" * 82)
    total = sum(r["potential"] for r in rows[: a.top])
    print(f"상위 {min(a.top, len(rows))}개 전부 상위노출 시 월 기대수익 합계: "
          f"₩{total:,.0f}")
    print("※ '전부 상위노출'은 현실적으로 불가능합니다. 상한선 참고용 수치입니다.\n")


if __name__ == "__main__":
    main()
