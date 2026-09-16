import React from "react";

const TONES = {
  plain: { background: "var(--surface-card)", border: "1px solid var(--border-hairline)" },
  tinted: { background: "var(--surface-tinted)", border: "1px solid var(--teal-100)" },
  sunken: { background: "var(--surface-sunken)", border: "1px solid var(--border-hairline)" },
};

export function Card({ children, title, meta, tone = "plain", raised, padding = "var(--space-5)", onClick, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        fontFamily: "var(--font-body)", borderRadius: "var(--radius-md)", padding,
        boxShadow: raised ? "var(--shadow-raised)" : "var(--shadow-card)",
        transition: "box-shadow var(--duration-medium) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)",
        cursor: onClick ? "pointer" : "default",
        ...TONES[tone],
        ...(onClick && hover ? { boxShadow: "var(--shadow-raised)", borderColor: "var(--teal-200)" } : null),
        ...style,
      }}
      {...rest}
    >
      {title || meta ? (
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--space-4)", marginBottom: "var(--space-3)" }}>
          {title ? <h3 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "var(--text-h3-size)", lineHeight: "var(--text-h3-lh)", fontWeight: 600, color: "var(--text-title)" }}>{title}</h3> : null}
          {meta ? <span style={{ fontSize: "var(--text-caption-size)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>{meta}</span> : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}
