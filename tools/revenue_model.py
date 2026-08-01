#!/usr/bin/env python3
"""애드센스 수익 목표 역산 및 시나리오 시뮬레이션.

사용법:
    python3 tools/revenue_model.py                      # 전체 리포트
    python3 tools/revenue_model.py --goal 10000000      # 목표액 변경
    python3 tools/revenue_model.py --scenario aggressive
"""

import argparse

# 니치별 RPM(1,000 PV당 원) 실무 관측 범위
RPM_BANDS = {
    "연예/이슈": (800, 2000),
    "일반정보/생활": (1500, 3500),
    "IT/제품리뷰": (2500, 5000),
    "금융/보험/법률(YMYL)": (5000, 15000),
}

# 31일 시나리오 (docs/11 3분할 구조 기준: T1 10 + T2 5 + N 3 = 18편/일)
# 애드센스 수익은 T1+T2에서만 발생. N은 유입 공급만 함.
# (일평균 발행수, 8월말 T1+T2 합산 일PV, 가중평균RPM)
#
# 4분할 → 3분할 통합 효과는 내부링크·도메인신뢰도 집중으로 +15~25% 수준.
# 자릿수를 바꾸지는 못하므로 base를 소폭 상향 반영.
SCENARIOS = {
    "conservative": (18, 3500, 1500),
    "base": (18, 14000, 2300),          # 홈판 미적중, 검색 유입만
    "homepan_1hit": (18, 32000, 2500),  # 네이버 홈판 1회 적중
    # 홈판 주 2~3회 재현 = 1000만원 경로.
    # 채널 실측 주장(하루 10만 유입 / 하루 60만원 = 월 1800만원)을 RPM 보수화해 반영
    "homepan_repeat": (18, 100000, 3300),
}


def won(n):
    return f"₩{n:,.0f}"


def backsolve(goal, blogs=2):
    print(f"\n{'='*68}")
    print(f" 목표 {won(goal)}/월 달성에 필요한 트래픽 역산 (블로그 {blogs}개)")
    print(f"{'='*68}")
    print(f"{'니치':<24}{'RPM':>8}{'필요 월PV':>14}{'필요 일PV':>12}{'T1/T2 각 일PV':>14}")
    print("-" * 68)
    for niche, (lo, hi) in RPM_BANDS.items():
        for rpm in (lo, hi):
            monthly_pv = goal / rpm * 1000
            daily_pv = monthly_pv / 30
            print(
                f"{niche:<24}{rpm:>8,}{monthly_pv:>14,.0f}"
                f"{daily_pv:>12,.0f}{daily_pv/blogs:>14,.0f}"
            )
    print("-" * 68)
    print(" 참고: 신규 티스토리 1개월차 실측 트래픽 = 일 100 ~ 2,000 PV")


def simulate(goal, days=31):
    print(f"\n{'='*68}")
    print(f" 31일 시나리오별 8월 말 예상 실적")
    print(f"{'='*68}")
    print(f"{'시나리오':<16}{'일발행':>8}{'8/31 일PV':>12}{'RPM':>8}"
          f"{'일수익':>11}{'월 run-rate':>14}{'목표대비':>9}")
    print("-" * 68)
    for name, (posts, pv, rpm) in SCENARIOS.items():
        daily_rev = pv * rpm / 1000
        run_rate = daily_rev * 30
        pct = run_rate / goal * 100
        print(
            f"{name:<16}{posts:>8}{pv:>12,}{rpm:>8,}"
            f"{won(daily_rev):>11}{won(run_rate):>14}{pct:>8.1f}%"
        )
    print("-" * 68)
    total_posts = SCENARIOS["homepan_repeat"][0] * days
    print(f" 최대 강도 기준 8월 누적 발행량: {total_posts}편 (T1+T2+N 합산)")


def payout_timeline():
    print(f"\n{'='*68}")
    print(" 실제 입금 시점")
    print(f"{'='*68}")
    rows = [
        ("애드센스", "8월 수익", "9월 초 확정", "9월 21~26일 입금"),
        ("쿠팡파트너스", "8월 수익", "9월 초 확정", "9월 15일경 입금"),
    ]
    for src, period, confirm, pay in rows:
        print(f"  {src:<14} {period:<10} → {confirm:<14} → {pay}")
    print("\n  ※ 8월 활동분이 8월 안에 입금되는 경로는 존재하지 않습니다.")
    print("     '8/31까지 월 1,000만원'은 run-rate(발생 기준)로만 정의 가능합니다.")


def gap_analysis(goal):
    print(f"\n{'='*68}")
    print(" 목표까지의 경로")
    print(f"{'='*68}")
    for name in ("base", "homepan_1hit", "homepan_repeat"):
        _, pv, rpm = SCENARIOS[name]
        rr = pv * rpm / 1000 * 30
        mark = " ← 목표 달성" if rr >= goal else f"  (목표까지 {goal/rr:.1f}배)"
        print(f"  {name:<18}{won(rr):>14}{mark}")
    print(f"\n  → 월 {won(goal)}은 '홈판 반복 적중'에서만 나옵니다.")
    print(f"     발행량만으로는 도달하지 않습니다. docs/06-핵심플레이북.md 참조.")
    print(f"     최대 분기점: 8/14 홈판 노출 여부 게이트")
    print(f"\n  [대안] 월 {won(goal)} 수익 사이트 매입 시세: "
          f"{won(goal*20)} ~ {won(goal*40)}  (docs/05 참조)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--goal", type=int, default=10_000_000, help="월 목표 수익(원)")
    p.add_argument("--blogs", type=int, default=2, help="애드센스 블로그 수(T1,T2)")
    p.add_argument("--scenario", choices=list(SCENARIOS), help="특정 시나리오만 출력")
    a = p.parse_args()

    if a.scenario:
        posts, pv, rpm = SCENARIOS[a.scenario]
        rev = pv * rpm / 1000
        print(f"\n[{a.scenario}] 일발행 {posts}편 / 8월말 일PV {pv:,} / RPM {rpm:,}")
        print(f"  일수익 {won(rev)}  월 run-rate {won(rev*30)}  "
              f"목표대비 {rev*30/a.goal*100:.1f}%")
        return

    backsolve(a.goal, a.blogs)
    simulate(a.goal)
    payout_timeline()
    gap_analysis(a.goal)
    print()


if __name__ == "__main__":
    main()
