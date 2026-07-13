import { useMemo, useState, type ReactNode } from "react";
import type {
  InstandardCatalog,
  InstandardOpenOptionRow,
} from "../../data/instandardOptions";
import {
  localizedConverterLabel,
  localizedEquipmentName,
  localizedInstandardOpenOptionRow,
} from "../../domain/openOptions/instandardRendering";
import { matchesSelectedTags, tagSearchText } from "../../domain/openOptions/tags";
import type {
  EquipmentGroups,
  OpenMetadata,
  OptionLocales,
  OptionTagData,
} from "../../domain/openOptions/types";
import {
  formatEquipmentOpenTitle,
  formatOpenSlot,
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
} from "../common/ExplorerPrimitives";
import { equipmentIconId } from "../iconMap";
import { InstandardModeTabs } from "./InstandardModeTabs";
import { InstandardOpenTable } from "./InstandardOpenTable";

export function InstandardOpenViewer({
  source,
  openRows,
  language,
  optionLocales,
  equipmentGroups,
  openMetadata,
  optionTags,
  controls,
}: {
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
  const [converter, setConverter] =
    useState<InstandardOpenOptionRow["converter_type"]>("normal");
  const [selectedOpenLines, setSelectedOpenLines] = useState<string[] | null>(
    null,
  );
  const [query, setQuery] = useState("");
  const [selectedOpenTags, setSelectedOpenTags] = useState<string[]>([]);
  const openLines = ["1", "2", "3", "4"];
  const equipment =
    source.equipment.find((item) => item.item_group_name === equipmentName) ??
    source.equipment[0];
  const equipmentDisplayName = localizedEquipmentName(
    equipment.item_group_id,
    equipment.item_group_name,
    language,
    equipmentGroups,
  );
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
  const availableOpenTags = useMemo(
    () =>
      [...new Set(equipmentOpenRows.flatMap((row) => row.tags))].sort((a, b) =>
        a.localeCompare(b, "ko"),
      ),
    [equipmentOpenRows],
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
          matchesSelectedTags(row.tags, selectedOpenTags, optionTags) &&
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
              tagSearchText(row.tags, optionTags),
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
    optionTags,
    query,
    selectedOpenTags,
  ]);
  const selectedOpenLineLabel =
    selectedOpenLines === null
      ? uiText(language, "common.allOpenSlots")
      : selectedOpenLines.length
        ? selectedOpenLines
          .map((line) => formatOpenSlot(language, line))
          .join(" · ")
        : uiText(language, "common.noOpenSlotsSelected");

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
    if (!nextConverters.includes(converter)) {
      setConverter(nextConverters[0] ?? converter);
    }
    setSelectedOpenLines(null);
    setSelectedOpenTags([]);
    setQuery("");
  }

  function toggleOpenLine(value: string) {
    if (value === "ALL") {
      setSelectedOpenLines(null);
    } else {
      const current = selectedOpenLines ?? openLines;
      const next = current.includes(value)
        ? current.filter((line) => line !== value)
        : [...current, value].sort((a, b) => Number(a) - Number(b));
      setSelectedOpenLines(next);
    }
    setSelectedOpenTags([]);
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
      <main className="instandard-mode-page instandard-open-mode">
        <InstandardModeTabs mode="open" language={language} />
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
                  setSelectedOpenTags([]);
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
              active={effectiveOpenLines.length === openLines.length}
              onClick={() => toggleOpenLine("ALL")}
            >
              ▤ ALL
            </Chip>
            {openLines.map((value) => (
              <Chip
                key={value}
                active={effectiveOpenLines.includes(value)}
                onClick={() => toggleOpenLine(value)}
              >
                {formatOpenSlot(language, value)}
              </Chip>
            ))}
            <Chip
              active={effectiveOpenLines.length === 0}
              onClick={() => {
                setSelectedOpenLines([]);
                setSelectedOpenTags([]);
                setQuery("");
              }}
            >
              {uiText(language, "common.clearSelection")}
            </Chip>
          </FilterGroup>
        </section>
        <TagFilterPanel
          availableTags={availableOpenTags}
          selectedTags={selectedOpenTags}
          onChange={setSelectedOpenTags}
          language={language}
          optionTags={optionTags}
        />
        <Context
          language={language}
          breadcrumb={[
            equipmentDisplayName,
            uiText(language, "mode.open.title"),
            localizedConverterLabel(converter, language, openMetadata),
            selectedOpenLineLabel,
          ]}
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
        <SelectedTagChips
          selectedTags={selectedOpenTags}
          onChange={setSelectedOpenTags}
          language={language}
          optionTags={optionTags}
        />
        {filteredOpenRows.length ? (
          <InstandardOpenTable
            rows={filteredOpenRows}
            openLines={openLines}
            localizedRows={localizedOpenRows}
            language={language}
            optionTags={optionTags}
          />
        ) : (
          <Empty language={language} onReset={() => { setSelectedOpenLines(null); setSelectedOpenTags([]); setQuery(""); }} />
        )}
      </main>
    </>
  );
}
