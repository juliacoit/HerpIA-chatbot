import React from "react";

export function Radio({ label, description, checked, onChange, name, value, disabled, style }) {
  return (
    <label style={{ display: "flex", gap: "var(--space-3)", alignItems: description ? "flex-start" : "center", fontFamily: "var(--font-body)", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.55 : 1, ...style }}>
      <span style={{
        width: 18, height: 18, flex: "0 0 auto", marginTop: description ? 2 : 0, borderRadius: "var(--radius-pill)",
        background: "var(--white)", border: `${checked ? "5px" : "1px"} solid ${checked ? "var(--action-primary)" : "var(--border-strong)"}`,
        transition: "var(--transition-control)",
      }} />
      <input type="radio" name={name} value={value} checked={!!checked} onChange={onChange} disabled={disabled} style={{ position: "absolute", opacity: 0, width: 0, height: 0 }} />
      <span>
        <span style={{ fontSize: "var(--text-body-size)", color: "var(--text-body)" }}>{label}</span>
        {description ? <span style={{ display: "block", fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{description}</span> : null}
      </span>
    </label>
  );
}
