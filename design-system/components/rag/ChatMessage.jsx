import React from "react";
import { Icon } from "../core/Icon.jsx";

export function ChatMessage({ autor = "assistente", children, hora, style }) {
  const usuario = autor === "usuario";
  if (usuario) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", fontFamily: "var(--font-body)", ...style }}>
        <div style={{
          maxWidth: "min(56ch, 82%)", padding: "12px 16px", background: "var(--surface-tinted)",
          border: "1px solid var(--teal-100)", borderRadius: "var(--radius-md) var(--radius-md) var(--radius-xs) var(--radius-md)",
          fontSize: "var(--text-body-size)", lineHeight: "var(--text-body-lh)", color: "var(--text-body)",
        }}>{children}</div>
      </div>
    );
  }
  return (
    <div style={{ display: "flex", gap: "var(--space-3)", fontFamily: "var(--font-body)", ...style }}>
      <span style={{
        flex: "0 0 auto", width: 28, height: 28, borderRadius: "var(--radius-pill)", background: "var(--teal-900)",
        color: "var(--white)", display: "inline-flex", alignItems: "center", justifyContent: "center",
      }}><Icon name="sparkles" size="md" /></span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-2)", marginBottom: 6 }}>
          <span style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-h3-size)", fontWeight: 600, color: "var(--text-title)" }}>HerpIA</span>
          {hora ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-subtle)" }}>{hora}</span> : null}
        </div>
        <div style={{ maxWidth: "var(--measure-answer)", fontSize: "var(--text-answer-size)", lineHeight: "var(--text-answer-lh)", color: "var(--text-body)", textWrap: "pretty" }}>{children}</div>
      </div>
    </div>
  );
}
