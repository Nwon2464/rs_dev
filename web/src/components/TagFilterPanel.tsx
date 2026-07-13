import { useId, useState } from "react";
import { formatSelectedTagCount, uiText, type Language } from "../i18n";
import { tagText, toggleSelectedTag } from "../domain/openOptions/tags";
import type { OptionTagData } from "../domain/openOptions/types";

type Props = {
  availableTags: string[];
  selectedTags: string[];
  onChange: (tags: string[]) => void;
  language: Language;
  optionTags: OptionTagData;
};

export function TagFilterPanel({ availableTags, selectedTags, onChange, language, optionTags }: Props) {
  const [expanded, setExpanded] = useState(false);
  const groupsId = useId();
  const groups = Object.entries(optionTags.groups).map(([groupId, labels]) => ({
    groupId,
    label: labels[language],
    tags: availableTags.filter((tag) => optionTags.tags[tag]?.group === groupId),
  })).filter((group) => group.tags.length);
  return <section className={`tag-filter-panel ${expanded ? "expanded" : ""}`}>
    <div className="tag-filter-panel-head">
      <button type="button" className="tag-filter-toggle" aria-expanded={expanded} aria-controls={groupsId} onClick={() => setExpanded((value) => !value)}>
        <span>{uiText(language, "filter.tags")}</span>
        <b>{formatSelectedTagCount(language, selectedTags.length)}</b>
        {expanded ? (
          <span className="tag-filter-chevron" aria-hidden="true">▲</span>
        ) : (
          <span className="tag-filter-chevron" aria-hidden="true">▼</span>
        )}
      </button>
      <button type="button" className="tag-filter-reset" onClick={() => onChange([])} disabled={!selectedTags.length}>{uiText(language, "common.reset")}</button>
    </div>
    {expanded && <div className="tag-filter-groups" id={groupsId}>{groups.map((group) => <div className="tag-filter-group" key={group.groupId}>
      <small>{group.label}</small>
      <div>{group.tags.map((tag) => <button className={`chip ${selectedTags.includes(tag) ? "active" : ""}`} aria-pressed={selectedTags.includes(tag)} key={tag} onClick={() => onChange(toggleSelectedTag(selectedTags, tag))}>{tagText(language, tag, optionTags)}</button>)}</div>
    </div>)}</div>}
  </section>;
}

export function SelectedTagChips({ selectedTags, onChange, language, optionTags }: Omit<Props, "availableTags">) {
  return selectedTags.length ? <div className="selected-tag-chips" aria-label={uiText(language, "filter.tags")}>{selectedTags.map((tag) => <button type="button" key={tag} onClick={() => onChange(selectedTags.filter((value) => value !== tag))}>{tagText(language, tag, optionTags)} <span aria-hidden="true">×</span></button>)}</div> : null;
}
