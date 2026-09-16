import React from "react";

export function Textarea({ label, hint, value, onChange, placeholder, rows = 3, disabled, id, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const taId = id || React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", fontFamily: "var(--font-body)", ...style }}>
      {label ? <label htmlFor={taId} style={{ fontSize: "var(--text-small-size)", fontWeight: 600, color: "var(--text-body)" }}>{label}</label> : null}
      <textarea
        id={taId} rows={rows} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled}
        onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
        style={{
          resize: "vertical", padding: "12px 14px", fontFamily: "var(--font-body)", fontSize: "var(--text-body-size)",
          lineHeight: "var(--text-body-lh)", color: "var(--text-body)", background: disabled ? "var(--surface-sunken)" : "var(--white)",
          border: `1px solid ${focus ? "var(--border-focus)" : "var(--border-hairline)"}`, borderRadius: "var(--radius-md)",
          boxShadow: focus ? "var(--focus-ring)" : "none", outline: "none", transition: "var(--transition-control)",
        }}
        {...rest}
      />
      {hint ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{hint}</span> : null}
    </div>
  );
}
