import uuid
from datetime import datetime, timezone
import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import ClientError

from app.config import settings
from app.models import ShortenRequest, ShortenResponse, UrlInfoResponse
from app.db import save_url_item, get_url_item

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("url_shortener.api")

app = FastAPI(
    title="AWS URL Shortener API",
    description="API REST para acortar URLs con persistencia en Amazon DynamoDB y ejecución en Amazon EC2.",
    version="1.0.0"
)

# Configuración de CORS para permitir solicitudes desde la interfaz en S3
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "AWS URL Shortener API está en funcionamiento",
        "endpoints": {
            "shorten": "POST /shorten",
            "info": "GET /urls/{short_code}",
            "redirect": "GET /{short_code}",
            "docs": "GET /docs"
        }
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "table": settings.DYNAMODB_TABLE_NAME, "region": settings.AWS_REGION}


@app.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Shortener"]
)
def shorten_url(payload: ShortenRequest):
    """
    Crea un enlace corto generando un identificador UUID dinámico
    y almacenando la información en DynamoDB.
    """
    # Generación dinámica de UUID
    short_code = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    original_url = str(payload.original_url)

    try:
        save_url_item(
            short_code=short_code,
            original_url=original_url,
            created_at=created_at
        )
    except ClientError as e:
        logger.error(f"Error al escribir en DynamoDB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el enlace en la base de datos: {e.response['Error']['Message']}"
        )
    except Exception as e:
        logger.error(f"Error inesperado al guardar el enlace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al procesar la solicitud."
        )

    # Construir URL corta pública
    base = settings.BASE_URL.rstrip("/")
    short_url = f"{base}/{short_code}"

    return ShortenResponse(
        short_code=short_code,
        original_url=original_url,
        short_url=short_url
    )


@app.get(
    "/urls/{short_code}",
    response_model=UrlInfoResponse,
    status_code=status.HTTP_200_OK,
    tags=["Shortener"]
)
def get_url_info(short_code: str):
    """
    Consulta DynamoDB y devuelve los metadatos del enlace (UUID, URL original y fecha de creación).
    """
    try:
        item = get_url_item(short_code)
    except ClientError as e:
        logger.error(f"Error al consultar DynamoDB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la base de datos: {e.response['Error']['Message']}"
        )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El enlace corto especificado no existe."
        )

    return UrlInfoResponse(
        short_code=item["short_code"],
        original_url=item["original_url"],
        created_at=item["created_at"]
    )


@app.get(
    "/{short_code}",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    tags=["Redirect"]
)
def redirect_to_url(short_code: str):
    """
    Redirecciona automáticamente al usuario a la URL original mediante HTTP 307.
    Si el short_code no existe en DynamoDB, responde con 404 Not Found.
    """
    try:
        item = get_url_item(short_code)
    except ClientError as e:
        logger.error(f"Error al consultar DynamoDB para redirección: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la redirección en la base de datos."
        )

    if not item or "original_url" not in item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enlace corto no encontrado en el sistema."
        )

    # Redirección HTTP real hacia la URL original
    return RedirectResponse(
        url=item["original_url"],
        status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
