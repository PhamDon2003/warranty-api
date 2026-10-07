import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models import Customer, Dealer, Product, Serial, User


@pytest.fixture
def auth_tokens(client: TestClient, db_session: Session) -> dict[str, str]:
    dealer = Dealer(name="Đại lý Phân Phối", phone="0912345678", address="Hà Nội")
    db_session.add(dealer)
    db_session.commit()

    admin = User(
        email="admin_crud@test.com",
        password_hash=get_password_hash("AdminPass123!"),
        role="admin",
        dealer_id=None,
        is_active=True,
    )
    dealer_user = User(
        email="dealer_crud@test.com",
        password_hash=get_password_hash("DealerPass123!"),
        role="dealer",
        dealer_id=dealer.id,
        is_active=True,
    )
    db_session.add_all([admin, dealer_user])
    db_session.commit()

    admin_token = client.post(
        "/auth/login", json={"email": "admin_crud@test.com", "password": "AdminPass123!"}
    ).json()["access_token"]
    dealer_token = client.post(
        "/auth/login", json={"email": "dealer_crud@test.com", "password": "DealerPass123!"}
    ).json()["access_token"]

    return {
        "admin": admin_token,
        "dealer": dealer_token,
        "dealer_id": str(dealer.id),
    }


def test_product_crud_and_referential_integrity(
    client: TestClient, db_session: Session, auth_tokens: dict[str, str]
) -> None:
    admin_hdr = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    dealer_hdr = {"Authorization": f"Bearer {auth_tokens['dealer']}"}

    # 1. Dealer tries to create product -> 403
    res = client.post(
        "/products",
        json={"code": "PROD-1", "name": "Máy ảnh", "warranty_months": 12},
        headers=dealer_hdr,
    )
    assert res.status_code == 403

    # 2. Admin creates product -> 201
    res = client.post(
        "/products",
        json={"code": "PROD-1", "name": "Máy ảnh", "warranty_months": 12},
        headers=admin_hdr,
    )
    assert res.status_code == 201
    prod_data = res.json()
    prod_id = prod_data["id"]
    assert prod_data["code"] == "PROD-1"

    # 3. Duplicate code -> 409
    res_dup = client.post(
        "/products",
        json={"code": "PROD-1", "name": "Máy ảnh 2", "warranty_months": 12},
        headers=admin_hdr,
    )
    assert res_dup.status_code == 409

    # 4. warranty_months <= 0 -> 422
    res_invalid = client.post(
        "/products",
        json={"code": "PROD-INVALID", "name": "Invalid", "warranty_months": 0},
        headers=admin_hdr,
    )
    assert res_invalid.status_code == 422

    # 5. List products with pagination
    res_list = client.get("/products?page=1&size=10", headers=dealer_hdr)
    assert res_list.status_code == 200
    page_data = res_list.json()
    assert "items" in page_data
    assert page_data["total"] >= 1
    assert page_data["page"] == 1
    assert page_data["size"] == 10

    # 6. Delete product referenced by serial -> 409
    serial = Serial(serial_no="SN-REF-PROD", product_id=prod_id, status="in_stock")
    db_session.add(serial)
    db_session.commit()

    del_res = client.delete(f"/products/{prod_id}", headers=admin_hdr)
    assert del_res.status_code == 409
    assert "referenced by serials" in del_res.json()["detail"].lower()

    # 7. Delete unreferenced product -> 204
    db_session.delete(serial)
    db_session.commit()

    del_ok = client.delete(f"/products/{prod_id}", headers=admin_hdr)
    assert del_ok.status_code == 204


def test_dealer_crud_and_referential_integrity(
    client: TestClient, db_session: Session, auth_tokens: dict[str, str]
) -> None:
    admin_hdr = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    dealer_hdr = {"Authorization": f"Bearer {auth_tokens['dealer']}"}

    # 1. Dealer cannot create dealer -> 403
    res_forbidden = client.post(
        "/dealers", json={"name": "Đại lý mới"}, headers=dealer_hdr
    )
    assert res_forbidden.status_code == 403

    # 2. Admin creates dealer -> 201
    res_create = client.post(
        "/dealers",
        json={"name": "Đại lý Đà Nẵng", "phone": "0236123456", "address": "Hải Châu"},
        headers=admin_hdr,
    )
    assert res_create.status_code == 201
    dealer_id = res_create.json()["id"]

    # 3. Delete dealer referenced by user -> 409
    existing_dealer_id = int(auth_tokens["dealer_id"])
    del_user_ref = client.delete(f"/dealers/{existing_dealer_id}", headers=admin_hdr)
    assert del_user_ref.status_code == 409
    assert "referenced by serials or users" in del_user_ref.json()["detail"].lower()

    # 4. Delete unreferenced dealer -> 204
    del_ok = client.delete(f"/dealers/{dealer_id}", headers=admin_hdr)
    assert del_ok.status_code == 204


def test_customer_crud_and_search(
    client: TestClient, db_session: Session, auth_tokens: dict[str, str]
) -> None:
    admin_hdr = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    dealer_hdr = {"Authorization": f"Bearer {auth_tokens['dealer']}"}

    # 1. Dealer can create customer -> 201
    res_create = client.post(
        "/customers",
        json={"name": "Trần Thị B", "phone": "0911222333", "email": "b@example.com"},
        headers=dealer_hdr,
    )
    assert res_create.status_code == 201
    cust_id = res_create.json()["id"]

    # 2. Search customers by name or phone
    res_search = client.get("/customers?q=0911222", headers=dealer_hdr)
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1
    assert res_search.json()["items"][0]["name"] == "Trần Thị B"

    # 3. Dealer cannot delete customer -> 403
    res_del_forbidden = client.delete(f"/customers/{cust_id}", headers=dealer_hdr)
    assert res_del_forbidden.status_code == 403

    # 4. Delete customer referenced by serial -> 409
    prod = Product(code="P-CUST-TEST", name="Test Prod", warranty_months=12)
    db_session.add(prod)
    db_session.commit()

    serial = Serial(
        serial_no="SN-CUST-REF",
        product_id=prod.id,
        customer_id=cust_id,
        status="activated",
    )
    db_session.add(serial)
    db_session.commit()

    res_del_ref = client.delete(f"/customers/{cust_id}", headers=admin_hdr)
    assert res_del_ref.status_code == 409
    assert "referenced by serials" in res_del_ref.json()["detail"].lower()

    # 5. Delete unreferenced customer -> 204
    db_session.delete(serial)
    db_session.commit()

    res_del_ok = client.delete(f"/customers/{cust_id}", headers=admin_hdr)
    assert res_del_ok.status_code == 204

