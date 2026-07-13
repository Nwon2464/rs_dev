import type { ReactNode } from "react";
import { uiText, type Language } from "../i18n";

export function PageHeader({
  language,
  title,
  description,
  controls,
  home = true,
}: {
  language: Language;
  title: string;
  description: string;
  controls: ReactNode;
  home?: boolean;
}) {
  return (
    <header>
      <div className="top">
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <div className="header-actions">
          {home && (
            <a className="home" href="?">
              ← {uiText(language, "common.home")}
            </a>
          )}
          {controls}
        </div>
      </div>
    </header>
  );
}
