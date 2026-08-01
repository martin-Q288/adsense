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

# 파생 8축 — 이슈 유형별로 실제로 검색되는 접미 패턴
AXES = {
    "방법/절차": ["{k} 신청 방법", "{k} 하는 법", "{k} 사용법", "{k} 등록 방법",
                "{k} 발급 방법", "{k} 절차"],
    "시청/접속": ["{k} 무료 중계", "{k} 실시간 보기", "{k} 시청 방법",
                "{k} 중계 채널", "{k} 다시보기"],
    "자격/조건": ["{k} 자격 조건", "{k} 대상자", "{k} 소득 기준",
                "{k} 신청 자격", "{k} 제외 대상"],
    "계산/금액": ["{k} 얼마", "{k} 계산 방법", "{k} 금액", "{k} 지급일",
                "{k} 수수료", "{k} 세금"],
    "오류/문제해결": ["{k} 안될 때", "{k} 오류 해결", "{k} 신청 실패",
                  "{k} 조회 안됨", "{k} 취소 방법"],
    "연락처/창구": ["{k} 고객센터", "{k} 전화번호", "{k} 문의처",
                 "{k} 접수처", "{k} 위치"],
    "준비물/서류": ["{k} 필요 서류", "{k} 준비물", "{k} 구비서류",
                 "{k} 신분증"],
    "비교/대안": ["{k} 비교", "{k} 차이", "{k} 추천", "{k} 순위", "{k} 후기"],
}

# 이슈 유형별 우선 축 (전부 쓰면 노이즈. 유형에 맞는 축부터 친다)
TYPE_PRIORITY = {
    "정책": ["자격/조건", "방법/절차", "계산/금액", "준비물/서류",
            "오류/문제해결", "연락처/창구"],
    "스포츠": ["시청/접속", "방법/절차", "비교/대안"],
    "사고": ["오류/문제해결", "방법/절차", "연락처/창구", "자격/조건"],
    "제품": ["비교/대안", "계산/금액", "오류/문제해결", "방법/절차"],
    "금융": ["계산/금액", "자격/조건", "방법/절차", "오류/문제해결",
            "연락처/창구", "비교/대안"],
    "방송": ["시청/접속", "비교/대안"],
    "전체": list(AXES),
}

# 고단가 신호어 — 포함되면 CPC가 높을 가능성
HIGH_CPC = ["대출", "보험", "세금", "변호사", "회생", "파산", "상속", "청약",
            "적금", "펀드", "ETF", "주식", "지원금", "환급", "실비", "치료",
            "수수료", "이자", "연금", "퇴직"]


def expand(keyword, issue_type):
    axes = TYPE_PRIORITY.get(issue_type, TYPE_PRIORITY["전체"])
    out = []
    for axis in axes:
        for tpl in AXES[axis]:
            kw = tpl.format(k=keyword)
            hot = [w for w in HIGH_CPC if w in kw]
            out.append((axis, kw, bool(hot)))
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
