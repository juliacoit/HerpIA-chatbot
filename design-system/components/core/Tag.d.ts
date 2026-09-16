export interface TagProps {
  children?: React.ReactNode;
  /** Mostra o "x" de remoção quando fornecido. */
  onRemove?: (e: React.MouseEvent) => void;
  selected?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  style?: React.CSSProperties;
}
export function Tag(props: TagProps): JSX.Element;
