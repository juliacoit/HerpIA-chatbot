export interface SelectOption { value: string; label: string }
export interface SelectProps {
  label?: string;
  hint?: string;
  options?: Array<SelectOption | string>;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  disabled?: boolean;
  id?: string;
  style?: React.CSSProperties;
}
export function Select(props: SelectProps): JSX.Element;
