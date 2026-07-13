import type {
  InstandardCatalog,
  InstandardOption,
} from "../../data/instandardOptions";
import {
  candidateValues,
  localizedInstandardOptionTitle,
  rangeLabel,
  tierCandidateValues,
} from "../../domain/openOptions/instandardRendering";
import type { OptionLocales } from "../../domain/openOptions/types";
import {
  formatActiveTierSummary,
  formatRangeSubtitle,
  type Language,
} from "../../i18n";
import { Modal } from "../common/Modal";

export function InstandardOptionModal({
  option,
  source,
  language,
  optionLocales,
  onClose,
}: {
  option: InstandardOption;
  source: InstandardCatalog;
  language: Language;
  optionLocales: OptionLocales;
  onClose: () => void;
}) {
  return (
    <Modal
      language={language}
      title={localizedInstandardOptionTitle(
        option,
        language,
        optionLocales,
        source,
      )}
      subtitle={formatRangeSubtitle(
        language,
        rangeLabel(option, language, optionLocales, source),
      )}
      onClose={onClose}
    >
      <p>
        {formatActiveTierSummary(
          language,
          option.tiers.filter((tier) => tier.enabled).length,
          candidateValues(option, language, optionLocales, source).length,
        )}
      </p>
      <div className="tier-value-groups">
        {option.tiers
          .filter((tier) => tier.enabled)
          .map((tier) => (
            <section className="tier-value-group" key={tier.tier}>
              <h3>Tier {tier.tier}</h3>
              <div className="value-list">
                {tierCandidateValues(
                  option,
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
  );
}
