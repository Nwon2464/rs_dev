import { tagText } from "../../../domain/openOptions/tags";
import type { OptionTagData } from "../../../domain/openOptions/types";
import type { Language } from "../../../i18n";

export function OptionTagsCell({
  tags,
  language,
  optionTags,
}: {
  tags: string[];
  language: Language;
  optionTags: OptionTagData;
}) {
  return (
    <td className="option-category-column">
      <div className="option-tag-badges">
        {tags.map((tag) => (
          <span key={tag}>{tagText(language, tag, optionTags)}</span>
        ))}
      </div>
    </td>
  );
}
