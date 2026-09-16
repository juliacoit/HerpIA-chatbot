import React from "react";
import { Icon } from "./Icon.jsx";

const H = { sm: "var(--control-h-sm)", md: "var(--control-h-md)", lg: "var(--control-h-lg)" };
const PAD = { sm: "0 14px", md: "0 18px", lg: "0 24px" };
const FS = { sm: "13px", md: "14.5px", lg: "16px" };

const VARIANTS = {
  primary: { background: "var(--action-primary)", color: "var(--action-primary-text)", border: "1px solid var(--action-primary)" },
  secondary: { background: "var(--action-secondary-bg)", color: "var(--text-body)", border: "1px solid var(--action-secondary-border)" },
  ghost: { background: "transparent", color: "var(--text-link)", border: "1px solid transparent" },
  danger: { background: "var(--clay-700)", color: "var(--white)", border: "1px solid var(--clay-700)" },
};
const HOVER = {
  primary: { background: "var(--action-primary-hover)", borderColor: "var(--action-primary-hover)" },
  secondary: { background: "var(--action-secondary-hover)", borderColor: "var(--border-strong)" },
  ghost: { background: "var(--surface-tinted)" },
  danger: { background: "#7A3125", borderColor: "#7A3125" },
};

export function Button({ children, variant = "primary", size = "md", iconLeft, iconRight, disabled, fullWidth, type = "button", onClick, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);
  const base = VARIANTS[variant] || VARIANTS.primary;
  return (
    <button
      type={type} disabled={disabled} onClick={onClick}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => { setHover(false); setPress(false); }}
      onMouseDown={() => setPress(true)} onMouseUp={() => setPress(false)}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "var(--space-2)",
        height: H[size], padding: PAD[size], fontFamily: "var(--font-body)", fontSize: FS[size],
        fontWeight: 600, letterSpacing: "0.01em", borderRadius: "var(--radius-pill)", cursor: disabled ? "not-allowed" : "pointer",
        width: fullWidth ? "100%" : "auto", transition: "var(--transition-control), transform var(--duration-instant) var(--ease-standard)",
        transform: press && !disabled ? "scale(0.985)" : "none", whiteSpace: "nowrap",
        ...base,
        ...(hover && !disabled ? HOVER[variant] : null),
        ...(disabled ? { background: "var(--action-disabled-bg)", color: "var(--action-disabled-text)", border: "1px solid var(--action-disabled-bg)" } : null),
        ...style,
      }}
      {...rest}
    >
      {iconLeft ? <Icon name={iconLeft} size={size === "lg" ? "lg" : "md"} /> : null}
      {children}
      {iconRight ? <Icon name={iconRight} size={size === "lg" ? "lg" : "md"} /> : null}
    </button>
  );
}
