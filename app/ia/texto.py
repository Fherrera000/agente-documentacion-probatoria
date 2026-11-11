"""Extracción local de texto (sin IA).

Se usa como referencia independiente para verificar lo que responde el modelo
(riesgo R03: alucinaciones). Los PDF escaneados y las imágenes no tienen capa de
texto; en ese caso el texto lo transcribe Gemini (OCR) y se marca como tal.
"""
import io
import logging
import unicodedata

MIN_CARACTERES = 40

registro = logging.getLogger(__name__)


def extraer_texto_pdf(contenido: bytes) -> str:
    try:
        from pypdf import PdfReader

        lector = PdfReader(io.BytesIO(contenido))
        return "\n".join((pagina.extract_text() or "") for pagina in lector.pages).strip()
    except Exception as error:  # PDF dañado o cifrado: no detiene el análisis
        registro.warning("No se pudo leer el texto del PDF: %s", error)
        return ""


def tiene_texto(texto: str | None) -> bool:
    return bool(texto) and len(texto.strip()) >= MIN_CARACTERES


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios simples, para comparar textos."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())
