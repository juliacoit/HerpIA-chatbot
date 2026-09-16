export interface TooltipProps {
  children?: React.ReactNode;
  content?: React.ReactNode;
  placement?: "top" | "bottom";
  style?: React.CSSProperties;
}
export function Tooltip(props: TooltipProps): JSX.Element;
