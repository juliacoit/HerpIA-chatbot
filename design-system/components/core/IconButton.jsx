import React from "react";
import { Icon } from "./Icon.jsx";

const H = { sm: 30, md: 38, lg: 46 };

export function IconButton({ icon, label, size = "md", variant = "secondary", disabled, active, onClick, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const px = H[size];
  const filled = variant === "primary";
  return (
    <button
      type="button" aria-label={label} title={label} disabled={disabled} onClick={onClick}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        width: px, height: px, display: "inline-flex", alignItems: "center", justifyContent: "center",
        borderRadius: "var(--radius-pill)", cursor: disabled ? "not-allowed" : "pointer",
        background: filled ? "var(--action-primary)" : active ? "var(--surface-tinted)" : hover ? "var(--action-secondary-hover)" : variant === "ghost" ? "transparent" : "var(--white)",
        color: filled ? "var(--white)" : active ? "var(--teal-800)" : "var(--text-muted)",
        border: variant === "ghost" ? "1px solid transparent" : `1px solid ${filled ? "var(--action-primary)" : "var(--action-secondary-border)"}`,
        opacity: disabled ? 0.5 : 1, transition: "var(--transition-control)", ...style,
      }}
      {...rest}
    >
      <Icon name={icon} size={size === "sm" ? "md" : "lg"} />
    </button>
  );
}
