import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.database import Base, engine
from app.models import Tenant, User
from app.auth import get_password_hash


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Setup test database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Get authentication headers"""
    # Login
    response = await client.post(
        "/auth/login",
        json={"email": "admin@financeiro.com", "password": "admin123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login"""
    response = await client.post(
        "/auth/login",
        json={"email": "admin@financeiro.com", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials"""
    response = await client.post(
        "/auth/login",
        json={"email": "wrong@email.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_employee(client: AsyncClient, auth_headers):
    """Test employee creation"""
    response = await client.post(
        "/employees",
        headers=auth_headers,
        json={
            "name": "João Silva",
            "role_name": "Desenvolvedor",
            "regime": "CLT",
            "cost_center": "TI"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "João Silva"
    assert data["regime"] == "CLT"


@pytest.mark.asyncio
async def test_list_employees(client: AsyncClient, auth_headers):
    """Test employee listing"""
    response = await client.get("/employees", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_competency(client: AsyncClient, auth_headers):
    """Test competency creation"""
    # First create an employee
    emp_response = await client.post(
        "/employees",
        headers=auth_headers,
        json={
            "name": "Maria Santos",
            "role_name": "Analista",
            "regime": "CLT"
        }
    )
    employee_id = emp_response.json()["id"]
    
    # Create competency
    response = await client.post(
        "/competencies",
        headers=auth_headers,
        json={
            "employee_id": employee_id,
            "year": 2025,
            "month": 12
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == employee_id
    assert data["year"] == 2025
    assert data["month"] == 12


@pytest.mark.asyncio
async def test_competency_summary(client: AsyncClient, auth_headers):
    """Test competency summary"""
    # Create employee and competency
    emp_response = await client.post(
        "/employees",
        headers=auth_headers,
        json={"name": "Test User", "role_name": "Test", "regime": "CLT"}
    )
    employee_id = emp_response.json()["id"]
    
    comp_response = await client.post(
        "/competencies",
        headers=auth_headers,
        json={"employee_id": employee_id, "year": 2025, "month": 12}
    )
    competency_id = comp_response.json()["id"]
    
    # Get summary
    response = await client.get(
        f"/competencies/{competency_id}/summary",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_previsto" in data
    assert "total_pago" in data
    assert "saldo_a_pagar" in data


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test unauthorized access"""
    response = await client.get("/employees")
    assert response.status_code == 401
