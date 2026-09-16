export interface EvidenceBannerProps {
  /** fundamentada = resposta_fundamentada true; retida = groundedness reprovou; semEvidencia = evidencia_suficiente false. */
  estado?: "fundamentada" | "retida" | "semEvidencia";
  titulo?: string;
  /** Texto de `justificativa_groundedness`, quando houver. */
  justificativa?: string;
  style?: React.CSSProperties;
}
export function EvidenceBanner(props: EvidenceBannerProps): JSX.Element;
