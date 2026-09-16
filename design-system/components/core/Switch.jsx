import React from "react";

export function Switch({ label, checked, onChange, disabled, style }) {
  return (
    <label style={{ display: "inline-flex", gap: "var(--space-3)", alignItems: "center", fontFamily: "var(--font-body)", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.55 : 1, ...style }}>
      <span
        onClick={() => !disabled && onChange && onChange(!checked)}
        style={{
          width: 40, height: 22, flex: "0 0 auto", borderRadius: "var(--radius-pill)", padding: 2,
          background: checked ? "var(--action-primary)" : "var(--sand-300)", transition: "background-color var(--duration-medium) var(--ease-standard)",
          display: "inline-flex", alignItems: "center",
        }}
      >
        <span style={{
          width: 18, height: 18, borderRadius: "var(--radius-pill)", background: "var(--white)",
          boxShadow: "0 1px 2px rgba(27,25,23,0.2)", transform: checked ? "translateX(18px)" : "translateX(0)",
          transition: "transform var(--duration-medium) var(--ease-out)",
        }} />
      </span>
      {label ? <span style={{ fontSize: "var(--text-body-size)", color: "var(--text-body)" }}>{label}</span> : null}
    </label>
  );
}
