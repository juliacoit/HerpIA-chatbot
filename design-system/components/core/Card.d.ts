export interface CardProps {
  children?: React.ReactNode;
  /** Título em Spectral, renderizado como h3. */
  title?: React.ReactNode;
  /** Metadado curto alinhado à direita do título (data, contagem). */
  meta?: React.ReactNode;
  tone?: "plain" | "tinted" | "sunken";
  raised?: boolean;
  padding?: string;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
  style?: React.CSSProperties;
}
export function Card(props: CardProps): JSX.Element;
