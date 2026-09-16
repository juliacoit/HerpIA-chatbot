export interface ChunkResultCardProps {
  /** Score de similaridade formatado, ex.: "0,62". */
  score?: number | string;
  fonte: string;
  documento: string;
  secao?: string | null;
  texto?: string;
  paginaInicio?: number | null;
  paginaFim?: number | null;
  nivelSensibilidade?: string | null;
  style?: React.CSSProperties;
}
export function ChunkResultCard(props: ChunkResultCardProps): JSX.Element;
