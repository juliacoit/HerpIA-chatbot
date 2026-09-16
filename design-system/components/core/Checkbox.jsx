import React from "react";
import { Icon } from "./Icon.jsx";

export function Checkbox({ label, description, checked, onChange, disabled, style }) {
  return (
    <label style={{ display: "flex", gap: "var(--space-3)", alignItems: description ? "flex-start" : "center", fontFamily: "var(--font-body)", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.55 : 1, ...style }}>
      <span style={{
        width: 18, height: 18, flex: "0 0 auto", marginTop: description ? 2 : 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
        borderRadius: "var(--radius-xs)", background: checked ? "var(--action-primary)" : "var(--white)",
        border: `1px solid ${checked ? "var(--action-primary)" : "var(--border-strong)"}`, transition: "var(--transition-control)",
      }}>
        {checked ? <Icon name="check" size="sm" color="var(--white)" strokeWidth={2.5} /> : null}
      </span>
      <input type="checkbox" checked={!!checked} onChange={onChange} disabled={disabled} style={{ position: "absolute", opacity: 0, width: 0, height: 0 }} />
      <span>
        <span style={{ fontSize: "var(--text-body-size)", color: "var(--text-body)" }}>{label}</span>
        {description ? <span style={{ display: "block", fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{description}</span> : null}
      </span>
    </label>
  );
}
