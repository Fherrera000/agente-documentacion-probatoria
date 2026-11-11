# Imagen de la API (FastAPI). Sirve para desarrollo local y para Cloud Run.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias primero: Docker reutiliza esta capa si requirements.txt no cambia.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Usuario sin privilegios y carpeta de almacenamiento de documentos.
RUN useradd --create-home appuser \
    && mkdir -p /app/storage/documentos \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Cloud Run indica el puerto en la variable PORT; en local se usa 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
