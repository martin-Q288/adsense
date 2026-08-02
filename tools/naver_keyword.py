#!/usr/bin/env python3
"""네이버 검색광고 키워드도구 API — 실측 월간 검색량·경쟁도 수집.

인증 정보는 환경변수로만 전달합니다. 절대 커밋하지 마세요.
    export NAVER_CUSTOMER_ID="..."
    export NAVER_API_KEY="..."       # 액세스 라이선스
    export NAVER_SECRET_KEY="..."

사용법:
    python3 tools/naver_keyword.py --from-bank        # 뱅크 전체 시드 조회
    python3 tools/naver_keyword.py 전세자금대출 개인회생
    python3 tools/naver_keyword.py --from-bank -o keywords/volume.csv
"""

import argparse
import base64
import csv
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://api.searchad.naver.com"
PATH = "/keywordstool"
ROOT = os.path.join(os.path.dirname(__file__), "..")


def creds():
    cid = os.environ.get("NAVER_CUSTOMER_ID")
    key = os.environ.get("NAVER_API_KEY")
    sec = os.environ.get("NAVER_SECRET_KEY")
    if not all([cid, key, sec]):
        raise SystemExit(
            "환경변수가 필요합니다:\n"
            "  NAVER_CUSTOMER_ID / NAVER_API_KEY / NAVER_SECRET_KEY")
    return cid, key, sec


def sign(ts, method, path, secret):
    msg = f"{ts}.{method}.{path}"
    return base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()


def call(keywords, cid, key, sec):
    """hintKeywords는 요청당 최대 5개. 공백은 제거해서 보냅니다."""
    hint = ",".join(k.replace(" ", "") for k in keywords)
    qs = urllib.parse.urlencode({"hintKeywords": hint, "showDetail": "1"})
    ts = str(int(time.time() * 1000))
    req = urllib.request.Request(f"{BASE}{PATH}?{qs}")
    req.add_header("X-Timestamp", ts)
    req.add_header("X-API-KEY", key)
    req.add_header("X-Customer", str(cid))
    req.add_header("X-Signature", sign(ts, "GET", PATH, sec))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def num(v):
    """'< 10' 같은 값을 정수로."""
    if isinstance(v, int):
        return v
    s = str(v).replace(",", "").strip()
    if s.startswith("<"):
        return 5
    try:
        return int(s)
    except ValueError:
        return 0


COMP = {"낮음": 0.3, "중간": 0.6, "높음": 0.9}


def fetch(seeds, verbose=True):
    cid, key, sec = creds()
    out, seen = [], set()
    for i in range(0, len(seeds), 5):
        chunk = seeds[i:i + 5]
        try:
            data = call(chunk, cid, key, sec)
        except Exception as e:
            print(f"  [실패] {chunk}: {e}", file=sys.stderr)
            time.sleep(1.0)
            continue
        for row in data.get("keywordList", []):
            kw = row.get("relKeyword", "")
            if not kw or kw in seen:
                continue
            seen.add(kw)
            pc = num(row.get("monthlyPcQcCnt", 0))
            mo = num(row.get("monthlyMobileQcCnt", 0))
            out.append({
                "keyword": kw,
                "pc": pc,
                "mobile": mo,
                "total": pc + mo,
                "comp_label": row.get("compIdx", ""),
                "competition": COMP.get(row.get("compIdx", ""), 0.6),
                "ad_depth": num(row.get("plAvgDepth", 0)),
            })
        if verbose:
            print(f"  {min(i+5, len(seeds))}/{len(seeds)} 시드 → 누적 {len(out)}개",
                  file=sys.stderr)
        time.sleep(0.35)          # 호출 제한 여유
    return out


def bank_seeds():
    p = os.path.join(ROOT, "keywords", "bank.csv")
    with open(p, encoding="utf-8-sig") as f:
        return [r["seed_keyword"].strip() for r in csv.DictReader(f)
                if r.get("seed_keyword", "").strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("keywords", nargs="*")
    p.add_argument("--from-bank", action="store_true")
    p.add_argument("-o", "--out", default="keywords/volume.csv")
    p.add_argument("--min", type=int, default=0, help="최소 검색량 필터")
    a = p.parse_args()

    seeds = bank_seeds() if a.from_bank else a.keywords
    if not seeds:
        raise SystemExit("시드를 지정하거나 --from-bank 를 쓰세요.")

    print(f"시드 {len(seeds)}개 조회 시작...", file=sys.stderr)
    rows = fetch(seeds)
    rows = [r for r in rows if r["total"] >= a.min]
    rows.sort(key=lambda x: -x["total"])

    out = os.path.join(ROOT, a.out) if not os.path.isabs(a.out) else a.out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"\n저장: {out}  ({len(rows)}개)", file=sys.stderr)
    print(f"\n{'키워드':<28}{'월검색량':>10}{'모바일비중':>10}{'경쟁도':>8}{'광고수':>7}")
    print("-" * 64)
    for r in rows[:25]:
        share = r["mobile"] / r["total"] * 100 if r["total"] else 0
        print(f"{r['keyword'][:26]:<28}{r['total']:>10,}{share:>9.0f}%"
              f"{r['comp_label']:>8}{r['ad_depth']:>7}")


if __name__ == "__main__":
    main()
