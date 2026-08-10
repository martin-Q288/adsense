#!/usr/bin/env python3
import csv, json, collections, os, datetime

ROOT = os.path.join(os.path.dirname(__file__), "..")
rows = list(csv.DictReader(open(f"{ROOT}/content/publish_queue.csv", encoding="utf-8")))

days = collections.OrderedDict()
for r in rows:
    days.setdefault(r["date"], []).append([r["keyword"], r["blog"], r["axis"], r["event"]])

cal = {}
for r in csv.DictReader(open(f"{ROOT}/keywords/august_calendar.csv", encoding="utf-8")):
    cal[r["event"]] = {"d": r["event_date"], "p": int(r["priority"]), "note": r["note"]}

DATA = json.dumps({"days": days, "cal": cal}, ensure_ascii=False, separators=(",", ":"))

html = open(os.path.join(os.path.dirname(__file__), "page.tpl.html"), encoding="utf-8").read()
html = html.replace("/*__DATA__*/", DATA)
out = os.path.join(os.path.dirname(__file__), "queue.html")
open(out, "w", encoding="utf-8").write(html)
print("wrote", out, len(html), "bytes /", len(rows), "items /", len(days), "days")
