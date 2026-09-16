import React from "react";
import { Icon } from "./Icon.jsx";

export function Tabs({ tabs = [], value, onChange, style }) {
  const [hover, setHover] = React.useState(null);
  return (
    <div role="tablist" style={{ display: "flex", gap: "var(--space-1)", borderBottom: "1px solid var(--border-hairline)", fontFamily: "var(--font-body)", ...style }}>
      {tabs.map((t) => {
        const tab = typeof t === "string" ? { value: t, label: t } : t;
        const active = tab.value === value;
        return (
          <button key={tab.value} role="tab" aria-selected={active} onClick={() => onChange && onChange(tab.value)}
            onMouseEnter={() => setHover(tab.value)} onMouseLeave={() => setHover(null)}
            style={{
              display: "inline-flex", alignItems: "center", gap: "var(--space-2)", padding: "10px 14px",
              background: "transparent", border: "none", borderBottom: `2px solid ${active ? "var(--teal-800)" : "transparent"}`,
              marginBottom: -1, fontFamily: "var(--font-body)", fontSize: "var(--text-small-size)", fontWeight: active ? 600 : 500,
              color: active ? "var(--teal-900)" : hover === tab.value ? "var(--text-body)" : "var(--text-muted)",
              cursor: "pointer", transition: "var(--transition-control)",
            }}>
            {tab.icon ? <Icon name={tab.icon} size="md" /> : null}
            {tab.label}
            {tab.count != null ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-subtle)" }}>{tab.count}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
