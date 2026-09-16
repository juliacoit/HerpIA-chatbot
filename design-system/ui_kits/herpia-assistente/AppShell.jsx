function Sidebar({ tela, onTela, fontes, onFonte }) {
  const { Logo, Icon, Checkbox, SourceChip, Badge } = window.HerpIADesignSystem_a5a8bd;
  const item = (id, icon, label) => {
    const ativo = tela === id;
    return (
      <button key={id} type="button" onClick={() => onTela(id)}
        style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "9px 12px", borderRadius: "var(--radius-pill)", border: "1px solid transparent",
          background: ativo ? "var(--surface-tinted)" : "transparent", color: ativo ? "var(--teal-900)" : "var(--text-body)",
          fontFamily: "var(--font-body)", fontSize: 14.5, fontWeight: ativo ? 600 : 500, cursor: "pointer", textAlign: "left", transition: "var(--transition-control)" }}>
        <Icon name={icon} size="lg" color={ativo ? "var(--teal-800)" : "var(--text-muted)"} />{label}
      </button>
    );
  };
  return (
    <aside style={{ width: "var(--layout-sidebar)", flex: "0 0 auto", borderRight: "1px solid var(--border-hairline)", background: "var(--white)", padding: "20px 16px", display: "flex", flexDirection: "column", gap: 22, overflow: "auto" }}>
      <Logo altura={84} reserva={false} />
      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {item("consulta", "message-square", "Consulta")}
        {item("busca", "search", "Busca nos trechos")}
      </nav>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <span style={{ fontSize: 11.5, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-subtle)" }}>Fontes da base</span>
        {["monitora", "pans", "salve"].map((k) => (
          <Checkbox key={k} checked={fontes.includes(k)} onChange={() => onFonte(k)} label={<SourceChip fonte={k} size="sm" />} />
        ))}
        <Checkbox disabled label={<SourceChip fonte="sei" size="sm" />} description="Não indexado — acesso restrito" />
      </div>
      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
        <Badge tone="info" icon="database">59.080 trechos indexados</Badge>
        <span style={{ fontSize: 12.5, color: "var(--text-subtle)" }}>Base atualizada semestralmente</span>
      </div>
    </aside>
  );
}

function TopBar({ titulo, descricao, acoes }) {
  return (
    <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 20, padding: "18px 28px", borderBottom: "1px solid var(--border-hairline)", background: "var(--white)" }}>
      <div>
        <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "var(--text-h2-size)", lineHeight: "var(--text-h2-lh)", fontWeight: 600, color: "var(--text-title)" }}>{titulo}</h1>
        {descricao ? <p style={{ margin: "4px 0 0", fontSize: 13.5, color: "var(--text-muted)" }}>{descricao}</p> : null}
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>{acoes}</div>
    </header>
  );
}
Object.assign(window, { Sidebar, TopBar });
