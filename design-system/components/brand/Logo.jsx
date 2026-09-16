import React from "react";

/* Assinatura oficial do RAN (assets/ran-logo.png — verde #4B7936 e azul #2F7FB7).
   assets/ran-logo.svg é um traçado monocromático (perdeu as cores da marca) e por isso
   NÃO é usado aqui; substitua ambos pelo vetor original colorido quando houver.
   Regras portadas do Manual de Identidade Visual do ICMBio:
   - área de reserva em volta da marca (p. 11) — nunca encoste conteúdo nela;
   - moldura branca quando o fundo não contrasta ou é imagem (p. 12 e 19);
   - não alterar proporções, cores, inclinação ou aplicar transparência (p. 20). */
export function Logo({ altura = 72, moldura = false, reserva = true, href, alt = "RAN — ICMBio/MMA", style, ...rest }) {
  const img = (
    <img src={new URL("../../assets/ran-logo.png", document.baseURI).href} alt={alt}
      style={{ height: altura, width: "auto", display: "block" }} />
  );
  const conteudo = moldura ? (
    <span style={{ display: "inline-flex", background: "var(--white)", padding: Math.round(altura * 0.08), borderRadius: 2 }}>{img}</span>
  ) : img;
  const wrapper = (
    <span style={{ display: "inline-flex", padding: reserva ? "var(--marca-reserva)" : 0, ...style }} {...rest}>{conteudo}</span>
  );
  return href ? <a href={href} style={{ display: "inline-flex" }}>{wrapper}</a> : wrapper;
}
