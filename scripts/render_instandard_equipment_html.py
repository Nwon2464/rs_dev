#!/usr/bin/env python3
"""Render non-standard equipment from the validated pre-render CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "instandard_equipment_render_rows.csv"
METADATA = ROOT / "data" / "processed" / "instandard_equipment.json"
OUTPUT = ROOT / "instandard_equipment_viewer.html"


def build_render_dataset() -> dict[str, Any]:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"no rows found in {SOURCE}")

    equipment: list[dict[str, Any]] = []
    equipment_map: dict[int, dict[str, Any]] = {}
    option_maps: dict[int, dict[int, dict[str, Any]]] = {}
    for row in rows:
        equipment_id = int(row["item_group_id"])
        option_id = int(row["option_id"])
        if equipment_id not in equipment_map:
            item = {
                "item_group_id": equipment_id,
                "item_group_name": row["item_group_name"],
                "options": [],
            }
            equipment_map[equipment_id] = item
            option_maps[equipment_id] = {}
            equipment.append(item)
        if option_id not in option_maps[equipment_id]:
            option = {
                "option_order": int(row["option_order_in_equipment"]),
                "option_id": option_id,
                "option_name": row["option_name"],
                "option_display_name": (
                    row["option_name"][:-1]
                    if row["option_name"].endswith("P")
                    else row["option_name"]
                ),
                "option_template": row["option_template"],
                "tags": row["tags"].split("/") if row["tags"] else [],
                "assignment_basis": row["assignment_basis"],
                "groups": [],
            }
            option_maps[equipment_id][option_id] = option
            equipment_map[equipment_id]["options"].append(option)
        option_maps[equipment_id][option_id]["groups"].append(
            {
                "raw_tier_index": int(row["raw_tier_index"]),
                "option_level_raw": int(row["option_level_raw"]),
                "group_index": int(row["option_level_group_index"]),
                "group_number": int(row["option_level_group_number"]),
                "offset": int(row["group_index_offset_from_raw_tier"]),
                "value_0_min": int(row["value_0_min"]),
                "value_0_max": int(row["value_0_max"]),
                "display_min": row["display_min"],
                "display_max": row["display_max"],
                "rolls": [
                    [int(value) for value in row[f"roll_{index:02d}_raw"].split("/")]
                    for index in range(1, 11)
                ],
            }
        )

    for item in equipment:
        item["options"].sort(key=lambda option: option["option_order"])
        for option in item["options"]:
            option["groups"].sort(key=lambda group: group["group_index"])

    return {
        "schema_version": metadata["schema_version"],
        "summary": metadata["summary"],
        "equipment": equipment,
        "source_csv": str(SOURCE.relative_to(ROOT)),
    }


TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>비규격 장비 옵션 탐색기</title>
  <style>
    :root { --bg:#f4f6f8; --panel:#fff; --ink:#17202a; --muted:#68717d; --line:#dce1e7; --head:#edf1f5; --accent:#7b3c9d; --soft:#f2e7f8; --shadow:0 1px 3px rgba(20,30,45,.08); --header-bg:rgba(244,246,248,.97); }
    body.night { color-scheme:dark; --bg:#10161d; --panel:#18222d; --ink:#e7edf4; --muted:#aebbc8; --line:#344454; --head:#243240; --accent:#d5a9ec; --soft:#3a2548; --shadow:0 1px 3px rgba(0,0,0,.3); --header-bg:rgba(16,22,29,.97); }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; } header { position:sticky; top:0; z-index:20; border-bottom:1px solid var(--line); background:var(--header-bg); backdrop-filter:blur(8px); }.top { max-width:1700px; margin:auto; padding:14px 18px; }.title-row,.results-head,.drawer-head,.group-head { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; } h1 { margin:0 0 3px; font-size:20px; }.subtitle,.breadcrumb,.results-head p,.guide { color:var(--muted); font-size:12px; }.nav { display:flex; gap:8px; } a,button,input { min-height:36px; border:1px solid var(--line); border-radius:9px; background:var(--panel); color:var(--ink); padding:7px 10px; font:inherit; } a { text-decoration:none; font-weight:700; } button { cursor:pointer; font-weight:700; } button:hover,a:hover { border-color:var(--accent); }.theme-toggle { min-height:32px; padding:5px 10px; font-size:12px; }.theme-toggle[aria-pressed="true"] { border-color:var(--accent); background:var(--soft); color:var(--accent); }
    main { max-width:1500px; margin:auto; padding:18px 20px 40px; }.explorer { display:grid; grid-template-columns:1.35fr 1fr 1fr; gap:10px 16px; padding:12px 14px; border:1px solid var(--line); border-radius:14px; background:var(--panel); box-shadow:var(--shadow); }.step-label { display:flex; align-items:center; gap:7px; margin-bottom:7px; color:var(--muted); font-size:11px; font-weight:800; }.step-number { display:inline-grid; width:20px; height:20px; place-items:center; border-radius:50%; background:var(--soft); color:var(--accent); }.choices { display:flex; gap:7px; overflow-x:auto; padding:1px 1px 5px; scrollbar-width:thin; }.choice { flex:none; min-height:34px; padding:6px 12px; border-radius:999px; color:var(--muted); font-size:12px; }.choice.active { border-color:var(--accent); background:var(--accent); color:#fff; } body.night .choice.active { color:#26112e; }
    .tools { display:grid; grid-template-columns:1fr minmax(220px,360px); align-items:center; gap:14px; margin:12px 0 8px; }.breadcrumb b { color:var(--ink); }.search { width:100%; }.results-head { align-items:end; margin:12px 0 7px; }.results-head h2 { margin:0; font-size:16px; }.results-head p { margin:2px 0 0; }.result-count { color:var(--accent); font-size:13px; font-weight:800; }.option-list { overflow:hidden; border:1px solid var(--line); border-radius:10px; background:var(--panel); box-shadow:var(--shadow); }.list-head,.option-row { display:grid; grid-template-columns:minmax(230px,1.45fr) minmax(160px,.9fr) 105px 125px minmax(190px,1fr); align-items:center; gap:10px; }.list-head { min-height:30px; padding:5px 11px; border-bottom:1px solid var(--line); background:var(--head); color:var(--muted); font-size:10px; font-weight:800; }.option-row { width:100%; min-height:47px; padding:6px 11px; border:0; border-bottom:1px solid var(--line); border-radius:0; background:var(--panel); color:var(--ink); text-align:left; }.option-row:last-child { border-bottom:0; }.option-row:hover { background:var(--soft); }.row-effect { overflow:hidden; font-size:13px; font-weight:800; text-overflow:ellipsis; white-space:nowrap; }.row-name,.row-level { overflow:hidden; color:var(--muted); font-size:11px; font-weight:700; text-overflow:ellipsis; white-space:nowrap; }.group-pill { display:inline-flex; min-height:20px; align-items:center; padding:2px 7px; border-radius:999px; background:var(--soft); color:var(--accent); font-size:10px; font-weight:800; }.rolls { overflow:hidden; color:var(--muted); font-size:11px; font-variant-numeric:tabular-nums; text-overflow:ellipsis; white-space:nowrap; }.empty { padding:52px 20px; border:1px dashed var(--line); border-radius:14px; text-align:center; color:var(--muted); }.guide { margin-top:18px; }.guide summary { cursor:pointer; font-weight:750; }.guide p { margin:7px 0 0; }
    .backdrop { position:fixed; inset:0; z-index:50; background:rgba(5,10,15,.44); opacity:0; transition:opacity .18s ease; }.backdrop.open { opacity:1; }.drawer { position:absolute; inset:0 0 0 auto; width:min(600px,94vw); overflow:auto; padding:22px; border-left:1px solid var(--line); background:var(--panel); box-shadow:-12px 0 40px rgba(0,0,0,.2); transform:translateX(100%); transition:transform .2s ease; }.backdrop.open .drawer { transform:translateX(0); }.drawer-head { align-items:center; }.drawer-head h2 { margin:0; font-size:17px; }.drawer-close { width:34px; min-height:34px; padding:0; font-size:18px; }.drawer-effect { margin:24px 0 4px; font-size:23px; font-weight:850; }.drawer-name { color:var(--muted); font-size:12px; }.detail-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:20px; }.detail-item { min-height:52px; padding:9px; border:1px solid var(--line); border-radius:9px; background:var(--bg); }.detail-item.wide { grid-column:1/-1; }.detail-item span { display:block; color:var(--muted); font-size:10px; font-weight:700; }.detail-item b { display:block; margin-top:3px; font-size:12px; overflow-wrap:anywhere; }.group-section { margin-top:18px; padding-top:14px; border-top:1px solid var(--line); }.group-head { align-items:center; }.group-head h3 { margin:0; font-size:14px; }.group-head span { color:var(--muted); font-size:11px; }.roll-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:6px; margin-top:9px; }.roll { padding:7px 4px; border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--accent); font-size:11px; font-weight:800; text-align:center; font-variant-numeric:tabular-nums; } body.drawer-open { overflow:hidden; }
    @media(max-width:900px) { .explorer { grid-template-columns:1fr; }.list-head,.option-row { grid-template-columns:minmax(180px,1.4fr) minmax(140px,1fr) 95px minmax(150px,1fr); }.list-head>:nth-child(4),.row-level { display:none; } } @media(max-width:700px) { .top,main { padding-left:12px; padding-right:12px; }.subtitle { display:none; }.explorer { padding:10px; }.tools { grid-template-columns:1fr; }.list-head,.option-row { grid-template-columns:minmax(140px,1fr) 90px 120px; }.list-head>:nth-child(2),.row-name { display:none; }.roll-grid { grid-template-columns:repeat(2,1fr); } }
  </style>
</head>
<body>
  <header><div class="top"><div class="title-row"><div><h1>비규격 장비 옵션</h1><div class="subtitle">장비군별 옵션과 OptionLevel 공통 수치 구간을 렌더링 직전 CSV에서 표시합니다.</div></div><div class="nav"><a href="index.html" target="_top">← 시작 화면</a><button id="themeToggle" class="theme-toggle" type="button" aria-pressed="false">나이트 모드: OFF</button></div></div></div></header>
  <main>
    <section class="explorer" aria-label="비규격 옵션 탐색 조건"><div class="step"><div class="step-label"><span class="step-number">1</span>장비 선택</div><div class="choices" id="equipmentChoices"></div></div><div class="step"><div class="step-label"><span class="step-number">2</span>태그 필터</div><div class="choices" id="tagChoices"></div></div><div class="step"><div class="step-label"><span class="step-number">3</span>공통 수치 구간</div><div class="choices" id="groupChoices"></div></div></section>
    <div class="tools"><div class="breadcrumb" id="breadcrumb"></div><input id="query" class="search" type="search" placeholder="현재 장비군의 옵션 검색" aria-label="옵션 검색"></div>
    <section class="results-head"><div><h2 id="resultTitle"></h2><p>전체 보기에서는 옵션당 한 행, 구간 선택 시 해당 구간의 정확한 10개 후보를 표시합니다.</p></div><div class="result-count" id="resultCount"></div></section><section id="optionGrid"></section>
    <details class="guide" open><summary>구조 해석 안내</summary><p><b>공통 수치 구간</b>은 활성 OptionLevel 키를 정렬한 내부 비교축이며 게임의 공식 티어 명칭으로 확정하지 않았습니다. 원본 <b>raw_tier_index</b>는 옵션 내부 배열 순번입니다. 고급 옵션은 로컬 0~6이 공통 구간 3~9에 대응합니다.</p><p><b>1500 장갑 실물 대조:</b> 물리 공격력 95%(구간 1), 무기 최대 공격력 17(구간 5), 물리 강타 대미지 46%(구간 4), 물리 강타 확률 32%(구간 3), 공격 속도 34%(구간 2).</p></details>
  </main>
  <div id="detailBackdrop" class="backdrop" hidden><aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawerTitle"><div class="drawer-head"><h2 id="drawerTitle">옵션 상세 정보</h2><button id="drawerClose" class="drawer-close" type="button" aria-label="닫기">×</button></div><div id="drawerContent"></div></aside></div>
  <script>
    const dataset = __EMBEDDED_DATA__;
    const state = {equipment:"",tag:"ALL",group:"ALL",query:""};
    const $ = id => document.getElementById(id);
    const esc = value => String(value ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const unique = values => [...new Set(values)];
    const numericSort = (a,b) => Number(a)-Number(b);
    function renderValue(template,vector) { return String(template||"").replace(/\[([012])(?:\.(\d+))?([%％])?\]/g,(_,index,digits,suffix)=>{const n=Number(vector[Number(index)]);const d=Number(digits||0);return `${d?(n/10**d).toFixed(d):n}${suffix||""}`;}); }
    function currentEquipment() { return dataset.equipment.find(item=>item.item_group_name===state.equipment); }
    function ensureSelections() { const equipment=dataset.equipment.map(item=>item.item_group_name);if(!equipment.includes(state.equipment))state.equipment=equipment.includes("헬멧")?"헬멧":equipment[0];const options=currentEquipment().options;const tags=["ALL",...unique(options.flatMap(option=>option.tags)).sort((a,b)=>a.localeCompare(b,"ko"))];if(!tags.includes(state.tag))state.tag="ALL";const groups=["ALL",...unique(options.flatMap(option=>option.groups.map(group=>String(group.group_index)))).sort(numericSort)];if(!groups.includes(state.group))state.group="ALL";return{equipment,tags,groups}; }
    function choices(id,field,values,label=value=>value) { $(id).innerHTML=values.map(value=>`<button class="choice ${state[field]===value?"active":""}" type="button" data-field="${field}" data-value="${esc(value)}" aria-pressed="${state[field]===value}">${esc(label(value))}</button>`).join(""); }
    function filteredOptions() { const q=state.query.trim().toLowerCase();return currentEquipment().options.filter(option=>{if(state.tag!=="ALL"&&!option.tags.includes(state.tag))return false;if(state.group!=="ALL"&&!option.groups.some(group=>String(group.group_index)===state.group))return false;if(!q)return true;return[option.option_id,option.option_name,option.option_template,option.tags.join(" ")].join(" ").toLowerCase().includes(q);}).sort((a,b)=>a.tags[0].localeCompare(b.tags[0],"ko")||a.tags.join("/").localeCompare(b.tags.join("/"),"ko")||a.option_order-b.option_order||a.option_id-b.option_id); }
    function groupFor(option) { return option.groups.find(group=>String(group.group_index)===state.group); }
    function summary(option) { const vectors=option.groups.flatMap(group=>group.rolls);const values=vectors.map(vector=>vector[0]);const min=Math.min(...values),max=Math.max(...values);return{effect:min===max?renderValue(option.option_template,[min,0,0]):`${renderValue(option.option_template,[min,0,0])} ~ ${renderValue(option.option_template,[max,0,0])}`,badge:`${option.groups.length}개 구간`,level:`${option.groups[0].option_level_raw}~${option.groups[option.groups.length-1].option_level_raw}`,rolls:`총 ${vectors.length}개 후보`}; }
    function row(option) { const group=state.group==="ALL"?null:groupFor(option);const view=group?{effect:group.display_min===group.display_max?group.display_min:`${group.display_min} ~ ${group.display_max}`,badge:`구간 ${group.group_index}`,level:`OptionLevel ${group.option_level_raw}`,rolls:group.rolls.map(vector=>vector[0]).join(", ")}:summary(option);return `<button type="button" class="option-row" data-option-id="${option.option_id}" data-group="${group?group.group_index:"ALL"}"><span class="row-effect">${esc(view.effect)}</span><span class="row-name">${esc(option.option_name)} · ${esc(option.tags.join("/"))}</span><span><span class="group-pill">${esc(view.badge)}</span></span><span class="row-level">${esc(view.level)}</span><span class="rolls">${esc(view.rolls)}</span></button>`; }
    const listHeader='<div class="list-head"><span>옵션 효과 범위</span><span>옵션 / 태그</span><span>공통 구간</span><span>OptionLevel</span><span>후보 수치</span></div>';
    function render() { const data=ensureSelections();choices("equipmentChoices","equipment",data.equipment);choices("tagChoices","tag",data.tags,value=>value==="ALL"?"전체 태그":value);choices("groupChoices","group",data.groups,value=>value==="ALL"?"전체 구간":`구간 ${value}`);const options=filteredOptions();const groupLabel=state.group==="ALL"?"전체 공통 구간":`공통 구간 ${state.group}`;$("breadcrumb").innerHTML=`현재 위치　<b>${esc(state.equipment)} › ${esc(state.tag==="ALL"?"전체 태그":state.tag)} › ${esc(groupLabel)}</b>`;$("resultTitle").textContent=`${state.equipment} · ${groupLabel}`;$("resultCount").textContent=`${options.length}개 옵션`;$("optionGrid").innerHTML=options.length?`<div class="option-list">${listHeader}${options.map(row).join("")}</div>`:'<div class="empty">조건에 맞는 옵션이 없습니다.</div>'; }
    function detailItem(label,value,wide=false) { return `<div class="detail-item ${wide?"wide":""}"><span>${esc(label)}</span><b>${esc(value)}</b></div>`; }
    function groupSection(option,group) { return `<section class="group-section"><div class="group-head"><h3>공통 수치 구간 ${group.group_index}</h3><span>OptionLevel ${group.option_level_raw} · raw tier ${group.raw_tier_index} · offset ${group.offset}</span></div><div class="roll-grid">${group.rolls.map((vector,index)=>`<div class="roll" title="${index+1}번째 원시값 ${esc(vector.join("/"))}">${esc(renderValue(option.option_template,vector))}</div>`).join("")}</div></section>`; }
    function openDrawer(optionId,groupValue) { const option=currentEquipment().options.find(item=>item.option_id===Number(optionId));const groups=groupValue==="ALL"?option.groups:[option.groups.find(group=>String(group.group_index)===String(groupValue))];const allValues=groups.flatMap(group=>group.rolls.map(vector=>vector[0]));const min=Math.min(...allValues),max=Math.max(...allValues);$("drawerContent").innerHTML=`<div class="drawer-effect">${esc(renderValue(option.option_template,[min,0,0]))} ~ ${esc(renderValue(option.option_template,[max,0,0]))}</div><div class="drawer-name">${esc(option.option_name)} · ID ${option.option_id}</div><div class="detail-grid">${detailItem("적용 장비",state.equipment)}${detailItem("태그",option.tags.join("/"))}${detailItem("표시문",option.option_template,true)}${detailItem("사용 공통 구간",option.groups.map(group=>group.group_index).join(", "),true)}</div>${groups.map(group=>groupSection(option,group)).join("")}`;$("detailBackdrop").hidden=false;document.body.classList.add("drawer-open");requestAnimationFrame(()=>$("detailBackdrop").classList.add("open"));$("drawerClose").focus(); }
    function closeDrawer() { $("detailBackdrop").classList.remove("open");document.body.classList.remove("drawer-open");setTimeout(()=>$("detailBackdrop").hidden=true,200); }
    function setNightMode(enabled) { document.body.classList.toggle("night",enabled);$("themeToggle").setAttribute("aria-pressed",String(enabled));$("themeToggle").textContent=`나이트 모드: ${enabled?"ON":"OFF"}`; }
    $("query").addEventListener("input",event=>{state.query=event.target.value;render();});$("equipmentChoices").parentElement.parentElement.addEventListener("click",event=>{const choice=event.target.closest(".choice");if(!choice)return;state[choice.dataset.field]=choice.dataset.value;if(choice.dataset.field==="equipment"){state.tag="ALL";state.group="ALL";}state.query="";$("query").value="";render();});$("optionGrid").addEventListener("click",event=>{const item=event.target.closest("[data-option-id]");if(item)openDrawer(item.dataset.optionId,item.dataset.group);});$("drawerClose").addEventListener("click",closeDrawer);$("detailBackdrop").addEventListener("click",event=>{if(event.target===$("detailBackdrop"))closeDrawer();});document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!$("detailBackdrop").hidden)closeDrawer();});$("themeToggle").addEventListener("click",()=>setNightMode(!document.body.classList.contains("night")));render();
  </script>
</body>
</html>
'''


def build_preview_html(dataset: dict[str, Any]) -> str:
    """Render the validated dataset in the approved preview UI, without mock rows."""
    page = (ROOT / "preview.html").read_text(encoding="utf-8")
    notes_start = page.find("  <!--\n    Codex implementation notes")
    if notes_start >= 0:
        notes_end = page.index("  -->\n", notes_start) + len("  -->\n")
        page = page[:notes_start] + page[notes_end:]
    page = page.replace(
        '      <div class="header-actions">\n        <button class="outline-button" id="themeToggle"',
        '      <div class="header-actions">\n        <a class="outline-button" href="index.html">← 홈으로</a>\n        <button class="outline-button" id="themeToggle"',
        1,
    )
    page = page.replace("장비 개방 옵션 · 변환기별", "비규격 장비 옵션", 2)
    page = page.replace(
        "변환기 종류별로 확률 필드를 분리한 원본 DAT 직접 조인 결과입니다.",
        "장비군별 옵션과 OptionLevel 공통 수치 구간을 확인합니다. 공통 수치 구간은 게임의 공식 티어 명칭으로 확정하지 않았습니다. 목걸이 보완 옵션은 로컬 교차검증 근거를 표시합니다.",
        1,
    )
    panel_start = page.index('    <section class="selection-panel"')
    panel_end = page.index('    <section class="context-row"', panel_start)
    panel = '''    <section class="selection-panel" aria-label="비규격 옵션 탐색 조건">
      <section class="filter-group"><h2 class="filter-heading"><span class="step-number">1</span>장비 선택</h2><div class="chip-grid" id="equipmentFilters"></div></section>
      <section class="filter-group"><h2 class="filter-heading"><span class="step-number">2</span>태그 필터</h2><div class="chip-grid" id="tagFilters"></div></section>
      <section class="filter-group"><h2 class="filter-heading"><span class="step-number">3</span>공통 수치 구간</h2><div class="chip-grid" id="groupFilters"></div></section>
    </section>

'''
    page = page[:panel_start] + panel + page[panel_end:]
    page = page.replace(
        "  </style>",
        """    .selection-panel { grid-template-columns:1.4fr 1fr 1fr; }
    .tag-text { color:var(--muted); font-size:12px; }
    .assignment-note { display:inline-block; margin-left:5px; padding:1px 5px; border-radius:999px; background:var(--soft); color:var(--accent); font-size:10px; font-weight:800; }
    @media (max-width:1220px) { .selection-panel { grid-template-columns:1fr 1fr; } }
  </style>""",
        1,
    )
    data = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script = r'''<script>
    const dataset = __EMBEDDED_DATA__;
    const $ = id => document.getElementById(id);
    const esc = value => String(value ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const unique = values => [...new Set(values)];
    const numericSort = (a,b) => Number(a)-Number(b);
    const state = {equipment:"",tag:"ALL",group:"ALL",query:""};
    function current() { return dataset.equipment.find(item=>item.item_group_name===state.equipment); }
    function ensure() { const equipment=dataset.equipment.map(item=>item.item_group_name); if(!equipment.includes(state.equipment)) state.equipment=equipment.includes("헬멧")?"헬멧":equipment[0]; const options=current().options; const tags=["ALL",...unique(options.flatMap(option=>option.tags)).sort((a,b)=>a.localeCompare(b,"ko"))]; if(!tags.includes(state.tag))state.tag="ALL"; const groups=["ALL",...unique(options.flatMap(option=>option.groups.map(group=>String(group.group_index)))).sort(numericSort)]; if(!groups.includes(state.group))state.group="ALL"; return {equipment,tags,groups}; }
    function button(value,pressed,label=value) { return `<button class="chip" type="button" data-value="${esc(value)}" aria-pressed="${pressed}">${esc(label)}</button>`; }
    function renderFilters(values) { $("equipmentFilters").innerHTML=values.equipment.map(value=>button(value,state.equipment===value,`◇ ${value}`)).join(""); $("tagFilters").innerHTML=values.tags.map(value=>button(value,state.tag===value,value==="ALL"?"전체 태그":value)).join(""); $("groupFilters").innerHTML=values.groups.map(value=>button(value,state.group===value,value==="ALL"?"전체 구간":`구간 ${value}`)).join(""); }
    function renderValue(template,vector) { return String(template||"").replace(/\[([012])(?:\.(\d+))?([%％])?\]/g,(_,index,digits,suffix)=>{const n=Number(vector[Number(index)]),d=Number(digits||0);return `${d?(n/10**d).toFixed(d):n}${suffix||""}`;}); }
    function view(option) { const group=state.group==="ALL"?null:option.groups.find(item=>String(item.group_index)===state.group); if(group) return {effect:group.display_min===group.display_max?group.display_min:`${group.display_min} ~ ${group.display_max}`,group:`구간 ${group.group_index}`,level:`OptionLevel ${group.option_level_raw}`,rolls:group.rolls.map(vector=>vector[0]).join(", ")}; const vectors=option.groups.flatMap(item=>item.rolls), values=vectors.map(vector=>vector[0]), min=Math.min(...values),max=Math.max(...values); return {effect:min===max?renderValue(option.option_template,[min,0,0]):`${renderValue(option.option_template,[min,0,0])} ~ ${renderValue(option.option_template,[max,0,0])}`,group:`${option.groups.length}개 구간`,level:`${option.groups[0].option_level_raw}~${option.groups.at(-1).option_level_raw}`,rolls:`총 ${vectors.length}개 후보`}; }
    function filtered() { const q=state.query.trim().toLowerCase(); return current().options.filter(option=>(state.tag==="ALL"||option.tags.includes(state.tag))&&(state.group==="ALL"||option.groups.some(group=>String(group.group_index)===state.group))&&(!q||[option.option_id,option.option_name,option.option_display_name,option.option_template,option.tags.join(" ")].join(" ").toLowerCase().includes(q))).sort((a,b)=>a.tags[0].localeCompare(b.tags[0],"ko")||a.tags.join("/").localeCompare(b.tags.join("/"),"ko")||a.option_order-b.option_order); }
    function results(values) { const options=filtered(), groupLabel=state.group==="ALL"?"전체 공통 수치 구간":`공통 수치 구간 ${state.group}`; $("resultTitle").textContent=`${state.equipment} · ${groupLabel}`; $("rowCount").textContent=`${options.length.toLocaleString()}개`; $("uniqueOptionCount").textContent="옵션"; $("activeSummary").textContent=`${state.equipment} · ${state.tag==="ALL"?"전체 태그":state.tag} · ${groupLabel}`; $("emptyState").classList.toggle("visible",!options.length); $("resultSections").innerHTML=options.length?`<section class="line-section"><header class="line-section-header"><h3 class="line-section-title">태그순 옵션 목록</h3><span class="line-row-count">${options.length}개 옵션</span></header><div class="table-wrap"><table><thead><tr><th class="col-effect">옵션 효과 범위</th><th class="col-name">옵션 / 태그</th><th class="col-tier">공통 구간</th><th class="col-probability">OptionLevel</th><th class="col-candidate">후보 수치</th></tr></thead><tbody>${options.map(option=>{const item=view(option),supplemental=option.assignment_basis==="supplemental_local_cross_reference";return `<tr><td><div class="option-effect"><span class="option-glyph">◇</span><span>${esc(item.effect)}</span></div></td><td>${esc(option.option_display_name)} <span class="tag-text">· ${esc(option.tags.join("/"))}</span>${supplemental?'<span class="assignment-note">로컬 교차검증 보완</span>':''}</td><td><span class="tier-badge">${esc(item.group)}</span></td><td>${esc(item.level)}</td><td class="candidate-value">${esc(item.rolls)}</td></tr>`;}).join("")}</tbody></table></div></section>`:""; }
    function breadcrumb(values) { const items=[["1","장비 선택",state.equipment],["2","태그",state.tag==="ALL"?"전체 태그":state.tag],["3","공통 수치 구간",state.group==="ALL"?"전체 구간":`구간 ${state.group}`]]; $("breadcrumbPath").innerHTML=items.map((item,index)=>`${index?'<span class="breadcrumb-separator">›</span>':''}<span class="breadcrumb-step"><span class="breadcrumb-step-number">${item[0]}</span><span class="breadcrumb-step-source">${item[1]}</span><span class="breadcrumb-step-value">${esc(item[2])}</span></span>`).join(""); }
    function render() { const values=ensure(); renderFilters(values); breadcrumb(values); results(values); $("clearSearch").classList.toggle("visible",Boolean(state.query)); }
    function reset() { state.equipment="";state.tag="ALL";state.group="ALL";state.query="";$("searchInput").value="";render(); }
    $("equipmentFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item){state.equipment=item.dataset.value;state.tag="ALL";state.group="ALL";render();}});
    $("tagFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item){state.tag=item.dataset.value;render();}});
    $("groupFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item){state.group=item.dataset.value;render();}});
    $("searchInput").addEventListener("input",event=>{state.query=event.target.value;render();}); $("clearSearch").addEventListener("click",()=>{state.query="";$("searchInput").value="";$("searchInput").focus();render();}); $("resetButton").addEventListener("click",reset);
    function setTheme(theme) { document.documentElement.dataset.theme=theme; const dark=theme==="dark"; $("themeToggleLabel").textContent=dark?"라이트 모드로 전환":"다크 모드로 전환"; $("themeToggle").querySelector("span").textContent=dark?"☾":"☀"; try {localStorage.setItem("redstone-ui-theme",theme);} catch(_) {} }
    $("themeToggle").addEventListener("click",()=>setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark")); window.addEventListener("storage",event=>{if(event.key==="redstone-ui-theme"&&(event.newValue==="dark"||event.newValue==="light"))setTheme(event.newValue);}); try {const theme=localStorage.getItem("redstone-ui-theme");if(theme==="dark"||theme==="light")setTheme(theme);} catch(_) {} render();
  </script>'''.replace("__EMBEDDED_DATA__", data)
    script_start = page.index("<script>")
    script_end = page.index("</script>", script_start) + len("</script>")
    return page[:script_start] + script + page[script_end:]


def render_html(dataset: dict[str, Any] | None = None) -> str:
    value = dataset or build_render_dataset()
    return build_preview_html(value)


def main() -> None:
    dataset = build_render_dataset()
    OUTPUT.write_text(render_html(dataset), encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)} from {SOURCE.relative_to(ROOT)} "
        f"({len(dataset['equipment'])} equipment groups)"
    )


if __name__ == "__main__":
    main()
