import React from "react";
import { Icon } from "./Icon.jsx";

export function Tag({ children, onRemove, selected, onClick, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const interactive = !!onClick;
  return (
    <span
      onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, height: 26, padding: onRemove ? "0 6px 0 12px" : "0 12px",
        borderRadius: "var(--radius-pill)", fontFamily: "var(--font-body)", fontSize: "var(--text-small-size)",
        background: selected ? "var(--teal-800)" : hover && interactive ? "var(--surface-tinted)" : "var(--white)",
        color: selected ? "var(--white)" : "var(--text-body)",
        border: `1px solid ${selected ? "var(--teal-800)" : "var(--border-strong)"}`,
        cursor: interactive ? "pointer" : "default", transition: "var(--transition-control)", ...style,
      }}
      {...rest}
    >
      {children}
      {onRemove ? (
        <button type="button" onClick={(e) => { e.stopPropagation(); onRemove(e); }} aria-label="Remover"
          style={{ display: "inline-flex", border: "none", background: "transparent", padding: 2, cursor: "pointer", color: "inherit" }}>
          <Icon name="x" size="sm" />
        </button>
      ) : null}
    </span>
  );
}
