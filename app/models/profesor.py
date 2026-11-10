import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

class Profesor(Base):
    __tablename__ = "profesores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    identificador_autenticacion: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
