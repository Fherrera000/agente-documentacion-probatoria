import re

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

class RegistroProfesor(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    correo: EmailStr
    contrasena: str = Field(min_length=10, max_length=128)

    @field_validator("contrasena")
    @classmethod
    def contrasena_segura(cls, valor: str) -> str:
        """Exige mayúscula, minúscula, número y carácter especial (además de los 10 caracteres)."""
        faltantes = []
        if not re.search(r"[A-Z]", valor):
            faltantes.append("una letra mayúscula")
        if not re.search(r"[a-z]", valor):
            faltantes.append("una letra minúscula")
        if not re.search(r"\d", valor):
            faltantes.append("un número")
        if not re.search(r"[^A-Za-z0-9]", valor):
            faltantes.append("un carácter especial (por ejemplo ! @ # $ % &)")
        if faltantes:
            raise PydanticCustomError("contrasena_debil", "La contraseña debe incluir " + ", ".join(faltantes) + ".")
        return valor

class InicioSesion(BaseModel):
    correo: EmailStr
    contrasena: str

class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"
