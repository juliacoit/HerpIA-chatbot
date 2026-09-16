/**
 * Identificador visual da fonte de dados de um trecho ou citação.
 */
export interface SourceChipProps {
  /** Chave da fonte tal como vem da API (campo `fonte`). */
  fonte: "monitora" | "pans" | "salve" | "sei" | "publicacoes" | string;
  size?: "sm" | "md";
  showIcon?: boolean;
  style?: React.CSSProperties;
}
export function SourceChip(props: SourceChipProps): JSX.Element;
export const FONTES: Record<string, { label: string; color: string; icon: string }>;
