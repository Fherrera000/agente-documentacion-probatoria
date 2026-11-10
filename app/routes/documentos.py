from datetime import datetime, timezone
import hashlib

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config.database import base_datos
from app.schemas.documento import DocumentoCrear
from app.security.auth import obtener_profesor_actual
from app.services.almacenamiento import guardar_archivo, resolver_archivo

router = APIRouter(prefix="/documentos", tags=["Documentos"])


@router.post("", status_code=201)
def registrar_documento(datos: DocumentoCrear, profesor=Depends(obtener_profesor_actual)):
    """Registra metadatos sin subir un archivo físico (compatibilidad con el flujo anterior)."""
    if not ObjectId.is_valid(datos.expediente_id):
        raise HTTPException(status_code=400, detail="ID de expediente inválido")
    expediente = base_datos.expedientes.find_one({"_id": ObjectId(datos.expediente_id), "profesor_id": profesor["_id"], "activo": True})
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    documento = datos.model_dump()
    documento.update({"expediente_id": ObjectId(datos.expediente_id), "profesor_id": profesor["_id"], "fecha_carga": datetime.now(timezone.utc), "estado": "registrado", "archivo_subido": False})
    resultado = base_datos.documentos.insert_one(documento)
    return {"id": str(resultado.inserted_id), "nombre_archivo": documento["nombre_archivo"], "expediente_id": datos.expediente_id, "estado": documento["estado"]}


@router.post("/subir", status_code=201)
async def subir_documento(
    expediente_id: str = Form(...),
    archivo: UploadFile = File(...),
    tipo_documento: str | None = Form(default=None),
    profesor=Depends(obtener_profesor_actual),
):
    if not ObjectId.is_valid(expediente_id):
        raise HTTPException(status_code=400, detail="ID de expediente inválido")

    expediente = base_datos.expedientes.find_one({"_id": ObjectId(expediente_id), "profesor_id": profesor["_id"], "activo": True})
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    guardado = await guardar_archivo(archivo, str(profesor["_id"]))
    try:
        contenido_hash = hashlib.sha256(guardado["ruta"].read_bytes()).hexdigest()
        documento = {
            "expediente_id": ObjectId(expediente_id),
            "profesor_id": profesor["_id"],
            "nombre_archivo": guardado["nombre_archivo"],
            "tipo_documento": tipo_documento,
            "storage_key": guardado["storage_key"],
            "content_type": guardado["content_type"],
            "extension": guardado["extension"],
            "tamano_bytes": guardado["tamano_bytes"],
            "sha256": contenido_hash,
            "fecha_carga": datetime.now(timezone.utc),
            "estado": "cargado",
            "archivo_subido": True,
        }
        resultado = base_datos.documentos.insert_one(documento)
    except Exception:
        guardado["ruta"].unlink(missing_ok=True)
        raise

    return {
        "id": str(resultado.inserted_id),
        "nombre_archivo": documento["nombre_archivo"],
        "expediente_id": expediente_id,
        "tamano_bytes": documento["tamano_bytes"],
        "content_type": documento["content_type"],
        "estado": documento["estado"],
    }


@router.get("")
def listar_documentos(expediente_id: str | None = None, profesor=Depends(obtener_profesor_actual)):
    filtro = {"profesor_id": profesor["_id"]}
    if expediente_id:
        if not ObjectId.is_valid(expediente_id):
            raise HTTPException(status_code=400, detail="ID de expediente inválido")
        filtro["expediente_id"] = ObjectId(expediente_id)
    documentos = base_datos.documentos.find(filtro).sort("fecha_carga", -1)
    return [{"id": str(d["_id"]), "nombre_archivo": d["nombre_archivo"], "expediente_id": str(d["expediente_id"]), "tipo_documento": d.get("tipo_documento"), "estado": d["estado"], "archivo_subido": d.get("archivo_subido", False), "fecha_carga": d["fecha_carga"].isoformat()} for d in documentos]


@router.get("/{documento_id}/descargar")
def descargar_documento(documento_id: str, profesor=Depends(obtener_profesor_actual)):
    if not ObjectId.is_valid(documento_id):
        raise HTTPException(status_code=400, detail="ID de documento inválido")
    documento = base_datos.documentos.find_one({"_id": ObjectId(documento_id), "profesor_id": profesor["_id"], "archivo_subido": True})
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    ruta = resolver_archivo(documento["storage_key"])
    return FileResponse(
        path=ruta,
        media_type=documento["content_type"],
        filename=documento["nombre_archivo"],
        content_disposition_type="attachment",
    )
