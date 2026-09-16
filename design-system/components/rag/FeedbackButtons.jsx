import React from "react";
import { Icon } from "../core/Icon.jsx";

export function FeedbackButtons({ value, onChange, label = "Esta resposta foi útil?", style }) {
  const [hover, setHover] = React.useState(null);
  const opcoes = [
    { v: 1, icon: "thumbs-up", label: "Resposta útil" },
    { v: -1, icon: "thumbs-down", label: "Resposta não útil" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", fontFamily: "var(--font-body)", ...style }}>
      {label ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{label}</span> : null}
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        {opcoes.map((o) => {
          const ativo = value === o.v;
          const positivo = o.v === 1;
          return (
            <button key={o.v} type="button" aria-label={o.label} title={o.label} aria-pressed={ativo}
              onClick={() => onChange && onChange(o.v)}
              onMouseEnter={() => setHover(o.v)} onMouseLeave={() => setHover(null)}
              style={{
                width: 30, height: 30, display: "inline-flex", alignItems: "center", justifyContent: "center",
                borderRadius: "var(--radius-pill)", cursor: "pointer", transition: "var(--transition-control)",
                background: ativo ? (positivo ? "var(--state-fundamentada-bg)" : "var(--state-sem-evidencia-bg)") : hover === o.v ? "var(--surface-sunken)" : "transparent",
                color: ativo ? (positivo ? "var(--state-fundamentada-fg)" : "var(--state-sem-evidencia-fg)") : "var(--text-muted)",
                border: `1px solid ${ativo ? "transparent" : "var(--border-hairline)"}`,
              }}>
              <Icon name={o.icon} size="md" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
