import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const CATEGORIAS = {
  DOC: "Docencia",
  VIN: "Vinculación",
  INV: "Investigación",
  GES: "Gestión",
};

// Tipos documentales del catálogo del paquete 2.1.
const TIPOS = ["Constancia", "Certificado", "Diploma", "Reconocimiento", "Nombramiento", "Informe", "Otro"];

const EXTENSIONES = [".pdf", ".jpg", ".jpeg", ".png"];
const MAX_MB = 10; // igual que MAX_UPLOAD_SIZE_MB del backend

function validarArchivo(archivo) {
  const nombre = archivo.name.toLowerCase();
  if (!EXTENSIONES.some((ext) => nombre.endsWith(ext))) return "Formato no permitido. Usa PDF, JPG o PNG.";
  if (archivo.size === 0) return "El archivo está vacío.";
  if (archivo.size > MAX_MB * 1024 * 1024) return `Supera ${MAX_MB} MB.`;
  return null;
}

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function Documentos() {
  const [expedientes, setExpedientes] = useState([]);
  const [expedienteId, setExpedienteId] = useState("");
  const [documentos, setDocumentos] = useState([]);
  const [error, setError] = useState("");
  const [creando, setCreando] = useState(false);

  async function cargarExpedientes(seleccionar) {
    try {
      const lista = await api.listarExpedientes();
      setExpedientes(lista);
      setExpedienteId((actual) => seleccionar || actual || lista[0]?.id || "");
      if (!lista.length) setCreando(true);
    } catch (err) {
      setError(err.message);
    }
  }

  async function cargarDocumentos(id) {
    if (!id) {
      setDocumentos([]);
      return;
    }
    try {
      setDocumentos(await api.listarDocumentos(id));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    cargarExpedientes();
  }, []);

  useEffect(() => {
    cargarDocumentos(expedienteId);
  }, [expedienteId]);

  const expediente = expedientes.find((e) => e.id === expedienteId);

  return (
    <div className="columna">
      {error && (
        <p className="mensaje error" role="alert">
          {error} <button className="enlace" onClick={() => setError("")}>Cerrar</button>
        </p>
      )}

      <section className="tarjeta">
        <div className="encabezado">
          <h2>Expediente</h2>
          {expedientes.length > 0 && !creando && (
            <button className="secundario" onClick={() => setCreando(true)}>
              + Nuevo expediente
            </button>
          )}
        </div>

        {expedientes.length > 0 && (
          <label className="selector">
            Expediente donde se guardarán los documentos
            <select value={expedienteId} onChange={(e) => setExpedienteId(e.target.value)}>
              {expedientes.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.titulo} · {CATEGORIAS[e.categoria_academica] || e.categoria_academica}
                </option>
              ))}
            </select>
          </label>
        )}
        {expediente?.descripcion && <p className="tenue">{expediente.descripcion}</p>}

        {creando && (
          <NuevoExpediente
            primero={expedientes.length === 0}
            alCancelar={expedientes.length ? () => setCreando(false) : null}
            alCrear={async (nuevo) => {
              setCreando(false);
              await cargarExpedientes(nuevo.id);
            }}
          />
        )}
      </section>

      {expedienteId && (
        <>
          <Carga expedienteId={expedienteId} alSubir={() => cargarDocumentos(expedienteId)} />
          <ListaDocumentos documentos={documentos} alError={setError} />
        </>
      )}
    </div>
  );
}

function NuevoExpediente({ primero, alCrear, alCancelar }) {
  const [titulo, setTitulo] = useState("");
  const [categoria, setCategoria] = useState("DOC");
  const [descripcion, setDescripcion] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      alCrear(await api.crearExpediente(titulo.trim(), categoria, descripcion.trim()));
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="formulario recuadro" onSubmit={enviar}>
      {primero && <p className="tenue">Aún no tienes expedientes. Crea el primero para poder subir documentos.</p>}
      {error && <p className="mensaje error">{error}</p>}
      <div className="fila">
        <label className="crece">
          Título
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)} required minLength={3} maxLength={250} placeholder="Ej. Docencia 2026-1" />
        </label>
        <label>
          Categoría académica
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            {Object.entries(CATEGORIAS).map(([clave, nombre]) => (
              <option key={clave} value={clave}>
                {clave} · {nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label>
        Descripción (opcional)
        <input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} maxLength={1000} />
      </label>
      <div className="acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Creando…" : "Crear expediente"}
        </button>
        {alCancelar && (
          <button type="button" className="secundario" onClick={alCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}

function Carga({ expedienteId, alSubir }) {
  const [tipo, setTipo] = useState("");
  const [arrastrando, setArrastrando] = useState(false);
  const [bitacora, setBitacora] = useState([]); // [{nombre, estado: "subiendo"|"ok"|"error", detalle}]
  const entrada = useRef(null);

  async function subir(archivos) {
    const lista = Array.from(archivos || []);
    if (!lista.length) return;
    setBitacora(lista.map((a) => ({ nombre: a.name, estado: "subiendo" })));
    for (let i = 0; i < lista.length; i++) {
      const archivo = lista[i];
      const problema = validarArchivo(archivo);
      let resultado;
      if (problema) {
        resultado = { estado: "error", detalle: problema };
      } else {
        try {
          await api.subirDocumento(expedienteId, archivo, tipo);
          resultado = { estado: "ok" };
        } catch (err) {
          resultado = { estado: "error", detalle: err.message };
        }
      }
      setBitacora((b) => b.map((r, j) => (j === i ? { ...r, ...resultado } : r)));
    }
    alSubir();
  }

  return (
    <section className="tarjeta">
      <h2>Subir documentos</h2>
      <p className="tenue">Constancias, diplomas, certificados, reconocimientos, nombramientos o informes. PDF, JPG o PNG de hasta {MAX_MB} MB.</p>
      <label className="selector">
        Tipo de documento (opcional, se aplica a todos los archivos que subas ahora)
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Sin especificar</option>
          {TIPOS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <div
        className={`zona ${arrastrando ? "encima" : ""}`}
        onClick={() => entrada.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entrada.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          subir(e.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
      >
        <p>
          <strong>Arrastra tus archivos aquí</strong> o haz clic para elegirlos
        </p>
        <input
          ref={entrada}
          type="file"
          multiple
          accept={EXTENSIONES.join(",")}
          hidden
          onChange={(e) => {
            subir(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {bitacora.length > 0 && (
        <ul className="bitacora">
          {bitacora.map((r, i) => (
            <li key={i} className={r.estado}>
              {r.estado === "subiendo" && "⏳ "}
              {r.estado === "ok" && "✓ "}
              {r.estado === "error" && "✗ "}
              {r.nombre}
              {r.detalle && <span> — {r.detalle}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ListaDocumentos({ documentos, alError }) {
  const [descargando, setDescargando] = useState("");

  async function descargar(doc) {
    setDescargando(doc.id);
    try {
      const blob = await api.descargarDocumento(doc.id);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = doc.nombre_archivo;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      alError(`No se pudo descargar ${doc.nombre_archivo}: ${err.message}`);
    } finally {
      setDescargando("");
    }
  }

  return (
    <section className="tarjeta">
      <div className="encabezado">
        <h2>Documentos del expediente</h2>
        <span className="contador">{documentos.length}</span>
      </div>
      {documentos.length === 0 ? (
        <p className="tenue">Todavía no hay documentos en este expediente.</p>
      ) : (
        <div className="tabla">
          <table>
            <thead>
              <tr>
                <th>Archivo</th>
                <th>Tipo</th>
                <th>Fecha de carga</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {documentos.map((d) => (
                <tr key={d.id}>
                  <td className="archivo">{d.nombre_archivo}</td>
                  <td>{d.tipo_documento || "—"}</td>
                  <td>{formatearFecha(d.fecha_carga)}</td>
                  <td>
                    <span className="etiqueta">{d.estado}</span>
                  </td>
                  <td>
                    {d.archivo_subido ? (
                      <button className="secundario" disabled={descargando === d.id} onClick={() => descargar(d)}>
                        {descargando === d.id ? "Descargando…" : "Descargar"}
                      </button>
                    ) : (
                      <span className="tenue">Sin archivo</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
