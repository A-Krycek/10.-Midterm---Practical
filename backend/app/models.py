from pydantic import BaseModel, Field, field_validator
import re

class ShortenRequest(BaseModel):
    original_url: str = Field(
        ..., 
        description="Dirección URL original a acortar",
        json_schema_extra={"example": "https://www.example.com/articulos/arquitectura-cloud"}
    )

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        url_pattern = re.compile(
            r'^(https?://)' # http:// o https://
            r'([a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})|localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # dominio/host
            r'(:\d+)?' # puerto opcional
            r'(/.*)?$', # ruta opcional
            re.IGNORECASE
        )
        if not url_pattern.match(v):
            raise ValueError("La URL debe ser válida y comenzar con http:// o https://")
        return v

class ShortenResponse(BaseModel):
    short_code: str = Field(..., description="Identificador único generado mediante UUID")
    original_url: str = Field(..., description="Dirección web original")
    short_url: str = Field(..., description="Enlace corto completo generado por el backend")

class UrlInfoResponse(BaseModel):
    short_code: str = Field(..., description="Identificador único generado mediante UUID")
    original_url: str = Field(..., description="Dirección web original")
    created_at: str = Field(..., description="Fecha y hora de creación en formato ISO 8601")
