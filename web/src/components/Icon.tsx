import type { CSSProperties } from "react";

type IconProps = {
  id: string;
  label?: string;
  size?: number;
  className?: string;
  style?: CSSProperties;
};

export function Icon({
  id,
  label,
  size = 20,
  className,
  style,
}: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      focusable="false"
      style={style}
    >
      <use href={`${import.meta.env.BASE_URL}icons/sprite.svg#${id}`} />
    </svg>
  );
}
