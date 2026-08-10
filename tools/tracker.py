#!/usr/bin/env python3
"""일일 실적 추적 및 run-rate 집계.

사용법:
    python3 tools/tracker.py init              # 8/1~8/31 빈 로그 생성
    python3 tools/tracker.py log 2026-08-05 --blog A --posts 3 --pv 120 --revenue 240
    python3 tools/tracker.py report            # 집계 + 목표 대비 진척
"""

import argparse
import csv
import os
from datetime import date, timedelta

LOG = os.path.join(os.path.dirname(__file__), "..", "content", "daily_log.csv")
HEADER = ["date", "blog", "posts", "indexed", "pv", "revenue_krw", "note"]
BLOGS = ["A", "B", "C", "D"]
GOAL = 10_000_000


def init():
    if os.path.exists(LOG):
        print(f"이미 존재합니다: {LOG}")
        return
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    start, end = date(2026, 8, 1), date(2026, 8, 31)
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        d = start
        while d <= end:
            for b in BLOGS:
                w.writerow([d.isoformat(), b, 0, 0, 0, 0, ""])
            d += timedelta(days=1)
    print(f"생성 완료: {LOG} ({(end-start).days+1}일 × {len(BLOGS)}블로그)")


def read_rows():
    if not os.path.exists(LOG):
        raise SystemExit("로그가 없습니다. 먼저 `tracker.py init` 실행하세요.")
    with open(LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(rows):
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)


def log(a):
    rows = read_rows()
    hit = False
    for r in rows:
        if r["date"] == a.date and r["blog"] == a.blog:
            for field, val in (("posts", a.posts), ("indexed", a.indexed),
                               ("pv", a.pv), ("revenue_krw", a.revenue)):
                if val is not None:
                    r[field] = str(val)
            if a.note:
                r["note"] = a.note
            hit = True
    if not hit:
        raise SystemExit(f"해당 행 없음: {a.date} / {a.blog}")
    write_rows(rows)
    print(f"기록 완료: {a.date} 블로그 {a.blog}")


def report():
    rows = read_rows()
    active = [r for r in rows if int(r["pv"] or 0) > 0 or int(r["posts"] or 0) > 0]

    by_blog = {}
    for r in rows:
        b = by_blog.setdefault(r["blog"], {"posts": 0, "indexed": 0, "pv": 0, "rev": 0})
        b["posts"] += int(r["posts"] or 0)
        b["indexed"] = max(b["indexed"], int(r["indexed"] or 0))
        b["pv"] += int(r["pv"] or 0)
        b["rev"] += float(r["revenue_krw"] or 0)

    print(f"\n{'블로그':<8}{'누적발행':>10}{'색인':>8}{'누적PV':>12}"
          f"{'누적수익':>14}{'RPM':>10}")
    print("-" * 62)
    tot = {"posts": 0, "pv": 0, "rev": 0.0}
    for b in BLOGS:
        d = by_blog.get(b, {"posts": 0, "indexed": 0, "pv": 0, "rev": 0})
        rpm = d["rev"] / d["pv"] * 1000 if d["pv"] else 0
        print(f"{b:<8}{d['posts']:>10,}{d['indexed']:>8,}{d['pv']:>12,}"
              f"{d['rev']:>13,.0f}원{rpm:>10,.0f}")
        tot["posts"] += d["posts"]
        tot["pv"] += d["pv"]
        tot["rev"] += d["rev"]
    print("-" * 62)
    rpm = tot["rev"] / tot["pv"] * 1000 if tot["pv"] else 0
    print(f"{'합계':<8}{tot['posts']:>10,}{'':>8}{tot['pv']:>12,}"
          f"{tot['rev']:>13,.0f}원{rpm:>10,.0f}")

    days = len({r["date"] for r in active}) or 1
    daily = tot["rev"] / days
    run_rate = daily * 30
    print(f"\n  기록된 활동 일수 : {days}일")
    print(f"  일평균 수익      : ₩{daily:,.0f}")
    print(f"  월 run-rate      : ₩{run_rate:,.0f}")
    print(f"  목표({GOAL:,}원) 대비 : {run_rate/GOAL*100:.2f}%")
    if run_rate:
        print(f"  목표까지 배수    : {GOAL/run_rate:.1f}배")
    print()


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("report")
    lg = sub.add_parser("log")
    lg.add_argument("date")
    lg.add_argument("--blog", required=True, choices=BLOGS)
    lg.add_argument("--posts", type=int)
    lg.add_argument("--indexed", type=int)
    lg.add_argument("--pv", type=int)
    lg.add_argument("--revenue", type=float)
    lg.add_argument("--note")
    a = p.parse_args()

    {"init": lambda: init(), "report": lambda: report(),
     "log": lambda: log(a)}[a.cmd]()


if __name__ == "__main__":
    main()
