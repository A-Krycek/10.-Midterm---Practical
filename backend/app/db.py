import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger("url_shortener.db")

def get_dynamodb_resource():
    """
    Obtiene el recurso DynamoDB de Boto3.
    En Amazon EC2, Boto3 utiliza de manera automática el rol IAM asignado a la instancia
    (Instance Profile), por lo que no es necesario guardar claves estáticas en el código.
    """
    kwargs = {"region_name": settings.AWS_REGION}
    if settings.DYNAMODB_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.DYNAMODB_ENDPOINT_URL
    return boto3.resource("dynamodb", **kwargs)

def get_table():
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(settings.DYNAMODB_TABLE_NAME)

def save_url_item(short_code: str, original_url: str, created_at: str) -> Dict[str, Any]:
    """
    Inserta un nuevo registro de enlace corto en DynamoDB.
    """
    table = get_table()
    item = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": created_at
    }
    try:
        table.put_item(Item=item)
        return item
    except ClientError as e:
        logger.error(f"Error al guardar en DynamoDB: {e.response['Error']['Message']}")
        raise e

def get_url_item(short_code: str) -> Optional[Dict[str, Any]]:
    """
    Consulta y recupera un enlace por su clave de partición (short_code).
    """
    table = get_table()
    try:
        response = table.get_item(Key={"short_code": short_code})
        return response.get("Item")
    except ClientError as e:
        logger.error(f"Error al consultar DynamoDB: {e.response['Error']['Message']}")
        raise e
