import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

class Expediente(Base):
    __tablename__ = "expedientes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    profesor_id: Mapped[str] = mapped_column(
        ForeignKey("profesores.id"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(250), nullable=False)
    categoria_academica: Mapped[str | None] = mapped_column(String(10))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
