#!/usr/bin/env python3
"""합니다체 → 해요체 부분 변환 (docs/20 말투 규칙).

전부 해요체면 가볍고 전부 합니다체면 딱딱하다. 그래서 섞는다.

  변환한다   설명·안내 문장
  그대로 둔다 굵게 강조한 문장(핵심 단정·경고), 인용문(>), 표, 코드,
             제목, 프런트매터

굵게 쓴 문장은 무게가 필요해서 굵게 쓴 것이므로 합니다체를 남긴다.
결과는 사람이 한 번 읽고 마감해야 한다. 이 도구는 초벌이다.
"""
import re
import sys

# 종결어미 표. 긴 것부터 맞춰야 짧은 것이 먼저 걸리지 않는다.
ENDINGS = [
    ("줄어듭니다", "줄어들어요"), ("늘어납니다", "늘어나요"),
    ("들어갑니다", "들어가요"), ("떨어집니다", "떨어져요"),
    ("어렵습니다", "어려워요"), ("달라집니다", "달라져요"),
    ("나옵니다", "나와요"), ("생깁니다", "생겨요"), ("걸립니다", "걸려요"),
    ("빠집니다", "빠져요"), ("붙습니다", "붙어요"), ("남습니다", "남아요"),
    ("드립니다", "드려요"), ("모릅니다", "몰라요"), ("받습니다", "받아요"),
    ("보냅니다", "보내요"), ("올립니다", "올려요"), ("내립니다", "내려요"),
    ("잡습니다", "잡아요"), ("찍습니다", "찍어요"), ("넣습니다", "넣어요"),
    ("있습니다", "있어요"), ("없습니다", "없어요"),
    ("많습니다", "많아요"), ("좋습니다", "좋아요"), ("같습니다", "같아요"),
    ("아닙니다", "아니에요"), ("다릅니다", "달라요"),
    ("쉽습니다", "쉬워요"), ("빠릅니다", "빨라요"), ("느립니다", "느려요"),
    ("높습니다", "높아요"), ("낮습니다", "낮아요"),
    ("짧습니다", "짧아요"), ("깁니다", "길어요"),
    ("큽니다", "커요"), ("작습니다", "작아요"),
    ("줍니다", "줘요"), ("납니다", "나요"), ("옵니다", "와요"),
    ("갑니다", "가요"), ("봅니다", "봐요"), ("씁니다", "써요"),
    ("압니다", "알아요"), ("됩니다", "돼요"), ("합니다", "해요"),
]

# 문장 끝에서만 바꾼다. 뒤에 문장부호나 줄끝이 와야 한다.
TAIL = r"(?=[.!?)\]]|$)"


def has_batchim(ch):
    if not ("가" <= ch <= "힣"):
        return True          # 숫자·영문 뒤는 "이에요"가 자연스럽다
    return (ord(ch) - 0xAC00) % 28 != 0


def to_haeyo(s):
    for a, b in ENDINGS:
        s = re.sub(a + TAIL, b, s)
    # "~입니다" 는 앞 글자 받침에 따라 갈린다.
    # 따옴표·괄호가 끼어 있으면 그 앞의 한글까지 거슬러 올라가 판정한다.
    def ida(m):
        head = m.group(1)
        ko = re.sub(r'["\'”’)\]』」]+$', "", head)
        last = ko[-1] if ko else "가"
        return head + ("이에요" if has_batchim(last) else "예요")
    s = re.sub(r'(.[\'"”’)\]』」]*)입니다' + TAIL, ida, s)
    return s


SKIP = re.compile(r"^\s*(#|>|\||```|---|\d+\.\s|[-*·]\s)")


def convert(md, keep_bold=True):
    out, in_fm, in_code, in_tail = [], False, False, False
    for i, line in enumerate(md.split("\n")):
        if i == 0 and line.strip() == "---":
            in_fm = True
            out.append(line)
            continue
        if in_fm:
            out.append(line)
            if line.strip() == "---":
                in_fm = False
            continue
        if line.startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code or SKIP.match(line) or not line.strip():
            out.append(line)
            continue
        if "함께 보면 좋은 글" in line:
            in_tail = True
        if in_tail:
            out.append(line)
            continue

        # 문장 단위로 쪼개, 굵게 강조된 문장은 합니다체로 남긴다
        parts = re.split(r"(?<=[다요][.!?])\s+", line)
        fixed = []
        for p in parts:
            if keep_bold and "**" in p:
                fixed.append(p)
            else:
                fixed.append(to_haeyo(p))
        out.append(" ".join(fixed))
    return "\n".join(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        src = open(p, encoding="utf-8").read()
        dst = convert(src)
        open(p, "w", encoding="utf-8").write(dst)
        n = sum(1 for a, b in ENDINGS if b in dst)
        print(f"{p.split('/')[-1]:44s} 어미 {n}종 변환")
