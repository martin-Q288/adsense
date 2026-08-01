#!/usr/bin/env python3
"""이슈 파생 키워드 자동 전개기.

512편 채널 분석에서 추출한 '파생 8축'으로 이슈 하나를 검색 가능한
롱테일 키워드 집합으로 기계적으로 확장합니다.

원칙: 메인 키워드는 언론사가 독식한다. 검색자가 실제로 겪는 문제를 노린다.

사용법:
    python3 tools/issue_radar.py "월드컵"
    python3 tools/issue_radar.py "고유가 지원금" --type 정책
    python3 tools/issue_radar.py "에어컨" --type 제품 --md
"""

import argparse

# 파생 8축.
# 각 템플릿은 (패턴, 허용 유형) — None이면 모든 유형에 적용.
# 유형 제한이 없으면 "층간소음 세금", "안마의자 무료 중계" 같은 쓰레기가 생성된다.
ADMIN = {"정책", "금융"}          # 신청·창구가 존재하는 행정/금융성 주제
BUYABLE = {"제품", "리뷰"}        # 구매 대상
WATCH = {"스포츠", "방송"}        # 중계·시청 대상

AXES = {
    "방법/절차": [
        ("{k} 신청 방법", ADMIN), ("{k} 하는 법", None),
        ("{k} 사용법", BUYABLE | {"생활"}), ("{k} 등록 방법", ADMIN),
        ("{k} 발급 방법", ADMIN), ("{k} 절차", ADMIN),
    ],
    "시청/접속": [
        ("{k} 무료 중계", WATCH), ("{k} 실시간 보기", WATCH),
        ("{k} 시청 방법", WATCH), ("{k} 중계 채널", WATCH),
        ("{k} 다시보기", WATCH),
    ],
    "자격/조건": [
        ("{k} 자격 조건", ADMIN), ("{k} 대상자", ADMIN),
        ("{k} 소득 기준", {"정책"}), ("{k} 신청 자격", ADMIN),
        ("{k} 제외 대상", ADMIN),
    ],
    "계산/금액": [
        ("{k} 얼마", None), ("{k} 계산 방법", None),
        ("{k} 가격", BUYABLE), ("{k} 비용", BUYABLE | {"생활"}),
        ("{k} 금액", ADMIN), ("{k} 지급일", {"정책"}),
        ("{k} 수수료", {"금융"}), ("{k} 세금", {"금융"}),
    ],
    "오류/문제해결": [
        ("{k} 안될 때", ADMIN), ("{k} 오류 해결", ADMIN),
        ("{k} 해결 방법", {"생활", "사고"}), ("{k} 신청 실패", ADMIN),
        ("{k} 조회 안됨", ADMIN), ("{k} 취소 방법", ADMIN | BUYABLE),
        ("{k} 고장", BUYABLE), ("{k} AS", BUYABLE),
    ],
    "연락처/창구": [
        ("{k} 고객센터", ADMIN | BUYABLE), ("{k} 전화번호", ADMIN),
        ("{k} 문의처", ADMIN), ("{k} 접수처", ADMIN), ("{k} 위치", ADMIN),
    ],
    "준비물/서류": [
        ("{k} 필요 서류", ADMIN), ("{k} 준비물", ADMIN | {"시즌"}),
        ("{k} 구비서류", ADMIN), ("{k} 신분증", ADMIN),
    ],
    "비교/대안": [
        ("{k} 비교", None), ("{k} 차이", None),
        ("{k} 추천", BUYABLE | {"시즌"}), ("{k} 순위", BUYABLE),
        ("{k} 후기", BUYABLE), ("{k} 단점", BUYABLE),
    ],
}

# 이슈 유형별 우선 축 (전부 쓰면 노이즈. 유형에 맞는 축부터 친다)
TYPE_PRIORITY = {
    "정책": ["자격/조건", "방법/절차", "계산/금액", "준비물/서류",
            "오류/문제해결", "연락처/창구"],
    "금융": ["계산/금액", "자격/조건", "방법/절차", "오류/문제해결",
            "연락처/창구", "비교/대안"],
    "스포츠": ["시청/접속", "방법/절차", "비교/대안"],
    "방송": ["시청/접속", "비교/대안"],
    "사고": ["오류/문제해결", "방법/절차", "연락처/창구", "자격/조건"],
    "생활": ["방법/절차", "오류/문제해결", "계산/금액", "비교/대안"],
    "제품": ["비교/대안", "계산/금액", "오류/문제해결", "방법/절차"],
    "리뷰": ["비교/대안", "계산/금액", "오류/문제해결", "방법/절차"],
    "시즌": ["방법/절차", "비교/대안", "계산/금액", "준비물/서류"],
    "전체": list(AXES),
}

# 고단가 신호어 — 포함되면 CPC가 높을 가능성
HIGH_CPC = ["대출", "보험", "세금", "변호사", "회생", "파산", "상속", "청약",
            "적금", "펀드", "ETF", "주식", "지원금", "환급", "실비", "치료",
            "수수료", "이자", "연금", "퇴직"]


def expand(keyword, issue_type):
    """유형에 맞는 축·템플릿만 전개. 허용 유형이 맞지 않는 조합은 버린다."""
    axes = TYPE_PRIORITY.get(issue_type, TYPE_PRIORITY["전체"])
    seed_words = set(keyword.split())
    out = []
    for axis in axes:
        for tpl, allowed in AXES[axis]:
            if allowed is not None and issue_type not in allowed:
                continue
            suffix = tpl.format(k="").strip()
            # 시드에 이미 있는 말을 또 붙이지 않는다 ("입주청소 비용 비용")
            if seed_words & set(suffix.split()):
                continue
            kw = tpl.format(k=keyword)
            out.append((axis, kw, any(w in kw for w in HIGH_CPC)))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("keyword", help="이슈 핵심어 (예: 월드컵, 고유가 지원금)")
    p.add_argument("--type", default="전체", choices=list(TYPE_PRIORITY),
                   help="이슈 유형. 유형에 맞는 축부터 전개")
    p.add_argument("--md", action="store_true", help="마크다운 체크리스트로 출력")
    a = p.parse_args()

    rows = expand(a.keyword, a.type)

    if a.md:
        print(f"# 이슈 파생 키워드: {a.keyword} ({a.type})\n")
        cur = None
        for axis, kw, hot in rows:
            if axis != cur:
                print(f"\n## {axis}")
                cur = axis
            print(f"- [ ] {kw}{'  **[고단가]**' if hot else ''}")
        print(f"\n---\n총 {len(rows)}개")
    else:
        print(f"\n이슈: {a.keyword}   유형: {a.type}   전개 {len(rows)}개")
        print("=" * 62)
        cur = None
        for axis, kw, hot in rows:
            if axis != cur:
                print(f"\n[{axis}]")
                cur = axis
            print(f"  {'★' if hot else ' '} {kw}")

    print("\n" + "-" * 62)
    print("다음 단계:")
    print("  1. 각 키워드를 네이버·구글에 직접 검색")
    print("  2. 상위 10개에 블로그 글이 3개 미만이면 즉시 채택")
    print("  3. 이슈 발생 후 2시간 내 발행 (6시간 넘으면 늦음)")
    print("  ★ = 고단가 신호어 포함. 우선 공략\n")


if __name__ == "__main__":
    main()
