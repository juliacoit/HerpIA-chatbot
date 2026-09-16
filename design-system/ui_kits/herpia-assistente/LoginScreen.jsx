function LoginScreen({ onEntrar }) {
  const { Logo, Button, Input, Toast } = window.HerpIADesignSystem_a5a8bd;
  const [usuario, setUsuario] = React.useState("");
  return (
    <div style={{ height: "100%", display: "grid", placeItems: "center", background: "var(--surface-page)", padding: 24 }}>
      <div style={{ width: 420, display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Logo altura={150} reserva={false} />
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "var(--text-muted)", maxWidth: "42ch" }}>
            Assistente interno para consulta de informações sobre a herpetofauna brasileira. Acesso restrito a técnicos, gestores e pesquisadores vinculados ao RAN.
          </p>
        </div>
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-hairline)", borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-card)", padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          <Input label="Usuário institucional" iconLeft="user" placeholder="nome.sobrenome" value={usuario} onChange={(e) => setUsuario(e.target.value)} />
          <Input label="Senha" type="password" iconLeft="lock" placeholder="••••••••" />
          <Button fullWidth iconLeft="log-in" onClick={onEntrar}>Entrar</Button>
        </div>
        <Toast tone="info">Autenticação de usuários ainda não implementada no backend — esta tela é ilustrativa.</Toast>
      </div>
    </div>
  );
}
Object.assign(window, { LoginScreen });
