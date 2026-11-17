"""Normalização de texto para comparar nomes e títulos sem depender de
acento, caixa, pontuação ou quebras de linha."""

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, só letras e dígitos separados por um espaço:
    "acanthochelys-radiolata-mikan-1820" vira "acanthochelys radiolata mikan
    1820", "Cágado-amarelo" vira "cagado amarelo" e "Pinto, H.\\n\\nB." vira
    "pinto h b"."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", sem_acento.lower()))
