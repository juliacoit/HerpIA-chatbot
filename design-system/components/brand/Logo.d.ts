export interface LogoProps {
  /** Altura em px da assinatura. Abaixo de ~56px use a versão com moldura ou o Wordmark. */
  altura?: number;
  /** Moldura branca — obrigatória sobre foto ou fundo de baixo contraste (manual, p. 12/19). */
  moldura?: boolean;
  /** Área de reserva em volta da marca (manual, p. 11). Mantenha true salvo em espaço já folgado. */
  reserva?: boolean;
  href?: string;
  alt?: string;
  style?: React.CSSProperties;
}
export function Logo(props: LogoProps): JSX.Element;
