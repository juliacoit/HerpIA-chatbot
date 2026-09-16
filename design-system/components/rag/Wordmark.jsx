import React from "react";

/* O repositório de origem não contém logo nem marca do RAN/ICMBio.
   Por decisão explícita, nada é desenhado: a marca é o nome em tipografia. */
export function Wordmark({ size = "md", subtitulo = "RAN/ICMBio", color = "var(--teal-900)", style }) {
  const fs = { sm: 18, md: 24, lg: 34 }[size] || size;
  return (
    <span style={{ display: "inline-flex", alignItems: "baseline", gap: 10, ...style }}>
      <span style={{ fontFamily: "var(--font-display)", fontSize: fs, fontWeight: 600, letterSpacing: "-0.01em", color, lineHeight: 1 }}>HerpIA</span>
      {subtitulo ? (
        <span style={{ fontFamily: "var(--font-body)", fontSize: Math.max(10, Math.round(fs * 0.42)), fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)", lineHeight: 1 }}>{subtitulo}</span>
      ) : null}
    </span>
  );
}
