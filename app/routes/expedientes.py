from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from app.config.database import base_datos
from app.schemas.expediente import ExpedienteCrear
from app.security.auth import obtener_profesor_actual

router = APIRouter(prefix="/expedientes", tags=["Expedientes"])

def presentar(exp):
    return {"id": str(exp["_id"]), "titulo": exp["titulo"], "categoria_academica": exp["categoria_academica"], "descripcion": exp.get("descripcion"), "fecha_creacion": exp["fecha_creacion"].isoformat()}

@router.post("", status_code=201)
def crear_expediente(datos: ExpedienteCrear, profesor=Depends(obtener_profesor_actual)):
    exp = datos.model_dump()
    exp.update({"profesor_id": profesor["_id"], "fecha_creacion": datetime.now(timezone.utc), "activo": True})
    resultado = base_datos.expedientes.insert_one(exp)
    exp["_id"] = resultado.inserted_id
    return presentar(exp)

@router.get("")
def listar_expedientes(profesor=Depends(obtener_profesor_actual)):
    return [presentar(e) for e in base_datos.expedientes.find({"profesor_id": profesor["_id"], "activo": True}).sort("fecha_creacion", -1)]

@router.get("/{expediente_id}")
def obtener_expediente(expediente_id: str, profesor=Depends(obtener_profesor_actual)):
    if not ObjectId.is_valid(expediente_id):
        raise HTTPException(status_code=400, detail="ID de expediente inválido")
    exp = base_datos.expedientes.find_one({"_id": ObjectId(expediente_id), "profesor_id": profesor["_id"], "activo": True})
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return presentar(exp)

@router.delete("/{expediente_id}", status_code=204)
def eliminar_expediente(expediente_id: str, profesor=Depends(obtener_profesor_actual)):
    if not ObjectId.is_valid(expediente_id):
        raise HTTPException(status_code=400, detail="ID de expediente inválido")
    resultado = base_datos.expedientes.update_one({"_id": ObjectId(expediente_id), "profesor_id": profesor["_id"]}, {"$set": {"activo": False}})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
