#!/usr/bin/env python3
"""브랜드 × 액션 조합 키워드 생성기 — 단답형 생활정보 발굴.

■ 왜 필요한가
  정책·금융 롱폼(실업급여 조건 등)은 편당 RPM이 높지만 검색량 상위를
  기존 강자가 점유하고 있어 신규 진입 순위가 낮습니다. 반면
  "쿠팡 고객센터 전화번호"류 단답형은 광고가 1~2개뿐이라 RPM은 낮아도
  검색량이 압도적이고 글 쓰는 시간이 1/5입니다.

  실측 (네이버 검색광고 API, 2026-08):
    쿠팡고객센터      207,400  광고 2   ← 실업급여조건(117,700)의 1.8배
    배달의민족고객센터  13,470  광고 1
    넷플릭스해지        4,780  광고 2

  단답형은 RPM 엔진이 아니라 **트래픽 엔진**입니다. 총 노출을 키워
  블로그 권위를 올리고 네이버 홈판 노출 확률을 높이는 역할입니다.

■ 쓰는 법
    python3 tools/combo_keywords.py --preview          # 조합만 출력
    python3 tools/combo_keywords.py --fetch            # 네이버 API 실측
    python3 tools/combo_keywords.py --fetch --category 구독 -o keywords/combo.csv

  --fetch 사용 시 환경변수 필요:
    NAVER_CUSTOMER_ID / NAVER_API_KEY / NAVER_SECRET_KEY
"""

import argparse
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")

# 브랜드 — 카테고리별. 검색량이 큰 순으로 배치
BRANDS = {
    "커머스": ["쿠팡", "네이버페이", "11번가", "지마켓", "옥션", "티몬",
              "위메프", "SSG", "마켓컬리", "올리브영", "무신사", "에이블리",
              "알리익스프레스", "테무", "당근마켓", "번개장터"],
    "구독": ["넷플릭스", "쿠팡플레이", "티빙", "웨이브", "디즈니플러스",
            "왓챠", "유튜브프리미엄", "밀리의서재", "지니뮤직", "멜론",
            "스포티파이", "챗GPT"],
    "배달외식": ["배달의민족", "요기요", "쿠팡이츠", "스타벅스", "맥도날드",
                "버거킹", "BBQ", "교촌치킨", "도미노피자"],
    "통신": ["SKT", "KT", "LG유플러스", "알뜰폰", "쿠팡모바일"],
    "금융": ["토스", "카카오뱅크", "케이뱅크", "국민은행", "신한은행",
            "우리은행", "하나은행", "농협", "카카오페이", "삼성카드",
            "현대카드", "신한카드"],
    "생활": ["CU", "GS25", "세븐일레븐", "이마트", "홈플러스", "다이소",
            "우체국", "택배", "CJ대한통운", "롯데택배", "한진택배"],
    "공공": ["정부24", "홈택스", "국민연금공단", "건강보험공단", "고용보험",
            "한국전력", "도로교통공단", "코레일", "SRT"],
}

# 액션 — 실제 검색되는 형태. 붙였을 때 자연스러운 것만
ACTIONS = {
    "문의": ["고객센터", "고객센터전화번호", "전화번호", "상담원연결",
            "채팅상담", "본사"],
    "해지": ["해지", "해지방법", "탈퇴", "탈퇴방법", "구독취소", "자동결제해지"],
    "환불": ["환불", "환불방법", "환불규정", "반품", "취소", "교환"],
    "계정": ["로그인", "로그인안됨", "비밀번호변경", "아이디찾기", "회원가입",
            "본인인증"],
    "이용": ["영업시간", "배송조회", "주문취소", "쿠폰사용법",
            "포인트사용법", "결제오류", "앱설치"],
}

# 브랜드 카테고리 → 어울리는 액션 그룹 (엉뚱한 조합 방지)
FITS = {
    "커머스": ["문의", "환불", "계정", "이용"],
    "구독": ["해지", "환불", "문의", "계정"],
    "배달외식": ["문의", "환불", "이용"],
    "통신": ["문의", "해지", "계정", "이용"],
    "금융": ["문의", "계정", "이용"],
    "생활": ["문의", "이용", "환불"],
    "공공": ["문의", "계정", "이용"],
}


def build(categories=None):
    out = []
    for cat, brands in BRANDS.items():
        if categories and cat not in categories:
            continue
        for b in brands:
            for grp in FITS[cat]:
                for act in ACTIONS[grp]:
                    out.append((cat, b, act, b + act))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--category", action="append",
                   choices=list(BRANDS), help="카테고리 한정 (반복 가능)")
    p.add_argument("--preview", action="store_true", help="조합만 출력")
    p.add_argument("--fetch", action="store_true",
                   help="네이버 API로 실측 검색량 조회")
    p.add_argument("--limit", type=int, default=0,
                   help="--fetch 시 시드 개수 제한 (API 호출량 절약)")
    p.add_argument("-o", "--out", default="keywords/combo.csv")
    a = p.parse_args()

    combos = build(a.category)
    print(f"조합 {len(combos):,}개 생성 "
          f"(브랜드 {sum(len(v) for v in BRANDS.values())}개 × 액션)")

    if a.preview or not a.fetch:
        for cat, b, act, kw in combos[:60]:
            print(f"  [{cat}] {kw}")
        if len(combos) > 60:
            print(f"  … 외 {len(combos)-60:,}개")
        if not a.fetch:
            print("\n실측 검색량을 보려면 --fetch 를 붙이세요.")
        return

    seeds = [kw for _, _, _, kw in combos]
    if a.limit:
        seeds = seeds[:a.limit]
    print(f"네이버 API 조회 {len(seeds)}개 시드…\n")

    cmd = [sys.executable, os.path.join(ROOT, "tools", "naver_keyword.py"),
           *seeds, "-o", a.out, "--min", "500"]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
