from app.config.database import Base, motor
from app.models.profesor import Profesor
from app.models.expediente import Expediente
from app.models.documento import Documento

def crear_tablas_locales():
    Base.metadata.create_all(bind=motor)
