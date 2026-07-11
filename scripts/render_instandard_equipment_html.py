#!/usr/bin/env python3
"""Render non-standard equipment from the validated pre-render CSV."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.models import InstandardRenderRow

from html_rendering import (
    json_for_script,
    read_template,
    remove_optional_block,
    replace_script,
    substitute_first,
    substitute_many,
    substitute_once,
)


SOURCE = ROOT / "data" / "processed" / "instandard_equipment_render_rows.csv"
METADATA = ROOT / "data" / "processed" / "instandard_equipment.json"
OUTPUT = ROOT / "instandard_equipment_viewer.html"


def build_render_dataset() -> dict[str, Any]:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"no rows found in {SOURCE}")
    for row in rows:
        InstandardRenderRow.model_validate(row)

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



def build_preview_html(dataset: dict[str, Any]) -> str:
    """Render the validated dataset in the approved preview UI, without mock rows."""
    page = read_template(ROOT / "preview.html")
    page = remove_optional_block(
        page, "  <!--\n    Codex implementation notes", "  -->\n"
    )
    page = substitute_once(
        page,
        '      <div class="header-actions">\n        <button class="outline-button" id="themeToggle"',
        '      <div class="header-actions">\n        <a class="outline-button" href="index.html">← 홈으로</a>\n        <button class="outline-button" id="themeToggle"',
        label="non-standard viewer home link",
    )
    page = substitute_many(
        page,
        "장비 개방 옵션 · 변환기별",
        "비규격 장비 옵션",
        count=2,
        label="non-standard viewer title",
    )
    page = substitute_once(
        page,
        "변환기 종류별로 확률 필드를 분리한 원본 DAT 직접 조인 결과입니다.",
        "선택한 장비에 붙을 수 있는 옵션의 수치 범위를 확인하고, 클릭해 가능한 값을 살펴봅니다.",
        label="non-standard viewer subtitle",
    )
    page = substitute_first(
        page,
        "전체 개방 줄 옵션",
        "비규격 장비 옵션",
        label="non-standard viewer result title",
    )
    page = substitute_once(
        page,
        "선택한 조건에서 등장할 수 있는 옵션과 변환 확률을 확인할 수 있습니다.",
        "수치 범위를 클릭하면 실제 가능한 값을 모두 확인할 수 있습니다.",
        label="non-standard viewer result description",
    )
    panel_start = page.index('    <section class="selection-panel"')
    panel_end = page.index('    <section class="context-row"', panel_start)
    panel = '''    <section class="selection-panel" aria-label="비규격 옵션 탐색 조건">
      <section class="filter-group"><h2 class="filter-heading"><span class="step-number">1</span>장비 선택</h2><div class="chip-grid" id="equipmentFilters"></div></section>
      <section class="filter-group"><h2 class="filter-heading"><span class="step-number">2</span>옵션 분류</h2><div class="chip-grid" id="tagFilters"></div></section>
    </section>

'''
    page = page[:panel_start] + panel + page[panel_end:]
    page = substitute_once(
        page,
        "  </style>",
        """    .selection-panel { grid-template-columns:1.4fr 1fr; }
    .tag-text { color:var(--muted); font-size:12px; }
    .range-cell { padding:8px 18px; }
    .range-button { display:flex; width:100%; min-height:44px; align-items:center; justify-content:space-between; gap:12px; padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:var(--panel-2); color:var(--text); text-align:left; cursor:pointer; }
    .range-button:hover { border-color:var(--accent-border); background:var(--accent-soft); }
    .range-value { font-size:13px; font-weight:760; }
    .range-hint { color:var(--muted); font-size:11px; white-space:nowrap; }
    .value-list { display:flex; flex-wrap:wrap; gap:6px; }
    .value-chip { display:inline-flex; align-items:center; min-height:28px; padding:3px 8px; border:1px solid var(--line); border-radius:7px; background:var(--panel-2); color:var(--text-soft); font-size:12px; font-variant-numeric:tabular-nums; }
    .col-name { width:28%; }
    .col-range { width:72%; text-align:left; }
    .candidate-dialog { width:min(760px,calc(100vw - 28px)); max-height:min(680px,calc(100vh - 28px)); padding:0; border:1px solid var(--line-strong); border-radius:var(--radius-lg); background:var(--panel); color:var(--text); box-shadow:var(--shadow); }
    .candidate-dialog::backdrop { background:rgba(0,0,0,.58); }
    .candidate-dialog-inner { padding:22px; }
    .candidate-dialog-head { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; margin-bottom:18px; }
    .candidate-dialog-title { font-size:19px; font-weight:820; }
    .candidate-dialog-range { margin-top:4px; color:var(--muted); font-size:13px; }
    .dialog-close { width:34px; height:34px; border:1px solid var(--line); border-radius:8px; background:var(--panel-2); color:var(--text-soft); cursor:pointer; font-size:20px; line-height:1; }
    .dialog-close:hover { border-color:var(--accent-border); color:var(--accent-strong); }
    .candidate-dialog-label { margin-bottom:9px; color:var(--muted); font-size:12px; font-weight:700; }
    @media (max-width:900px) { .selection-panel { grid-template-columns:1fr; } .filter-group + .filter-group { border-top:1px solid var(--line); border-left:0; } }
  </style>""",
        label="non-standard viewer styles",
    )
    dialog = '''  <dialog class="candidate-dialog" id="candidateDialog" aria-labelledby="candidateDialogTitle">
    <div class="candidate-dialog-inner">
      <div class="candidate-dialog-head"><div><h2 class="candidate-dialog-title" id="candidateDialogTitle"></h2><p class="candidate-dialog-range" id="candidateDialogRange"></p></div><button class="dialog-close" id="candidateDialogClose" type="button" aria-label="닫기">×</button></div>
      <p class="candidate-dialog-label" id="candidateDialogCount"></p>
      <div class="value-list" id="candidateDialogValues"></div>
    </div>
  </dialog>

'''
    page = substitute_once(
        page,
        "  </main>\n\n  <script>",
        "  </main>\n\n" + dialog + "  <script>",
        label="non-standard viewer candidate dialog",
    )
    data = json_for_script(dataset)
    script = r'''<script>
    const dataset = __EMBEDDED_DATA__;
    const $ = id => document.getElementById(id);
    const esc = value => String(value ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const unique = values => [...new Set(values)];
    const state = {equipment:"",tag:"ALL",query:""};
    function current() { return dataset.equipment.find(item=>item.item_group_name===state.equipment); }
    function ensure() { const equipment=dataset.equipment.map(item=>item.item_group_name); if(!equipment.includes(state.equipment)) state.equipment=equipment.includes("헬멧")?"헬멧":equipment[0]; const options=current().options; const tags=["ALL",...unique(options.flatMap(option=>option.tags)).sort((a,b)=>a.localeCompare(b,"ko"))]; if(!tags.includes(state.tag))state.tag="ALL"; return {equipment,tags}; }
    function button(value,pressed,label=value) { return `<button class="chip" type="button" data-value="${esc(value)}" aria-pressed="${pressed}">${esc(label)}</button>`; }
    function renderFilters(values) { $("equipmentFilters").innerHTML=values.equipment.map(value=>button(value,state.equipment===value,`◇ ${value}`)).join(""); $("tagFilters").innerHTML=values.tags.map(value=>button(value,state.tag===value,value==="ALL"?"전체 분류":value)).join(""); }
    function renderValue(template,vector) { return String(template||"").replace(/\[([012])(?:\.(\d+))?([%％])?\]/g,(_,index,digits,suffix)=>{const n=Number(vector[Number(index)]),d=Number(digits||0);return `${d?(n/10**d).toFixed(d):n}${suffix||""}`;}); }
    function candidateValues(option) { return unique(option.groups.flatMap(group=>group.rolls.map(vector=>renderValue(option.option_template,vector)))); }
    function rangeLabel(option) { const vectors=option.groups.flatMap(group=>group.rolls); const minVector=vectors.reduce((min,vector)=>vector[0]<min[0]?vector:min,vectors[0]); const maxVector=vectors.reduce((max,vector)=>vector[0]>max[0]?vector:max,vectors[0]); const min=renderValue(option.option_template,minVector),max=renderValue(option.option_template,maxVector); return min===max?min:`${min} ~ ${max}`; }
    function filtered() { const q=state.query.trim().toLowerCase(); return current().options.filter(option=>(state.tag==="ALL"||option.tags.includes(state.tag))&&(!q||[option.option_name,option.option_display_name,option.option_template,option.tags.join(" ")].join(" ").toLowerCase().includes(q))).sort((a,b)=>a.tags[0].localeCompare(b.tags[0],"ko")||a.tags.join("/").localeCompare(b.tags.join("/"),"ko")||a.option_order-b.option_order); }
    function results() { const options=filtered(); $("resultTitle").textContent=`${state.equipment} 비규격 옵션`; $("rowCount").textContent=`${options.length.toLocaleString()}개`; $("uniqueOptionCount").textContent="수치 범위 클릭하여 열람"; $("activeSummary").textContent=`${state.equipment} · ${state.tag==="ALL"?"전체 분류":state.tag}`; $("emptyState").classList.toggle("visible",!options.length); $("resultSections").innerHTML=options.length?`<section class="line-section"><header class="line-section-header"><h3 class="line-section-title">등장 가능 옵션</h3><span class="line-row-count">${options.length}개 옵션</span></header><div class="table-wrap"><table><thead><tr><th class="col-name">옵션</th><th class="col-range">수치 범위</th></tr></thead><tbody>${options.map(option=>{const values=candidateValues(option);return `<tr><td><div class="option-effect"><span class="option-glyph">◇</span><span>${esc(option.option_display_name)}</span></div><span class="tag-text">${esc(option.tags.join(" / "))}</span></td><td class="range-cell"><button class="range-button" type="button" data-option-id="${option.option_id}" aria-label="${esc(option.option_display_name)}의 가능한 수치 보기"><span class="range-value">${esc(rangeLabel(option))}</span><span class="range-hint">가능 수치 ${values.length}개 보기</span></button></td></tr>`;}).join("")}</tbody></table></div></section>`:""; }
    function breadcrumb() { const items=[["1","장비 선택",state.equipment],["2","옵션 분류",state.tag==="ALL"?"전체 분류":state.tag]]; $("breadcrumbPath").innerHTML=items.map((item,index)=>`${index?'<span class="breadcrumb-separator">›</span>':''}<span class="breadcrumb-step"><span class="breadcrumb-step-number">${item[0]}</span><span class="breadcrumb-step-source">${item[1]}</span><span class="breadcrumb-step-value">${esc(item[2])}</span></span>`).join(""); }
    function render() { const values=ensure(); renderFilters(values); breadcrumb(); results(); $("clearSearch").classList.toggle("visible",Boolean(state.query)); }
    function reset() { state.equipment="";state.tag="ALL";state.query="";$("searchInput").value="";render(); }
    $("equipmentFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item){state.equipment=item.dataset.value;state.tag="ALL";render();}});
    $("tagFilters").addEventListener("click",event=>{const item=event.target.closest("[data-value]");if(item){state.tag=item.dataset.value;render();}});
    function openCandidates(optionId) { const option=current().options.find(item=>item.option_id===Number(optionId)); if(!option)return; const values=candidateValues(option); $("candidateDialogTitle").textContent=option.option_display_name; $("candidateDialogRange").textContent=`수치 범위: ${rangeLabel(option)}`; $("candidateDialogCount").textContent=`가능 수치 ${values.length}개`; $("candidateDialogValues").innerHTML=values.map(value=>`<span class="value-chip">${esc(value)}</span>`).join(""); $("candidateDialog").showModal(); }
    $("resultSections").addEventListener("click",event=>{const button=event.target.closest("[data-option-id]");if(button)openCandidates(button.dataset.optionId);});
    $("candidateDialogClose").addEventListener("click",()=>$("candidateDialog").close()); $("candidateDialog").addEventListener("click",event=>{if(event.target===$("candidateDialog"))$("candidateDialog").close();});
    $("searchInput").addEventListener("input",event=>{state.query=event.target.value;render();}); $("clearSearch").addEventListener("click",()=>{state.query="";$("searchInput").value="";$("searchInput").focus();render();}); $("resetButton").addEventListener("click",reset);
    function setTheme(theme) { document.documentElement.dataset.theme=theme; const dark=theme==="dark"; $("themeToggleLabel").textContent=dark?"라이트 모드로 전환":"다크 모드로 전환"; $("themeToggle").querySelector("span").textContent=dark?"☾":"☀"; try {localStorage.setItem("redstone-ui-theme",theme);} catch(_) {} }
    $("themeToggle").addEventListener("click",()=>setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark")); window.addEventListener("storage",event=>{if(event.key==="redstone-ui-theme"&&(event.newValue==="dark"||event.newValue==="light"))setTheme(event.newValue);}); try {const theme=localStorage.getItem("redstone-ui-theme");if(theme==="dark"||theme==="light")setTheme(theme);} catch(_) {} render();
  </script>'''
    script = substitute_once(
        script, "__EMBEDDED_DATA__", data, label="non-standard viewer embedded data"
    )
    return replace_script(page, script)


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
