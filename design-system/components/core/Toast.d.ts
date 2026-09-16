export interface ToastProps {
  children?: React.ReactNode;
  tone?: "info" | "sucesso" | "alerta" | "erro";
  onClose?: () => void;
  style?: React.CSSProperties;
}
export function Toast(props: ToastProps): JSX.Element;
