from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo.errors import PyMongoError
from app.config.database import comprobar_conexion, inicializar_indices, cerrar_conexion
from app.config.storage import inicializar_almacenamiento
from app.routes import auth, profesores, expedientes, documentos

@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    try:
        comprobar_conexion()
        inicializar_indices()
        inicializar_almacenamiento()
    except PyMongoError as error:
        raise RuntimeError("No se pudo conectar con MongoDB. Verifica que el servicio esté iniciado y MONGODB_URI sea correcto.") from error
    yield
    cerrar_conexion()

app = FastAPI(title="Agente Inteligente de Documentación Probatoria", description="Backend inicial multitenant con FastAPI y MongoDB.", version="0.3.0", lifespan=ciclo_vida)
app.include_router(auth.router)
app.include_router(profesores.router)
app.include_router(expedientes.router)
app.include_router(documentos.router)

@app.get("/", tags=["Inicio"])
def inicio():
    return {"proyecto": "Agente Inteligente de Documentación Probatoria", "estado": "Backend principal en desarrollo", "version": "0.3.0"}

@app.get("/health", tags=["Salud"])
def salud():
    return {"estado": "correcto"}

@app.get("/database", tags=["Salud"])
def estado_base_datos():
    comprobar_conexion()
    return {"mongodb": "conectado"}
