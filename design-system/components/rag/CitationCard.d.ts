export interface CitationCardProps {
  /** Número da citação exibido na resposta (1, 2, 3…). */
  index?: number;
  fonte: string;
  /** Nome do documento (campo `documento`). */
  documento: string;
  secao?: string | null;
  paginaInicio?: number | null;
  paginaFim?: number | null;
  urlOrigem?: string | null;
  /** Similaridade do trecho, quando exibida (visão /buscar). */
  score?: number | string;
  onClick?: (e: React.MouseEvent) => void;
  style?: React.CSSProperties;
}
export function CitationCard(props: CitationCardProps): JSX.Element;
