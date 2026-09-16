Assinatura oficial do RAN (ICMBio/MMA) — usar em cabeçalhos, capas, slides e rodapés de documento. Renderiza `assets/ran-logo.png` (o SVG disponível é um traçado monocromático e não serve).

```jsx
<Logo altura={72} />
<Logo altura={56} moldura />   {/* sobre foto ou fundo escuro */}
```

Nunca recolorir, distorcer, inclinar ou aplicar transparência; nunca usar a tipografia sem o símbolo. Em fundo escuro ou imagem, use `moldura`. Para espaços muito pequenos (cabeçalho compacto, favicon) use `Wordmark`.
