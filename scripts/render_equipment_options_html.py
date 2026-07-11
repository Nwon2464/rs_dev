#!/usr/bin/env python3
"""Render equipment open-option rows grouped by converter type as HTML."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.models import OpenOptionOutputRow

from html_rendering import (
    json_for_script,
    read_template,
    remove_optional_block,
    replace_script,
    substitute_once,
)


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


def render_html(rows: list[dict[str, str]]) -> str:
    """Apply the approved preview shell while injecting only collected DAT rows."""
    preview = read_template(ROOT / "preview.html")
    preview = remove_optional_block(
        preview, "  <!--\n    Codex implementation notes", "  -->\n"
    )
    preview = substitute_once(
        preview,
        '      <div class="header-actions">\n        <button class="outline-button" id="themeToggle"',
        '      <div class="header-actions">\n        <a class="outline-button" href="index.html">← 홈으로</a>\n        <button class="outline-button" id="themeToggle"',
        label="open viewer home link",
    )
    tag_filter = '''
      <section class="filter-group tag-filter-group">
        <h2 class="filter-heading"><span class="step-number">5</span>태그 필터</h2>
        <div class="chip-grid" id="tagFilters"></div>
      </section>'''
    preview = substitute_once(
        preview,
        "    </section>\n\n    <section class=\"context-row\"",
        f"{tag_filter}\n    </section>\n\n    <section class=\"context-row\"",
        label="open viewer tag filter",
    )
    preview = substitute_once(
        preview,
        "  </style>",
        """    .tag-filter-group { grid-column:1 / -1; border-top:1px solid var(--line); border-left:0 !important; }
    @media (max-width:1220px) { .tag-filter-group { border-top:1px solid var(--line) !important; } }
  </style>""",
        label="open viewer tag styles",
    )
    data = json_for_script(rows)
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
  </script>'''
    script = substitute_once(
        script, "__EMBEDDED_DATA__", data, label="open viewer embedded data"
    )
    return replace_script(preview, script)


def main() -> None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"no rows found in {CSV_PATH}")
    for row in rows:
        OpenOptionOutputRow.model_validate(row)
    add_tags(rows)

    html = render_html(rows)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {len(rows)} rows to {HTML_PATH}")


if __name__ == "__main__":
    main()
