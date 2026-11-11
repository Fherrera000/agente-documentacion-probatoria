from pydantic_settings import BaseSettings, SettingsConfigDict

class Configuracion(BaseSettings):
    app_env: str = "development"
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_database: str = "agente_documentacion_probatoria"
    jwt_secret: str = "solo-para-desarrollo-cambiar"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    storage_path: str = "storage"
    max_upload_size_mb: int = 10
    # Inteligencia artificial (paquete 3.2). Llave gratuita: https://aistudio.google.com/apikey
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    # Si el modelo principal está saturado (503), sin cuota (429) o no disponible (404),
    # se intenta con estos, en orden. Separados por coma; vacío = sin respaldo.
    gemini_modelos_respaldo: str = "gemini-3.6-flash,gemini-3.5-flash-lite"
    gemini_timeout_segundos: int = 60
    ia_analisis_automatico: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

configuracion = Configuracion()
