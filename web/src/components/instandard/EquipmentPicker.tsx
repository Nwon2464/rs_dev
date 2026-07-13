import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { InstandardEquipment } from "../../data/instandardOptions";
import { localizedEquipmentName } from "../../domain/openOptions/instandardRendering";
import type { EquipmentGroups } from "../../domain/openOptions/types";
import { uiText, type Language } from "../../i18n";
import { Icon } from "../Icon";
import { equipmentIconId } from "../iconMap";

export function EquipmentPicker({
  equipment,
  equipmentItems,
  language,
  equipmentGroups,
  toggleRef,
  onClose,
  onChange,
}: {
  equipment: InstandardEquipment;
  equipmentItems: InstandardEquipment[];
  language: Language;
  equipmentGroups: EquipmentGroups;
  toggleRef: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
  onChange: (name: string) => void;
}) {
  const [query, setQuery] = useState("");
  const pickerRef = useRef<HTMLElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const filteredEquipment = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return equipmentItems.filter(
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
  }, [equipmentGroups, equipmentItems, language, query]);

  useEffect(() => {
    searchRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const closeOnOutsideClick = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        !pickerRef.current?.contains(target) &&
        !toggleRef.current?.contains(target)
      ) {
        onClose();
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOnOutsideClick);
    };
  }, []);

  return (
    <section
      ref={pickerRef}
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
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <label className="equipment-name-search">
        <span className="visually-hidden">
          {uiText(language, "filter.equipmentSearch")}
        </span>
        <input
          ref={searchRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={uiText(language, "filter.equipmentSearchPlaceholder")}
        />
      </label>
      <div className="equipment-icon-grid">
        {filteredEquipment.map((item) => (
          <button
            type="button"
            className={`equipment-picker-item ${
              equipment.item_group_id === item.item_group_id ? "active" : ""
            }`}
            aria-pressed={equipment.item_group_id === item.item_group_id}
            onClick={() => onChange(item.item_group_name)}
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
  );
}
