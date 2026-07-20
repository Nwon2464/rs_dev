import { useMemo, useState, type ReactNode } from "react";
import type { InstandardCatalog } from "../../data/instandardOptions";
import {
  localizedEquipmentName,
  localizedInstandardOptionTitle,
  tierCandidateValues,
} from "../../domain/openOptions/instandardRendering";
import { matchesSelectedTags, tagSearchText, tagText } from "../../domain/openOptions/tags";
import type {
  EquipmentGroups,
  OptionLocales,
  OptionTagData,
} from "../../domain/openOptions/types";
import {
  formatAppliedEquipmentCount,
  formatPossibleValueCount,
  formatTierOptionsTitle,
  formatTierValuesTitle,
  uiText,
  type Language,
} from "../../i18n";
import { Icon } from "../Icon";
import { PageHeader } from "../PageHeader";
import {
  Chip,
  Empty,
  FilterGroup,
  ResultsHead,
  TagFilterChips,
} from "../common/ExplorerPrimitives";
import { OptionTitle } from "../common/OptionTitle";
import { equipmentIconId, featureIconId } from "../iconMap";
import { InstandardModeTabs } from "./InstandardModeTabs";

export function InstandardTierViewer({
  source,
  language,
  optionLocales,
  equipmentGroups,
  optionTags,
  controls,
}: {
  source: InstandardCatalog;
  language: Language;
  optionLocales: OptionLocales;
  equipmentGroups: EquipmentGroups;
  optionTags: OptionTagData;
  controls: ReactNode;
}) {
  const [selectedTier, setSelectedTier] = useState<number | null>(null);
  const [selectedTierTags, setSelectedTierTags] = useState<string[]>([]);
  const [tierQuery, setTierQuery] = useState("");
  const [expandedOptionIds, setExpandedOptionIds] = useState<Set<number>>(
    () => new Set(),
  );
  const tierNumbers = useMemo(
    () =>
      [
        ...new Set(
          source.options.flatMap((option) =>
            option.tiers
              .filter((tier) => tier.enabled)
              .map((tier) => tier.tier),
          ),
        ),
      ].sort((a, b) => a - b),
    [source.options],
  );
  const tierOptions = useMemo(
    () =>
      selectedTier === null
        ? []
        : source.options.filter((option) =>
            option.tiers.some(
              (tier) => tier.enabled && tier.tier === selectedTier,
            ),
          ),
    [selectedTier, source.options],
  );
  const tierTags = useMemo(
    () =>
      [...new Set(tierOptions.flatMap((option) => option.canonical_tags))].sort(
        (a, b) => a.localeCompare(b, "ko"),
      ),
    [tierOptions],
  );
  const optionResults = useMemo(() => {
    if (selectedTier === null) return [];
    const normalized = tierQuery.trim().toLocaleLowerCase();
    return tierOptions
      .filter((option) =>
        matchesSelectedTags(
          option.canonical_tags,
          selectedTierTags,
          optionTags,
        ),
      )
      .map((option) => ({
        option,
        equipment: source.equipment.filter((item) =>
          item.option_ids.includes(option.option_id),
        ),
      }))
      .filter(
        ({ option, equipment }) =>
          !normalized ||
          [
            optionLocales.ko[String(option.option_id)],
            optionLocales.ja[String(option.option_id)],
            localizedInstandardOptionTitle(option, "ko", optionLocales, source),
            localizedInstandardOptionTitle(option, "ja", optionLocales, source),
            tagSearchText(option.canonical_tags, optionTags),
          ]
            .join(" ")
            .toLocaleLowerCase()
            .includes(normalized) ||
          equipment.some((item) =>
            [
              item.item_group_name,
              localizedEquipmentName(
                item.item_group_id,
                item.item_group_name,
                language,
                equipmentGroups,
              ),
            ]
              .join(" ")
              .toLocaleLowerCase()
              .includes(normalized),
          ),
      );
  }, [
    equipmentGroups,
    language,
    optionLocales,
    optionTags,
    selectedTier,
    selectedTierTags,
    source,
    tierOptions,
    tierQuery,
  ]);

  function changeTier(tierNumber: number) {
    setSelectedTier(tierNumber);
    setSelectedTierTags([]);
    setExpandedOptionIds(new Set());
  }

  function toggleOption(optionId: number) {
    setExpandedOptionIds((current) => {
      const next = new Set(current);
      if (next.has(optionId)) next.delete(optionId);
      else next.add(optionId);
      return next;
    });
  }

  return (
    <>
      <PageHeader
        language={language}
        title={uiText(language, "header.instandard.title")}
        description={uiText(language, "header.tier.description")}
        controls={controls}
      />
      <main className="instandard-mode-page instandard-tier-mode tier-mode-page">
        <InstandardModeTabs mode="tier" language={language} />
        <section
          className={`selection-panel tier-filter-panel ${
            selectedTier === null ? "tier-filter-awaiting" : ""
          }`}
          aria-label={uiText(language, "aria.tierFilters")}
        >
          <FilterGroup
            className="tier-number-filter"
            number="1"
            title={uiText(language, "filter.tier")}
          >
            {tierNumbers.map((tierNumber) => (
              <Chip
                key={tierNumber}
                active={selectedTier === tierNumber}
                onClick={() => changeTier(tierNumber)}
              >
                Tier {tierNumber}
              </Chip>
            ))}
          </FilterGroup>
          {selectedTier !== null && (
            <>
              <FilterGroup
                className="tier-tag-filter"
                number="2"
                title={uiText(language, "filter.optionCategory")}
              >
                <TagFilterChips
                  availableTags={tierTags}
                  selectedTags={selectedTierTags}
                  onChange={setSelectedTierTags}
                  language={language}
                  optionTags={optionTags}
                  allLabelKey="common.allCategories"
                />
              </FilterGroup>
              <FilterGroup
                className="tier-search-filter"
                number="3"
                title={uiText(language, "common.search")}
              >
                <div className="panel-search-control">
                  <input
                    value={tierQuery}
                    onChange={(event) => setTierQuery(event.target.value)}
                    placeholder={uiText(
                      language,
                      "filter.equipmentOrOptionSearchPlaceholder",
                    )}
                    aria-label={uiText(
                      language,
                      "filter.equipmentOrOptionSearchPlaceholder",
                    )}
                  />
                  {tierQuery && (
                    <button type="button" onClick={() => setTierQuery("")}>
                      {uiText(language, "common.reset")}
                    </button>
                  )}
                </div>
              </FilterGroup>
            </>
          )}
        </section>
        {selectedTier === null ? (
          <section className="tier-mode-empty">
            <Icon
              className="app-icon"
              id={featureIconId["티어별 옵션"]}
              size={34}
            />
            <h2>{uiText(language, "tier.selectPrompt")}</h2>
            <p>{uiText(language, "tier.selectDescription")}</p>
          </section>
        ) : (
          <section className="tier-results">
            <ResultsHead
              language={language}
              title={formatTierOptionsTitle(language, selectedTier)}
              description={uiText(language, "tier.resultsDescription")}
              count={optionResults.length}
            />
            {optionResults.length ? (
              <div className="tier-option-accordion-list">
                {optionResults.map(({ option, equipment }) => {
                  const expanded = expandedOptionIds.has(option.option_id);
                  const contentId = `tier-option-${option.option_id}`;
                  const tierData = option.tiers.find(
                    (tier) => tier.enabled && tier.tier === selectedTier,
                  )!;
                  const values = tierCandidateValues(
                    option,
                    tierData,
                    language,
                    optionLocales,
                    source,
                  );
                  const optionTitle = localizedInstandardOptionTitle(
                    option,
                    language,
                    optionLocales,
                    source,
                  );
                  return (
                    <article
                      className={`tier-option-accordion ${
                        expanded ? "expanded" : ""
                      }`}
                      key={option.option_id}
                    >
                      <button
                        className="tier-option-toggle"
                        type="button"
                        aria-expanded={expanded}
                        aria-controls={contentId}
                        onClick={() => toggleOption(option.option_id)}
                      >
                        <OptionTitle title={optionTitle} />
                        <div className="option-tag-badges">
                          {option.canonical_tags.map((optionTag) => (
                            <span key={optionTag}>
                              {tagText(language, optionTag, optionTags)}
                            </span>
                          ))}
                        </div>
                        <span>
                          {formatAppliedEquipmentCount(
                            language,
                            equipment.length,
                          )}
                        </span>
                        <span>
                          {formatPossibleValueCount(language, values.length)}
                        </span>
                        <Icon
                          className="app-icon tier-chevron"
                          id={
                            expanded ? "ui-chevron-down" : "ui-chevron-right"
                          }
                          size={18}
                        />
                      </button>
                      {expanded && (
                        <section
                          className="tier-option-content"
                          id={contentId}
                        >
                          <div className="tier-option-values">
                            <h3>
                              {formatTierValuesTitle(language, selectedTier)}
                            </h3>
                            <div className="value-list">
                              {values.map((value) => (
                                <span key={value}>{value}</span>
                              ))}
                            </div>
                          </div>
                          <div className="tier-option-equipment">
                            <h3>{uiText(language, "tier.appliedEquipment")}</h3>
                            <div className="tier-applied-equipment-grid">
                              {equipment.map((item) => (
                                <div
                                  className="tier-applied-equipment"
                                  key={item.item_group_id}
                                >
                                  <Icon
                                    className="app-icon"
                                    id={
                                      equipmentIconId[item.item_group_name] ??
                                      "feature-instandard-option"
                                    }
                                    size={20}
                                  />
                                  <span>
                                    {localizedEquipmentName(
                                      item.item_group_id,
                                      item.item_group_name,
                                      language,
                                      equipmentGroups,
                                    )}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </section>
                      )}
                    </article>
                  );
                })}
              </div>
            ) : (
              <Empty language={language} onReset={() => { setSelectedTierTags([]); setTierQuery(""); }} />
            )}
          </section>
        )}
      </main>
    </>
  );
}
