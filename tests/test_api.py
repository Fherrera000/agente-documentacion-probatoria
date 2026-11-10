import mongomock
import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import database
from app.routes import auth as ruta_auth, expedientes as ruta_expedientes, documentos as ruta_documentos
from app.security import auth as seguridad


@pytest.fixture()
def cliente_api(monkeypatch):
    cliente_mongo = mongomock.MongoClient()
    bd = cliente_mongo["pruebas_agente"]
    bd.profesores.create_index("correo", unique=True)

    # Todas las rutas y la autenticación usan la misma base de datos simulada.
    monkeypatch.setattr(database, "base_datos", bd)
    monkeypatch.setattr(ruta_auth, "base_datos", bd)
    monkeypatch.setattr(ruta_expedientes, "base_datos", bd)
    monkeypatch.setattr(ruta_documentos, "base_datos", bd)
    monkeypatch.setattr(seguridad, "base_datos", bd)

    # Evita requerir un servidor MongoDB real durante las pruebas.
    monkeypatch.setattr(main, "comprobar_conexion", lambda: True)
    monkeypatch.setattr(main, "inicializar_indices", lambda: None)
    monkeypatch.setattr(main, "cerrar_conexion", lambda: None)

    with TestClient(main.app) as cliente:
        yield cliente
    cliente_mongo.close()


def registrar_y_entrar(cliente, correo="ana@example.com"):
    respuesta = cliente.post("/auth/registro", json={
        "nombre": "Ana Profesora",
        "correo": correo,
        "contrasena": "ContrasenaSegura123"
    })
    assert respuesta.status_code == 201, respuesta.text
    respuesta_login = cliente.post("/auth/login", json={
        "correo": correo,
        "contrasena": "ContrasenaSegura123"
    })
    assert respuesta_login.status_code == 200, respuesta_login.text
    token = respuesta_login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def crear_expediente(cliente, headers, titulo="Expediente de docencia"):
    return cliente.post("/expedientes", headers=headers, json={
        "titulo": titulo,
        "categoria_academica": "DOC",
        "descripcion": "Expediente para pruebas"
    })


def test_inicio_y_salud(cliente_api):
    assert cliente_api.get("/").status_code == 200
    assert cliente_api.get("/health").json()["estado"] == "correcto"


def test_registro_login_y_perfil(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    perfil = cliente_api.get("/profesores/yo", headers=headers)
    assert perfil.status_code == 200
    assert perfil.json()["correo"] == "ana@example.com"


def test_no_permite_correo_duplicado(cliente_api):
    registrar_y_entrar(cliente_api)
    respuesta = cliente_api.post("/auth/registro", json={
        "nombre": "Otra profesora",
        "correo": "ana@example.com",
        "contrasena": "ContrasenaSegura123"
    })
    assert respuesta.status_code == 409


def test_login_rechaza_contrasena_incorrecta(cliente_api):
    registrar_y_entrar(cliente_api)
    respuesta = cliente_api.post("/auth/login", json={
        "correo": "ana@example.com",
        "contrasena": "incorrecta"
    })
    assert respuesta.status_code == 401


def test_rutas_privadas_requieren_token(cliente_api):
    assert cliente_api.get("/profesores/yo").status_code == 401
    assert cliente_api.get("/expedientes").status_code == 401
    assert cliente_api.get("/documentos").status_code == 401


def test_crear_listar_y_obtener_expediente(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    creado = crear_expediente(cliente_api, headers)
    assert creado.status_code == 201, creado.text
    expediente_id = creado.json()["id"]
    assert cliente_api.get("/expedientes", headers=headers).json()[0]["id"] == expediente_id
    assert cliente_api.get(f"/expedientes/{expediente_id}", headers=headers).status_code == 200


def test_rechaza_categoria_academica_invalida(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    respuesta = cliente_api.post("/expedientes", headers=headers, json={
        "titulo": "Expediente inválido",
        "categoria_academica": "DEPORTE"
    })
    assert respuesta.status_code == 422


def test_profesor_no_puede_consultar_expediente_de_otro(cliente_api):
    headers_ana = registrar_y_entrar(cliente_api, "ana@example.com")
    expediente = crear_expediente(cliente_api, headers_ana).json()
    headers_luis = registrar_y_entrar(cliente_api, "luis@example.com")
    respuesta = cliente_api.get(f"/expedientes/{expediente['id']}", headers=headers_luis)
    assert respuesta.status_code == 404


def test_profesor_no_puede_listar_documentos_de_otro(cliente_api):
    headers_ana = registrar_y_entrar(cliente_api, "ana@example.com")
    expediente = crear_expediente(cliente_api, headers_ana).json()
    cliente_api.post("/documentos", headers=headers_ana, json={
        "expediente_id": expediente["id"],
        "nombre_archivo": "constancia.pdf",
        "tipo_documento": "Constancia",
        "ruta_storage": "documentos/constancia.pdf",
        "metadatos": {}
    })
    headers_luis = registrar_y_entrar(cliente_api, "luis@example.com")
    assert cliente_api.get("/documentos", headers=headers_luis).json() == []


def test_registrar_documento_en_expediente_propio(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    expediente = crear_expediente(cliente_api, headers).json()
    respuesta = cliente_api.post("/documentos", headers=headers, json={
        "expediente_id": expediente["id"],
        "nombre_archivo": "constancia.pdf",
        "tipo_documento": "Constancia",
        "ruta_storage": "documentos/constancia.pdf",
        "metadatos": {"anio": 2026}
    })
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["estado"] == "registrado"


def test_no_registra_documento_en_expediente_ajeno(cliente_api):
    headers_ana = registrar_y_entrar(cliente_api, "ana@example.com")
    expediente = crear_expediente(cliente_api, headers_ana).json()
    headers_luis = registrar_y_entrar(cliente_api, "luis@example.com")
    respuesta = cliente_api.post("/documentos", headers=headers_luis, json={
        "expediente_id": expediente["id"],
        "nombre_archivo": "constancia.pdf",
        "ruta_storage": "documentos/constancia.pdf"
    })
    assert respuesta.status_code == 404


def test_rechaza_id_de_expediente_invalido(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    assert cliente_api.get("/expedientes/no-es-id", headers=headers).status_code == 400


def test_eliminar_expediente_lo_oculta_de_listado(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    expediente = crear_expediente(cliente_api, headers).json()
    respuesta = cliente_api.delete(f"/expedientes/{expediente['id']}", headers=headers)
    assert respuesta.status_code == 204
    assert cliente_api.get("/expedientes", headers=headers).json() == []


def crear_expediente_prueba(cliente, headers):
    respuesta = crear_expediente(cliente, headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_subir_y_descargar_pdf(cliente_api, monkeypatch, tmp_path):
    from app.services import almacenamiento

    monkeypatch.setattr(almacenamiento, "RUTA_DOCUMENTOS", tmp_path / "documentos")
    headers = registrar_y_entrar(cliente_api)
    expediente_id = crear_expediente_prueba(cliente_api, headers)
    contenido = b"%PDF-1.4\ncontenido de prueba\n%%EOF"

    subida = cliente_api.post(
        "/documentos/subir",
        headers=headers,
        data={"expediente_id": expediente_id, "tipo_documento": "Constancia"},
        files={"archivo": ("constancia.pdf", contenido, "application/pdf")},
    )
    assert subida.status_code == 201, subida.text
    documento_id = subida.json()["id"]
    assert subida.json()["estado"] == "cargado"

    descarga = cliente_api.get(f"/documentos/{documento_id}/descargar", headers=headers)
    assert descarga.status_code == 200
    assert descarga.content == contenido
    assert "constancia.pdf" in descarga.headers["content-disposition"]


def test_rechaza_extension_no_permitida(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    expediente_id = crear_expediente_prueba(cliente_api, headers)
    respuesta = cliente_api.post(
        "/documentos/subir",
        headers=headers,
        data={"expediente_id": expediente_id},
        files={"archivo": ("programa.exe", b"MZcontenido", "application/octet-stream")},
    )
    assert respuesta.status_code == 415


def test_rechaza_archivo_con_firma_incorrecta(cliente_api):
    headers = registrar_y_entrar(cliente_api)
    expediente_id = crear_expediente_prueba(cliente_api, headers)
    respuesta = cliente_api.post(
        "/documentos/subir",
        headers=headers,
        data={"expediente_id": expediente_id},
        files={"archivo": ("falso.pdf", b"esto no es un pdf", "application/pdf")},
    )
    assert respuesta.status_code == 415


def test_no_permite_subir_archivo_a_expediente_ajeno(cliente_api):
    headers_ana = registrar_y_entrar(cliente_api, "ana@example.com")
    expediente_ana = crear_expediente_prueba(cliente_api, headers_ana)
    headers_luis = registrar_y_entrar(cliente_api, "luis@example.com")
    respuesta = cliente_api.post(
        "/documentos/subir",
        headers=headers_luis,
        data={"expediente_id": expediente_ana},
        files={"archivo": ("constancia.pdf", b"%PDF-1.4\nprueba", "application/pdf")},
    )
    assert respuesta.status_code == 404


def test_profesor_no_puede_descargar_archivo_de_otro(cliente_api, monkeypatch, tmp_path):
    from app.services import almacenamiento

    monkeypatch.setattr(almacenamiento, "RUTA_DOCUMENTOS", tmp_path / "documentos")
    headers_ana = registrar_y_entrar(cliente_api, "ana@example.com")
    expediente_ana = crear_expediente_prueba(cliente_api, headers_ana)
    subida = cliente_api.post(
        "/documentos/subir",
        headers=headers_ana,
        data={"expediente_id": expediente_ana},
        files={"archivo": ("privado.pdf", b"%PDF-1.4\nprivado", "application/pdf")},
    )
    assert subida.status_code == 201, subida.text

    headers_luis = registrar_y_entrar(cliente_api, "luis@example.com")
    descarga = cliente_api.get(f"/documentos/{subida.json()['id']}/descargar", headers=headers_luis)
    assert descarga.status_code == 404


def test_descarga_requiere_autenticacion(cliente_api):
    respuesta = cliente_api.get("/documentos/" + "0" * 24 + "/descargar")
    assert respuesta.status_code == 401
