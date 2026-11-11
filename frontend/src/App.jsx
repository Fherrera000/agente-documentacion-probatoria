import { useEffect, useState } from "react";
import { api, guardarToken, obtenerToken } from "./api.js";
import Acceso from "./components/Acceso.jsx";
import Documentos from "./components/Documentos.jsx";

export default function App() {
  const [profesor, setProfesor] = useState(null);
  const [cargando, setCargando] = useState(Boolean(obtenerToken()));
  const [aviso, setAviso] = useState("");

  // Si ya hay un token guardado, recupera el perfil para entrar directo.
  useEffect(() => {
    if (!obtenerToken()) return;
    api
      .perfil()
      .then(setProfesor)
      .catch(() => guardarToken(null))
      .finally(() => setCargando(false));
  }, []);

  // Cuando el token vence, la API responde 401 y volvemos al inicio de sesión.
  useEffect(() => {
    const alExpirar = () => {
      setProfesor(null);
      setAviso("Tu sesión expiró. Inicia sesión de nuevo.");
    };
    window.addEventListener("sesion-expirada", alExpirar);
    return () => window.removeEventListener("sesion-expirada", alExpirar);
  }, []);

  async function alEntrar(token) {
    guardarToken(token);
    setAviso("");
    setProfesor(await api.perfil());
  }

  function salir() {
    guardarToken(null);
    setProfesor(null);
  }

  if (cargando) return <p className="centrado">Cargando…</p>;

  return (
    <>
      <header className="barra">
        <div className="marca">
          <span className="logo">AD</span>
          <div>
            <strong>Agente de Documentación Probatoria</strong>
            <small>Expedientes docentes · UABC</small>
          </div>
        </div>
        {profesor && (
          <div className="usuario">
            <span>
              {profesor.nombre}
              <small>{profesor.correo}</small>
            </span>
            <button className="secundario claro" onClick={salir}>
              Cerrar sesión
            </button>
          </div>
        )}
      </header>
      <main>{profesor ? <Documentos /> : <Acceso alEntrar={alEntrar} aviso={aviso} />}</main>
    </>
  );
}
