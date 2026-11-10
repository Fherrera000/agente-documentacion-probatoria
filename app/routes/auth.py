from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError
from app.config.database import base_datos
from app.schemas.auth import RegistroProfesor, InicioSesion, TokenRespuesta
from app.security.auth import obtener_hash, verificar_contrasena, crear_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/registro", status_code=201)
def registrar(datos: RegistroProfesor):
    profesor = {"nombre": datos.nombre.strip(), "correo": datos.correo.lower(), "contrasena_hash": obtener_hash(datos.contrasena), "activo": True}
    try:
        resultado = base_datos.profesores.insert_one(profesor)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    return {"id": str(resultado.inserted_id), "nombre": profesor["nombre"], "correo": profesor["correo"]}

@router.post("/login", response_model=TokenRespuesta)
def iniciar_sesion(datos: InicioSesion):
    profesor = base_datos.profesores.find_one({"correo": datos.correo.lower(), "activo": True})
    if not profesor or not verificar_contrasena(datos.contrasena, profesor["contrasena_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")
    return {"access_token": crear_token(str(profesor["_id"])), "token_type": "bearer"}
