import type { ReactNode } from "react";
import { tagText } from "../../../domain/openOptions/tags";
import type { OptionTagData } from "../../../domain/openOptions/types";
import type { Language } from "../../../i18n";
import { OptionTitle } from "../OptionTitle";

export function OptionIdentityCell({
  title,
  tags,
  language,
  optionTags,
  children,
}: {
  title: string;
  tags: string[];
  language: Language;
  optionTags: OptionTagData;
  children?: ReactNode;
}) {
  return (
    <td className="option-identity-cell">
      <OptionTitle title={title} />
      <div className="option-tag-badges option-inline-tags">
        {tags.map((tag) => (
          <span key={tag}>{tagText(language, tag, optionTags)}</span>
        ))}
      </div>
      {children}
    </td>
  );
}
