import type { InstandardOpenOptionRow } from "../../data/instandardOptions";
import { formatProbability } from "../../domain/openOptions/instandardRendering";
import type { OptionTagData } from "../../domain/openOptions/types";
import {
  formatCandidateCount,
  formatIncompleteWarning,
  formatIncompleteWarningTitle,
  formatOpenSlot,
  uiText,
  type Language,
} from "../../i18n";
import { SectionHead } from "../common/ExplorerPrimitives";
import { OptionIdentityCell } from "../common/optionTable/OptionIdentityCell";
import { OptionTagsCell } from "../common/optionTable/OptionTagsCell";
import { OptionValueCell } from "../common/optionTable/OptionValueCell";
import { ProgressBadge } from "../common/optionTable/ProgressBadge";

type LocalizedOpenRow = { title: string; display: string };

export function InstandardOpenTable({
  rows,
  openLines,
  localizedRows,
  language,
  optionTags,
}: {
  rows: InstandardOpenOptionRow[];
  openLines: string[];
  localizedRows: Map<InstandardOpenOptionRow, LocalizedOpenRow>;
  language: Language;
  optionTags: OptionTagData;
}) {
  const openGroups = new Map(
    openLines.map((line) => [
      line,
      rows.filter((row) => row.open_slot === line),
    ]),
  );
  return openLines
    .filter((line) => (openGroups.get(line)?.length ?? 0) > 0)
    .map((line) => {
      const group = openGroups.get(line) ?? [];
      const probabilitySum = group.reduce(
        (sum, row) => sum + Number(row.probability),
        0,
      );
      const anomaly = Math.abs(probabilitySum - 100) > 0.06;
      const missingProbability = anomaly ? 100 - probabilitySum : 0;
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
              <strong>{formatIncompleteWarningTitle(language, line)}</strong>
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
                  <th>{uiText(language, "instandardOpen.optionName")}</th>
                  <th>{uiText(language, "instandardOpen.value")}</th>
                  <th className="option-category-column">{uiText(language, "option.category")}</th>
                  <th>{uiText(language, "instandardOpen.internalTier")}</th>
                  <th>{uiText(language, "instandardOpen.probability")}</th>
                </tr>
              </thead>
              <tbody>
                {group.map((row) => {
                  const localized = localizedRows.get(row)!;
                  return (
                    <tr
                      key={`${row.source_block_index}-${row.source_file_offset}`}
                    >
                      <OptionIdentityCell
                        title={localized.title}
                        tags={row.tags}
                        language={language}
                        optionTags={optionTags}
                      />
                      <OptionValueCell value={localized.display} />
                      <OptionTagsCell
                        tags={row.tags}
                        language={language}
                        optionTags={optionTags}
                      />
                      <td><ProgressBadge label={row.tier} /></td>
                      <td><b className="probability">{formatProbability(row.probability)}%</b></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      );
    });
}
