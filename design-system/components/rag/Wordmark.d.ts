/**
 * Marca tipográfica do HerpIA — não existe logo no repositório de origem.
 */
export interface WordmarkProps {
  size?: "sm" | "md" | "lg" | number;
  /** Qualificador institucional; passe null para omitir. */
  subtitulo?: string | null;
  color?: string;
  style?: React.CSSProperties;
}
export function Wordmark(props: WordmarkProps): JSX.Element;
