#!/usr/bin/env python3
"""Render equipment open-option rows grouped by converter type as HTML."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "equipment_converter_type_options.csv"
INSTANDARD_JSON_PATH = ROOT / "data" / "processed" / "instandard_equipment.json"
HTML_PATH = ROOT / "equipment_open_options_viewer.html"


def inferred_tags(option_name: str) -> list[str]:
    """Supply browse tags when an open-option ID is absent from InstandardEquip."""
    tags: list[str] = []
    name = option_name.replace(" ", "")
    if "소환수" in name or "펫" in name or "조련" in name:
        tags.append("소환수/펫")
    if name.startswith("vs"):
        tags.extend(["대상", "피해"])
    if "pvp" in name.lower():
        tags.append("PvP")
    if any(word in name for word in ("힘", "민첩", "건강", "지혜", "지식", "카리스마", "운", "능력치")):
        tags.append("스탯")
    if any(word in name for word in ("체력", "CP", "마나")):
        tags.append("자원")
    if "속도" in name:
        tags.append("속도")
    if any(word in name for word in ("치명", "강타")):
        tags.append("치명타")
    if any(word in name for word in ("흡수", "흡혈")):
        tags.append("흡수")
    if any(word in name for word in ("저항", "방어", "피격", "감소")):
        tags.append("방어")
    if any(word in name for word in ("공격력", "대미지", "즉사")):
        tags.append("피해")
    if "물리" in name:
        tags.append("물리")
    if "마법" in name or "속성" in name:
        tags.append("속성")
    if "착용레벨" in name:
        tags.append("착용 조건")
    return list(dict.fromkeys(tags)) or ["기타"]


def add_tags(rows: list[dict[str, str]]) -> None:
    instandard = json.loads(INSTANDARD_JSON_PATH.read_text(encoding="utf-8"))
    known_tags = {
        str(option["option_id"]): option.get("tags", [])
        for option in instandard["options"]
    }
    for row in rows:
        row["tags"] = known_tags.get(row["option_id"]) or inferred_tags(row["option_name"])
        row["option_display_name"] = (
            row["option_name"][:-1]
            if row["option_name"].endswith("P")
            else row["option_name"]
        )


def build_html(rows: list[dict[str, str]]) -> str:
    """Apply the approved preview shell while injecting only collected DAT rows."""
    preview = (ROOT / "preview.html").read_text(encoding="utf-8")
    notes_start = preview.find("  <!--\n    Codex implementation notes")
    if notes_start >= 0:
        notes_end = preview.index("  -->\n", notes_start) + len("  -->\n")
        preview = preview[:notes_start] + preview[notes_end:]
    preview = preview.replace(
        '      <div class="header-actions">\n        <button class="outline-button" id="themeToggle"',
        '      <div class="header-actions">\n        <a class="outline-button" href="index.html">← 홈으로</a>\n        <button class="outline-button" id="themeToggle"',
        1,
    )
    tag_filter = '''
      <section class="filter-group tag-filter-group">
        <h2 class="filter-heading"><span class="step-number">5</span>태그 필터</h2>
        <div class="chip-grid" id="tagFilters"></div>
      </section>'''
    preview = preview.replace(
        "    </section>\n\n    <section class=\"context-row\"",
        f"{tag_filter}\n    </section>\n\n    <section class=\"context-row\"",
        1,
    ).replace(
        "  </style>",
        """    .tag-filter-group { grid-column:1 / -1; border-top:1px solid var(--line); border-left:0 !important; }
    @media (max-width:1220px) { .tag-filter-group { border-top:1px solid var(--line) !important; } }
  </style>""",
        1,
    )
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script = r'''<script>
    const rows = __EMBEDDED_DATA__;
    const CONVERTER_ORDER = {"일반 변환기":0,"개량된 변환기":1,"모조 변환기":2,"불타는 변환기":3,"협회 변환기":4};
    const $ = id => document.getElementById(id);
    const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const unique = values => [...new Set(values)];
    const numericSort = (a,b) => Number(a) - Number(b);
    const state = {equipment:"", converter:"", grade:"", selectedLines:[], linesInitialized:false, tag:"ALL", query:""};

    function gradeLabel(code) { const row=rows.find(item=>item.grade_code===code && item.grade_name); return `${code} · ${row?.grade_name || "명칭 미확정"}`; }
    function linesForCurrent() { return unique(rows.filter(row=>row.equipment_bucket===state.equipment && row.converter_type===state.converter && row.grade_code===state.grade).map(row=>row.open_slot)).sort(numericSort); }
    function ensureSelections() {
      const equipment=unique(rows.map(row=>row.equipment_bucket)).sort((a,b)=>a.localeCompare(b,"ko"));
      if(!equipment.includes(state.equipment)) state.equipment=equipment.includes("헬멧") ? "헬멧" : equipment[0];
      const converters=unique(rows.filter(row=>row.equipment_bucket===state.equipment).map(row=>row.converter_type)).sort((a,b)=>CONVERTER_ORDER[a]-CONVERTER_ORDER[b]);
      if(!converters.includes(state.converter)) state.converter=converters[0];
      const grades=unique(rows.filter(row=>row.equipment_bucket===state.equipment && row.converter_type===state.converter).map(row=>row.grade_code)).sort(numericSort);
      if(!grades.includes(state.grade)) state.grade=grades[0];
      const lines=linesForCurrent();
      state.selectedLines=state.selectedLines.filter(line=>lines.includes(line));
      if(!state.linesInitialized) { state.selectedLines=[...lines]; state.linesInitialized=true; }
      const tags=["ALL",...unique(rows.filter(row=>row.equipment_bucket===state.equipment && row.converter_type===state.converter && row.grade_code===state.grade && state.selectedLines.includes(row.open_slot)).flatMap(row=>row.tags)).sort((a,b)=>a.localeCompare(b,"ko"))];
      if(!tags.includes(state.tag)) state.tag="ALL";
      return {equipment,converters,grades,lines,tags};
    }
    function button(className,label,pressed,inner) { return `<button class="${className}" type="button" data-value="${esc(label)}" aria-pressed="${pressed}">${inner || esc(label)}</button>`; }
    const icons={"무기":"†","헬멧":"◉","갑옷":"◫","장갑":"✤","부츠":"∟","벨트":"⊏","목걸이":"◌","귀걸이":"◇"};
    function renderFilters(values) {
      $("equipmentFilters").innerHTML=values.equipment.map(value=>button("chip",value,state.equipment===value,`<span class="chip-icon">${icons[value]||"◇"}</span>${esc(value)}`)).join("");
      $("converterFilters").innerHTML=values.converters.map(value=>button("converter-chip",value,state.converter===value)).join("");
      $("gradeFilters").innerHTML=values.grades.map(value=>button("grade-chip",value,state.grade===value,esc(gradeLabel(value)))).join("");
      const all=values.lines.length===state.selectedLines.length;
      $("lineFilters").innerHTML=[button("line-chip","ALL",all,'<span class="line-icon">▤</span>ALL'),...values.lines.map(value=>button("line-chip",value,state.selectedLines.includes(value),`<span class="line-icon">${esc(value)}</span>${esc(value)}번째<br>개방 줄`))].join("");
      $("tagFilters").innerHTML=values.tags.map(value=>button("chip",value,state.tag===value,esc(value==="ALL" ? "전체 태그" : value))).join("");
    }
    function selectedLineLabel(lines) { if(!state.selectedLines.length) return "선택 없음"; if(state.selectedLines.length===lines.length) return "전체 개방 줄"; return state.selectedLines.length===1 ? `${state.selectedLines[0]}번째 개방 줄` : `${state.selectedLines.map(value=>`${value}번째`).join(" · ")} 개방 줄`; }
    function breadcrumb(values) {
      const items=[["1","장비 선택",state.equipment],["2","변환기 선택",state.converter],["3","아이템 등급",gradeLabel(state.grade)],["4","개방 줄",selectedLineLabel(values.lines)],["5","태그",state.tag==="ALL"?"전체 태그":state.tag]];
      $("breadcrumbPath").innerHTML=items.map((item,index)=>`${index?'<span class="breadcrumb-separator">›</span>':''}<span class="breadcrumb-step"><span class="breadcrumb-step-number">${item[0]}</span><span class="breadcrumb-step-source">${item[1]}</span><span class="breadcrumb-step-value">${esc(item[2])}</span></span>`).join("");
    }
    function filtered() {
      const q=state.query.trim().toLowerCase();
      return rows.filter(row=>row.equipment_bucket===state.equipment && row.converter_type===state.converter && row.grade_code===state.grade && state.selectedLines.includes(row.open_slot) && (state.tag==="ALL" || row.tags.includes(state.tag)) && (!q || [row.option_display,row.option_name,row.option_display_name,row.tags.join(" ")].join(" ").toLowerCase().includes(q))).sort((a,b)=>Number(a.open_slot)-Number(b.open_slot)||a.tags[0].localeCompare(b.tags[0],"ko")||a.tags.join("/").localeCompare(b.tags.join("/"),"ko")||Number(a.option_id)-Number(b.option_id)||Number(a.candidate_index)-Number(b.candidate_index));
    }
    function probability(value) { const number=Number(value); return `${Number.isInteger(number)?number:number.toFixed(2)}%`; }
    function table(data) { return `<div class="table-wrap"><table><thead><tr><th class="col-effect">옵션 효과</th><th class="col-name">옵션명 / 태그</th><th class="col-tier">단계</th><th class="col-probability">변환 확률</th><th class="col-candidate">후보</th></tr></thead><tbody>${data.map(row=>`<tr><td><div class="option-effect"><span class="option-glyph">◇</span><span>${esc(row.option_display)}</span></div></td><td>${esc(row.option_display_name)} <span class="tag-text">· ${esc(row.tags.join("/"))}</span></td><td><span class="tier-badge ${Number(row.option_tier)>=2?"tier-2":""}">${esc(row.option_tier)}단계</span></td><td><div class="probability-cell"><span class="probability-value">${probability(row.converter_probability)}</span></div></td><td class="candidate-value">${esc(row.candidate_index)}</td></tr>`).join("")}</tbody></table></div>`; }
    function results(values) {
      const data=filtered(), groups={}; data.forEach(row=>(groups[row.open_slot]??=[]).push(row));
      $("rowCount").textContent=`${data.length.toLocaleString()}개`;
      $("uniqueOptionCount").textContent=`${new Set(data.map(row=>`${row.option_id}/${row.option_tier}`)).size.toLocaleString()}개 옵션`;
      $("resultTitle").textContent=`${selectedLineLabel(values.lines)} 옵션`;
      $("activeSummary").textContent=`${state.equipment} · ${state.converter} · ${gradeLabel(state.grade)} · ${selectedLineLabel(values.lines)} · ${state.tag==="ALL"?"전체 태그":state.tag}`;
      $("emptyState").classList.toggle("visible",!data.length);
      $("resultSections").innerHTML=data.length?state.selectedLines.filter(line=>groups[line]).map(line=>`<section class="line-section"><header class="line-section-header"><h3 class="line-section-title">${line}번째 개방 줄</h3><span class="line-row-count">${groups[line].length}개 후보</span></header>${table(groups[line])}</section>`).join(""):"";
    }
    function render() { const values=ensureSelections(); renderFilters(values); breadcrumb(values); results(values); $("clearSearch").classList.toggle("visible",Boolean(state.query)); }
    function reset() { state.equipment=""; state.converter=""; state.grade=""; state.selectedLines=[]; state.linesInitialized=false; state.tag="ALL"; state.query=""; $("searchInput").value=""; render(); }
    function change(filter,value) { if(filter==="equipment") { state.equipment=value; state.converter=""; state.grade=""; state.selectedLines=[]; state.linesInitialized=false; state.tag="ALL"; } if(filter==="converter") { state.converter=value; state.grade=""; state.selectedLines=[]; state.linesInitialized=false; state.tag="ALL"; } if(filter==="grade") { state.grade=value; state.selectedLines=[]; state.linesInitialized=false; state.tag="ALL"; } if(filter==="tag") state.tag=value; render(); }
    $("equipmentFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item)change("equipment",item.dataset.value);});
    $("converterFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item)change("converter",item.dataset.value);});
    $("gradeFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item)change("grade",item.dataset.value);});
    $("tagFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item)change("tag",item.dataset.value);});
    $("lineFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(!item)return;const value=item.dataset.value, lines=linesForCurrent(); if(value==="ALL") state.selectedLines=state.selectedLines.length===lines.length?[]:[...lines]; else state.selectedLines=state.selectedLines.includes(value)?state.selectedLines.filter(line=>line!==value):[...state.selectedLines,value].sort(numericSort); state.tag="ALL"; render();});
    $("searchInput").addEventListener("input",event=>{state.query=event.target.value;render();});
    $("clearSearch").addEventListener("click",()=>{state.query="";$("searchInput").value="";$("searchInput").focus();render();});
    $("resetButton").addEventListener("click",reset);
    function setTheme(theme) { document.documentElement.dataset.theme=theme; const dark=theme==="dark"; $("themeToggleLabel").textContent=dark?"라이트 모드로 전환":"다크 모드로 전환"; $("themeToggle").querySelector("span").textContent=dark?"☾":"☀"; try { localStorage.setItem("redstone-ui-theme",theme); } catch (_) {} }
    $("themeToggle").addEventListener("click",()=>setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark"));
    window.addEventListener("storage",event=>{if(event.key==="redstone-ui-theme"&&(event.newValue==="dark"||event.newValue==="light"))setTheme(event.newValue);});
    try { const theme=localStorage.getItem("redstone-ui-theme"); if(theme==="dark"||theme==="light") setTheme(theme); } catch (_) {}
    render();
  </script>'''.replace("__EMBEDDED_DATA__", data)
    script_start = preview.index("<script>")
    script_end = preview.index("</script>", script_start) + len("</script>")
    return preview[:script_start] + script + preview[script_end:]


def main() -> None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"no rows found in {CSV_PATH}")
    add_tags(rows)

    html = build_html(rows)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {len(rows)} rows to {HTML_PATH}")


TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>장비 개방 옵션 · 변환기별</title>
  <style>
    :root {
      --bg:#f4f6f8; --panel:#fff; --ink:#17202a; --muted:#68717d;
      --line:#dce1e7; --head:#edf1f5; --accent:#176b5b; --soft:#e2f3ee;
      --bad:#a42a2a; --bad-bg:#fff0f0; --shadow:0 1px 3px rgba(20,30,45,.08); --header-bg:rgba(244,246,248,.97);
    }
    body.night { color-scheme:dark; --bg:#10161d; --panel:#18222d; --ink:#e7edf4; --muted:#aebbc8; --line:#344454; --head:#243240; --accent:#55c7ad; --soft:#173e3a; --bad:#ff9c9c; --bad-bg:#44252a; --shadow:0 1px 3px rgba(0,0,0,.3); --header-bg:rgba(16,22,29,.97); }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
    header { position:sticky; top:0; z-index:20; border-bottom:1px solid var(--line); background:var(--header-bg); backdrop-filter:blur(8px); }
    .top { max-width:1800px; margin:auto; padding:14px 18px; }
    .title-row { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
    .header-actions { display:flex; align-items:center; gap:8px; }
    h1 { margin:0 0 3px; font-size:20px; }
    .subtitle { color:var(--muted); font-size:12px; }
    input,button { min-height:36px; border:1px solid var(--line); border-radius:9px; background:var(--panel); color:var(--ink); padding:7px 10px; font:inherit; }
    .home-link { min-height:32px; border:1px solid var(--line); border-radius:9px; background:var(--panel); color:var(--ink); padding:5px 10px; font-size:12px; font-weight:700; text-decoration:none; }
    button { cursor:pointer; font-weight:700; }
    button:hover,.home-link:hover { border-color:var(--accent); }
    .theme-toggle { flex:none; min-height:32px; padding:5px 10px; font-size:12px; }
    .theme-toggle[aria-pressed="true"] { border-color:var(--accent); background:var(--soft); color:var(--accent); }
    main { max-width:1500px; margin:auto; padding:18px 20px 40px; }
    .explorer { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:10px 16px; padding:12px 14px; border:1px solid var(--line); border-radius:14px; background:var(--panel); box-shadow:var(--shadow); }
    .step:first-child { grid-column:1/-1; }
    .step-label { display:flex; align-items:center; gap:7px; margin-bottom:7px; color:var(--muted); font-size:11px; font-weight:800; }
    .step-number { display:inline-grid; width:20px; height:20px; place-items:center; border-radius:50%; background:var(--soft); color:var(--accent); }
    .choices { display:flex; gap:7px; overflow-x:auto; padding:1px 1px 5px; scrollbar-width:thin; }
    .choice { flex:none; min-height:34px; padding:6px 12px; border-radius:999px; color:var(--muted); font-size:12px; }
    .choice.active { border-color:var(--accent); background:var(--accent); color:#fff; }
    body.night .choice.active { color:#0c211c; }
    .tools { display:grid; grid-template-columns:1fr minmax(220px,360px); align-items:center; gap:14px; margin:12px 0 8px; }
    .breadcrumb { color:var(--muted); font-size:12px; }
    .breadcrumb b { color:var(--ink); }
    .search { width:100%; }
    .results-head { display:flex; align-items:end; justify-content:space-between; gap:12px; margin:12px 0 7px; }
    .results-head h2 { margin:0; font-size:16px; }
    .results-head p { margin:2px 0 0; color:var(--muted); font-size:12px; }
    .result-count { color:var(--accent); font-size:13px; font-weight:800; }
    .slot-section + .slot-section { margin-top:20px; padding-top:14px; border-top:1px solid var(--line); }
    .slot-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:0 2px 6px; }
    .slot-heading h3 { margin:0; font-size:14px; }
    .slot-heading span { color:var(--muted); font-size:11px; font-weight:750; }
    .option-list { overflow:hidden; border:1px solid var(--line); border-radius:10px; background:var(--panel); box-shadow:var(--shadow); }
    .list-head,.option-row { display:grid; grid-template-columns:minmax(220px,1.5fr) minmax(180px,1fr) 70px 150px 58px; align-items:center; gap:10px; }
    .list-head { min-height:30px; padding:5px 11px; border-bottom:1px solid var(--line); background:var(--head); color:var(--muted); font-size:10px; font-weight:800; }
    .option-row { width:100%; min-height:39px; padding:5px 11px; border:0; border-bottom:1px solid var(--line); border-radius:0; background:var(--panel); color:var(--ink); text-align:left; }
    .option-row:last-child { border-bottom:0; }
    .option-row:hover { background:var(--soft); }
    .option-row:focus-visible { position:relative; outline:2px solid var(--accent); outline-offset:-2px; }
    .row-effect { overflow:hidden; font-size:13px; font-weight:800; text-overflow:ellipsis; white-space:nowrap; }
    .row-name { overflow:hidden; color:var(--muted); font-size:11px; font-weight:700; text-overflow:ellipsis; white-space:nowrap; }
    .row-candidate { color:var(--muted); text-align:right; font-size:10px; font-weight:700; }
    .probability { display:flex; align-items:center; gap:7px; color:var(--muted); font-size:10px; }
    .probability b { min-width:38px; color:var(--accent); text-align:right; font-size:12px; font-variant-numeric:tabular-nums; }
    .probability-track { width:70px; height:4px; overflow:hidden; border-radius:999px; background:var(--line); }
    .probability-fill { height:100%; min-width:3px; border-radius:inherit; background:var(--accent); }
    .tier { display:inline-flex; align-items:center; min-height:19px; padding:1px 6px; border-radius:999px; font-size:10px; font-weight:800; }
    .tier-1 { background:#e9edf1; color:#53606d; }
    .tier-2 { background:#dcecff; color:#245c91; }
    .tier-3 { background:#eee3ff; color:#7143a2; }
    .tier-high { background:#ffe4c9; color:#8d5015; }
    body.night .tier-1 { background:#33414e; color:#d0dae4; }
    body.night .tier-2 { background:#193b5b; color:#9dccfa; }
    body.night .tier-3 { background:#3b2852; color:#d5b6f7; }
    body.night .tier-high { background:#4c3420; color:#f0bd82; }
    .detail-item { min-height:52px; padding:9px 0; border-bottom:1px solid var(--line); }
    .detail-item span { display:block; color:var(--muted); font-size:10px; font-weight:700; }
    .detail-item b { display:block; margin-top:3px; color:var(--ink); font-size:12px; overflow-wrap:anywhere; }
    .guide { margin-top:18px; color:var(--muted); font-size:11px; }
    .guide summary { cursor:pointer; font-weight:750; }
    .guide p { margin:7px 0 0; }
    .empty { grid-column:1/-1; padding:52px 20px; border:1px dashed var(--line); border-radius:14px; text-align:center; color:var(--muted); }
    .backdrop { position:fixed; inset:0; z-index:50; background:rgba(5,10,15,.44); opacity:0; transition:opacity .18s ease; }
    .backdrop.open { opacity:1; }
    .drawer { position:absolute; inset:0 0 0 auto; width:min(420px,92vw); overflow:auto; padding:22px; border-left:1px solid var(--line); background:var(--panel); box-shadow:-12px 0 40px rgba(0,0,0,.2); transform:translateX(100%); transition:transform .2s ease; }
    .backdrop.open .drawer { transform:translateX(0); }
    .drawer-head { display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .drawer-head h2 { margin:0; font-size:17px; }
    .drawer-close { width:34px; min-height:34px; padding:0; font-size:18px; }
    .drawer-effect { margin:24px 0 4px; font-size:23px; font-weight:850; }
    .drawer-name { color:var(--muted); font-size:12px; }
    .drawer-details { margin-top:20px; }
    body.drawer-open { overflow:hidden; }
    @media (max-width:900px) { .explorer { grid-template-columns:1fr; } .step:first-child { grid-column:auto; } .list-head,.option-row { grid-template-columns:minmax(180px,1.4fr) minmax(150px,1fr) 65px 110px; } .list-head > :last-child,.row-candidate { display:none; } }
    @media (max-width:700px) { main { padding:12px 12px 30px; } .top { padding:12px; } .subtitle { display:none; } .explorer { padding:10px; border-radius:12px; } .tools { grid-template-columns:1fr; } .list-head,.option-row { grid-template-columns:minmax(150px,1fr) 60px 90px; } .list-head > :nth-child(2),.row-name { display:none; } .probability-track { display:none; } }
  </style>
</head>
<body>
  <header>
    <div class="top">
      <div class="title-row">
        <div>
          <h1>장비 개방 옵션 · 변환기별</h1>
          <div class="subtitle">변환기 종류별로 확률 필드를 분리한 원본 DAT 직접 조인 결과입니다.</div>
        </div>
        <div class="header-actions"><a class="home-link" href="index.html">← 시작 화면</a><button id="themeToggle" class="theme-toggle" type="button" aria-pressed="false">나이트 모드: OFF</button></div>
      </div>
    </div>
  </header>
  <main>
    <section class="explorer" aria-label="옵션 탐색 조건">
      <div class="step"><div class="step-label"><span class="step-number">1</span>장비 선택</div><div class="choices" id="equipmentChoices"></div></div>
      <div class="step"><div class="step-label"><span class="step-number">2</span>변환기 선택</div><div class="choices" id="converterChoices"></div></div>
      <div class="step"><div class="step-label"><span class="step-number">3</span>아이템 등급</div><div class="choices" id="gradeChoices"></div></div>
      <div class="step"><div class="step-label"><span class="step-number">4</span>개방 줄</div><div class="choices" id="slotChoices"></div></div>
      <div class="step"><div class="step-label"><span class="step-number">5</span>태그 필터</div><div class="choices" id="tagChoices"></div></div>
    </section>
    <div class="tools">
      <div class="breadcrumb" id="breadcrumb"></div>
      <input id="query" class="search" type="search" placeholder="현재 목록에서 옵션 검색" aria-label="옵션 검색">
    </div>
    <section class="results-head"><div><h2 id="resultTitle"></h2><p>행을 누르면 원본 데이터까지 확인할 수 있습니다.</p></div><div class="result-count" id="resultCount"></div></section>
    <section id="optionGrid"></section>
    <details class="guide"><summary>변환기 확률·태그 안내</summary><p>일반·모조·불타는·협회 변환기는 <b>float_a</b>, 개량된 변환기는 <b>float_b</b>를 표시합니다. 협회 변환기는 DX 유니크만 포함하며 현재 원본에서 두 값이 동일합니다.</p><p>태그는 비규격 장비 데이터에 같은 옵션 ID가 있는 경우 해당 태그를 사용하며, 그 외 옵션은 이름을 기준으로 탐색용 범주를 부여합니다.</p></details>
  </main>
  <div id="detailBackdrop" class="backdrop" hidden>
    <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawerTitle">
      <div class="drawer-head"><h2 id="drawerTitle">옵션 상세 정보</h2><button id="drawerClose" class="drawer-close" type="button" aria-label="닫기">×</button></div>
      <div id="drawerContent"></div>
    </aside>
  </div>
  <script>
    const rows = __EMBEDDED_DATA__;
    const CONVERTER_ORDER = {"일반 변환기":0,"개량된 변환기":1,"모조 변환기":2,"불타는 변환기":3,"협회 변환기":4};
    const state = {equipment:"",converter:"",grade:"",slot:"",tag:"ALL",query:""};
    const $ = (id) => document.getElementById(id);
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const numericSort = (a,b) => Number(a)-Number(b);
    const unique = (values) => [...new Set(values)];
    const tierClass = (tier) => Number(tier) >= 4 ? "tier-high" : `tier-${tier || 1}`;
    const gradeLabel = (code) => {
      const row=rows.find(r=>r.grade_code===code && r.grade_name);
      return `${code} · ${row ? row.grade_name : "명칭 미확정"}`;
    };
    function ensureSelections() {
      const equipment=unique(rows.map(r=>r.equipment_bucket)).sort((a,b)=>a.localeCompare(b,"ko"));
      if(!equipment.includes(state.equipment)) state.equipment=equipment.includes("헬멧") ? "헬멧" : equipment[0];
      const converters=unique(rows.filter(r=>r.equipment_bucket===state.equipment).map(r=>r.converter_type)).sort((a,b)=>CONVERTER_ORDER[a]-CONVERTER_ORDER[b]);
      if(!converters.includes(state.converter)) state.converter=converters[0];
      const grades=unique(rows.filter(r=>r.equipment_bucket===state.equipment && r.converter_type===state.converter).map(r=>r.grade_code)).sort(numericSort);
      if(!grades.includes(state.grade)) state.grade=grades[0];
      const slots=["ALL",...unique(rows.filter(r=>r.equipment_bucket===state.equipment && r.converter_type===state.converter && r.grade_code===state.grade).map(r=>r.open_slot)).sort(numericSort)];
      if(!slots.includes(state.slot)) state.slot="ALL";
      const tags=["ALL",...unique(rows.filter(r=>r.equipment_bucket===state.equipment && r.converter_type===state.converter && r.grade_code===state.grade && (state.slot==="ALL" || r.open_slot===state.slot)).flatMap(r=>r.tags)).sort((a,b)=>a.localeCompare(b,"ko"))];
      if(!tags.includes(state.tag)) state.tag="ALL";
      return {equipment,converters,grades,slots,tags};
    }
    function choiceButtons(id,filter,values,label=(value)=>value) {
      $(id).innerHTML=values.map(value=>`<button type="button" class="choice ${state[filter]===value?"active":""}" data-filter="${filter}" data-value="${esc(value)}" aria-pressed="${state[filter]===value}">${esc(label(value))}</button>`).join("");
    }
    function renderNavigation() {
      const values=ensureSelections();
      choiceButtons("equipmentChoices","equipment",values.equipment);
      choiceButtons("converterChoices","converter",values.converters);
      choiceButtons("gradeChoices","grade",values.grades,gradeLabel);
      choiceButtons("slotChoices","slot",values.slots,value=>value==="ALL" ? "ALL" : `${value}번째 개방 줄`);
      choiceButtons("tagChoices","tag",values.tags,value=>value==="ALL" ? "전체 태그" : value);
    }
    function filtered() {
      const q=state.query.trim().toLowerCase();
      const data=rows.filter(r => {
        if(r.equipment_bucket!==state.equipment || r.converter_type!==state.converter || r.grade_code!==state.grade) return false;
        if(state.slot!=="ALL" && r.open_slot!==state.slot) return false;
        if(state.tag!=="ALL" && !r.tags.includes(state.tag)) return false;
        if(!q) return true;
        return [r.option_id,r.option_name,r.option_display_name,r.option_display,r.tags.join(" ")].join(" ").toLowerCase().includes(q);
      });
      data.sort((a,b) =>
        (a.tags[0].localeCompare(b.tags[0],"ko")) ||
        (a.tags.join("/").localeCompare(b.tags.join("/"),"ko")) ||
        (Number(a.option_id)-Number(b.option_id)) ||
        (Number(a.option_tier)-Number(b.option_tier)) ||
        (Number(a.candidate_index)-Number(b.candidate_index))
      );
      return data;
    }
    function detailItem(label,value) { return `<div class="detail-item"><span>${esc(label)}</span><b>${esc(value || "-")}</b></div>`; }
    const listHeader = '<div class="list-head"><span>옵션 효과</span><span>옵션 / 태그</span><span>단계</span><span>변환 확률</span><span>후보</span></div>';
    function optionRow(row) {
      const probability=Math.max(0,Math.min(100,Number(row.converter_probability)||0));
      const tier=row.option_tier || "1";
      const index=rows.indexOf(row);
      return `<button type="button" class="option-row" data-row-index="${index}">
        <span class="row-effect">${esc(row.option_display)}</span>
        <span class="row-name">${esc(row.option_display_name)} · ${esc(row.tags.join("/"))}</span>
        <span><span class="tier ${tierClass(tier)}">${esc(tier)}단계</span></span>
        <span class="probability"><b>${esc(row.converter_probability)}%</b><span class="probability-track"><span class="probability-fill" style="width:${Math.max(5,probability)}%"></span></span></span>
        <span class="row-candidate">${esc(row.candidate_index)}</span>
      </button>`;
    }
    function optionList(data) { return `<div class="option-list">${listHeader}${data.map(optionRow).join("")}</div>`; }
    function openDrawer(row) {
      $("drawerContent").innerHTML=`<div class="drawer-effect">${esc(row.option_display)}</div><div class="drawer-name">${esc(row.option_display_name)} · ${esc(row.option_tier || 1)}단계</div><div class="drawer-details">
        ${detailItem("장비",row.equipment_bucket)}${detailItem("변환기",row.converter_type)}${detailItem("등급",`${row.grade_code} · ${row.grade_name || "명칭 미확정"}`)}${detailItem("개방 줄",`${row.open_slot}번째`)}${detailItem("태그",row.tags.join("/"))}${detailItem("변환 확률",`${row.converter_probability}%`)}${detailItem("후보 순서",row.candidate_index)}${detailItem("옵션 ID",row.option_id)}${detailItem("원본 확률 필드",row.converter_probability_source)}${detailItem("원본 값",row.value_raw)}${detailItem("블록",row.source_block_index)}${detailItem("오프셋",row.source_file_offset)}</div>`;
      $("detailBackdrop").hidden=false;
      document.body.classList.add("drawer-open");
      requestAnimationFrame(()=>$("detailBackdrop").classList.add("open"));
      $("drawerClose").focus();
    }
    function closeDrawer() {
      $("detailBackdrop").classList.remove("open");
      document.body.classList.remove("drawer-open");
      setTimeout(()=>$("detailBackdrop").hidden=true,200);
    }
    function render() {
      renderNavigation();
      const data=filtered();
      const grade=gradeLabel(state.grade);
      const slotLabel=state.slot==="ALL" ? "전체 개방 줄" : `${state.slot}번째 개방 줄`;
      const tagLabel=state.tag==="ALL" ? "전체 태그" : state.tag;
      $("breadcrumb").innerHTML=`현재 위치　<b>${esc(state.equipment)} › ${esc(state.converter)} › ${esc(grade)} › ${esc(slotLabel)} › ${esc(tagLabel)}</b>`;
      $("resultTitle").textContent=`${slotLabel} 옵션`;
      $("resultCount").textContent=`${data.length}개`;
      if(!data.length) $("optionGrid").innerHTML='<div class="empty">조건에 맞는 옵션이 없습니다.</div>';
      else if(state.slot!=="ALL") $("optionGrid").innerHTML=optionList(data);
      else {
        const slots=unique(data.map(row=>row.open_slot)).sort(numericSort);
        $("optionGrid").innerHTML=slots.map(slot=>{
          const slotRows=data.filter(row=>row.open_slot===slot);
          return `<section class="slot-section"><div class="slot-heading"><h3>${esc(slot)}번째 개방 줄</h3><span>${slotRows.length}개 옵션</span></div>${optionList(slotRows)}</section>`;
        }).join("");
      }
    }
    function setNightMode(enabled) {
      document.body.classList.toggle("night", enabled);
      $("themeToggle").setAttribute("aria-pressed", String(enabled));
      $("themeToggle").textContent=`나이트 모드: ${enabled ? "ON" : "OFF"}`;
    }
    $("query").addEventListener("input",e=>{state.query=e.target.value;render();});
    $("equipmentChoices").parentElement.parentElement.addEventListener("click",e=>{
      const choice=e.target.closest(".choice");
      if(!choice) return;
      const filter=choice.dataset.filter;
      state[filter]=choice.dataset.value;
      if(filter==="equipment") { state.converter=""; state.grade=""; state.slot=""; state.tag="ALL"; }
      if(filter==="converter") { state.grade=""; state.slot=""; state.tag="ALL"; }
      if(filter==="grade") { state.slot=""; state.tag="ALL"; }
      if(filter==="slot") state.tag="ALL";
      state.query=""; $("query").value=""; render();
    });
    $("optionGrid").addEventListener("click",e=>{ const card=e.target.closest("[data-row-index]"); if(card) openDrawer(rows[Number(card.dataset.rowIndex)]); });
    $("drawerClose").addEventListener("click",closeDrawer);
    $("detailBackdrop").addEventListener("click",e=>{if(e.target===$("detailBackdrop")) closeDrawer();});
    document.addEventListener("keydown",e=>{if(e.key==="Escape" && !$("detailBackdrop").hidden) closeDrawer();});
    $("themeToggle").addEventListener("click",()=>setNightMode(!document.body.classList.contains("night")));
    render();
  </script>
</body>
</html>
'''


if __name__ == "__main__":
    main()
