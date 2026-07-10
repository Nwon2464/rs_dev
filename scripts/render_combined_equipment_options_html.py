#!/usr/bin/env python3
"""Build one self-contained explorer containing both equipment option systems."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import render_equipment_options_html as open_options
import render_instandard_equipment_html as instandard_options


ROOT = Path(__file__).resolve().parents[1]
OPEN_CSV = ROOT / "data" / "processed" / "equipment_converter_type_options.csv"
OUTPUT = ROOT / "equipment_options_viewer.html"

SHELL = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Red Stone 장비 옵션 탐색기</title>
  <style>
    :root { --bg:#f4f6f8; --panel:#fff; --ink:#17202a; --muted:#68717d; --line:#dce1e7; --open:#176b5b; --instandard:#7b3c9d; }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
    header { position:sticky; top:0; z-index:10; border-bottom:1px solid var(--line); background:rgba(244,246,248,.97); backdrop-filter:blur(8px); }.top { max-width:1800px; margin:auto; padding:12px 18px 0; }.title { display:flex; align-items:center; justify-content:space-between; gap:14px; padding-bottom:10px; } h1 { margin:0; font-size:19px; }.subtitle { color:var(--muted); font-size:12px; }.tabs { display:flex; gap:7px; }.tab { min-height:38px; border:1px solid var(--line); border-bottom:0; border-radius:10px 10px 0 0; background:var(--panel); color:var(--muted); padding:8px 13px; cursor:pointer; font:inherit; font-size:12px; font-weight:800; }.tab[aria-selected="true"] { color:var(--accent); border-color:var(--accent); background:var(--panel); }.tab.open { --accent:var(--open); }.tab.instandard { --accent:var(--instandard); }.frame { display:block; width:100%; height:calc(100vh - 101px); min-height:640px; border:0; background:var(--bg); }.frame[hidden] { display:none; } @media(max-width:700px) { .top { padding:10px 12px 0; }.subtitle { display:none; }.title { padding-bottom:8px; } h1 { font-size:16px; }.tab { padding:8px 9px; font-size:11px; }.frame { height:calc(100vh - 85px); } }
  </style>
</head>
<body>
  <header><div class="top"><div class="title"><div><h1>Red Stone 장비 옵션 탐색기</h1><div class="subtitle">개방 옵션 변환기와 비규격 장비 옵션을 한 화면에서 확인합니다.</div></div></div><nav class="tabs" aria-label="장비 옵션 시스템"><button class="tab open" type="button" data-page="open" role="tab" aria-selected="true">장비 개방 옵션 변환기</button><button class="tab instandard" type="button" data-page="instandard" role="tab" aria-selected="false">비규격 장비 옵션</button></nav></div></header>
  <iframe id="openFrame" class="frame" title="장비 개방 옵션 변환기"></iframe>
  <iframe id="instandardFrame" class="frame" title="비규격 장비 옵션" hidden></iframe>
  <script>
    const pages = __EMBEDDED_PAGES__;
    const frames = { open: document.getElementById("openFrame"), instandard: document.getElementById("instandardFrame") };
    const loaded = new Set();
    function show(page) {
      if (!loaded.has(page)) { frames[page].srcdoc = pages[page]; loaded.add(page); }
      Object.entries(frames).forEach(([key, frame]) => { frame.hidden = key !== page; });
      document.querySelectorAll(".tab").forEach(tab => tab.setAttribute("aria-selected", String(tab.dataset.page === page)));
      history.replaceState(null, "", `#${page}`);
    }
    document.querySelector(".tabs").addEventListener("click", event => { const tab=event.target.closest("[data-page]"); if(tab) show(tab.dataset.page); });
    show(location.hash === "#instandard" ? "instandard" : "open");
  </script>
</body>
</html>
'''


def main() -> None:
    with OPEN_CSV.open(encoding="utf-8-sig", newline="") as handle:
        open_rows = list(csv.DictReader(handle))
    if not open_rows:
        raise ValueError(f"no rows found in {OPEN_CSV}")
    instandard = instandard_options.build_render_dataset()
    open_html = open_options.TEMPLATE.replace(
        "__EMBEDDED_DATA__", json.dumps(open_rows, ensure_ascii=False, separators=(",", ":"))
    )
    instandard_html = instandard_options.render_html(instandard)
    pages = json.dumps({"open": open_html, "instandard": instandard_html}, ensure_ascii=False)
    OUTPUT.write_text(SHELL.replace("__EMBEDDED_PAGES__", pages.replace("</", "<\\/")), encoding="utf-8")
    print(f"wrote combined viewer ({len(open_rows)} open-option rows, {len(instandard['equipment'])} non-standard equipment groups)")


if __name__ == "__main__":
    main()
