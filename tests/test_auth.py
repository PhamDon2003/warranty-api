from datetime import timedelta
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.dependencies import require_admin, require_dealer_or_admin
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Dealer, User

# Helper router to test role dependencies
test_role_router = APIRouter(prefix="/test-roles")


@test_role_router.get("/admin-only")
def admin_only_endpoint(user: User = Depends(require_admin)):
    return {"message": "Hello Admin", "role": user.role}


@test_role_router.get("/dealer-or-admin")
def dealer_or_admin_endpoint(user: User = Depends(require_dealer_or_admin)):
    return {"message": "Hello", "role": user.role}


app.include_router(test_role_router)


@pytest.fixture
def seed_users(db_session: Session) -> dict[str, User]:
    dealer = Dealer(name="Đại lý Auth Test", phone="0123456789", address="Hà Nội")
    db_session.add(dealer)
    db_session.commit()

    admin = User(
        email="admin@test.com",
        password_hash=get_password_hash("AdminPass123!"),
        role="admin",
        dealer_id=None,
        is_active=True,
    )
    dealer_user = User(
        email="dealer@test.com",
        password_hash=get_password_hash("DealerPass123!"),
        role="dealer",
        dealer_id=dealer.id,
        is_active=True,
    )
    inactive_user = User(
        email="inactive@test.com",
        password_hash=get_password_hash("Pass123!"),
        role="dealer",
        dealer_id=dealer.id,
        is_active=False,
    )
    db_session.add_all([admin, dealer_user, inactive_user])
    db_session.commit()
    return {"admin": admin, "dealer": dealer_user, "inactive": inactive_user}


def test_login_success(client: TestClient, seed_users: dict[str, User]) -> None:
    res = client.post("/auth/login", json={"email": "admin@test.com", "password": "AdminPass123!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, seed_users: dict[str, User]) -> None:
    res = client.post("/auth/login", json={"email": "admin@test.com", "password": "WrongPassword"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_email(client: TestClient, seed_users: dict[str, User]) -> None:
    res = client.post("/auth/login", json={"email": "notfound@test.com", "password": "Password123!"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_login_inactive_user(client: TestClient, seed_users: dict[str, User]) -> None:
    res = client.post("/auth/login", json={"email": "inactive@test.com", "password": "Pass123!"})
    assert res.status_code == 400
    assert res.json()["detail"] == "Inactive user"


def test_get_me_success(client: TestClient, seed_users: dict[str, User]) -> None:
    login_res = client.post("/auth/login", json={"email": "dealer@test.com", "password": "DealerPass123!"})
    token = login_res.json()["access_token"]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "dealer@test.com"
    assert data["role"] == "dealer"
    assert data["dealer_id"] == seed_users["dealer"].dealer_id


def test_get_me_unauthorized(client: TestClient) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_get_me_expired_token(client: TestClient) -> None:
    expired_token = create_access_token(
        data={"sub": "admin@test.com"},
        expires_delta=timedelta(minutes=-10),  # expired 10 minutes ago
    )
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_role_permissions(client: TestClient, seed_users: dict[str, User]) -> None:
    # 1. Dealer token
    dealer_token = client.post(
        "/auth/login", json={"email": "dealer@test.com", "password": "DealerPass123!"}
    ).json()["access_token"]

    # Dealer accesses admin endpoint -> 403 Forbidden
    res_admin = client.get(
        "/test-roles/admin-only", headers={"Authorization": f"Bearer {dealer_token}"}
    )
    assert res_admin.status_code == 403
    assert "Admin role required" in res_admin.json()["detail"]

    # Dealer accesses dealer-or-admin endpoint -> 200 OK
    res_dealer = client.get(
        "/test-roles/dealer-or-admin", headers={"Authorization": f"Bearer {dealer_token}"}
    )
    assert res_dealer.status_code == 200
    assert res_dealer.json()["role"] == "dealer"

    # 2. Admin token
    admin_token = client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "AdminPass123!"}
    ).json()["access_token"]

    # Admin accesses admin endpoint -> 200 OK
    res_admin_ok = client.get(
        "/test-roles/admin-only", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin_ok.status_code == 200
    assert res_admin_ok.json()["role"] == "admin"
