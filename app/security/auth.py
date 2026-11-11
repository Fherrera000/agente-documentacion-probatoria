from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bson import ObjectId
from app.config.database import base_datos
from app.config.settings import configuracion

# Esquema "Bearer": en /docs el botón Authorize muestra un campo para pegar el
# access_token obtenido en POST /auth/login. auto_error=False permite responder
# 401 (y no 403) cuando falta el token, igual que antes.
esquema_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="TokenJWT",
    description="Pega aquí el access_token que devuelve POST /auth/login (sin la palabra Bearer).",
)
hash_contrasenas = PasswordHash.recommended()

def obtener_hash(contrasena: str) -> str:
    return hash_contrasenas.hash(contrasena)

def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    return hash_contrasenas.verify(contrasena, hash_guardado)

def crear_token(profesor_id: str) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {"sub": profesor_id, "iat": ahora, "exp": ahora + timedelta(minutes=configuracion.jwt_expire_minutes)}
    return jwt.encode(datos, configuracion.jwt_secret, algorithm=configuracion.jwt_algorithm)

def obtener_profesor_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)):
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales no válidas", headers={"WWW-Authenticate": "Bearer"})
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise error
    token = credenciales.credentials
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
