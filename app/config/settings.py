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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

configuracion = Configuracion()
