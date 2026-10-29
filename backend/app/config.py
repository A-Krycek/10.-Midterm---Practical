import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env si existe
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    # Configuración de AWS y DynamoDB
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "url_shortener_links")
    DYNAMODB_ENDPOINT_URL: str | None = os.getenv("DYNAMODB_ENDPOINT_URL", None)

    # URL base del backend para componer el enlace corto
    # En producción EC2, se configura con: http://<IP_PUBLICA_EC2>:8000
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    # Orígenes permitidos para CORS (por defecto "*" o separados por comas)
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

settings = Settings()
