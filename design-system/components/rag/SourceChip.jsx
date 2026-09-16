import React from "react";
import { Icon } from "../core/Icon.jsx";

/* As cinco fontes de dados do HerpIA (CLAUDE.md, "Fontes de dados"). */
export const FONTES = {
  monitora: { label: "Monitora", color: "var(--fonte-monitora)", icon: "activity" },
  pans: { label: "PANs", color: "var(--fonte-pans)", icon: "clipboard-list" },
  salve: { label: "SALVE", color: "var(--fonte-salve)", icon: "leaf" },
  sei: { label: "SEI", color: "var(--fonte-sei)", icon: "folder-lock" },
  publicacoes: { label: "Publicações", color: "var(--fonte-publicacoes)", icon: "book-open" },
};

export function SourceChip({ fonte, size = "md", showIcon = true, style, ...rest }) {
  const f = FONTES[fonte] || { label: fonte, color: "var(--sand-600)", icon: "file-text" };
  const sm = size === "sm";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, height: sm ? 20 : 24, padding: sm ? "0 8px" : "0 10px",
      borderRadius: "var(--radius-pill)", background: "var(--white)", border: `1px solid ${f.color}`, color: f.color,
      fontFamily: "var(--font-body)", fontSize: sm ? "11.5px" : "var(--text-caption-size)", fontWeight: 600,
      letterSpacing: "0.01em", whiteSpace: "nowrap", ...style,
    }} {...rest}>
      {showIcon ? <Icon name={f.icon} size="sm" /> : null}{f.label}
    </span>
  );
}
