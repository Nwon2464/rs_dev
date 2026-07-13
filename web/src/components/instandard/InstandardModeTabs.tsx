import { Icon } from "../Icon";
import { featureIconId } from "../iconMap";
import { uiText, type Language } from "../../i18n";
import { instandardModes, type InstandardMode } from "./modes";

export function InstandardModeTabs({
  mode,
  language,
}: {
  mode: InstandardMode;
  language: Language;
}) {
  return (
    <nav
      className="instandard-mode-tabs"
      aria-label={uiText(language, "mode.navigation")}
    >
      {instandardModes.map((item) => (
        <a
          className={`mode-tab mode-tab--${item.className} ${
            mode === item.mode ? "active" : ""
          }`}
          href={`?view=instandard&mode=${item.mode}`}
          aria-current={mode === item.mode ? "page" : undefined}
          key={item.mode}
        >
          <Icon
            className="app-icon"
            id={featureIconId[item.iconLabel]}
            size={18}
          />
          {uiText(language, item.titleKey)}
        </a>
      ))}
    </nav>
  );
}
