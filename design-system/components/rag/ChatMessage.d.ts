export interface ChatMessageProps {
  autor?: "usuario" | "assistente";
  children?: React.ReactNode;
  hora?: string;
  style?: React.CSSProperties;
}
export function ChatMessage(props: ChatMessageProps): JSX.Element;
