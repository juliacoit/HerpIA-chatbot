import React from "react";
import { Icon } from "./Icon.jsx";

export function Select({ label, hint, options = [], value, onChange, disabled, id, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const selId = id || React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", fontFamily: "var(--font-body)", ...style }}>
      {label ? <label htmlFor={selId} style={{ fontSize: "var(--text-small-size)", fontWeight: 600, color: "var(--text-body)" }}>{label}</label> : null}
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <select
          id={selId} value={value} onChange={onChange} disabled={disabled}
          onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
          style={{
            appearance: "none", width: "100%", height: "var(--control-h-md)", padding: "0 38px 0 14px",
            fontFamily: "var(--font-body)", fontSize: "var(--text-body-size)", color: "var(--text-body)",
            background: disabled ? "var(--surface-sunken)" : "var(--white)",
            border: `1px solid ${focus ? "var(--border-focus)" : "var(--border-hairline)"}`,
            borderRadius: "var(--radius-pill)", boxShadow: focus ? "var(--focus-ring)" : "none",
            outline: "none", cursor: disabled ? "not-allowed" : "pointer", transition: "var(--transition-control)",
          }}
          {...rest}
        >
          {options.map((o) => {
            const opt = typeof o === "string" ? { value: o, label: o } : o;
            return <option key={opt.value} value={opt.value}>{opt.label}</option>;
          })}
        </select>
        <span style={{ position: "absolute", right: 14, pointerEvents: "none", display: "inline-flex" }}>
          <Icon name="chevron-down" size="md" color="var(--text-muted)" />
        </span>
      </div>
      {hint ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{hint}</span> : null}
    </div>
  );
}
