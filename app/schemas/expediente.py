from pydantic import BaseModel, Field
from typing import Literal

Categoria = Literal["DOC", "VIN", "INV", "GES"]
class ExpedienteCrear(BaseModel):
    titulo: str = Field(min_length=3, max_length=250)
    categoria_academica: Categoria
    descripcion: str | None = Field(default=None, max_length=1000)
class ExpedienteRespuesta(BaseModel):
    id: str
    titulo: str
    categoria_academica: str
    descripcion: str | None = None
    fecha_creacion: str
