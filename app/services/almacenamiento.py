from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config.storage import RUTA_DOCUMENTOS, TAMANO_MAXIMO_BYTES, TIPOS_PERMITIDOS


def validar_contenido(extension: str, contenido: bytes) -> bool:
    """Comprueba la firma básica del archivo, no solamente su extensión."""
    if extension == ".pdf":
        return contenido.startswith(b"%PDF-")
    if extension in (".jpg", ".jpeg"):
        return contenido.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return contenido.startswith(b"\x89PNG\r\n\x1a\n")
    return False


async def guardar_archivo(archivo: UploadFile, profesor_id: str) -> dict:
    nombre_original = PurePosixPath((archivo.filename or "").replace("\\", "/")).name
    extension = Path(nombre_original).suffix.lower()

    if extension not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=415, detail="Formato no permitido. Utiliza PDF, JPG o PNG")

    contenido = await archivo.read(TAMANO_MAXIMO_BYTES + 1)
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el tamaño máximo permitido")
    if not validar_contenido(extension, contenido):
        raise HTTPException(status_code=415, detail="El contenido del archivo no coincide con su extensión")

    carpeta_profesor = (RUTA_DOCUMENTOS / profesor_id).resolve()
    if RUTA_DOCUMENTOS.resolve() not in carpeta_profesor.parents:
        raise HTTPException(status_code=400, detail="Ruta de almacenamiento inválida")
    carpeta_profesor.mkdir(parents=True, exist_ok=True)

    nombre_interno = f"{uuid4().hex}{extension}"
    ruta = carpeta_profesor / nombre_interno
    ruta.write_bytes(contenido)

    return {
        "ruta": ruta,
        "storage_key": f"documentos/{profesor_id}/{nombre_interno}",
        "nombre_archivo": nombre_original,
        "extension": extension,
        "content_type": TIPOS_PERMITIDOS[extension],
        "tamano_bytes": len(contenido),
    }


def resolver_archivo(storage_key: str) -> Path:
    ruta = (RUTA_DOCUMENTOS.parent / storage_key).resolve()
    if RUTA_DOCUMENTOS.resolve() not in ruta.parents:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return ruta
