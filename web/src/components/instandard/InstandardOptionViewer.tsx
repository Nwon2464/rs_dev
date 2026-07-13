import { useMemo, useRef, useState, type ReactNode } from "react";
import type {
  InstandardCatalog,
  InstandardOption,
} from "../../data/instandardOptions";
import {
  localizedEquipmentName,
  localizedInstandardOptionTitle,
} from "../../domain/openOptions/instandardRendering";
import {
  matchesSelectedTags,
  tagSearchText,
} from "../../domain/openOptions/tags";
import type {
  EquipmentGroups,
  OptionLocales,
  OptionTagData,
} from "../../domain/openOptions/types";
import { formatEquipmentOptionTitle, uiText, type Language } from "../../i18n";
import { Icon } from "../Icon";
import { PageHeader } from "../PageHeader";
import { SelectedTagChips, TagFilterPanel } from "../TagFilterPanel";
import {
  Context,
  Empty,
  FilterGroup,
  ResultsHead,
  selectedTagLabel,
} from "../common/ExplorerPrimitives";
import { equipmentIconId } from "../iconMap";
import { EquipmentPicker } from "./EquipmentPicker";
import { InstandardModeTabs } from "./InstandardModeTabs";
import { InstandardOptionModal } from "./InstandardOptionModal";
import { InstandardOptionTable } from "./InstandardOptionTable";

export function InstandardOptionViewer({
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
  const [equipmentName, setEquipmentName] = useState("헬멧");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [equipmentPickerOpen, setEquipmentPickerOpen] = useState(false);
  const [selectedOption, setSelectedOption] =
    useState<InstandardOption | null>(null);
  const equipmentToggleRef = useRef<HTMLButtonElement>(null);
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

  function closeEquipmentPicker() {
    setEquipmentPickerOpen(false);
    requestAnimationFrame(() => equipmentToggleRef.current?.focus());
  }

  function changeEquipment(name: string) {
    setEquipmentName(name);
    setSelectedTags([]);
    closeEquipmentPicker();
    setQuery("");
    setSelectedOption(null);
  }

  return (
    <>
      <PageHeader
        language={language}
        title={uiText(language, "header.instandard.title")}
        description={uiText(language, "header.instandard.description")}
        controls={controls}
      />
      <main className="instandard-mode-page instandard-option-mode">
        <InstandardModeTabs mode="option" language={language} />
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
                placeholder={uiText(language, "filter.optionSearchPlaceholder")}
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
            <EquipmentPicker
              equipment={equipment}
              equipmentItems={source.equipment}
              language={language}
              equipmentGroups={equipmentGroups}
              toggleRef={equipmentToggleRef}
              onClose={closeEquipmentPicker}
              onChange={changeEquipment}
            />
          )}
        </section>
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
          title={formatEquipmentOptionTitle(language, equipmentDisplayName)}
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
          <InstandardOptionTable
            options={filteredOptions}
            equipment={equipment}
            source={source}
            language={language}
            optionLocales={optionLocales}
            optionTags={optionTags}
            onSelect={setSelectedOption}
          />
        ) : (
          <Empty language={language} />
        )}
      </main>
      {selectedOption && (
        <InstandardOptionModal
          option={selectedOption}
          source={source}
          language={language}
          optionLocales={optionLocales}
          onClose={() => setSelectedOption(null)}
        />
      )}
    </>
  );
}
