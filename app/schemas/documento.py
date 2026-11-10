from pydantic import BaseModel, Field

class DocumentoCrear(BaseModel):
    expediente_id: str
    nombre_archivo: str = Field(min_length=1, max_length=255)
    tipo_documento: str | None = Field(default=None, max_length=100)
    ruta_storage: str = Field(min_length=1, max_length=500)
    metadatos: dict = Field(default_factory=dict)
