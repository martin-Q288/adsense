#!/usr/bin/env python3
"""마크다운 원고 → 티스토리·네이버 에디터에 그대로 붙여넣는 순수 텍스트.

에디터(티스토리 기본모드, 네이버 스마트에디터)는 마크다운을 해석하지
않는다. `##`, `**`, `|표|` 가 그대로 화면에 찍히므로 전부 풀어서 낸다.

산출물 규칙
  - 첫 줄은 제목. 제목 칸에 따로 넣으라고 구분선으로 떼어 둔다
  - 소제목은 기호 없는 한 줄. 붙여넣은 뒤 에디터에서 소제목 스타일 지정
  - 표는 "항목: 값" 줄로 푼다 (텍스트 표는 모바일에서 깨진다)
  - 문단 사이는 빈 줄 하나 (알파남 영상: 2~3줄마다 엔터)
"""
import os
import re
import sys


def strip_inline(s):
    """굵게·기울임·코드·링크 표시를 벗긴다."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1(\2)", s)
    return s.strip()


def split_row(line):
    return [strip_inline(c) for c in line.strip().strip("|").split("|")]


# 문장 끝 마침표만 자른다. 한글·닫는괄호·따옴표 뒤의 구두점만 경계로 보므로
# "2.4억", "hometax.go.kr", "1,157." 같은 것은 잘리지 않는다.
SENT_END = re.compile(r'(?<=[가-힣)\]"\'])([.!?])\s+')

# 한 화면에 두세 줄씩 — 문장마다 줄을 바꾸고 두 문장마다 빈 줄을 넣는다.
# 폰에서 문단이 통짜 벽으로 보이는 것을 막는다 (docs/14 8-5).
SENT_PER_BLOCK = 2

# 폰 한 줄에 대략 25자. 이보다 두 배 이상 긴 문장은 접속 어미 뒤에서 한 번
# 더 끊는다. 어미를 남기고 자르므로 뜻은 그대로다.
LONG_SENT = 50
CLAUSE_END = re.compile(r"(?<=[고며데서만나]),\s+")


def split_sentence(s):
    if len(s) <= LONG_SENT:
        return [s]
    parts = [p.strip() for p in CLAUSE_END.sub(",\n", s).split("\n") if p.strip()]
    # 쪼갠 조각이 너무 짧으면 원래대로 둔다 (토막난 줄이 더 안 읽힌다)
    return parts if all(len(p) >= 12 for p in parts) else [s]


def wrap_para(text, out):
    """문단 하나를 문장 단위로 쪼개 모바일 가독성에 맞게 늘어놓는다.

    빈 줄은 문장이 끝난 자리에만 넣는다. 긴 문장을 절 단위로 나눈 조각들은
    한 문장이므로 사이를 벌리지 않는다.
    """
    parts = SENT_END.sub(r"\1\n", text).split("\n")
    sents = [split_sentence(s.strip()) for s in parts if s.strip()]
    if len(sents) <= 1:
        out.extend(sents[0] if sents else [text])
        return
    for i, lines in enumerate(sents):
        out.extend(lines)
        left = len(sents) - (i + 1)
        # 한 문장만 남으면 끊지 않는다. 홀로 떨어진 줄이 생기지 않게.
        if (i + 1) % SENT_PER_BLOCK == 0 and left > 1:
            out.append("")


def flush_table(rows, out):
    """표를 텍스트 줄로 푼다.

    2열이면 "왼쪽: 오른쪽" 한 줄. 3열 이상은 셀이 전부 짧으면 가운뎃점으로
    한 줄에 붙이고, 긴 셀이 섞여 있으면 첫 열을 제목으로 세운 뒤 나머지를
    "헤더: 값"으로 들여쓴다. 어느 쪽이든 모바일에서 가로로 밀리지 않는다.
    """
    if not rows:
        return
    head, body = rows[0], rows[1:]
    if len(head) == 2:
        for r in body:
            out.append(f"{r[0]}: {r[1]}" if len(r) > 1 else r[0])
        out.append("")
        return
    short = all(len(c) <= 12 for r in body for c in r)
    for r in body:
        if short:
            out.append(" · ".join(c for c in r if c))
            continue
        out.append(r[0])
        for h, v in zip(head[1:], r[1:]):
            if v:
                out.append(f"  {h}: {v}")
        out.append("")
    if short:
        out.append("")


def convert(md):
    body = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)
    lines = body.split("\n")

    title = ""
    out = []
    table = []
    in_code = False

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            in_code = not in_code
            if not in_code:
                out.append("")
            continue
        if in_code:
            out.append(line)
            continue

        # 표 수집 — 구분선(|---|)은 버린다
        if line.startswith("|"):
            if re.match(r"^\|[\s:|-]+\|$", line):
                continue
            table.append(split_row(line))
            continue
        if table:
            flush_table(table, out)
            table = []

        if not line:
            if out and out[-1] != "":
                out.append("")
            continue

        # 수평선은 문단 사이 여백으로만 쓴다
        if re.match(r"^-{3,}$", line):
            if out and out[-1] != "":
                out.append("")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            text = strip_inline(m.group(2))
            if len(m.group(1)) == 1 and not title:
                title = text
                continue
            if out and out[-1] != "":
                out.append("")
            # 기호를 앞에 달아 소제목 스타일을 지정하기 전에도 구조가 보이게
            # 한다. 에디터에서 소제목으로 잡은 뒤 지워도 된다.
            out.append(("■ " if len(m.group(1)) == 2 else "▪ ") + text)
            out.append("")
            continue

        # 목록 — 마크다운 기호 대신 가운뎃점, 번호는 그대로 살린다.
        # 원고에서 이미 가운뎃점으로 쓴 줄도 목록으로 받는다 (문장 분리 제외).
        m = re.match(r"^\s*[-*·]\s+(.*)", line)
        if m:
            out.append("· " + strip_inline(m.group(1)))
            continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if m:
            out.append(f"{m.group(1)}. {strip_inline(m.group(2))}")
            continue

        # 인용문 기호는 떼고 평문으로
        line = re.sub(r"^>\s?", "", line)
        wrap_para(strip_inline(line), out)

    if table:
        flush_table(table, out)

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text


def main(paths):
    outdir = os.path.join(os.path.dirname(paths[0]), "text")
    os.makedirs(outdir, exist_ok=True)
    for p in paths:
        title, text = convert(open(p, encoding="utf-8").read())
        dst = os.path.join(outdir, os.path.basename(p).replace(".md", ".txt"))
        open(dst, "w", encoding="utf-8").write(
            f"{title}\n{'=' * 40}\n위 한 줄은 제목 칸에, 아래부터 본문 칸에\n"
            f"{'=' * 40}\n\n{text}\n")
        print(f"{os.path.basename(dst):50s} {len(text):>6,}자")


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(
        __import__("glob").glob(
            os.path.join(os.path.dirname(__file__), "..",
                         "content/articles/*.md"))))
