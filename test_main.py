import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import json
from datetime import datetime
from unittest.mock import patch, Mock
import requests
import base64

from main import app
from database import Base, get_db, ApiToken, SuperAdmin
from security import create_access_token, get_password_hash

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)

# Test data
TEST_SUPERADMIN = {
    "username": "test_admin",
    "password": "test_password"
}

TEST_TOKEN = {
    "description": "Test API Token",
    "token": "test-api-token"
}

VALID_CFDI = {
    "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
    "emisor_rfc": "CDZ050722LA9",
    "receptor_rfc": "XIN06112344A",
    "total": "12000.00"
}

# Mock SAT service response
MOCK_SAT_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <ConsultaResponse xmlns="http://tempuri.org/">
            <ConsultaResult>
                <CodigoEstatus>S - Comprobante obtenido satisfactoriamente.</CodigoEstatus>
                <Estado>Vigente</Estado>
                <EsCancelable>Cancelable sin aceptación</EsCancelable>
                <EstatusCancelacion>No cancelado</EstatusCancelacion>
                <ValidacionEFOS>200</ValidacionEFOS>
            </ConsultaResult>
        </ConsultaResponse>
    </soap:Body>
</soap:Envelope>"""

def get_basic_auth_header(username: str, password: str) -> dict:
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

@pytest.fixture(autouse=True)
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create test API token and superadmin
    db = TestingSessionLocal()
    try:
        # Add test token
        db_token = ApiToken(
            description=TEST_TOKEN["description"],
            token=TEST_TOKEN["token"]
        )
        db.add(db_token)
        
        # Add test superadmin
        db_admin = SuperAdmin(
            username=TEST_SUPERADMIN["username"],
            hashed_password=get_password_hash(TEST_SUPERADMIN["password"])
        )
        db.add(db_admin)
        
        db.commit()
    finally:
        db.close()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_sat_service():
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = MOCK_SAT_RESPONSE.encode('utf-8')
        mock_post.return_value = mock_response
        yield mock_post

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_verify_cfdi_unauthorized():
    response = client.post("/verify-cfdi", json=VALID_CFDI)
    assert response.status_code == 403

def test_verify_cfdi_with_invalid_token():
    response = client.post(
        "/verify-cfdi",
        json=VALID_CFDI,
        headers={"Authorization": "Bearer invalid-token"}
    )
    # Accept either 401 Unauthorized or 403 Forbidden
    assert response.status_code in [401, 403]
    assert "detail" in response.json()

def test_verify_cfdi_batch_unauthorized():
    response = client.post("/verify-cfdi-batch", json={"cfdis": [VALID_CFDI]})
    assert response.status_code == 403

def test_check_rfc_efos_unauthorized():
    response = client.post("/check-rfc-efos", json={"rfc": "TEST010101TEST"})
    assert response.status_code == 403

def test_check_rfc_efos_batch_unauthorized():
    response = client.post("/check-rfc-efos-batch", json={"rfcs": ["TEST010101TEST"]})
    assert response.status_code == 403

def test_update_efos_database_unauthorized():
    response = client.post("/update-efos-database")
    assert response.status_code == 401

def test_admin_endpoints_unauthorized():
    # Test token management endpoints
    response = client.get("/admin/tokens")
    assert response.status_code == 401
    
    response = client.post("/admin/tokens", json=TEST_TOKEN)
    assert response.status_code == 401
    
    response = client.get("/admin/tokens/1")
    assert response.status_code == 401
    
    response = client.put("/admin/tokens/1", json={"description": "Updated"})
    assert response.status_code == 401
    
    response = client.delete("/admin/tokens/1")
    assert response.status_code == 401
    
    response = client.post("/admin/tokens/1/regenerate")
    assert response.status_code == 401

    # Test superadmin management endpoints
    response = client.post("/admin/superadmins", json=TEST_SUPERADMIN)
    assert response.status_code == 401
    
    response = client.put(
        f"/admin/superadmins/{TEST_SUPERADMIN['username']}/password",
        json={"password": "new_password"}
    )
    assert response.status_code == 401
    
    response = client.delete(f"/admin/superadmins/{TEST_SUPERADMIN['username']}")
    assert response.status_code == 401

def test_verify_cfdi_with_valid_token(mock_sat_service):
    response = client.post(
        "/verify-cfdi",
        json=VALID_CFDI,
        headers={"Authorization": f"Bearer {TEST_TOKEN['token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "Vigente"
    assert data["es_cancelable"] == "Cancelable sin aceptación"
    assert data["codigo_estatus"] == "S - Comprobante obtenido satisfactoriamente."

def test_verify_cfdi_batch_with_valid_token(mock_sat_service):
    response = client.post(
        "/verify-cfdi-batch",
        json={"cfdis": [VALID_CFDI]},
        headers={"Authorization": f"Bearer {TEST_TOKEN['token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["response"]["estado"] == "Vigente"

def test_check_rfc_efos_with_valid_token():
    response = client.post(
        "/check-rfc-efos",
        json={"rfc": "TEST010101TEST"},
        headers={"Authorization": f"Bearer {TEST_TOKEN['token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "rfc" in data
    assert "is_in_efos_list" in data

def test_check_rfc_efos_batch_with_valid_token():
    response = client.post(
        "/check-rfc-efos-batch",
        json={"rfcs": ["TEST010101TEST"]},
        headers={"Authorization": f"Bearer {TEST_TOKEN['token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1

def test_admin_operations_with_valid_token():
    # Get admin auth headers
    headers = get_basic_auth_header(TEST_SUPERADMIN["username"], TEST_SUPERADMIN["password"])
    
    # Test creating new API token
    new_token = {
        "description": "New Test Token"
    }
    response = client.post("/admin/tokens", json=new_token, headers=headers)
    assert response.status_code == 200
    token_id = response.json()["id"]
    
    # Test listing tokens
    response = client.get("/admin/tokens", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["tokens"]) > 0
    
    # Test getting specific token
    response = client.get(f"/admin/tokens/{token_id}", headers=headers)
    assert response.status_code == 200
    
    # Test updating token
    update_data = {"description": "Updated Description"}
    response = client.put(f"/admin/tokens/{token_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["description"] == "Updated Description"
    
    # Test regenerating token
    response = client.post(f"/admin/tokens/{token_id}/regenerate", headers=headers)
    assert response.status_code == 200
    assert "token" in response.json()
    
    # Test creating new superadmin
    new_admin = {
        "username": "new_admin",
        "password": "new_password"
    }
    response = client.post("/admin/superadmins", json=new_admin, headers=headers)
    assert response.status_code == 200
    
    # Test updating admin password
    password_update = {
        "current_password": "new_password",
        "new_password": "updated_password"
    }
    response = client.put(
        f"/admin/superadmins/{new_admin['username']}/password",
        json=password_update,
        headers=headers
    )
    assert response.status_code == 200
    
    # Test deactivating admin
    response = client.delete(f"/admin/superadmins/{new_admin['username']}", headers=headers)
    assert response.status_code == 200
    
    # Test deleting token
    response = client.delete(f"/admin/tokens/{token_id}", headers=headers)
    assert response.status_code == 200

def test_update_efos_database_with_valid_token():
    # Get admin auth headers
    headers = get_basic_auth_header(TEST_SUPERADMIN["username"], TEST_SUPERADMIN["password"])
    response = client.post(
        "/update-efos-database",
        headers=headers,
        params={"run_in_background": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "message" in data

if __name__ == "__main__":
    pytest.main(["-v", "test_main.py"]) 