import type {
  InstandardCatalog,
  InstandardEquipment,
  InstandardOption,
} from "../../data/instandardOptions";
import {
  candidateValues,
  localizedInstandardOptionTitle,
  rangeLabel,
} from "../../domain/openOptions/instandardRendering";
import type { OptionLocales, OptionTagData } from "../../domain/openOptions/types";
import { formatPossibleValueCount, uiText, type Language } from "../../i18n";
import { OptionIdentityCell } from "../common/optionTable/OptionIdentityCell";
import { OptionTagsCell } from "../common/optionTable/OptionTagsCell";
import { OptionValueCell } from "../common/optionTable/OptionValueCell";

export function InstandardOptionTable({
  options,
  equipment,
  source,
  language,
  optionLocales,
  optionTags,
  onSelect,
}: {
  options: InstandardOption[];
  equipment: InstandardEquipment;
  source: InstandardCatalog;
  language: Language;
  optionLocales: OptionLocales;
  optionTags: OptionTagData;
  onSelect: (option: InstandardOption) => void;
}) {
  return (
    <section className="option-section instandard-option-results-section">
      <div className="table-wrap">
        <table className="instandard-option-results">
          <thead>
            <tr>
              <th>{uiText(language, "option.name")}</th>
              <th>{uiText(language, "option.range")}</th>
              <th className="option-category-column">{uiText(language, "option.category")}</th>
              <th>{uiText(language, "option.tierDetails")}</th>
            </tr>
          </thead>
          <tbody>
            {options.map((option) => (
              <tr key={option.option_id}>
                <OptionIdentityCell
                  title={localizedInstandardOptionTitle(
                    option,
                    language,
                    optionLocales,
                    source,
                  )}
                  tags={option.canonical_tags}
                  language={language}
                  optionTags={optionTags}
                >
                  {equipment.supplemental_option_ids.includes(
                    option.option_id,
                  ) && <em>{uiText(language, "option.supplemental")}</em>}
                </OptionIdentityCell>
                <OptionValueCell
                  value={rangeLabel(option, language, optionLocales, source)}
                />
                <OptionTagsCell
                  tags={option.canonical_tags}
                  language={language}
                  optionTags={optionTags}
                />
                <td>
                  <div className="tier-detail-group">
                    <button
                      className="tier-detail-button"
                      onClick={() => onSelect(option)}
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
  );
}
