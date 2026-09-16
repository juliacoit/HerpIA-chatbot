import React from "react";
import { Icon } from "./Icon.jsx";

export function Input({ label, hint, error, iconLeft, value, onChange, placeholder, disabled, id, type = "text", style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", fontFamily: "var(--font-body)", ...style }}>
      {label ? <label htmlFor={inputId} style={{ fontSize: "var(--text-small-size)", fontWeight: 600, color: "var(--text-body)" }}>{label}</label> : null}
      <div style={{
        display: "flex", alignItems: "center", gap: "var(--space-2)", height: "var(--control-h-md)",
        padding: "0 14px", background: disabled ? "var(--surface-sunken)" : "var(--white)",
        border: `1px solid ${error ? "var(--clay-500)" : focus ? "var(--border-focus)" : "var(--border-hairline)"}`,
        borderRadius: "var(--radius-pill)", boxShadow: focus ? "var(--focus-ring)" : "none", transition: "var(--transition-control)",
      }}>
        {iconLeft ? <Icon name={iconLeft} size="md" color="var(--text-subtle)" /> : null}
        <input
          id={inputId} type={type} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled}
          onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
          style={{ flex: 1, minWidth: 0, border: "none", outline: "none", background: "transparent", fontFamily: "var(--font-body)", fontSize: "var(--text-body-size)", color: "var(--text-body)" }}
          {...rest}
        />
      </div>
      {error ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--clay-700)" }}>{error}</span>
        : hint ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{hint}</span> : null}
    </div>
  );
}
