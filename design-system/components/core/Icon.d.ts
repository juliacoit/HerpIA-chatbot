export interface IconProps {
  /** Nome do ícone Lucide em kebab-case, ex.: "search", "thumbs-up". */
  name: string;
  size?: "sm" | "md" | "lg" | "xl" | number;
  color?: string;
  strokeWidth?: number;
  style?: React.CSSProperties;
}
export function Icon(props: IconProps): JSX.Element;
