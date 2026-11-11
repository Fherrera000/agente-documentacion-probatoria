"""Proceso de análisis de un documento con IA (paquete 3.2).

Se ejecuta en segundo plano después de subir un archivo, para que la carga
responda de inmediato. El estado queda en el campo `analisis_estado`:

    pendiente -> procesando -> completado | revision | error | no_configurado
"""
import logging
from datetime import datetime, timezone

from app.config import database
from app.ia import analizador as ia
from app.ia.texto import extraer_texto_pdf
from app.services.almacenamiento import resolver_archivo

registro = logging.getLogger(__name__)


def _actualizar(documento_id, **campos):
    database.base_datos.documentos.update_one({"_id": documento_id}, {"$set": campos})


def procesar_documento(documento_id) -> None:
    documento = database.base_datos.documentos.find_one({"_id": documento_id, "archivo_subido": True})
    if not documento:
        return
    _actualizar(documento_id, analisis_estado="procesando", analisis_error=None)

    try:
        analizador = ia.obtener_analizador()
    except ia.IANoConfigurada as error:
        _actualizar(documento_id, analisis_estado="no_configurado", analisis_error=str(error))
        return

    try:
        contenido = resolver_archivo(documento["storage_key"]).read_bytes()
        texto_local = extraer_texto_pdf(contenido) if documento["content_type"] == "application/pdf" else ""
        resultado = analizador.analizar(contenido, documento["content_type"], texto_local)
    except ia.ErrorIA as error:  # error conocido de la IA: mensaje entendible para el usuario
        registro.warning("Falló el análisis del documento %s: %s (%s)", documento_id, error, error.__cause__)
        _actualizar(documento_id, analisis_estado="error", analisis_error=str(error))
        return
    except Exception as error:  # la falla de la IA no debe romper la carga
        registro.exception("Falló el análisis del documento %s", documento_id)
        _actualizar(documento_id, analisis_estado="error",
                    analisis_error=f"No se pudo analizar el documento ({type(error).__name__}). Intenta analizarlo de nuevo.")
        return

    texto = resultado.pop("texto", "")

    # R-06: un archivo idéntico ya cargado por el mismo profesor se marca, no se elimina.
    duplicado = database.base_datos.documentos.find_one({
        "_id": {"$ne": documento_id},
        "profesor_id": documento["profesor_id"],
        "sha256": documento.get("sha256"),
        "archivo_subido": True,
    })
    if duplicado:
        resultado["requiere_revision"] = True
        resultado["motivos_revision"].append(
            f"Posible duplicado de «{duplicado['nombre_archivo']}» (mismo contenido).")

    _actualizar(
        documento_id,
        analisis=resultado,
        texto_extraido=texto,
        analisis_estado="revision" if resultado["requiere_revision"] else "completado",
        analisis_error=None,
        fecha_analisis=datetime.now(timezone.utc),
    )
