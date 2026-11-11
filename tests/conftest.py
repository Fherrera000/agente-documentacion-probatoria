import pytest

from app.ia import analizador as ia


@pytest.fixture(autouse=True)
def sin_ia_real(monkeypatch):
    """Las pruebas nunca llaman a Gemini, aunque exista GEMINI_API_KEY en el .env.
    Las pruebas que necesitan IA usan un analizador simulado."""
    def no_configurada():
        raise ia.IANoConfigurada("IA desactivada durante las pruebas")

    monkeypatch.setattr(ia, "obtener_analizador", no_configurada)
