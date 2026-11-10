from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from app.config.settings import configuracion

cliente = MongoClient(configuracion.mongodb_uri, serverSelectionTimeoutMS=3000)
base_datos = cliente[configuracion.mongodb_database]

def inicializar_indices():
    """Crea índices necesarios; no elimina ni modifica documentos existentes."""
    base_datos.profesores.create_index([("correo", ASCENDING)], unique=True)
    base_datos.expedientes.create_index([("profesor_id", ASCENDING), ("fecha_creacion", ASCENDING)])
    base_datos.documentos.create_index([("profesor_id", ASCENDING), ("expediente_id", ASCENDING)])
    base_datos.documentos.create_index([("profesor_id", ASCENDING), ("fecha_carga", ASCENDING)])

def comprobar_conexion() -> bool:
    cliente.admin.command("ping")
    return True

def cerrar_conexion():
    cliente.close()
