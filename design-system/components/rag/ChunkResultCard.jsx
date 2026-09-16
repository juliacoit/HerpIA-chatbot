import React from "react";
import { SourceChip } from "./SourceChip.jsx";

export function ChunkResultCard({ score, fonte, documento, secao, texto, paginaInicio, paginaFim, nivelSensibilidade, style }) {
  const pg = paginaInicio == null ? null : paginaFim != null && paginaFim !== paginaInicio ? `p. ${paginaInicio}–${paginaFim}` : `p. ${paginaInicio}`;
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: "var(--space-3)", padding: "var(--space-4)",
      background: "var(--surface-card)", border: "1px solid var(--border-hairline)", borderRadius: "var(--radius-md)",
      fontFamily: "var(--font-body)", ...style,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
        {score != null ? (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-mono-size)", fontWeight: 500, color: "var(--teal-800)", background: "var(--surface-tinted)", padding: "2px 8px", borderRadius: "var(--radius-pill)" }}>{score}</span>
        ) : null}
        <SourceChip fonte={fonte} size="sm" />
        {pg ? <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-mono-size)", color: "var(--text-muted)" }}>{pg}</span> : null}
        {nivelSensibilidade ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>sensibilidade: {nivelSensibilidade}</span> : null}
      </div>
      <div>
        <div style={{ fontSize: "var(--text-small-size)", fontWeight: 600, color: "var(--text-body)", overflowWrap: "anywhere" }}>{documento}</div>
        {secao ? <div style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{secao}</div> : null}
      </div>
      <p style={{ margin: 0, fontSize: "var(--text-small-size)", lineHeight: 1.6, color: "var(--text-body)", maxWidth: "var(--measure-prose)", textWrap: "pretty" }}>{texto}</p>
    </div>
  );
}
