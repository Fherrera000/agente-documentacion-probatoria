# Agente Inteligente de Documentación Probatoria

Backend inicial del proyecto con **FastAPI + MongoDB**. Implementa registro e inicio de sesión, perfil del profesor, expedientes y registro/listado de documentos. El aislamiento multitenant se realiza filtrando cada operación por el profesor obtenido del token JWT.

## Requisitos
- Python 3.13 (probado como entorno objetivo)
- MongoDB local iniciado o URI de MongoDB Atlas

## Instalación en Windows PowerShell
```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Edita `.env` y configura `MONGODB_URI`, `MONGODB_DATABASE` y una clave `JWT_SECRET` larga y aleatoria. Después:
```powershell
uvicorn app.main:app --reload
```
Abre `http://127.0.0.1:8000/docs`.

## Flujo de prueba
1. `POST /auth/registro` para crear un profesor.
2. `POST /auth/login` para obtener el token.
3. En Swagger pulsa **Authorize** y pega el token (Bearer).
4. `GET /profesores/yo` para verificar la identidad.
5. `POST /expedientes` para crear un expediente.
6. `POST /documentos` para registrar metadatos de un documento dentro de un expediente propio.

## Colecciones e índices
- `profesores`: correo único, nombre, hash de contraseña y estado.
- `expedientes`: `profesor_id`, título, categoría y fecha.
- `documentos`: `profesor_id`, `expediente_id`, metadatos y ruta de almacenamiento.

## Importante sobre seguridad y alcance
- El `profesor_id` no se recibe en las rutas: se obtiene del JWT validado.
- Las consultas de expedientes y documentos siempre incluyen el `profesor_id` autenticado.
- La contraseña se almacena con hash Argon2; nunca en texto plano.
- El registro de documentos **solo guarda metadatos y una ruta**; todavía no carga archivos ni implementa OCR.
- Este es un punto de partida para desarrollo local, no una versión lista para producción. Antes de usar datos reales se deben añadir HTTPS, gestión segura de secretos, recuperación de cuenta, límites de intentos, auditoría, validación de archivos, almacenamiento privado y pruebas automatizadas de acceso cruzado entre profesores.
- El dataset sintético debe permanecer separado en `dataset_documentos`; no mezclarlo con los expedientes privados.

## Carga y descarga de documentos (versión 0.3.0)

La API permite cargar archivos físicos asociados a expedientes propios. Los archivos se guardan en `storage/documentos/<profesor_id>/` con un nombre interno aleatorio; MongoDB conserva los metadatos y la clave de almacenamiento.

### Endpoint de carga

`POST /documentos/subir` (requiere Bearer token, `multipart/form-data`):
- `expediente_id`: identificador del expediente del profesor autenticado.
- `archivo`: archivo PDF, JPG/JPEG o PNG.
- `tipo_documento`: campo opcional.

Tamaño máximo predeterminado: 10 MB. Se valida la extensión y la firma básica del contenido. El límite y la ruta se pueden configurar con `MAX_UPLOAD_SIZE_MB` y `STORAGE_PATH` en `.env`.

### Endpoint de descarga

`GET /documentos/{documento_id}/descargar` (requiere Bearer token). Solo permite descargar archivos asociados al profesor autenticado.

### Ejemplo PowerShell

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documentos/subir" `
  -H "Authorization: Bearer TU_TOKEN" `
  -F "expediente_id=ID_DEL_EXPEDIENTE" `
  -F "tipo_documento=Constancia" `
  -F "archivo=@C:\\Documentos\\constancia.pdf"
```

Para ejecutar las pruebas automatizadas:

```powershell
pip install -r requirements-dev.txt
python -m pytest -v
```

Las pruebas de carga y descarga usan un directorio temporal. No escriben archivos en el almacenamiento de desarrollo.

**Nota de despliegue:** el almacenamiento local es adecuado para desarrollo y pruebas en una sola instancia. Para producción con varias instancias de FastAPI, conviene sustituirlo por almacenamiento de objetos privado (por ejemplo, un bucket) y mantener autorización por profesor antes de generar descargas.
