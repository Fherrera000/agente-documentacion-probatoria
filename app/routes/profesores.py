from fastapi import APIRouter, Depends
from app.security.auth import obtener_profesor_actual

router = APIRouter(prefix="/profesores", tags=["Profesores"])

@router.get("/yo")
def consultar_perfil(profesor=Depends(obtener_profesor_actual)):
    return {"id": str(profesor["_id"]), "nombre": profesor["nombre"], "correo": profesor["correo"]}
