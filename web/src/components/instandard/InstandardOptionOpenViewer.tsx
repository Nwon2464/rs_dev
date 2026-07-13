import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type {
  InstandardCatalog,
  InstandardOpenOptionRow,
  InstandardOption,
} from "../../data/instandardOptions";
import {
  candidateValues,
  formatProbability,
  localizedConverterLabel,
  localizedEquipmentName,
  localizedInstandardOpenOptionRow,
  localizedInstandardOptionTitle,
  rangeLabel,
  tierCandidateValues,
} from "../../domain/openOptions/instandardRendering";
import {
  matchesSelectedTags,
  tagSearchText,
  tagText,
} from "../../domain/openOptions/tags";
import type {
  EquipmentGroups,
  OpenMetadata,
  OptionLocales,
  OptionTagData,
} from "../../domain/openOptions/types";
import {
  formatActiveTierSummary,
  formatCandidateCount,
  formatEquipmentOpenTitle,
  formatEquipmentOptionTitle,
  formatIncompleteWarning,
  formatIncompleteWarningTitle,
  formatOpenSlot,
  formatPossibleValueCount,
  formatRangeSubtitle,
  uiText,
  type Language,
} from "../../i18n";
import { Icon } from "../Icon";
import { PageHeader } from "../PageHeader";
import { SelectedTagChips, TagFilterPanel } from "../TagFilterPanel";
import {
  Chip,
  Context,
  Empty,
  FilterGroup,
  ResultsHead,
  SectionHead,
  selectedTagLabel,
} from "../common/ExplorerPrimitives";
import { Modal } from "../common/Modal";
import { equipmentIconId } from "../iconMap";
import { InstandardModeTabs } from "./InstandardModeTabs";

export function InstandardOptionOpenViewer({
  mode,
  source,
  openRows,
  language,
  optionLocales,
  equipmentGroups,
  openMetadata,
  optionTags,
  controls,
}: {
  mode: "option" | "open";
  source: InstandardCatalog;
  openRows: InstandardOpenOptionRow[];
  language: Language;
  optionLocales: OptionLocales;
  equipmentGroups: EquipmentGroups;
  openMetadata: OpenMetadata;
  optionTags: OptionTagData;
  controls: ReactNode;
}) {
  const [equipmentName, setEquipmentName] = useState("헬멧");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [converter, setConverter] =
    useState<InstandardOpenOptionRow["converter_type"]>("normal");
  const [selectedOpenLines, setSelectedOpenLines] = useState<string[] | null>(
    null,
  );
  const [query, setQuery] = useState("");
  const [equipmentPickerOpen, setEquipmentPickerOpen] = useState(false);
  const [equipmentQuery, setEquipmentQuery] = useState("");
  const [selectedOption, setSelectedOption] =
    useState<InstandardOption | null>(null);
  const equipmentToggleRef = useRef<HTMLButtonElement>(null);
  const equipmentPickerRef = useRef<HTMLElement>(null);
  const equipmentSearchRef = useRef<HTMLInputElement>(null);
  const openLines = ["1", "2", "3", "4"];
  const optionMap = useMemo(
    () => new Map(source.options.map((option) => [option.option_id, option])),
    [source],
  );
  const equipment =
    source.equipment.find((item) => item.item_group_name === equipmentName) ??
    source.equipment[0];
  const equipmentDisplayName = localizedEquipmentName(
    equipment.item_group_id,
    equipment.item_group_name,
    language,
    equipmentGroups,
  );
  const options = useMemo(
    () =>
      equipment.option_ids
        .map((id) => optionMap.get(id))
        .filter((option): option is InstandardOption => Boolean(option)),
    [equipment],
  );
  const tags = useMemo(
    () =>
      [...new Set(options.flatMap((option) => option.canonical_tags))].sort(
        (a, b) => a.localeCompare(b, "ko"),
      ),
    [options],
  );
  const filteredEquipment = useMemo(() => {
    const normalized = equipmentQuery.trim().toLocaleLowerCase();
    return source.equipment.filter(
      (item) =>
        !normalized ||
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
    );
  }, [equipmentGroups, equipmentQuery, language, source.equipment]);
  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return options.filter(
      (option) =>
        matchesSelectedTags(
          option.canonical_tags,
          selectedTags,
          optionTags,
        ) &&
        (!normalized ||
          [
            optionLocales.ko[String(option.option_id)],
            optionLocales.ja[String(option.option_id)],
            localizedInstandardOptionTitle(
              option,
              "ko",
              optionLocales,
              source,
            ),
            localizedInstandardOptionTitle(
              option,
              "ja",
              optionLocales,
              source,
            ),
            tagSearchText(option.canonical_tags, optionTags),
          ]
            .join(" ")
            .toLocaleLowerCase()
            .includes(normalized)),
    );
  }, [optionLocales, optionTags, options, query, selectedTags, source]);
  const equipmentOpenRows = useMemo(
    () =>
      openRows.filter(
        (row) => Number(row.item_group_id) === equipment.item_group_id,
      ),
    [equipment.item_group_id, openRows],
  );
  const localizedOpenRows = useMemo(
    () =>
      new Map(
        equipmentOpenRows.map((row) => [
          row,
          localizedInstandardOpenOptionRow(
            row,
            language,
            optionLocales,
            source,
          ),
        ]),
      ),
    [equipmentOpenRows, language, optionLocales, source],
  );
  const converters = useMemo(
    () =>
      ["normal", "improved", "fake", "burning"].filter((value) =>
        equipmentOpenRows.some((row) => row.converter_type === value),
      ) as InstandardOpenOptionRow["converter_type"][],
    [equipmentOpenRows],
  );
  const effectiveOpenLines = selectedOpenLines ?? openLines;
  const filteredOpenRows = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return equipmentOpenRows
      .filter((row) => {
        const localized = localizedOpenRows.get(row);
        return (
          converter === row.converter_type &&
          effectiveOpenLines.includes(row.open_slot) &&
          (!normalized ||
            [
              optionLocales.ko[row.option_id],
              optionLocales.ja[row.option_id],
              localized?.title,
              localized?.display,
              row.option_id,
              row.converter_type,
              localizedConverterLabel(row.converter_type, "ko", openMetadata),
              localizedConverterLabel(row.converter_type, "ja", openMetadata),
            ]
              .join(" ")
              .toLocaleLowerCase()
              .includes(normalized))
        );
      })
      .sort(
        (a, b) =>
          Number(a.open_slot) - Number(b.open_slot) ||
          Number(a.candidate_index) - Number(b.candidate_index),
      );
  }, [
    converter,
    effectiveOpenLines,
    equipmentOpenRows,
    localizedOpenRows,
    openMetadata,
    optionLocales,
    query,
  ]);
  const openGroups = new Map(
    openLines.map((line) => [
      line,
      filteredOpenRows.filter((row) => row.open_slot === line),
    ]),
  );
  const selectedOpenLineLabel =
    selectedOpenLines === null
      ? "ALL"
      : selectedOpenLines
          .map((line) => formatOpenSlot(language, line))
          .join(" · ");

  useEffect(() => {
    if (!equipmentPickerOpen) return;
    equipmentSearchRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeEquipmentPicker();
    };
    const closeOnOutsideClick = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        !equipmentPickerRef.current?.contains(target) &&
        !equipmentToggleRef.current?.contains(target)
      ) {
        closeEquipmentPicker();
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOnOutsideClick);
    };
  }, [equipmentPickerOpen]);

  function closeEquipmentPicker() {
    setEquipmentPickerOpen(false);
    setEquipmentQuery("");
    requestAnimationFrame(() => equipmentToggleRef.current?.focus());
  }

  function changeEquipment(name: string) {
    const nextEquipment = source.equipment.find(
      (item) => item.item_group_name === name,
    );
    const nextConverters = openRows
      .filter(
        (row) => Number(row.item_group_id) === nextEquipment?.item_group_id,
      )
      .map((row) => row.converter_type);
    setEquipmentName(name);
    setSelectedTags([]);
    closeEquipmentPicker();
    if (!nextConverters.includes(converter)) {
      setConverter(nextConverters[0] ?? converter);
    }
    setSelectedOpenLines(null);
    setQuery("");
    setSelectedOption(null);
  }

  function toggleOpenLine(value: string) {
    if (value === "ALL") {
      setSelectedOpenLines(null);
    } else {
      const current = selectedOpenLines ?? [];
      const next = current.includes(value)
        ? current.filter((line) => line !== value)
        : [...current, value].sort((a, b) => Number(a) - Number(b));
      setSelectedOpenLines(next.length ? next : null);
    }
    setQuery("");
  }

  return (
    <>
      <PageHeader
        language={language}
        title={uiText(language, "header.instandard.title")}
        description={uiText(language, "header.instandard.description")}
        controls={controls}
      />
      <main className={`instandard-mode-page instandard-${mode}-mode`}>
        <InstandardModeTabs mode={mode} language={language} />
        {mode === "option" ? (
          <section
            className="selection-panel instandard-option-toolbar"
            aria-label={uiText(language, "aria.optionFilters")}
          >
            <FilterGroup
              className="option-equipment-filter"
              number="1"
              title={uiText(language, "filter.equipment")}
            >
              <div className="selected-equipment-card">
                <Icon
                  className="app-icon"
                  id={
                    equipmentIconId[equipment.item_group_name] ??
                    "feature-instandard-option"
                  }
                  size={24}
                />
                <strong>{equipmentDisplayName}</strong>
                <button
                  ref={equipmentToggleRef}
                  type="button"
                  aria-expanded={equipmentPickerOpen}
                  aria-controls="instandard-equipment-picker"
                  onClick={() =>
                    equipmentPickerOpen
                      ? closeEquipmentPicker()
                      : setEquipmentPickerOpen(true)
                  }
                >
                  {uiText(
                    language,
                    equipmentPickerOpen
                      ? "filter.collapseEquipment"
                      : "filter.changeEquipment",
                  )}
                </button>
              </div>
            </FilterGroup>
            <FilterGroup
              className="option-search-filter"
              number="2"
              title={uiText(language, "filter.optionSearch")}
            >
              <div className="panel-search-control">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={uiText(
                    language,
                    "filter.optionSearchPlaceholder",
                  )}
                  aria-label={uiText(language, "filter.optionSearch")}
                />
                {query && (
                  <button type="button" onClick={() => setQuery("")}>
                    {uiText(language, "common.reset")}
                  </button>
                )}
              </div>
            </FilterGroup>
            {equipmentPickerOpen && (
              <section
                ref={equipmentPickerRef}
                className="equipment-picker-floating"
                id="instandard-equipment-picker"
                role="dialog"
                aria-label={uiText(language, "filter.equipment")}
              >
                <div className="equipment-picker-head">
                  <h3>{uiText(language, "filter.equipment")}</h3>
                  <button
                    type="button"
                    aria-label={uiText(language, "filter.closeEquipment")}
                    onClick={closeEquipmentPicker}
                  >
                    ×
                  </button>
                </div>
                <label className="equipment-name-search">
                  <span className="visually-hidden">
                    {uiText(language, "filter.equipmentSearch")}
                  </span>
                  <input
                    ref={equipmentSearchRef}
                    value={equipmentQuery}
                    onChange={(event) => setEquipmentQuery(event.target.value)}
                    placeholder={uiText(
                      language,
                      "filter.equipmentSearchPlaceholder",
                    )}
                  />
                </label>
                <div className="equipment-icon-grid">
                  {filteredEquipment.map((item) => (
                    <button
                      type="button"
                      className={`equipment-picker-item ${
                        equipment.item_group_id === item.item_group_id
                          ? "active"
                          : ""
                      }`}
                      aria-pressed={
                        equipment.item_group_id === item.item_group_id
                      }
                      onClick={() => changeEquipment(item.item_group_name)}
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
                    </button>
                  ))}
                </div>
                {!filteredEquipment.length && (
                  <p className="equipment-picker-empty">
                    {uiText(language, "common.noSearchResults")}
                  </p>
                )}
              </section>
            )}
          </section>
        ) : (
          <section
            className="selection-panel instandard-panel inst-open-panel"
            aria-label={uiText(language, "aria.openFilters")}
          >
            <FilterGroup
              number="1"
              title={uiText(language, "filter.equipment")}
            >
              {source.equipment.map((item) => (
                <Chip
                  key={item.item_group_id}
                  active={equipment.item_group_id === item.item_group_id}
                  onClick={() => changeEquipment(item.item_group_name)}
                >
                  <span className="inst-open-equipment-chip">
                    <Icon
                      className="app-icon"
                      id={
                        equipmentIconId[item.item_group_name] ??
                        "feature-instandard-option"
                      }
                      size={18}
                    />
                    {localizedEquipmentName(
                      item.item_group_id,
                      item.item_group_name,
                      language,
                      equipmentGroups,
                    )}
                  </span>
                </Chip>
              ))}
            </FilterGroup>
            <FilterGroup
              number="2"
              title={uiText(language, "filter.converter")}
            >
              {converters.map((value) => (
                <Chip
                  key={value}
                  active={converter === value}
                  onClick={() => {
                    setConverter(value);
                    setQuery("");
                  }}
                >
                  {localizedConverterLabel(value, language, openMetadata)}
                </Chip>
              ))}
            </FilterGroup>
            <FilterGroup
              number="3"
              title={uiText(language, "filter.openSlot")}
            >
              <Chip
                active={selectedOpenLines === null}
                onClick={() => toggleOpenLine("ALL")}
              >
                ALL
              </Chip>
              {openLines.map((value) => (
                <Chip
                  key={value}
                  active={selectedOpenLines?.includes(value) ?? false}
                  onClick={() => toggleOpenLine(value)}
                >
                  {value}
                </Chip>
              ))}
            </FilterGroup>
          </section>
        )}
        {mode === "option" ? (
          <>
            <TagFilterPanel
              availableTags={tags}
              selectedTags={selectedTags}
              onChange={setSelectedTags}
              language={language}
              optionTags={optionTags}
            />
            <Context
              language={language}
              breadcrumb={`${equipmentDisplayName} › ${uiText(
                language,
                "mode.option.title",
              )} › ${selectedTagLabel(
                selectedTags,
                language,
                optionTags,
                "common.allCategories",
              )}`}
              query={query}
              onQuery={setQuery}
              placeholder={uiText(language, "filter.currentOptionSearch")}
              hideSearch
            />
            <ResultsHead
              language={language}
              title={formatEquipmentOptionTitle(
                language,
                equipmentDisplayName,
              )}
              description={uiText(language, "option.resultsDescription")}
              count={filteredOptions.length}
            />
            <SelectedTagChips
              selectedTags={selectedTags}
              onChange={setSelectedTags}
              language={language}
              optionTags={optionTags}
            />
            {filteredOptions.length ? (
              <section className="option-section instandard-option-results-section">
                <div className="table-wrap">
                  <table className="instandard-option-results">
                    <thead>
                      <tr>
                        <th>{uiText(language, "option.name")}</th>
                        <th>{uiText(language, "option.category")}</th>
                        <th>{uiText(language, "option.range")}</th>
                        <th>{uiText(language, "option.tierDetails")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredOptions.map((option) => (
                        <tr key={option.option_id}>
                          <td>
                            <strong>
                              {localizedInstandardOptionTitle(
                                option,
                                language,
                                optionLocales,
                                source,
                              )}
                            </strong>
                            {equipment.supplemental_option_ids.includes(
                              option.option_id,
                            ) && <em>{uiText(language, "option.supplemental")}</em>}
                          </td>
                          <td>
                            <div className="option-tag-badges">
                              {option.canonical_tags.map((optionTag) => (
                                <span key={optionTag}>
                                  {tagText(language, optionTag, optionTags)}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td>
                            <span className="option-range-text">
                              {rangeLabel(
                                option,
                                language,
                                optionLocales,
                                source,
                              )}
                            </span>
                          </td>
                          <td>
                            <div className="tier-detail-group">
                              <button
                                className="tier-detail-button"
                                onClick={() => setSelectedOption(option)}
                              >
                                {uiText(language, "option.viewTierValues")}
                              </button>
                              <small>
                                {formatPossibleValueCount(
                                  language,
                                  candidateValues(
                                    option,
                                    language,
                                    optionLocales,
                                    source,
                                  ).length,
                                )}
                              </small>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : (
              <Empty language={language} />
            )}
          </>
        ) : (
          <>
            <Context
              language={language}
              breadcrumb={`${equipmentDisplayName} › ${uiText(
                language,
                "mode.open.title",
              )} › ${localizedConverterLabel(
                converter,
                language,
                openMetadata,
              )} › ${selectedOpenLineLabel}`}
              query={query}
              onQuery={setQuery}
              placeholder={uiText(language, "filter.currentOpenSearch")}
            />
            <ResultsHead
              language={language}
              title={formatEquipmentOpenTitle(language, equipmentDisplayName)}
              description={uiText(
                language,
                "instandardOpen.resultsDescription",
              )}
              count={filteredOpenRows.length}
            />
            {filteredOpenRows.length ? (
              openLines
                .filter((line) => (openGroups.get(line)?.length ?? 0) > 0)
                .map((line) => {
                  const group = openGroups.get(line) ?? [];
                  const probabilitySum = group.reduce(
                    (sum, row) => sum + Number(row.probability),
                    0,
                  );
                  const anomaly = Math.abs(probabilitySum - 100) > 0.06;
                  const missingProbability = anomaly
                    ? 100 - probabilitySum
                    : 0;
                  return (
                    <section
                      className="option-section instandard-open-section"
                      key={line}
                    >
                      <SectionHead
                        title={formatOpenSlot(language, line)}
                        count={formatCandidateCount(language, group.length)}
                      />
                      {anomaly && (
                        <aside className="probability-warning">
                          <strong>
                            {formatIncompleteWarningTitle(language, line)}
                          </strong>
                          <span>
                            {formatIncompleteWarning(
                              language,
                              formatProbability(String(probabilitySum)),
                              formatProbability(String(missingProbability)),
                            ).map((message, index) => (
                              <span key={message}>
                                {message}
                                {index < 2 && <br />}
                              </span>
                            ))}
                          </span>
                        </aside>
                      )}
                      <div className="table-wrap">
                        <table className="instandard-open-table">
                          <thead>
                            <tr>
                              <th>
                                {uiText(language, "instandardOpen.optionName")}
                              </th>
                              <th>
                                {uiText(language, "instandardOpen.value")}
                              </th>
                              <th>
                                {uiText(
                                  language,
                                  "instandardOpen.probability",
                                )}
                              </th>
                              <th>
                                {uiText(
                                  language,
                                  "instandardOpen.internalTier",
                                )}
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {group.map((row) => {
                              const localized = localizedOpenRows.get(row)!;
                              return (
                                <tr
                                  key={`${row.source_block_index}-${row.source_file_offset}`}
                                >
                                  <td>
                                    <strong>{localized.title}</strong>
                                  </td>
                                  <td>{localized.display}</td>
                                  <td>
                                    <b className="probability">
                                      {formatProbability(row.probability)}%
                                    </b>
                                  </td>
                                  <td>
                                    <span className="tier">{row.tier}</span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  );
                })
            ) : (
              <Empty language={language} />
            )}
          </>
        )}
      </main>
      {mode === "option" && selectedOption && (
        <Modal
          language={language}
          title={localizedInstandardOptionTitle(
            selectedOption,
            language,
            optionLocales,
            source,
          )}
          subtitle={formatRangeSubtitle(
            language,
            rangeLabel(selectedOption, language, optionLocales, source),
          )}
          onClose={() => setSelectedOption(null)}
        >
          <p>
            {formatActiveTierSummary(
              language,
              selectedOption.tiers.filter((tier) => tier.enabled).length,
              candidateValues(
                selectedOption,
                language,
                optionLocales,
                source,
              ).length,
            )}
          </p>
          <div className="tier-value-groups">
            {selectedOption.tiers
              .filter((tier) => tier.enabled)
              .map((tier) => (
                <section className="tier-value-group" key={tier.tier}>
                  <h3>Tier {tier.tier}</h3>
                  <div className="value-list">
                    {tierCandidateValues(
                      selectedOption,
                      tier,
                      language,
                      optionLocales,
                      source,
                    ).map((value) => (
                      <span key={`${tier.tier}-${value}`}>{value}</span>
                    ))}
                  </div>
                </section>
              ))}
          </div>
        </Modal>
      )}
    </>
  );
}
