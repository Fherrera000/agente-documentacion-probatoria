"""Análisis de documentos probatorios con Gemini (paquete 3.2).

Gemini recibe el archivo original (PDF o imagen, incluso escaneado), lo lee (OCR)
y devuelve en JSON los metadatos y la clasificación según los catálogos del
paquete 2.1. Después, este módulo valida y verifica la respuesta:

- Valores fuera de catálogo se descartan (R-01, R-02).
- El periodo se calcula con las reglas del catálogo, no lo decide el modelo (R-04).
- Lo extraído se compara contra el texto del documento para detectar datos
  inventados (R-07, R-09; riesgo R03 de OpenProject).
- Confianza baja o ambigüedad mandan el documento a revisión humana (R-05).

La capa es intercambiable: el resto del backend solo usa `obtener_analizador()`
y el método `analizar()`, así se puede cambiar a Vertex AI u otro proveedor.
"""
from __future__ import annotations

import json
import re
from datetime import date

from app.config.settings import configuracion
from app.ia.catalogos import CATEGORIAS, PERIODOS, TIPOS_DOCUMENTO, calcular_periodo
from app.ia.texto import normalizar, tiene_texto

UMBRAL_CONFIANZA = 0.70
MAX_TEXTO_GUARDADO = 50_000


class IANoConfigurada(Exception):
    """No hay llave de Gemini ni Vertex AI configurados en el .env."""


class ErrorIA(Exception):
    """Falla al llamar a la IA, con un mensaje entendible para el usuario."""


# Errores de Google por los que conviene intentar con el siguiente modelo.
CODIGOS_PROBAR_OTRO_MODELO = {404, 429, 500, 502, 503, 504}


def mensaje_de_error(codigo: int | None, modelo: str) -> str:
    if codigo == 503 or codigo in (500, 502, 504):
        return "Los servidores de Gemini están saturados en este momento. Intenta de nuevo en unos minutos."
    if codigo == 429:
        return "Se alcanzó el límite de uso de la llave de Gemini. Espera un minuto e intenta de nuevo."
    if codigo == 404:
        return f"El modelo {modelo} no está disponible para esta llave. Cambia GEMINI_MODEL en el .env."
    if codigo in (401, 403):
        return "La llave de Gemini no es válida o no tiene permisos. Revisa GEMINI_API_KEY en el .env."
    if codigo == 400:
        return "Gemini rechazó la petición (400). Puede que el archivo esté dañado o no sea compatible."
    return "No se pudo analizar el documento con la IA. Intenta de nuevo."


INSTRUCCIONES = f"""Eres un asistente que analiza documentación probatoria del personal docente
de la Universidad Autónoma de Baja California (constancias, certificados, diplomas,
reconocimientos, nombramientos e informes).

Lee el documento completo (si es imagen o escaneo, transcríbelo con OCR) y responde
SOLO con el JSON solicitado. Reglas obligatorias:

R-01 tipo_documento: una clave de {json.dumps(TIPOS_DOCUMENTO, ensure_ascii=False)}.
R-02 categoria_academica: clasifica por la ACTIVIDAD PRINCIPAL que acredita el documento,
     no solo por su título. Claves: {json.dumps(CATEGORIAS, ensure_ascii=False)}.
R-03 Fechas en formato AAAA-MM-DD. fecha_emision = fecha en que se expide el documento.
     fecha_inicio y fecha_fin = periodo en que se realizó la actividad, si aparece.
R-05 Si la actividad podría pertenecer a dos categorías, o falta información importante,
     pon requiere_revision = true y explica el motivo en motivos_revision (en español).
R-09 NO inventes datos. Si un dato no aparece en el documento, devuelve null.
     Nunca completes nombres, fechas u horas por suposición.
R-10 No copies datos personales sensibles (CURP, RFC, domicilio, teléfono) en ningún campo.

Campos adicionales:
- titulo_actividad: nombre del curso, cargo, proyecto, ponencia o actividad, tal como aparece.
- institucion_emisora: quién expide el documento, tal como aparece.
- horas: número entero de horas acreditadas, si aparece.
- resumen: 1 o 2 oraciones en español sobre qué acredita el documento.
- evidencia: fragmento LITERAL del documento (máximo 150 caracteres) que justifica la categoría.
- confianza: número de 0 a 1 sobre qué tan seguro estás de la categoría.
- texto: transcripción completa del texto del documento.

Los periodos académicos ({", ".join(PERIODOS)}) se calculan después a partir de las fechas.
"""

def instrucciones_con_fecha() -> str:
    """El modelo no sabe qué día es: se lo decimos para que no tome por error una fecha
    reciente como futura o inconsistente."""
    hoy = date.today().isoformat()
    return (
        f"{INSTRUCCIONES}\n"
        f"FECHA ACTUAL: {hoy}. Usa esta fecha como referencia. Tu conocimiento puede terminar antes de esta fecha, "
        f"así que NO marques como error, inconsistencia ni errata una fecha del documento solo porque su año "
        f"te parezca reciente o futuro. Solo repórtala si es posterior a {hoy}, o si el propio documento se contradice."
    )


ESQUEMA_RESPUESTA = {
    "type": "object",
    "properties": {
        "tipo_documento": {"type": "string", "enum": list(TIPOS_DOCUMENTO)},
        "categoria_academica": {"type": "string", "enum": list(CATEGORIAS), "nullable": True},
        "titulo_actividad": {"type": "string", "nullable": True},
        "institucion_emisora": {"type": "string", "nullable": True},
        "fecha_emision": {"type": "string", "nullable": True},
        "fecha_inicio": {"type": "string", "nullable": True},
        "fecha_fin": {"type": "string", "nullable": True},
        "horas": {"type": "integer", "nullable": True},
        "resumen": {"type": "string"},
        "evidencia": {"type": "string", "nullable": True},
        "confianza": {"type": "number"},
        "requiere_revision": {"type": "boolean"},
        "motivos_revision": {"type": "array", "items": {"type": "string"}},
        "texto": {"type": "string"},
    },
    "required": ["tipo_documento", "categoria_academica", "resumen", "confianza",
                 "requiere_revision", "motivos_revision", "texto"],
}

FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fecha_valida(valor):
    return valor if isinstance(valor, str) and FECHA_ISO.match(valor) else None


def _respaldado(valor: str | None, texto_norm: str) -> bool:
    """¿Las palabras importantes del valor aparecen en el texto del documento?"""
    palabras = [p for p in normalizar(valor or "").split() if len(p) > 3]
    if not palabras:
        return True
    encontradas = sum(1 for p in palabras if p in texto_norm)
    return encontradas / len(palabras) >= 0.6


def interpretar(datos: dict, texto_local: str, modelo: str) -> dict:
    """Valida y verifica la respuesta del modelo. No necesita conexión ni SDK."""
    motivos = [str(m) for m in (datos.get("motivos_revision") or []) if m]
    revision = bool(datos.get("requiere_revision"))

    tipo = datos.get("tipo_documento")
    if tipo not in TIPOS_DOCUMENTO:
        tipo = "OTR"

    categoria = datos.get("categoria_academica")
    if categoria not in CATEGORIAS:
        if categoria:
            motivos.append(f"La IA propuso una categoría fuera de catálogo ({categoria}); se descartó.")
        categoria = None
        revision = True

    fechas = {}
    for campo in ("fecha_emision", "fecha_inicio", "fecha_fin"):
        valor = datos.get(campo)
        fechas[campo] = _fecha_valida(valor)
        if valor and not fechas[campo]:
            motivos.append(f"{campo} con formato inválido ({valor}); se dejó vacío.")

    try:
        confianza = max(0.0, min(1.0, float(datos.get("confianza") or 0)))
    except (TypeError, ValueError):
        confianza = 0.0
    if confianza < UMBRAL_CONFIANZA:
        revision = True
        motivos.append(f"Confianza baja en la categoría ({confianza:.0%}).")

    horas = datos.get("horas")
    horas = horas if isinstance(horas, int) and 0 < horas < 10_000 else None

    texto_ia = (datos.get("texto") or "").strip()
    if tiene_texto(texto_local):
        referencia, origen_texto = texto_local, "pdf"
    else:
        referencia, origen_texto = texto_ia, "ia"
    texto_norm = normalizar(referencia)

    # Verificación contra el texto (R-07 / R-09, riesgo R03).
    if texto_norm:
        for campo in ("titulo_actividad", "institucion_emisora"):
            valor = datos.get(campo)
            if valor and not _respaldado(valor, texto_norm):
                revision = True
                motivos.append(f"'{campo}' no se encontró en el texto del documento (posible dato inventado).")
        evidencia = datos.get("evidencia")
        if evidencia and normalizar(evidencia)[:60] not in texto_norm:
            revision = True
            motivos.append("La evidencia citada por la IA no aparece literalmente en el documento.")
    else:
        revision = True
        motivos.append("No se pudo obtener texto del documento para verificar el análisis.")

    if origen_texto == "ia" and not tiene_texto(texto_ia):
        revision = True

    fecha_ref = fechas["fecha_fin"] or fechas["fecha_emision"] or fechas["fecha_inicio"]
    return {
        "tipo_documento": tipo,
        "tipo_documento_nombre": TIPOS_DOCUMENTO[tipo],
        "categoria_academica": categoria,
        "titulo_actividad": datos.get("titulo_actividad") or None,
        "institucion_emisora": datos.get("institucion_emisora") or None,
        **fechas,
        "periodo_academico": calcular_periodo(fechas["fecha_inicio"], fechas["fecha_fin"], fechas["fecha_emision"]),
        "anio": int(fecha_ref[:4]) if fecha_ref else None,
        "horas": horas,
        "resumen": datos.get("resumen") or None,
        "evidencia": datos.get("evidencia") or None,
        "confianza": round(confianza, 2),
        "requiere_revision": revision,
        "motivos_revision": list(dict.fromkeys(motivos)),  # sin repetidos
        "origen_texto": origen_texto,
        "modelo": modelo,
        "texto": referencia[:MAX_TEXTO_GUARDADO],
    }


class AnalizadorGemini:
    def __init__(self, cliente=None, modelo: str | None = None, respaldo: list[str] | None = None):
        self.modelo = modelo or configuracion.gemini_model
        if respaldo is None:
            respaldo = [m.strip() for m in configuracion.gemini_modelos_respaldo.split(",") if m.strip()]
        self.modelos = list(dict.fromkeys([self.modelo, *respaldo]))  # sin repetidos
        if cliente is None:
            from google import genai  # importación diferida: solo cuando se usa la IA
            from google.genai import types

            opciones = types.HttpOptions(
                timeout=configuracion.gemini_timeout_segundos * 1000,  # milisegundos
                # Reintentos cortos ante saturación; si siguen fallando se prueba otro modelo.
                retry_options=types.HttpRetryOptions(attempts=2, initial_delay=2, max_delay=8),
            )
            if configuracion.gemini_api_key:
                cliente = genai.Client(api_key=configuracion.gemini_api_key, http_options=opciones)
            else:  # Vertex AI con GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT y GOOGLE_CLOUD_LOCATION
                cliente = genai.Client(http_options=opciones)
        self.cliente = cliente

    def _llamar(self, modelo: str, contenido: bytes, content_type: str):
        from google.genai import types

        return self.cliente.models.generate_content(
            model=modelo,
            contents=[
                types.Part.from_bytes(data=contenido, mime_type=content_type),
                "Analiza este documento probatorio y responde en el JSON indicado.",
            ],
            config=types.GenerateContentConfig(
                system_instruction=instrucciones_con_fecha(),
                response_mime_type="application/json",
                response_schema=ESQUEMA_RESPUESTA,
                temperature=0.1,
            ),
        )

    def analizar(self, contenido: bytes, content_type: str, texto_local: str = "") -> dict:
        ultimo_error = None
        for i, modelo in enumerate(self.modelos):
            try:
                respuesta = self._llamar(modelo, contenido, content_type)
            except Exception as error:
                codigo = getattr(error, "code", None)
                ultimo_error = ErrorIA(mensaje_de_error(codigo, modelo))
                ultimo_error.__cause__ = error
                hay_otro = i + 1 < len(self.modelos)
                # Tiempo agotado o error temporal de Google: probar con el siguiente modelo.
                if hay_otro and (codigo in CODIGOS_PROBAR_OTRO_MODELO or codigo is None):
                    continue
                if codigo is None:
                    raise ErrorIA("Gemini tardó demasiado en responder o no hubo conexión. Intenta de nuevo.") from error
                raise ultimo_error
            try:
                datos = json.loads(respuesta.text)
            except (TypeError, ValueError) as error:
                raise ErrorIA("La IA no devolvió una respuesta válida. Intenta de nuevo.") from error
            return interpretar(datos, texto_local, modelo)
        raise ultimo_error


def ia_configurada() -> bool:
    import os

    return bool(configuracion.gemini_api_key) or os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"


def obtener_analizador():
    if not ia_configurada():
        raise IANoConfigurada("La IA no está configurada: agrega GEMINI_API_KEY en el archivo .env y reinicia la API.")
    return AnalizadorGemini()