export interface TextareaProps {
  label?: string;
  hint?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  rows?: number;
  disabled?: boolean;
  id?: string;
  style?: React.CSSProperties;
}
export function Textarea(props: TextareaProps): JSX.Element;
