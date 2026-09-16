const RESPOSTAS = {
  cerrado: {
    resposta: "As fichas recuperadas registram ocorrência no Cerrado para três espécies de anfíbios com status de ameaça: Bokermannohyla itapoty (Vulnerável), Physalaemus deimaticus (Em Perigo) e Proceratophrys moratoi (Criticamente em Perigo). As fichas indicam perda de habitat por conversão agrícola como principal pressão. Não há, nos trechos recuperados, uma lista completa de anfíbios ameaçados do bioma.",
    estado: "fundamentada",
    citacoes: [
      { index: 1, fonte: "salve", documento: "Ficha SALVE — Bokermannohyla itapoty", secao: "Distribuição geográfica", paginaInicio: 2, urlOrigem: "https://salve.icmbio.gov.br/" },
      { index: 2, fonte: "salve", documento: "Ficha SALVE — Proceratophrys moratoi", secao: "Ameaças", paginaInicio: 4, urlOrigem: "https://salve.icmbio.gov.br/" },
      { index: 3, fonte: "pans", documento: "PAN Herpetofauna do Cerrado — relatório de ciclo", paginaInicio: 31, paginaFim: 33 },
    ],
  },
  sei: {
    resposta: "A base de conhecimento ainda não tem documentos do SEI indexados (fonte de acesso restrito, pendente de exportação e autorização). Não é possível responder com base em processos, notas técnicas ou outros documentos do SEI.",
    estado: "retida",
    justificativa: "Verificação estrutural: a pergunta menciona SEI, mas nenhum trecho recuperado é da fonte 'sei' (ainda não indexada).",
    citacoes: [],
  },
  vazio: {
    resposta: "Não há evidência suficiente na base de conhecimento para responder a essa pergunta.",
    estado: "semEvidencia",
    citacoes: [],
  },
};

function ConsultaScreen({ fontes }) {
  const NS = window.HerpIADesignSystem_a5a8bd;
  const { ChatMessage, EvidenceBanner, CitationCard, FeedbackButtons, Textarea, Button, IconButton, Input, Select, Tabs, Badge, Dialog, Toast } = NS;
  const [turnos, setTurnos] = React.useState([{ pergunta: "Quais anfíbios ameaçados ocorrem no Cerrado?", ...RESPOSTAS.cerrado, hora: "14:32", avaliacao: null, tab: "resp" }]);
  const [texto, setTexto] = React.useState("");
  const [topK, setTopK] = React.useState("5");
  const [pendente, setPendente] = React.useState(false);
  const [comentarioAberto, setComentarioAberto] = React.useState(false);
  const [aviso, setAviso] = React.useState(null);
  const fim = React.useRef(null);

  const enviar = () => {
    const p = texto.trim();
    if (!p) return;
    const chave = /\bSEI\b/i.test(p) ? "sei" : /cerrado|anf[íi]bio|amea/i.test(p) ? "cerrado" : "vazio";
    setTexto("");
    setPendente(true);
    setTimeout(() => {
      setTurnos((t) => [...t, { pergunta: p, ...RESPOSTAS[chave], hora: "14:3" + (t.length + 4), avaliacao: null, tab: "resp" }]);
      setPendente(false);
    }, 650);
  };

  const avaliar = (i, v) => {
    setTurnos((t) => t.map((x, k) => (k === i ? { ...x, avaliacao: v } : x)));
    if (v === -1) setComentarioAberto(true); else setAviso("Feedback registrado. Obrigado.");
  };

  return (
    <div style={{ position: "relative", flex: 1, display: "flex", flexDirection: "column", minWidth: 0, background: "var(--surface-page)" }}>
      <TopBar titulo="Consulta" descricao="Respostas geradas apenas a partir dos trechos recuperados, sempre com as fontes."
        acoes={<><Select value={topK} onChange={(e) => setTopK(e.target.value)} options={[{value:"3",label:"top_k 3"},{value:"5",label:"top_k 5"},{value:"10",label:"top_k 10"}]} /><IconButton icon="history" label="Consultas recentes" /></>} />

      <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
        <div style={{ maxWidth: "var(--layout-content-max)", margin: "0 auto", display: "flex", flexDirection: "column", gap: 26 }}>
          {turnos.map((t, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <ChatMessage autor="usuario">{t.pergunta}</ChatMessage>
              <ChatMessage autor="assistente" hora={t.hora}>{t.resposta}</ChatMessage>
              <div style={{ paddingLeft: 40, display: "flex", flexDirection: "column", gap: 12 }}>
                <EvidenceBanner estado={t.estado} justificativa={t.justificativa} />
                {t.citacoes.length ? (
                  <>
                    <Tabs value={t.tab} onChange={(v) => setTurnos((ts) => ts.map((x, k) => (k === i ? { ...x, tab: v } : x)))}
                      tabs={[{ value: "resp", label: "Citações", count: t.citacoes.length }, { value: "meta", label: "Metadados" }]} />
                    {t.tab === "resp" ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>{t.citacoes.map((c) => <CitationCard key={c.index} {...c} />)}</div>
                    ) : (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-muted)" }}>
                        <Badge tone="neutral">top_k {topK}</Badge><Badge tone="neutral">fontes: {fontes.join(", ")}</Badge><Badge tone="neutral">qwen2.5-3b-instruct</Badge><Badge tone="neutral">1.842 ms</Badge>
                      </div>
                    )}
                  </>
                ) : null}
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <FeedbackButtons value={t.avaliacao} onChange={(v) => avaliar(i, v)} />
                  <Button variant="ghost" size="sm" iconLeft="copy">Copiar resposta</Button>
                </div>
              </div>
            </div>
          ))}
          {pendente ? (
            <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-muted)", fontSize: 14 }}>
              <NS.Icon name="loader" size="md" /> Recuperando trechos e gerando resposta…
            </div>
          ) : null}
          <div ref={fim} />
        </div>
      </div>

      <div style={{ borderTop: "1px solid var(--border-hairline)", background: "var(--white)", padding: "16px 28px" }}>
        <div style={{ maxWidth: "var(--layout-content-max)", margin: "0 auto", display: "flex", gap: 10, alignItems: "flex-end" }}>
          <Input style={{ flex: 1 }} value={texto} onChange={(e) => setTexto(e.target.value)} onKeyDown={(e) => e.key === "Enter" && enviar()}
            placeholder="Pergunte sobre répteis e anfíbios — ex.: quais anfíbios ameaçados ocorrem no Cerrado?" />
          <IconButton icon="arrow-up" label="Enviar pergunta" variant="primary" onClick={enviar} />
        </div>
        <p style={{ maxWidth: "var(--layout-content-max)", margin: "10px auto 0", fontSize: 12.5, color: "var(--text-subtle)" }}>
          O HerpIA responde apenas com base nos documentos indexados e informa quando não há evidência suficiente.
        </p>
      </div>

      {aviso ? <div style={{ position: "absolute", bottom: 110, right: 28 }}><Toast tone="sucesso" onClose={() => setAviso(null)}>{aviso}</Toast></div> : null}

      <Dialog open={comentarioAberto} title="O que faltou nesta resposta?" description="O comentário é opcional e fica registrado junto da avaliação."
        onClose={() => setComentarioAberto(false)}
        footer={<><Button variant="secondary" onClick={() => setComentarioAberto(false)}>Cancelar</Button><Button onClick={() => { setComentarioAberto(false); setAviso("Feedback registrado. Obrigado."); }}>Enviar feedback</Button></>}>
        <Textarea rows={4} placeholder="Ex.: a resposta citou o documento errado." hint="Máx. 2000 caracteres" />
      </Dialog>
    </div>
  );
}
Object.assign(window, { ConsultaScreen });
