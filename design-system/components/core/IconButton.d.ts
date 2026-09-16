export interface IconButtonProps {
  /** Nome do ícone Lucide. */
  icon: string;
  /** Rótulo acessível obrigatório (aria-label + title). */
  label: string;
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "secondary" | "ghost";
  disabled?: boolean;
  active?: boolean;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  style?: React.CSSProperties;
}
export function IconButton(props: IconButtonProps): JSX.Element;
