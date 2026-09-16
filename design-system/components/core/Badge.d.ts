export interface BadgeProps {
  children?: React.ReactNode;
  /** Estados do RAG: fundamentada / retida / semEvidencia; mais neutral e info. */
  tone?: "neutral" | "fundamentada" | "retida" | "semEvidencia" | "info";
  icon?: string;
  style?: React.CSSProperties;
}
export function Badge(props: BadgeProps): JSX.Element;
