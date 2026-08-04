#!/usr/bin/env python3
"""마크다운 원고 → 붙여넣고 바로 발행하는 티스토리 HTML.

원칙
  - 광고 코드 없음. 티스토리 자동광고(관리 → 수익 → 애드센스 관리)가 처리한다
  - 스크립트·주석 없음. 붙여넣으면 그게 끝이다
  - 스타일은 전부 인라인. <style> 블록은 에디터가 지우는 경우가 있다
  - 목차는 H2에서 자동 생성해 앵커로 건다
  - 표는 가로 스크롤 상자에 넣는다. 폰에서 본문이 밀리지 않게

산출: content/articles/html/<원고명>.html
"""
import html
import os
import re
import sys

INK = "#222"
RULE = "#E0DED9"
ACCENT = "#C1272D"
SLATE = "#2F4858"

S = {
    "body": f"font-size:17px;line-height:1.8;color:{INK};word-break:keep-all",
    "lede": f"background:#F7F7F5;border-left:4px solid {ACCENT};"
            "padding:18px 20px;margin:0 0 26px",
    "ledep": "margin:0 0 12px;font-size:17px;line-height:1.8",
    "toc": f"border:1px solid {RULE};padding:18px 20px;margin:0 0 30px;"
           "background:#FCFCFB",
    "toct": "font-size:14px;font-weight:700;margin:0 0 12px;color:#555;"
            "letter-spacing:.02em",
    "toca": f"color:{SLATE};text-decoration:none",
    "h2": f"font-size:22px;font-weight:700;margin:46px 0 16px;"
          f"padding-bottom:10px;border-bottom:2px solid {INK};line-height:1.4",
    "h3": "font-size:18.5px;font-weight:700;margin:30px 0 12px;line-height:1.5",
    "p": "margin:0 0 18px;line-height:1.8",
    "ul": "margin:0 0 20px;padding-left:22px;line-height:1.8",
    "li": "margin-bottom:9px",
    "wrap": "overflow-x:auto;margin:0 0 24px;-webkit-overflow-scrolling:touch",
    "table": "border-collapse:collapse;width:100%;min-width:320px;font-size:16px",
    "th": f"border:1px solid {RULE};padding:12px 13px;text-align:left;"
          "background:#F4F3F0;font-weight:700;white-space:nowrap",
    "td": f"border:1px solid {RULE};padding:12px 13px;text-align:left",
    "pre": f"background:#F7F7F5;border:1px solid {RULE};padding:16px 18px;"
           "margin:0 0 24px;overflow-x:auto;font-size:15px;line-height:1.7;"
           "font-family:ui-monospace,Menlo,Consolas,monospace",
    "quote": f"border-left:4px solid {SLATE};background:#F0F4F6;"
             "padding:16px 18px;margin:0 0 24px;font-size:16px;line-height:1.8",
    "rel": f"border:1px solid {RULE};padding:20px;margin:36px 0 24px;"
           "background:#FCFCFB",
    "relt": "font-size:15.5px;font-weight:700;margin:0 0 14px",
    "note": "margin-top:32px;padding-top:18px;border-top:1px solid #E8E6E1;"
            "font-size:14px;color:#777;line-height:1.75",
}


def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    """굵게·코드·링크만 변환한다. 그 밖의 기호는 글자로 남기지 않는다."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`",
               r'<code style="background:#F2F1EE;padding:1px 5px;'
               r'border-radius:3px;font-size:15px">\1</code>', s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)",
               rf'<a href="\2" style="color:{SLATE}">\1</a>', s)
    return s


def cells(line):
    return [inline(c.strip()) for c in line.strip().strip("|").split("|")]


def convert(md):
    body = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)
    lines = body.split("\n")

    title = ""
    heads = []          # 목차용 (id, 텍스트)
    out = []            # 첫 H2 이후 본문
    lede = []           # 첫 H2 이전 도입부
    related = []        # 함께 보면 좋은 글
    note = []           # 하단 고지
    buf, mode = [], None
    seen_h2 = False
    in_tail = False     # "함께 보면 좋은 글" 이후 — 관련글·고지 구역

    def sink():
        return out if seen_h2 else lede

    def flush():
        nonlocal buf, mode
        if not buf:
            mode = None
            return
        if mode == "table":
            head, rows = buf[0], buf[1:]
            t = [f'<div style="{S["wrap"]}"><table style="{S["table"]}">',
                 "<thead><tr>"]
            t += [f'<th style="{S["th"]}">{c}</th>' for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(
                    f'<td style="{S["td"]}">{c}</td>' for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            sink().append("".join(t))
        elif mode in ("ul", "ol"):
            items = "".join(f'<li style="{S["li"]}">{x}</li>' for x in buf)
            sink().append(f'<{mode} style="{S["ul"]}">{items}</{mode}>')
        elif mode == "quote":
            txt = "<br>".join(buf)
            if in_tail:
                note.append(f'<div style="{S["note"]}">{txt}</div>')
            else:
                sink().append(f'<div style="{S["quote"]}">{txt}</div>')
        elif mode == "pre":
            sink().append(f'<pre style="{S["pre"]}">{esc(chr(10).join(buf))}</pre>')
        buf, mode = [], None

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            if mode == "pre":
                flush()
            else:
                flush()
                mode = "pre"
            continue
        if mode == "pre":
            buf.append(line)
            continue

        if line.startswith("|"):
            if re.match(r"^\|[\s:|-]+\|$", line):
                continue
            if mode != "table":
                flush()
                mode = "table"
            buf.append(cells(line))
            continue

        if line.startswith(">"):
            if mode != "quote":
                flush()
                mode = "quote"
            buf.append(inline(re.sub(r"^>\s?", "", line)))
            continue

        m = re.match(r"^\s*[-*·]\s+(.*)", line)
        if m:
            # 꼬리 구역의 목록은 본문이 아니라 관련글 상자로 간다
            if in_tail:
                related.append(inline(m.group(1)))
                continue
            if mode != "ul":
                flush()
                mode = "ul"
            buf.append(inline(m.group(1)))
            continue
        m = re.match(r"^\s*\d+\.\s+(.*)", line)
        if m:
            if mode != "ol":
                flush()
                mode = "ol"
            buf.append(inline(m.group(1)))
            continue

        flush()

        if not line or re.match(r"^-{3,}$", line):
            continue

        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            lvl, text = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and not title:
                title = re.sub(r"\*\*", "", text)
                continue
            if lvl == 2:
                seen_h2 = True
                hid = f"s{len(heads) + 1}"
                heads.append((hid, esc(text)))
                out.append(f'<h2 id="{hid}" style="{S["h2"]}">{inline(text)}</h2>')
            else:
                out.append(f'<h3 style="{S["h3"]}">{inline(text)}</h3>')
            continue

        # "함께 보면 좋은 글"부터는 꼬리 구역. 본문 흐름에서 떼어 하단으로 보낸다
        if re.match(r"^\*\*함께 보면 좋은 글\*\*", line):
            in_tail = True
            continue

        sink().append(f'<p style="{S["p"]}">{inline(line)}</p>')

    flush()

    # 조립
    doc = [f'<div style="{S["body"]}">']

    if lede:
        inner = "".join(x.replace(f'style="{S["p"]}"', f'style="{S["ledep"]}"')
                        for x in lede)
        doc.append(f'<div style="{S["lede"]}">{inner}</div>')

    if len(heads) >= 3:
        items = "".join(
            f'<li style="{S["li"]}"><a href="#{i}" style="{S["toca"]}">{t}</a></li>'
            for i, t in heads)
        doc.append(f'<nav style="{S["toc"]}">'
                   f'<p style="{S["toct"]}">목차</p>'
                   f'<ol style="{S["ul"]}">{items}</ol></nav>')

    doc.extend(out)

    if related:
        items = "".join(f'<li style="{S["li"]}">{x}</li>' for x in related)
        doc.append(f'<div style="{S["rel"]}">'
                   f'<p style="{S["relt"]}">함께 보면 좋은 글</p>'
                   f'<ul style="{S["ul"]}">{items}</ul></div>')

    doc.extend(note)

    doc.append("</div>")
    return title, "\n".join(doc)


def main(paths):
    outdir = os.path.join(os.path.dirname(paths[0]), "html")
    os.makedirs(outdir, exist_ok=True)
    for p in paths:
        if os.path.basename(p) == "README.md":
            continue
        title, doc = convert(open(p, encoding="utf-8").read())
        dst = os.path.join(outdir, os.path.basename(p).replace(".md", ".html"))
        open(dst, "w", encoding="utf-8").write(doc + "\n")
        print(f"{os.path.basename(dst):48s} {len(doc):>7,}자  {title[:30]}")


if __name__ == "__main__":
    import glob
    main(sys.argv[1:] or sorted(glob.glob(os.path.join(
        os.path.dirname(__file__), "..", "content/articles/*.md"))))
