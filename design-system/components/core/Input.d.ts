export interface InputProps {
  label?: string;
  hint?: string;
  error?: string;
  /** Nome do ícone Lucide dentro do campo, à esquerda. */
  iconLeft?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
  type?: string;
  style?: React.CSSProperties;
}
export function Input(props: InputProps): JSX.Element;
