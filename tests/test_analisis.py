"""Pruebas del paquete 3.2: análisis de documentos con IA.

No se conectan a Gemini: usan un analizador simulado o prueban directamente la
validación de las respuestas del modelo.
"""
import json
from types import SimpleNamespace

import pytest

from app.ia import analizador as ia
from app.ia.catalogos import calcular_periodo, periodo_de_fecha
from test_api import cliente_api, crear_expediente_prueba, registrar_y_entrar  # noqa: F401

TEXTO_CONSTANCIA = (
    "UNIVERSIDAD AUTÓNOMA DE BAJA CALIFORNIA. Facultad de Ingeniería Mexicali. "
    "Hace constar que impartió la unidad de aprendizaje Programación Estructurada "
    "del 2 de febrero al 5 de junio de 2026, con un total de 64 horas. "
    "Mexicali, B.C., a 20 de junio de 2026."
)

RESPUESTA_BUENA = {
    "tipo_documento": "CON",
    "categoria_academica": "DOC",
    "titulo_actividad": "Programación Estructurada",
    "institucion_emisora": "Universidad Autónoma de Baja California",
    "fecha_emision": "2026-06-20",
    "fecha_inicio": "2026-02-02",
    "fecha_fin": "2026-06-05",
    "horas": 64,
    "resumen": "Constancia de impartición de una unidad de aprendizaje.",
    "evidencia": "impartió la unidad de aprendizaje Programación Estructurada",
    "confianza": 0.94,
    "requiere_revision": False,
    "motivos_revision": [],
    "texto": TEXTO_CONSTANCIA,
}


# ---------------------------------------------------------------- catálogos y periodos
def test_periodo_por_fecha():
    assert periodo_de_fecha("2026-03-10") == "2026-1"
    assert periodo_de_fecha("2025-10-01") == "2025-2"
    assert periodo_de_fecha("2025-07-05") == "2025-5"
    assert periodo_de_fecha("fecha rara") is None


def test_actividad_en_dos_periodos_es_multi():
    assert calcular_periodo("2025-10-06", "2026-03-20", None) == "MULTI"


def test_sin_fechas_es_sin_periodo():
    assert calcular_periodo(None, None, None) == "S/P"


# ---------------------------------------------------------------- validación de la respuesta (R03)
def test_respuesta_correcta_no_requiere_revision():
    r = ia.interpretar(dict(RESPUESTA_BUENA), "", "modelo-prueba")
    assert r["categoria_academica"] == "DOC"
    assert r["periodo_academico"] == "2026-1"
    assert r["anio"] == 2026
    assert r["horas"] == 64
    assert r["requiere_revision"] is False, r["motivos_revision"]


def test_detecta_titulo_inventado():
    datos = dict(RESPUESTA_BUENA, titulo_actividad="Diplomado en Robótica Submarina")
    r = ia.interpretar(datos, TEXTO_CONSTANCIA, "modelo-prueba")
    assert r["requiere_revision"] is True
    assert any("posible dato inventado" in m for m in r["motivos_revision"])


def test_detecta_evidencia_que_no_esta_en_el_documento():
    datos = dict(RESPUESTA_BUENA, evidencia="participó como ponente en un congreso internacional")
    r = ia.interpretar(datos, TEXTO_CONSTANCIA, "modelo-prueba")
    assert r["requiere_revision"] is True


def test_usa_texto_del_pdf_como_referencia_antes_que_el_de_la_ia():
    datos = dict(RESPUESTA_BUENA, texto="texto inventado por el modelo " * 5)
    r = ia.interpretar(datos, TEXTO_CONSTANCIA, "modelo-prueba")
    assert r["origen_texto"] == "pdf"
    assert r["requiere_revision"] is False, r["motivos_revision"]


def test_descarta_categoria_fuera_de_catalogo():
    r = ia.interpretar(dict(RESPUESTA_BUENA, categoria_academica="XYZ"), TEXTO_CONSTANCIA, "m")
    assert r["categoria_academica"] is None
    assert r["requiere_revision"] is True


def test_confianza_baja_va_a_revision():
    r = ia.interpretar(dict(RESPUESTA_BUENA, confianza=0.4), TEXTO_CONSTANCIA, "m")
    assert r["requiere_revision"] is True


def test_fecha_con_formato_invalido_se_deja_vacia():
    r = ia.interpretar(dict(RESPUESTA_BUENA, fecha_emision="20 de junio"), TEXTO_CONSTANCIA, "m")
    assert r["fecha_emision"] is None


def test_llamada_a_gemini_con_cliente_simulado():
    pytest.importorskip("google.genai")
    llamadas = []

    def generar(model, contents, config):
        llamadas.append(model)
        return SimpleNamespace(text=json.dumps(RESPUESTA_BUENA))

    cliente = SimpleNamespace(models=SimpleNamespace(generate_content=generar))
    r = ia.AnalizadorGemini(cliente=cliente, modelo="gemini-prueba").analizar(b"%PDF-1.4", "application/pdf", TEXTO_CONSTANCIA)
    assert llamadas == ["gemini-prueba"]
    assert r["categoria_academica"] == "DOC"


# ---------------------------------------------------------------- flujo completo por la API
class AnalizadorSimulado:
    def __init__(self, respuesta=None, error=None):
        self.respuesta, self.error, self.llamadas = respuesta or RESPUESTA_BUENA, error, 0

    def analizar(self, contenido, content_type, texto_local=""):
        self.llamadas += 1
        if self.error:
            raise self.error
        return ia.interpretar(dict(self.respuesta), texto_local, "simulado")


@pytest.fixture()
def almacenamiento_temporal(monkeypatch, tmp_path):
    from app.services import almacenamiento

    monkeypatch.setattr(almacenamiento, "RUTA_DOCUMENTOS", tmp_path / "documentos")


def subir_pdf(cliente, headers, expediente_id, nombre="constancia.pdf", contenido=b"%PDF-1.4\nconstancia\n%%EOF"):
    respuesta = cliente.post("/documentos/subir", headers=headers, data={"expediente_id": expediente_id},
                             files={"archivo": (nombre, contenido, "application/pdf")})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_subir_documento_lo_analiza_automaticamente(cliente_api, almacenamiento_temporal, monkeypatch):
    simulado = AnalizadorSimulado()
    monkeypatch.setattr(ia, "obtener_analizador", lambda: simulado)
    headers = registrar_y_entrar(cliente_api)
    documento_id = subir_pdf(cliente_api, headers, crear_expediente_prueba(cliente_api, headers))

    detalle = cliente_api.get(f"/documentos/{documento_id}", headers=headers).json()
    assert simulado.llamadas == 1
    assert detalle["analisis_estado"] == "completado"
    assert detalle["analisis"]["categoria_academica"] == "DOC"
    assert detalle["analisis"]["periodo_academico"] == "2026-1"
    assert "Programación Estructurada" in detalle["texto_extraido"]

    lista = cliente_api.get("/documentos", headers=headers).json()
    assert lista[0]["analisis"]["categoria_academica"] == "DOC"
    assert "texto_extraido" not in lista[0]


def test_sin_llave_queda_como_no_configurado(cliente_api, almacenamiento_temporal):
    headers = registrar_y_entrar(cliente_api)
    documento_id = subir_pdf(cliente_api, headers, crear_expediente_prueba(cliente_api, headers))
    detalle = cliente_api.get(f"/documentos/{documento_id}", headers=headers).json()
    assert detalle["analisis_estado"] == "no_configurado"
    assert detalle["analisis_error"]


def test_error_de_la_ia_no_rompe_la_carga(cliente_api, almacenamiento_temporal, monkeypatch):
    monkeypatch.setattr(ia, "obtener_analizador", lambda: AnalizadorSimulado(error=RuntimeError("cuota excedida")))
    headers = registrar_y_entrar(cliente_api)
    documento_id = subir_pdf(cliente_api, headers, crear_expediente_prueba(cliente_api, headers))
    detalle = cliente_api.get(f"/documentos/{documento_id}", headers=headers).json()
    assert detalle["analisis_estado"] == "error"
    assert cliente_api.get(f"/documentos/{documento_id}/descargar", headers=headers).status_code == 200


def test_reanalizar_documento(cliente_api, almacenamiento_temporal, monkeypatch):
    headers = registrar_y_entrar(cliente_api)
    documento_id = subir_pdf(cliente_api, headers, crear_expediente_prueba(cliente_api, headers))
    simulado = AnalizadorSimulado()
    monkeypatch.setattr(ia, "obtener_analizador", lambda: simulado)

    respuesta = cliente_api.post(f"/documentos/{documento_id}/analizar", headers=headers)
    assert respuesta.status_code == 202
    assert cliente_api.get(f"/documentos/{documento_id}", headers=headers).json()["analisis_estado"] == "completado"


def test_marca_duplicado(cliente_api, almacenamiento_temporal, monkeypatch):
    monkeypatch.setattr(ia, "obtener_analizador", lambda: AnalizadorSimulado())
    headers = registrar_y_entrar(cliente_api)
    expediente_id = crear_expediente_prueba(cliente_api, headers)
    subir_pdf(cliente_api, headers, expediente_id)
    segundo = subir_pdf(cliente_api, headers, expediente_id, nombre="copia.pdf")
    detalle = cliente_api.get(f"/documentos/{segundo}", headers=headers).json()
    assert detalle["analisis_estado"] == "revision"
    assert any("duplicado" in m for m in detalle["analisis"]["motivos_revision"])


def test_profesor_no_puede_ver_ni_analizar_documento_de_otro(cliente_api, almacenamiento_temporal):
    headers_ana = registrar_y_entrar(cliente_api, "ana@example.com")
    documento_id = subir_pdf(cliente_api, headers_ana, crear_expediente_prueba(cliente_api, headers_ana))
    headers_luis = registrar_y_entrar(cliente_api, "luis@example.com")
    assert cliente_api.get(f"/documentos/{documento_id}", headers=headers_luis).status_code == 404
    assert cliente_api.post(f"/documentos/{documento_id}/analizar", headers=headers_luis).status_code == 404


def test_documento_anterior_a_la_ia_se_muestra_sin_analizar(cliente_api, almacenamiento_temporal):
    from app.config import database

    headers = registrar_y_entrar(cliente_api)
    documento_id = subir_pdf(cliente_api, headers, crear_expediente_prueba(cliente_api, headers))
    # Simula un documento cargado antes del paquete 3.2 (sin campos de análisis).
    from bson import ObjectId
    database.base_datos.documentos.update_one({"_id": ObjectId(documento_id)},
                                              {"$unset": {"analisis_estado": "", "analisis_error": ""}})
    detalle = cliente_api.get(f"/documentos/{documento_id}", headers=headers).json()
    assert detalle["analisis_estado"] == "sin_analizar"
    assert detalle["fecha_carga"].endswith("+00:00")


# ---------------------------------------------------------------- resistencia a fallas de Google
class ErrorGoogle(Exception):
    def __init__(self, code):
        super().__init__(f"{code} error simulado")
        self.code = code


def cliente_que_falla(fallas: dict):
    """Cliente simulado: los modelos en `fallas` lanzan ese código; los demás responden bien."""
    usados = []

    def generar(model, contents, config):
        usados.append(model)
        if model in fallas:
            raise ErrorGoogle(fallas[model])
        return SimpleNamespace(text=json.dumps(RESPUESTA_BUENA))

    return SimpleNamespace(models=SimpleNamespace(generate_content=generar)), usados


def test_si_el_modelo_esta_saturado_usa_el_de_respaldo(monkeypatch):
    pytest.importorskip("google.genai")
    cliente, usados = cliente_que_falla({"principal": 503})
    analizador = ia.AnalizadorGemini(cliente=cliente, modelo="principal", respaldo=["respaldo"])
    r = analizador.analizar(b"%PDF-1.4", "application/pdf", TEXTO_CONSTANCIA)
    assert usados == ["principal", "respaldo"]
    assert r["modelo"] == "respaldo"


def test_si_todos_fallan_da_mensaje_entendible():
    pytest.importorskip("google.genai")
    cliente, _ = cliente_que_falla({"principal": 503, "respaldo": 503})
    analizador = ia.AnalizadorGemini(cliente=cliente, modelo="principal", respaldo=["respaldo"])
    with pytest.raises(ia.ErrorIA, match="saturados"):
        analizador.analizar(b"%PDF-1.4", "application/pdf", TEXTO_CONSTANCIA)


def test_llave_invalida_no_prueba_otros_modelos():
    pytest.importorskip("google.genai")
    cliente, usados = cliente_que_falla({"principal": 403})
    analizador = ia.AnalizadorGemini(cliente=cliente, modelo="principal", respaldo=["respaldo"])
    with pytest.raises(ia.ErrorIA, match="llave"):
        analizador.analizar(b"%PDF-1.4", "application/pdf", TEXTO_CONSTANCIA)
    assert usados == ["principal"]


def test_error_de_ia_se_guarda_con_mensaje_para_el_usuario(cliente_api, almacenamiento_temporal, monkeypatch):
    class Saturado:
        def analizar(self, *args):
            raise ia.ErrorIA(ia.mensaje_de_error(503, "m"))

    monkeypatch.setattr(ia, "obtener_analizador", lambda: Saturado())
    headers = registrar_y_entrar(cliente_api)
    documento_id = subir_pdf(cliente_api, headers, crear_expediente_prueba(cliente_api, headers))
    detalle = cliente_api.get(f"/documentos/{documento_id}", headers=headers).json()
    assert detalle["analisis_estado"] == "error"
    assert "saturados" in detalle["analisis_error"]


def test_instrucciones_incluyen_fecha_actual():
    from datetime import date
    from app.ia.analizador import instrucciones_con_fecha

    texto = instrucciones_con_fecha()
    assert f"FECHA ACTUAL: {date.today().isoformat()}" in texto