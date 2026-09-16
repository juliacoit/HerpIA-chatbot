import React from "react";
import { IconButton } from "./IconButton.jsx";

export function Dialog({ open, title, description, children, footer, onClose, width = 520 }) {
  if (!open) return null;
  return (
    <div role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : undefined}
      style={{ position: "absolute", inset: 0, zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center", padding: "var(--space-6)", background: "var(--overlay-scrim)", backdropFilter: "var(--blur-overlay)" }}>
      <div style={{ width: "100%", maxWidth: width, background: "var(--surface-card)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-overlay)", padding: "var(--space-6)", fontFamily: "var(--font-body)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
          <div>
            <h2 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "var(--text-h2-size)", lineHeight: "var(--text-h2-lh)", fontWeight: 600, color: "var(--text-title)" }}>{title}</h2>
            {description ? <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--text-small-size)", lineHeight: "var(--text-small-lh)", color: "var(--text-muted)" }}>{description}</p> : null}
          </div>
          {onClose ? <IconButton icon="x" label="Fechar" size="sm" variant="ghost" onClick={onClose} /> : null}
        </div>
        {children ? <div style={{ marginTop: "var(--space-5)" }}>{children}</div> : null}
        {footer ? <div style={{ marginTop: "var(--space-6)", display: "flex", justifyContent: "flex-end", gap: "var(--space-3)" }}>{footer}</div> : null}
      </div>
    </div>
  );
}
