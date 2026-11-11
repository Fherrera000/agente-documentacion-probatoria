// Comunicación con la API de FastAPI.
// Todas las rutas empiezan con /api; Vite las reenvía al backend (ver vite.config.js).
const BASE = "/api";
const CLAVE_TOKEN = "adp.token";

export function obtenerToken() {
  try {
    return localStorage.getItem(CLAVE_TOKEN);
  } catch {
    return null;
  }
}

export function guardarToken(token) {
  try {
    if (token) localStorage.setItem(CLAVE_TOKEN, token);
    else localStorage.removeItem(CLAVE_TOKEN);
  } catch {
    /* el navegador bloquea el almacenamiento: la sesión dura hasta recargar */
  }
}

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

// FastAPI devuelve {detail: "texto"} o, en errores de validación (422),
// {detail: [{loc: [...], msg: "..."}]}. Esto lo convierte en un mensaje legible.
function mensajeDeError(datos, estado) {
  const detalle = datos?.detail;
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle) && detalle.length) {
    return detalle
      .map((e) => {
        const campo = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "";
        return campo ? `${campo}: ${e.msg}` : e.msg;
      })
      .join(" · ");
  }
  if (estado === 0) return "No hay conexión con el servidor. ¿Está encendida la API?";
  return `Error ${estado}`;
}

async function peticion(ruta, { metodo = "GET", json, formulario, comoArchivo = false } = {}) {
  const encabezados = {};
  const token = obtenerToken();
  if (token) encabezados.Authorization = `Bearer ${token}`;
  let cuerpo;
  if (json !== undefined) {
    encabezados["Content-Type"] = "application/json";
    cuerpo = JSON.stringify(json);
  } else if (formulario) {
    cuerpo = formulario; // el navegador pone el Content-Type multipart
  }

  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, { method: metodo, headers: encabezados, body: cuerpo });
  } catch {
    throw new ErrorApi(mensajeDeError(null, 0), 0);
  }

  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => null);
    if (respuesta.status === 401 && token) {
      guardarToken(null);
      window.dispatchEvent(new Event("sesion-expirada"));
    }
    throw new ErrorApi(mensajeDeError(datos, respuesta.status), respuesta.status);
  }
  if (comoArchivo) return respuesta.blob();
  if (respuesta.status === 204) return null;
  return respuesta.json();
}

export const api = {
  registrar: (nombre, correo, contrasena) =>
    peticion("/auth/registro", { metodo: "POST", json: { nombre, correo, contrasena } }),
  iniciarSesion: (correo, contrasena) =>
    peticion("/auth/login", { metodo: "POST", json: { correo, contrasena } }),
  perfil: () => peticion("/profesores/yo"),

  listarExpedientes: () => peticion("/expedientes"),
  crearExpediente: (titulo, categoria_academica, descripcion) =>
    peticion("/expedientes", { metodo: "POST", json: { titulo, categoria_academica, descripcion: descripcion || null } }),

  listarDocumentos: (expedienteId) =>
    peticion(`/documentos${expedienteId ? `?expediente_id=${encodeURIComponent(expedienteId)}` : ""}`),
  subirDocumento: (expedienteId, archivo, tipoDocumento) => {
    const datos = new FormData();
    datos.append("expediente_id", expedienteId);
    datos.append("archivo", archivo);
    if (tipoDocumento) datos.append("tipo_documento", tipoDocumento);
    return peticion("/documentos/subir", { metodo: "POST", formulario: datos });
  },
  obtenerDocumento: (documentoId) => peticion(`/documentos/${encodeURIComponent(documentoId)}`),
  analizarDocumento: (documentoId) =>
    peticion(`/documentos/${encodeURIComponent(documentoId)}/analizar`, { metodo: "POST" }),
  descargarDocumento: (documentoId) =>
    peticion(`/documentos/${encodeURIComponent(documentoId)}/descargar`, { comoArchivo: true }),
};
