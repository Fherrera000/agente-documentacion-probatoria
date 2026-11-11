# Agente Inteligente de Documentación Probatoria

Proyecto con **FastAPI + MongoDB** en el backend y **React + Vite** en la interfaz web. El backend (versión 0.3.0) implementa registro e inicio de sesión de profesores, perfil, expedientes, y carga y descarga de documentos. El aislamiento multitenant se logra filtrando cada operación por el profesor que viene en el token JWT.

Hay dos formas de correr el proyecto:

| Forma | Cuándo usarla | Qué necesitas |
|---|---|---|
| **A. Con Docker** (recomendada) | Para usar y probar todo. Levanta la interfaz web, la API y MongoDB con un solo comando. | Docker Desktop |
| **B. Local con Python y Node.js** | Para correr las pruebas automáticas, o si no tienes Docker. | Python 3.13, MongoDB y Node.js 20 o superior |

Lo normal es usar las dos: **Docker para correr el proyecto** y el **entorno de Python para las pruebas**.

| Qué | Dirección |
|---|---|
| Interfaz web | http://localhost:5173 |
| Documentación de la API (Swagger) | http://127.0.0.1:8000/docs |
| MongoDB (Compass) | `mongodb://localhost:27017` |

---

## 1. Requisitos (una sola vez)

| Programa | Descarga | Notas |
|---|---|---|
| Git | https://git-scm.com/download/win | Opciones por defecto. |
| Visual Studio Code | https://code.visualstudio.com | Instala la extensión **Python** (Microsoft). |
| Python 3.13 | https://www.python.org/downloads | Marca **"Add Python to PATH"** al instalar. |
| Docker Desktop | https://www.docker.com/products/docker-desktop | Para la forma A. Debe estar abierto al usarlo. |
| Node.js 20 o superior (LTS) | https://nodejs.org | Solo para la forma B (correr la interfaz sin Docker). |
| MongoDB Compass (opcional) | https://www.mongodb.com/try/download/compass | Para ver los datos de la base. |
| MongoDB Community Server | https://www.mongodb.com/try/download/community | Solo para la forma B. Deja marcado **"Install MongoD as a Service"**. |

> **Consejo para Windows:** si tu disco C: tiene poco espacio, en Docker Desktop ve a **Settings › Resources › Advanced › Disk image location** y elige una carpeta en otro disco (por ejemplo `D:\Docker`). Ahí se guardan las imágenes y los datos de MongoDB.

---

## 2. Clonar el repositorio en VS Code

1. Abre VS Code y presiona **Ctrl + Shift + P**.
2. Escribe **Git: Clone** y pega:
   ```
   https://github.com/Fherrera000/agente-documentacion-probatoria.git
   ```
3. Elige la carpeta donde quieres guardarlo y presiona **Open** (no "Add to Workspace").
4. Si pregunta *"Do you trust the authors?"*, elige **Yes, I trust the authors**.

---

## 3. Crear el archivo `.env` (obligatorio en ambas formas)

El archivo `.env` guarda la configuración y la clave secreta. **No se sube a GitHub** (está en `.gitignore`), así que cada quien crea el suyo.

En la terminal de VS Code (**Terminal › New Terminal**):

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copia el texto largo que imprime el segundo comando. Abre el archivo **`.env`** (no `.env.example`) y pégalo en la línea:

```
JWT_SECRET=el_texto_largo_que_copiaste
```

Guarda con **Ctrl + S**.

> **Importante:** nunca pongas tu clave en `.env.example`. Ese archivo sí se sube a GitHub y la clave quedaría pública.
>
> Si VS Code muestra el aviso *"An environment file is configured but terminal environment injection is disabled"*, presiona **Don't Show Again**. No hace falta: el proyecto ya lee el `.env` por su cuenta.

---

## 4A. Correr con Docker (recomendado)

Con Docker Desktop abierto, en la terminal de VS Code, dentro de la carpeta del proyecto:

```powershell
docker compose up -d --build
```

- La primera vez tarda unos minutos (descarga Python y MongoDB).
- `-d` lo deja corriendo en segundo plano.
- Revisa que esté arriba con `docker compose ps`: deben aparecer **adp-web** (`Up`), **adp-api** (`Up`) y **adp-mongo** (`Up (healthy)`).
- La primera vez, la interfaz tarda uno o dos minutos más en abrir porque instala sus dependencias (`npm install`). Puedes seguir el avance con `docker compose logs -f web`.

Abre la interfaz en **http://localhost:5173** o la API en **http://127.0.0.1:8000/docs**.

| Para... | Comando |
|---|---|
| Ver los mensajes de la API | `docker compose logs -f api` (salir con Ctrl + C; no apaga nada) |
| Ver los mensajes de la interfaz | `docker compose logs -f web` |
| Apagar todo | `docker compose down` |
| Volver a encender | `docker compose up -d` |
| Reiniciar solo la API | `docker compose restart api` |
| Reconstruir tras cambiar `requirements.txt` | `docker compose up -d --build` |
| Reinstalar dependencias tras cambiar `frontend/package.json` | `docker compose restart web` |

Notas:
- Al guardar cambios en `app/` (API) o en `frontend/src/` (interfaz) desde VS Code, se recargan solos.
- Los datos de MongoDB se guardan en el volumen `mongo_data` y **no se pierden** al apagar.
- Los archivos subidos quedan en la carpeta `storage/` del proyecto (no se suben a GitHub).
- MongoDB Compass se conecta con `mongodb://localhost:27017`. La base se llama `agente_documentacion_probatoria`.
- No corras al mismo tiempo `uvicorn` local (puerto 8000), `npm run dev` local (puerto 5173) ni un MongoDB instalado en Windows (puerto 27017): chocan con Docker.

---

## 4B. Correr local con Python

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

- Si `Activate.ps1` da error de *"ejecución de scripts deshabilitada"*, corre `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, responde **S** y vuelve a activar.
- Al activarse, la terminal muestra **(.venv)** al inicio.
- En VS Code: **Ctrl + Shift + P › Python: Select Interpreter** y elige la opción con **`.venv`**.

Con el servicio de MongoDB encendido (`Get-Service *mongo*` debe decir `Running`):

```powershell
uvicorn app.main:app --reload
```

Abre **http://127.0.0.1:8000/docs**.

Para la interfaz web, en **otra terminal** (con Node.js instalado):

```powershell
cd frontend
npm install
npm run dev
```

Abre **http://localhost:5173**. La API debe estar corriendo en el puerto 8000.

---

## 4C. La interfaz web (React + Vite)

El código está en la carpeta `frontend/`:

```
frontend/
  index.html             página base
  vite.config.js         configuración de Vite y reenvío de /api a FastAPI
  package.json           dependencias (React, Vite)
  src/
    main.jsx             punto de entrada
    App.jsx              sesión del profesor y cambio de pantallas
    api.js               todas las llamadas a la API (token, errores, descargas)
    styles.css           estilos
    components/
      Acceso.jsx         iniciar sesión y crear cuenta
      Documentos.jsx     expediente, subir documentos, lista y descarga
```

Cómo se conecta con la API: la interfaz llama a rutas que empiezan con `/api` (por ejemplo `/api/auth/login`) y Vite las reenvía a FastAPI quitando el `/api`. Por eso el navegador ve un solo origen y **no hace falta configurar CORS** en desarrollo. El destino se elige con la variable `API_URL` (en Docker es `http://api:8000`; sin Docker, `http://127.0.0.1:8000`).

Qué se puede hacer en esta versión:
1. Crear cuenta e iniciar sesión (el token se guarda en el navegador; al vencer, regresa al inicio de sesión con un aviso).
2. Elegir un expediente o crear uno nuevo (título, categoría DOC/VIN/INV/GES y descripción).
3. Subir uno o varios PDF, JPG o PNG (máximo 10 MB) arrastrándolos o con clic, con tipo de documento opcional. Cada archivo muestra si se subió o el motivo del error.
4. Ver los documentos del expediente y descargarlos.

> `package-lock.json` se genera la primera vez que se instala; súbanlo a GitHub para que todos usen las mismas versiones. `node_modules/` no se sube.

---

## 5. Probar la API en `/docs`

1. **`GET /database`** › *Try it out* › *Execute*. Debe responder `{"mongodb": "conectado"}`.
2. **`POST /auth/registro`** para crear un profesor (contraseña de **mínimo 10 caracteres**):
   ```json
   { "nombre": "Profesor Prueba", "correo": "prueba@ejemplo.com", "contrasena": "MiClave12345" }
   ```
3. **`POST /auth/login`** con el mismo correo y contraseña. Copia el `access_token` de la respuesta (sin comillas).
4. Presiona **Authorize** (arriba a la derecha), pega **solo el token** (sin escribir "Bearer"), presiona **Authorize** y **Close**. Los candados se cierran.
5. **`GET /profesores/yo`** debe mostrar tus datos.
6. **`POST /expedientes`** para crear un expediente.
7. **`POST /documentos/subir`** para subir un archivo a ese expediente.

> El token dura 60 minutos (`JWT_EXPIRE_MINUTES`). Si todo empieza a dar **401**, haz login de nuevo y pega el token nuevo en Authorize (primero *Logout*).

### Carga y descarga de documentos

Los archivos se guardan en `storage/documentos/<profesor_id>/` con un nombre interno aleatorio; MongoDB guarda los metadatos y la clave de almacenamiento.

`POST /documentos/subir` (requiere token, `multipart/form-data`):
- `expediente_id`: identificador de un expediente propio.
- `archivo`: PDF, JPG/JPEG o PNG. Máximo 10 MB (`MAX_UPLOAD_SIZE_MB`). Se valida la extensión y la firma del contenido.
- `tipo_documento`: opcional.

`GET /documentos/{documento_id}/descargar` (requiere token): solo descarga archivos del profesor autenticado.

Ejemplo desde PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documentos/subir" `
  -H "Authorization: Bearer TU_TOKEN" `
  -F "expediente_id=ID_DEL_EXPEDIENTE" `
  -F "tipo_documento=Constancia" `
  -F "archivo=@C:\\Documentos\\constancia.pdf"
```

---

## 6. Pruebas automáticas

Usan `mongomock` (MongoDB simulado en memoria): **no necesitan MongoDB ni Docker** y no tocan datos reales. Con el `(.venv)` activo:

```powershell
python -m pytest -v
```

Todas deben salir **PASSED**. Para una sola prueba:

```powershell
python -m pytest tests/test_api.py::test_profesor_no_puede_consultar_expediente_de_otro -v
```

Cubren registro, inicio de sesión, perfil, validación, expedientes, documentos, carga y descarga, el esquema de Authorize y el aislamiento entre profesores. Cada función nueva debe llevar su prueba.

---

## 7. Cómo trabajamos con Git

1. **Antes de empezar:** cambia a `main` (clic en el nombre de la rama, abajo a la izquierda) y presiona **Sync** para traer lo último.
2. **Crea una rama** para tu tarea: **Ctrl + Shift + P › Git: Create Branch...** (por ejemplo `interfaz-carga`). No trabajes directo en `main`.
3. **Haz commits pequeños** desde **Source Control**: marca los archivos con **+**, escribe un mensaje claro (por ejemplo *"Agrega validación de tamaño de archivo"*) y presiona **Commit**.
4. **Corre las pruebas** antes de publicar.
5. **Publica** con **Publish Branch** (o **Sync** si ya existe) y abre un **Pull Request** en GitHub.
6. Otro integrante revisa y hace **Merge** a `main`.

Nunca subas: `.env`, `.venv/`, `storage/documentos/`, `node_modules/` (ya están en `.gitignore`).

---

## 8. Problemas comunes

| Problema | Solución |
|---|---|
| *"No se pudo conectar con MongoDB"* | Docker: revisa `docker compose ps`. Local: inicia el servicio en `services.msc` › **MongoDB Server**. |
| Compass: `ECONNREFUSED 127.0.0.1:27017` | MongoDB no está encendido (ver fila anterior). |
| `py -3.13` no encuentra Python | Revisa las versiones con `py --list`; instala Python 3.13. |
| Error al activar `.venv` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `port is already allocated` en Docker | Algo más usa el 8000 o el 27017: apaga `uvicorn` local o el servicio de MongoDB de Windows. |
| Todo responde **401** | Token vencido o mal pegado: login de nuevo y Authorize con el token nuevo. |
| http://localhost:5173 no abre | Espera a que termine `npm install` (`docker compose logs -f web`). |
| La interfaz dice *"No hay conexión con el servidor"* | La API no está corriendo: revisa `docker compose ps` o enciende `uvicorn`. |
| `npm` no se reconoce | Instala Node.js LTS y abre una terminal nueva (o usa Docker). |
| `/docs` no refleja un cambio | `docker compose restart api` y recarga con **Ctrl + F5**. |

---

## Colecciones e índices

- `profesores`: correo único, nombre, hash de contraseña y estado.
- `expedientes`: `profesor_id`, título, categoría y fecha.
- `documentos`: `profesor_id`, `expediente_id`, metadatos y ruta de almacenamiento.

## Seguridad y alcance

- El `profesor_id` no se recibe en las rutas: se obtiene del JWT validado.
- Las consultas de expedientes y documentos siempre incluyen el `profesor_id` autenticado.
- La contraseña se almacena con hash Argon2, nunca en texto plano.
- Todavía no hay OCR ni análisis con IA de los documentos.
- Es un punto de partida para desarrollo local, no una versión lista para producción. Antes de usar datos reales se deben añadir HTTPS, gestión segura de secretos, recuperación de cuenta, límites de intentos, auditoría, almacenamiento privado y más pruebas de acceso cruzado entre profesores.
- El dataset sintético debe permanecer separado en `dataset_documentos`; no mezclarlo con los expedientes privados.

## Despliegue

El almacenamiento local sirve para desarrollo con una sola instancia. Para producción con varias instancias conviene usar almacenamiento de objetos privado (por ejemplo, un bucket de Cloud Storage) y mantener la autorización por profesor antes de generar descargas. El `Dockerfile` ya está preparado para Cloud Run: usa la variable `PORT` que asigna el servicio.
