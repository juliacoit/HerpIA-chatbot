import React from "react";

const SIZES = { sm: 14, md: 16, lg: 20, xl: 24 };

/* Ícones: Lucide (CDN UMD). O repositório de origem não tem nenhum asset de
   ícone, então Lucide é uma SUBSTITUIÇÃO documentada em readme.md. */
export function Icon({ name, size = "md", color = "currentColor", strokeWidth = 1.75, style, ...rest }) {
  const ref = React.useRef(null);
  const px = SIZES[size] || size;
  React.useEffect(() => {
    const draw = () => {
      const el = ref.current;
      if (!el || !window.lucide) return;
      el.innerHTML = "";
      const i = document.createElement("i");
      i.setAttribute("data-lucide", name);
      el.appendChild(i);
      window.lucide.createIcons({ attrs: { width: px, height: px, "stroke-width": strokeWidth }, nameAttr: "data-lucide" });
    };
    draw();
    if (!window.lucide) {
      const t = setInterval(() => { if (window.lucide) { draw(); clearInterval(t); } }, 60);
      return () => clearInterval(t);
    }
  }, [name, px, strokeWidth]);
  return <span ref={ref} aria-hidden="true" style={{ display: "inline-flex", width: px, height: px, color, flex: "0 0 auto", ...style }} {...rest} />;
}
