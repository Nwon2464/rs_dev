import type { ReactNode } from "react";
import {
  formatResultCount,
  uiText,
  type Language,
  type UiMessageKey,
} from "../../i18n";
import { tagText, toggleSelectedTag } from "../../domain/openOptions/tags";
import type { OptionTagData } from "../../domain/openOptions/types";

export function FilterGroup({
  number,
  title,
  children,
  className = "",
}: {
  number: string;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`filter-group ${className}`}>
      <h2>
        <span>{number}</span>
        {title}
      </h2>
      <div className="chip-grid">{children}</div>
    </section>
  );
}

export function Chip({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={`chip ${active ? "active" : ""}`}
      aria-pressed={active}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function selectedTagLabel(
  selectedTags: string[],
  language: Language,
  optionTags: OptionTagData,
  allLabelKey: UiMessageKey,
): string {
  return selectedTags.length
    ? selectedTags.map((tag) => tagText(language, tag, optionTags)).join(" · ")
    : uiText(language, allLabelKey);
}

export function TagFilterChips({
  availableTags,
  selectedTags,
  onChange,
  language,
  optionTags,
  allLabelKey,
}: {
  availableTags: string[];
  selectedTags: string[];
  onChange: (tags: string[]) => void;
  language: Language;
  optionTags: OptionTagData;
  allLabelKey: UiMessageKey;
}) {
  const groups = Object.entries(optionTags.groups)
    .map(([groupId, labels]) => ({
      groupId,
      label: labels[language],
      tags: availableTags.filter(
        (tag) => optionTags.tags[tag]?.group === groupId,
      ),
    }))
    .filter((group) => group.tags.length);
  return (
    <>
      <Chip active={!selectedTags.length} onClick={() => onChange([])}>
        {uiText(language, allLabelKey)}
      </Chip>
      {groups.map((group) => (
        <div className="tag-filter-group" key={group.groupId}>
          <small>{group.label}</small>
          <div>
            {group.tags.map((tag) => (
              <Chip
                key={tag}
                active={selectedTags.includes(tag)}
                onClick={() =>
                  onChange(toggleSelectedTag(selectedTags, tag))
                }
              >
                {tagText(language, tag, optionTags)}
              </Chip>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

export function Context({
  language,
  breadcrumb,
  query,
  onQuery,
  placeholder,
  hideSearch = false,
}: {
  language: Language;
  breadcrumb: string[];
  query: string;
  onQuery: (value: string) => void;
  placeholder: string;
  hideSearch?: boolean;
}) {
  return (
    <section
      className={`context-row ${hideSearch ? "breadcrumb-only" : ""}`}
    >
      <div className="breadcrumb" aria-label={uiText(language, "common.currentLocation")}>
        <span className="breadcrumb-label">{uiText(language, "common.currentLocation")}</span>
        <span className="breadcrumb-trail">
          {breadcrumb.map((part, index) => (
            <span className="breadcrumb-item" key={`${part}-${index}`}>
              {index > 0 && <span className="breadcrumb-separator" aria-hidden="true">›</span>}
              <b className={index === breadcrumb.length - 1 ? "breadcrumb-current" : undefined}>{part}</b>
            </span>
          ))}
        </span>
      </div>
      {!hideSearch && (
        <label className="search">
          <span className="visually-hidden">
            {uiText(language, "filter.optionSearch")}
          </span>
          <input
            value={query}
            onChange={(event) => onQuery(event.target.value)}
            placeholder={placeholder}
          />
        </label>
      )}
    </section>
  );
}

export function ResultsHead({
  language,
  title,
  description,
  count,
}: {
  language: Language;
  title: string;
  description: string;
  count: number;
}) {
  return (
    <section className="results-head">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <b>{formatResultCount(language, count)}</b>
    </section>
  );
}

export function SectionHead({ title, count }: { title: string; count: string }) {
  return (
    <div className="option-section-head">
      <h3>{title}</h3>
      <span>{count}</span>
    </div>
  );
}

export function Empty({
  language,
  onReset,
}: {
  language: Language;
  onReset?: () => void;
}) {
  return (
    <div className="empty">
      <p>{uiText(language, "common.noResults")}</p>
      {onReset && <button type="button" onClick={onReset}>{uiText(language, "common.resetFilters")}</button>}
    </div>
  );
}
