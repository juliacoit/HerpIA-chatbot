import React from "react";
import { Icon } from "./Icon.jsx";
import { IconButton } from "./IconButton.jsx";

const TONES = {
  info: { icon: "info", fg: "var(--state-info-fg)", bg: "var(--state-info-bg)" },
  sucesso: { icon: "check", fg: "var(--state-fundamentada-fg)", bg: "var(--state-fundamentada-bg)" },
  alerta: { icon: "triangle-alert", fg: "var(--state-retida-fg)", bg: "var(--state-retida-bg)" },
  erro: { icon: "circle-x", fg: "var(--state-sem-evidencia-fg)", bg: "var(--state-sem-evidencia-bg)" },
};

export function Toast({ children, tone = "info", onClose, style }) {
  const t = TONES[tone] || TONES.info;
  return (
    <div role="status" style={{
      display: "flex", alignItems: "flex-start", gap: "var(--space-3)", maxWidth: 420, padding: "12px 12px 12px 14px",
      background: "var(--surface-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-hairline)",
      boxShadow: "var(--shadow-raised)", fontFamily: "var(--font-body)", fontSize: "var(--text-small-size)",
      lineHeight: "var(--text-small-lh)", color: "var(--text-body)", ...style,
    }}>
      <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, borderRadius: "var(--radius-pill)", background: t.bg, color: t.fg, flex: "0 0 auto" }}>
        <Icon name={t.icon} size="md" />
      </span>
      <span style={{ flex: 1, paddingTop: 2 }}>{children}</span>
      {onClose ? <IconButton icon="x" label="Fechar aviso" size="sm" variant="ghost" onClick={onClose} /> : null}
    </div>
  );
}
