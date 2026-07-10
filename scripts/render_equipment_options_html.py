#!/usr/bin/env python3
"""Render the current equipment open-option CSV as a self-contained HTML viewer."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "equipment_open_options_test.csv"
HTML_PATH = ROOT / "equipment_options_viewer.html"


def main() -> None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"no rows found in {CSV_PATH}")

    embedded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    html = TEMPLATE.replace("__EMBEDDED_DATA__", embedded)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {len(rows)} rows to {HTML_PATH}")


TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>장비 개방 옵션 검증 뷰어</title>
  <style>
    :root {
      --bg:#f4f6f8; --panel:#fff; --ink:#17202a; --muted:#68717d;
      --line:#dce1e7; --head:#edf1f5; --accent:#176b5b; --soft:#e2f3ee;
      --bad:#a42a2a; --bad-bg:#fff0f0; --shadow:0 1px 3px rgba(20,30,45,.08);
    }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
    header { position:sticky; top:0; z-index:20; border-bottom:1px solid var(--line); background:rgba(244,246,248,.97); backdrop-filter:blur(8px); }
    .top { max-width:1800px; margin:auto; padding:14px 18px; }
    h1 { margin:0 0 3px; font-size:20px; }
    .subtitle { color:var(--muted); font-size:12px; }
    .filters { display:grid; grid-template-columns:repeat(5,minmax(110px,150px)) minmax(220px,1fr) auto; gap:9px; margin-top:13px; align-items:end; }
    label { display:grid; gap:4px; color:var(--muted); font-size:11px; font-weight:700; }
    select,input,button { min-height:36px; border:1px solid var(--line); border-radius:7px; background:var(--panel); color:var(--ink); padding:7px 9px; font:inherit; }
    button { cursor:pointer; font-weight:700; }
    button:hover { border-color:var(--accent); }
    main { max-width:1800px; margin:auto; padding:16px 18px 24px; }
    .notice { margin-bottom:12px; padding:10px 12px; border:1px solid #bcded5; border-radius:8px; background:var(--soft); color:#205d52; font-size:12px; }
    .metrics { display:grid; grid-template-columns:repeat(5,minmax(120px,1fr)); gap:9px; margin-bottom:12px; }
    .metric { padding:11px 12px; border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:var(--shadow); }
    .metric b { display:block; font-size:21px; line-height:1.15; font-variant-numeric:tabular-nums; }
    .metric span { color:var(--muted); font-size:11px; font-weight:700; }
    .table-box { overflow:auto; max-height:calc(100vh - 290px); border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:var(--shadow); }
    table { width:100%; min-width:1560px; border-collapse:separate; border-spacing:0; }
    th,td { padding:7px 9px; border-bottom:1px solid var(--line); white-space:nowrap; vertical-align:middle; }
    th { position:sticky; top:0; z-index:2; background:var(--head); color:#3a4652; text-align:left; font-size:11px; }
    td.num { text-align:right; font-variant-numeric:tabular-nums; }
    td.option { min-width:180px; font-weight:700; }
    tr.invalid td { background:var(--bad-bg); }
    tr:hover td { box-shadow:inset 0 0 0 9999px rgba(23,107,91,.035); }
    .pill { display:inline-block; padding:2px 7px; border-radius:999px; background:#e9edf1; font-size:11px; font-weight:750; }
    .pill.good { background:var(--soft); color:var(--accent); }
    .pill.bad { background:#ffdada; color:var(--bad); }
    .unknown { color:#8c5b16; }
    .pager { display:flex; align-items:center; justify-content:flex-end; gap:8px; margin-top:11px; }
    .pager span { min-width:130px; text-align:center; color:var(--muted); font-size:12px; }
    .empty { padding:40px; text-align:center; color:var(--muted); }
    @media (max-width:1100px) { .filters { grid-template-columns:repeat(2,1fr); } .metrics { grid-template-columns:repeat(2,1fr); } .table-box { max-height:none; } }
  </style>
</head>
<body>
  <header>
    <div class="top">
      <h1>장비 개방 옵션 검증 뷰어</h1>
      <div class="subtitle">원본 DAT 직접 조인 결과 · CSV 전체 데이터 내장</div>
      <div class="filters">
        <label>장비<select id="equipment"></select></label>
        <label>등급 코드<select id="grade"></select></label>
        <label>section group<select id="section"></select></label>
        <label>개방 줄<select id="slot"></select></label>
        <label>확률 합<select id="validity"><option value="">전체</option><option value="true">정상</option><option value="false">오류</option></select></label>
        <label>검색<input id="query" type="search" placeholder="옵션명, ID, 블록, 오프셋 검색"></label>
        <button id="reset" type="button">초기화</button>
      </div>
    </div>
  </header>
  <main>
    <div class="notice">그룹명은 <b>simpleGameText.dat</b>, 옵션명은 <b>capa.dat</b>에서 직접 조인했습니다. 등급 코드 11과 section group은 미확정 숫자 원문을 유지합니다.</div>
    <section class="metrics" id="metrics"></section>
    <section class="table-box" id="tableBox"></section>
    <nav class="pager">
      <button id="prev" type="button">이전</button><span id="pageInfo"></span><button id="next" type="button">다음</button>
    </nav>
  </main>
  <script>
    const rows = __EMBEDDED_DATA__;
    const PAGE_SIZE = 100;
    const state = {equipment:"",grade:"",section:"",slot:"",validity:"",query:"",page:1};
    const $ = (id) => document.getElementById(id);
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const numericSort = (a,b) => Number(a)-Number(b);

    function options(id, values, allLabel="전체") {
      $(id).innerHTML = `<option value="">${allLabel}</option>` + values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
    }
    function initializeFilters() {
      options("equipment", [...new Set(rows.map(r=>r.equipment_bucket))].sort());
      options("grade", [...new Set(rows.map(r=>r.grade_code))].sort(numericSort).map(code => code === "11" ? "11 (명칭 미확정)" : `${code} (${rows.find(r=>r.grade_code===code).grade_name})`));
      options("section", [...new Set(rows.map(r=>r.section_group))].sort(numericSort));
      options("slot", [...new Set(rows.map(r=>r.open_slot))].sort(numericSort));
    }
    function gradeCodeFromFilter(value) { return value ? value.split(" ")[0] : ""; }
    function filtered() {
      const q=state.query.trim().toLowerCase();
      return rows.filter(r => {
        if(state.equipment && r.equipment_bucket!==state.equipment) return false;
        if(state.grade && r.grade_code!==gradeCodeFromFilter(state.grade)) return false;
        if(state.section && r.section_group!==state.section) return false;
        if(state.slot && r.open_slot!==state.slot) return false;
        if(state.validity && r.probability_sum_valid!==state.validity) return false;
        if(!q) return true;
        return [r.equipment_bucket,r.item_group_names,r.grade_code,r.grade_name,r.section_group,r.open_slot,r.option_id,r.option_name,r.source_block_index,r.source_file_offset].join(" ").toLowerCase().includes(q);
      });
    }
    function renderMetrics(data) {
      const values=[
        [data.length,"표시 행"],
        [new Set(data.map(r=>r.source_block_index)).size,"블록"],
        [new Set(data.map(r=>r.option_id)).size,"옵션 ID"],
        [new Set(data.map(r=>r.equipment_bucket)).size,"장비 묶음"],
        [data.filter(r=>r.probability_sum_valid==="false").length,"확률 오류 행"],
      ];
      $("metrics").innerHTML=values.map(([v,l])=>`<div class="metric"><b>${v.toLocaleString()}</b><span>${l}</span></div>`).join("");
    }
    const columns=[
      ["equipment_bucket","장비"],["item_group_names","그룹명"],["grade_code","등급 코드"],["grade_name","등급명"],
      ["section_group","section"],["open_slot","개방 줄"],["candidate_index","후보"],["option_id","옵션 ID"],
      ["option_name","옵션명"],["value_0_low16","수치 0"],["value_1_high16","수치 1"],
      ["normal_probability","일반 확률"],["improved_probability","개선 확률"],["option_tier","단계"],
      ["probability_sum_valid","확률 합"],["source_block_index","블록"],["source_file_offset","오프셋"]
    ];
    function cell(row,key) {
      let value=row[key] ?? "";
      if(key==="grade_name" && !value) return '<td class="unknown">미확정</td>';
      if(key==="probability_sum_valid") return `<td><span class="pill ${value==="true"?"good":"bad"}">${value==="true"?"정상":"오류"}</span></td>`;
      if(key==="equipment_bucket") return `<td><span class="pill">${esc(value)}</span></td>`;
      const cls=["grade_code","section_group","open_slot","candidate_index","option_id","value_0_low16","value_1_high16","normal_probability","improved_probability","option_tier","source_block_index"].includes(key)?"num":key==="option_name"?"option":"";
      return `<td class="${cls}">${esc(value)}</td>`;
    }
    function renderTable(data) {
      const pages=Math.max(1,Math.ceil(data.length/PAGE_SIZE)); state.page=Math.min(state.page,pages);
      const start=(state.page-1)*PAGE_SIZE, pageRows=data.slice(start,start+PAGE_SIZE);
      if(!pageRows.length) $("tableBox").innerHTML='<div class="empty">표시할 데이터가 없습니다.</div>';
      else $("tableBox").innerHTML=`<table><thead><tr>${columns.map(c=>`<th>${c[1]}</th>`).join("")}</tr></thead><tbody>${pageRows.map(r=>`<tr class="${r.probability_sum_valid==="false"?"invalid":""}">${columns.map(c=>cell(r,c[0])).join("")}</tr>`).join("")}</tbody></table>`;
      $("pageInfo").textContent=`${state.page} / ${pages} 페이지`;
      $("prev").disabled=state.page<=1; $("next").disabled=state.page>=pages;
    }
    function render() { const data=filtered(); renderMetrics(data); renderTable(data); }
    ["equipment","grade","section","slot","validity"].forEach(id=>$(id).addEventListener("change",e=>{state[id]=e.target.value;state.page=1;render();}));
    $("query").addEventListener("input",e=>{state.query=e.target.value;state.page=1;render();});
    $("prev").addEventListener("click",()=>{state.page-=1;render();});
    $("next").addEventListener("click",()=>{state.page+=1;render();});
    $("reset").addEventListener("click",()=>{Object.assign(state,{equipment:"",grade:"",section:"",slot:"",validity:"",query:"",page:1});["equipment","grade","section","slot","validity","query"].forEach(id=>$(id).value="");render();});
    initializeFilters(); render();
  </script>
</body>
</html>
'''


if __name__ == "__main__":
    main()
