from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from app.config.database import base_datos
from app.config.settings import configuracion

oauth2_esquema = OAuth2PasswordBearer(tokenUrl="/auth/login")
hash_contrasenas = PasswordHash.recommended()

def obtener_hash(contrasena: str) -> str:
    return hash_contrasenas.hash(contrasena)

def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    return hash_contrasenas.verify(contrasena, hash_guardado)

def crear_token(profesor_id: str) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {"sub": profesor_id, "iat": ahora, "exp": ahora + timedelta(minutes=configuracion.jwt_expire_minutes)}
    return jwt.encode(datos, configuracion.jwt_secret, algorithm=configuracion.jwt_algorithm)

def obtener_profesor_actual(token: str = Depends(oauth2_esquema)):
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales no válidas", headers={"WWW-Authenticate": "Bearer"})
    try:
        carga = jwt.decode(token, configuracion.jwt_secret, algorithms=[configuracion.jwt_algorithm])
        profesor_id = carga.get("sub")
        if not profesor_id or not ObjectId.is_valid(profesor_id):
            raise error
    except jwt.InvalidTokenError:
        raise error
    profesor = base_datos.profesores.find_one({"_id": ObjectId(profesor_id), "activo": True})
    if not profesor:
        raise error
    return profesor
