import React from "react";

export function Tooltip({ children, content, placement = "top", style }) {
  const [open, setOpen] = React.useState(false);
  const pos = placement === "bottom"
    ? { top: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" }
    : { bottom: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" };
  return (
    <span style={{ position: "relative", display: "inline-flex", ...style }}
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
      {children}
      {open ? (
        <span role="tooltip" style={{
          position: "absolute", ...pos, zIndex: 40, maxWidth: 260, padding: "7px 10px",
          background: "var(--surface-inverse)", color: "var(--text-inverse)", borderRadius: "var(--radius-sm)",
          fontFamily: "var(--font-body)", fontSize: "var(--text-caption-size)", lineHeight: "var(--text-caption-lh)",
          boxShadow: "var(--shadow-overlay)", pointerEvents: "none",
        }}>{content}</span>
      ) : null}
    </span>
  );
}
