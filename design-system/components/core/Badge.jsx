import React from "react";
import { Icon } from "./Icon.jsx";

const TONES = {
  neutral: { bg: "var(--sand-100)", fg: "var(--sand-800)" },
  fundamentada: { bg: "var(--state-fundamentada-bg)", fg: "var(--state-fundamentada-fg)" },
  retida: { bg: "var(--state-retida-bg)", fg: "var(--state-retida-fg)" },
  semEvidencia: { bg: "var(--state-sem-evidencia-bg)", fg: "var(--state-sem-evidencia-fg)" },
  info: { bg: "var(--state-info-bg)", fg: "var(--state-info-fg)" },
};

export function Badge({ children, tone = "neutral", icon, style, ...rest }) {
  const t = TONES[tone] || TONES.neutral;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6, height: 22, padding: "0 10px",
      background: t.bg, color: t.fg, borderRadius: "var(--radius-pill)", fontFamily: "var(--font-body)",
      fontSize: "var(--text-caption-size)", fontWeight: 600, whiteSpace: "nowrap", ...style,
    }} {...rest}>
      {icon ? <Icon name={icon} size="sm" /> : null}{children}
    </span>
  );
}
