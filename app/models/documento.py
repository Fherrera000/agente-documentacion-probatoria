import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    profesor_id: Mapped[str] = mapped_column(
        ForeignKey("profesores.id"), nullable=False, index=True
    )
    expediente_id: Mapped[str] = mapped_column(
        ForeignKey("expedientes.id"), nullable=False, index=True
    )
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_storage: Mapped[str] = mapped_column(String(500), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
