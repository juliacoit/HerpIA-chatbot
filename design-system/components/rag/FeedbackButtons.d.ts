export interface FeedbackButtonsProps {
  /** 1 = positivo, -1 = negativo, null = sem avaliação (campo `avaliacao`). */
  value?: 1 | -1 | null;
  onChange?: (avaliacao: 1 | -1) => void;
  label?: string;
  style?: React.CSSProperties;
}
export function FeedbackButtons(props: FeedbackButtonsProps): JSX.Element;
