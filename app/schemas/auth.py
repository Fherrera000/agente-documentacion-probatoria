from pydantic import BaseModel, EmailStr, Field

class RegistroProfesor(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    correo: EmailStr
    contrasena: str = Field(min_length=10, max_length=128)

class InicioSesion(BaseModel):
    correo: EmailStr
    contrasena: str

class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"
