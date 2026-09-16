const CHUNKS = [
  { score: "0,6214", fonte: "salve", documento: "Ficha SALVE — Bokermannohyla itapoty", secao: "Distribuição geográfica", paginaInicio: 2, nivelSensibilidade: "público", texto: "Espécie registrada em áreas de campo rupestre e cerrado sensu stricto no sudeste de Minas Gerais, com registros pontuais associados a córregos de cabeceira." },
  { score: "0,5981", fonte: "salve", documento: "Ficha SALVE — Proceratophrys moratoi", secao: "Ameaças", paginaInicio: 4, nivelSensibilidade: "público", texto: "A conversão de áreas de cerrado para agricultura intensiva e a drenagem de veredas são apontadas como as principais pressões sobre as populações conhecidas." },
  { score: "0,5477", fonte: "pans", documento: "PAN Herpetofauna do Cerrado — relatório de ciclo", paginaInicio: 31, paginaFim: 33, nivelSensibilidade: "público", texto: "As ações do plano priorizam o monitoramento de anfíbios em unidades de conservação federais, com metas de amostragem no período chuvoso." },
  { score: "0,5102", fonte: "monitora", documento: "Relatório Programa Monitora — componente terrestre", paginaInicio: 12, nivelSensibilidade: "público", texto: "O protocolo de transecções em poças temporárias foi aplicado em doze unidades amostrais, com esforço padronizado de quatro noites por campanha." },
];

function BuscaScreen({ fontes }) {
  const NS = window.HerpIADesignSystem_a5a8bd;
  const { ChunkResultCard, Input, Select, Button, Tag, Badge, Toast } = NS;
  const [q, setQ] = React.useState("anfíbios ameaçados Cerrado");
  const [topK, setTopK] = React.useState("5");
  const visiveis = CHUNKS.filter((c) => fontes.includes(c.fonte)).slice(0, Number(topK));
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, background: "var(--surface-page)" }}>
      <TopBar titulo="Busca nos trechos" descricao="Visão de depuração: mostra os trechos recuperados e seus scores, sem geração de resposta."
        acoes={<Badge tone="info" icon="bug">endpoint /buscar</Badge>} />
      <div style={{ padding: "20px 28px", borderBottom: "1px solid var(--border-hairline)", background: "var(--white)" }}>
        <div style={{ maxWidth: 980, display: "flex", gap: 10, alignItems: "flex-end" }}>
          <Input style={{ flex: 1 }} iconLeft="search" value={q} onChange={(e) => setQ(e.target.value)} label="Pergunta" />
          <Select label="top_k" options={["3", "5", "10", "20"]} value={topK} onChange={(e) => setTopK(e.target.value)} style={{ width: 130 }} />
          <Button iconLeft="corner-down-right">Buscar</Button>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 14, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>Filtro aplicado:</span>
          {fontes.map((k) => <Tag key={k} selected>{k}</Tag>)}
        </div>
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: "22px 28px" }}>
        <div style={{ maxWidth: 980, display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13.5, color: "var(--text-muted)" }}>{visiveis.length} trecho(s) recuperado(s)</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-subtle)" }}>modelo de embeddings local</span>
          </div>
          {visiveis.map((c, i) => <ChunkResultCard key={i} {...c} />)}
          {!visiveis.length ? <Toast tone="alerta">Nenhuma fonte selecionada na barra lateral — a busca não retorna trechos.</Toast> : null}
        </div>
      </div>
    </div>
  );
}
Object.assign(window, { BuscaScreen });
