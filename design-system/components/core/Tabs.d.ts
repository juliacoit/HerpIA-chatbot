export interface TabItem { value: string; label: string; icon?: string; count?: number }
export interface TabsProps {
  tabs?: Array<TabItem | string>;
  value?: string;
  onChange?: (value: string) => void;
  style?: React.CSSProperties;
}
export function Tabs(props: TabsProps): JSX.Element;
