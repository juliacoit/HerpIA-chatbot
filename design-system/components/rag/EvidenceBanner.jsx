import React from "react";
import { Icon } from "../core/Icon.jsx";

const ESTADOS = {
  fundamentada: { icon: "shield-check", fg: "var(--state-fundamentada-fg)", bg: "var(--state-fundamentada-bg)", titulo: "Resposta fundamentada nos trechos recuperados" },
  retida: { icon: "shield-alert", fg: "var(--state-retida-fg)", bg: "var(--state-retida-bg)", titulo: "Resposta retida pela verificação de fundamentação" },
  semEvidencia: { icon: "search-x", fg: "var(--state-sem-evidencia-fg)", bg: "var(--state-sem-evidencia-bg)", titulo: "Não há evidência suficiente na base de conhecimento" },
};

export function EvidenceBanner({ estado = "fundamentada", titulo, justificativa, style }) {
  const e = ESTADOS[estado] || ESTADOS.fundamentada;
  return (
    <div style={{
      display: "flex", gap: "var(--space-3)", padding: "var(--space-4)", background: e.bg,
      borderRadius: "var(--radius-md)", fontFamily: "var(--font-body)", ...style,
    }}>
      <span style={{ color: e.fg, display: "inline-flex", flex: "0 0 auto", paddingTop: 1 }}><Icon name={e.icon} size="lg" /></span>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: "var(--text-small-size)", lineHeight: "var(--text-small-lh)", fontWeight: 600, color: e.fg }}>{titulo || e.titulo}</div>
        {justificativa ? <p style={{ margin: "6px 0 0", fontSize: "var(--text-caption-size)", lineHeight: 1.55, color: "var(--text-body)", maxWidth: "62ch" }}>{justificativa}</p> : null}
      </div>
    </div>
  );
}
