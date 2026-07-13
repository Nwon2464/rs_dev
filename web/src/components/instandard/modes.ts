import type { UiMessageKey } from "../../i18n";

export type InstandardMode = "option" | "open" | "tier";

export type InstandardModeDefinition = {
  mode: InstandardMode;
  titleKey: UiMessageKey;
  descriptionKey: UiMessageKey;
  iconLabel: string;
  className: string;
};

export const instandardModes: InstandardModeDefinition[] = [
  {
    mode: "option",
    titleKey: "mode.option.title",
    descriptionKey: "mode.option.description",
    iconLabel: "비규격 옵션",
    className: "option",
  },
  {
    mode: "open",
    titleKey: "mode.open.title",
    descriptionKey: "mode.open.description",
    iconLabel: "비규격 개방옵션",
    className: "open",
  },
  {
    mode: "tier",
    titleKey: "mode.tier.title",
    descriptionKey: "mode.tier.description",
    iconLabel: "티어별 옵션",
    className: "tier",
  },
];
