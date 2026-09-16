import React from "react";
import { Icon } from "../core/Icon.jsx";
import { SourceChip } from "./SourceChip.jsx";

function paginas(inicio, fim) {
  if (inicio == null) return null;
  return fim != null && fim !== inicio ? `p. ${inicio}–${fim}` : `p. ${inicio}`;
}

export function CitationCard({ index, fonte, documento, secao, paginaInicio, paginaFim, urlOrigem, score, onClick, style }) {
  const [hover, setHover] = React.useState(false);
  const pg = paginas(paginaInicio, paginaFim);
  return (
    <div
      onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        display: "flex", gap: "var(--space-3)", padding: "var(--space-4)", background: "var(--surface-card)",
        border: `1px solid ${hover && onClick ? "var(--teal-200)" : "var(--border-hairline)"}`, borderRadius: "var(--radius-md)",
        boxShadow: hover && onClick ? "var(--shadow-card)" : "none", cursor: onClick ? "pointer" : "default",
        fontFamily: "var(--font-body)", transition: "var(--transition-control)", ...style,
      }}
    >
      {index != null ? (
        <span style={{
          flex: "0 0 auto", width: 22, height: 22, borderRadius: "var(--radius-pill)", background: "var(--surface-tinted)",
          color: "var(--teal-800)", display: "inline-flex", alignItems: "center", justifyContent: "center",
          fontSize: "11.5px", fontWeight: 700, fontFamily: "var(--font-mono)",
        }}>{index}</span>
      ) : null}
      <div style={{ minWidth: 0, flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
          <SourceChip fonte={fonte} size="sm" />
          {pg ? <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-mono-size)", color: "var(--text-muted)" }}>{pg}</span> : null}
          {score != null ? <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-mono-size)", color: "var(--text-subtle)" }}>score {score}</span> : null}
        </div>
        <span style={{ fontSize: "var(--text-small-size)", lineHeight: "var(--text-small-lh)", fontWeight: 600, color: "var(--text-body)", overflowWrap: "anywhere" }}>{documento}</span>
        {secao ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)" }}>{secao}</span> : null}
        {urlOrigem ? (
          <a href={urlOrigem} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}
            style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: "var(--text-caption-size)", color: "var(--text-link)", textDecoration: "none", overflowWrap: "anywhere" }}>
            <Icon name="external-link" size="sm" />Abrir fonte
          </a>
        ) : null}
      </div>
    </div>
  );
}
