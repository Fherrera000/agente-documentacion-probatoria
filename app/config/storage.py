from pathlib import Path
from app.config.settings import configuracion

# La ruta se mantiene dentro del proyecto y puede cambiarse mediante .env.
RUTA_ALMACENAMIENTO = Path(configuracion.storage_path).resolve()
RUTA_DOCUMENTOS = RUTA_ALMACENAMIENTO / "documentos"

TAMANO_MAXIMO_BYTES = configuracion.max_upload_size_mb * 1024 * 1024

TIPOS_PERMITIDOS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def inicializar_almacenamiento():
    RUTA_DOCUMENTOS.mkdir(parents=True, exist_ok=True)
