import { useState } from "react";
import { api } from "../api.js";

// Pantalla de inicio de sesión y registro de profesores.
export default function Acceso({ alEntrar, aviso }) {
  const [modo, setModo] = useState("entrar"); // "entrar" | "registro"
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");
  const [enviando, setEnviando] = useState(false);

  function cambiarModo(nuevo) {
    setModo(nuevo);
    setError("");
    setExito("");
  }

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setExito("");
    setEnviando(true);
    try {
      if (modo === "registro") {
        await api.registrar(nombre.trim(), correo.trim(), contrasena);
        setExito("Cuenta creada. Ahora inicia sesión.");
        setModo("entrar");
        setContrasena("");
      } else {
        const { access_token } = await api.iniciarSesion(correo.trim(), contrasena);
        await alEntrar(access_token);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  const registro = modo === "registro";
  const reglas = [
    ["10 o más caracteres", contrasena.length >= 10],
    ["Una mayúscula", /[A-Z]/.test(contrasena)],
    ["Una minúscula", /[a-z]/.test(contrasena)],
    ["Un número", /\d/.test(contrasena)],
    ["Un carácter especial", /[^A-Za-z0-9]/.test(contrasena)],
  ];
  const contrasenaValida = reglas.every(([, cumple]) => cumple);

  return (
    <section className="tarjeta acceso">
      <div className="bienvenida">
        <h1>{registro ? "Crea tu cuenta" : "Bienvenido(a)"}</h1>
        <p>Gestiona y organiza tu documentación probatoria docente.</p>
      </div>
      <div className="pestanas" role="tablist">
        <button role="tab" aria-selected={!registro} className={!registro ? "activa" : ""} onClick={() => cambiarModo("entrar")}>
          Iniciar sesión
        </button>
        <button role="tab" aria-selected={registro} className={registro ? "activa" : ""} onClick={() => cambiarModo("registro")}>
          Crear cuenta
        </button>
      </div>

      {aviso && !error && <p className="mensaje aviso">{aviso}</p>}
      {exito && <p className="mensaje ok">{exito}</p>}
      {error && <p className="mensaje error">{error}</p>}

      <form onSubmit={enviar} className="formulario">
        {registro && (
          <label>
            Nombre completo
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} required minLength={2} maxLength={150} autoComplete="name" />
          </label>
        )}
        <label>
          Correo institucional
          <input type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} required autoComplete="email" />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            required
            minLength={registro ? 10 : 1}
            maxLength={128}
            autoComplete={registro ? "new-password" : "current-password"}
          />
          {registro && (
            <ul className="requisitos">
              {reglas.map(([texto, cumple]) => (
                <li key={texto} className={cumple ? "cumple" : ""}>{texto}</li>
              ))}
            </ul>
          )}
        </label>
        <button type="submit" disabled={enviando || (registro && !contrasenaValida)}>
          {enviando ? "Un momento…" : registro ? "Crear cuenta" : "Entrar"}
        </button>
      </form>
    </section>
  );
}
