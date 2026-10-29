import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

# Base de datos simulada en memoria para pruebas
MOCK_DB = {}

def mock_save_url_item(short_code: str, original_url: str, created_at: str):
    item = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": created_at
    }
    MOCK_DB[short_code] = item
    return item

def mock_get_url_item(short_code: str):
    return MOCK_DB.get(short_code)


@pytest.fixture(autouse=True)
def clean_mock_db():
    MOCK_DB.clear()
    yield
    MOCK_DB.clear()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@patch("app.main.save_url_item", side_effect=mock_save_url_item)
def test_shorten_url_valid(mock_save):
    payload = {
        "original_url": "https://www.example.com/articulos/arquitectura-cloud"
    }
    response = client.post("/shorten", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == payload["original_url"]
    assert data["short_code"] in data["short_url"]
    assert mock_save.called


def test_shorten_url_invalid():
    payload = {
        "original_url": "ftp://invalido.com"
    }
    response = client.post("/shorten", json=payload)
    assert response.status_code == 422


@patch("app.main.get_url_item", side_effect=mock_get_url_item)
@patch("app.main.save_url_item", side_effect=mock_save_url_item)
def test_redirect_to_original_url(mock_save, mock_get):
    # 1. Crear enlace
    payload = {"original_url": "https://aws.amazon.com/dynamodb/"}
    create_res = client.post("/shorten", json=payload)
    assert create_res.status_code == 201
    short_code = create_res.json()["short_code"]

    # 2. Redireccionar (sin seguir redirección para inspeccionar código de estado y Location header)
    redirect_res = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_res.status_code == 307
    assert redirect_res.headers["location"] == "https://aws.amazon.com/dynamodb/"


@patch("app.main.get_url_item", side_effect=mock_get_url_item)
def test_redirect_not_found(mock_get):
    fake_code = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/{fake_code}", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "Enlace corto no encontrado en el sistema."


@patch("app.main.get_url_item", side_effect=mock_get_url_item)
@patch("app.main.save_url_item", side_effect=mock_save_url_item)
def test_get_url_info(mock_save, mock_get):
    # 1. Crear enlace
    payload = {"original_url": "https://fastapi.tiangolo.com/"}
    create_res = client.post("/shorten", json=payload)
    short_code = create_res.json()["short_code"]

    # 2. Consultar información (GET /urls/{short_code})
    info_res = client.get(f"/urls/{short_code}")
    assert info_res.status_code == 200
    info_data = info_res.json()
    assert info_data["short_code"] == short_code
    assert info_data["original_url"] == payload["original_url"]
    assert "created_at" in info_data


@patch("app.main.get_url_item", side_effect=mock_get_url_item)
def test_get_url_info_not_found(mock_get):
    fake_code = "11111111-1111-1111-1111-111111111111"
    response = client.get(f"/urls/{fake_code}")
    assert response.status_code == 404
    assert response.json()["detail"] == "El enlace corto especificado no existe."
